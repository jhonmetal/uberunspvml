

"""
Anomaly detection logic (Isolation Forest, evaluation, etc.)
"""
import pandas as pd
import numpy as np
import pickle
import yaml
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from mlflow.models import infer_signature
from .feature_engineering import SpatialPreprocessor
from anomaly_detector.kernel import ensure_dir
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from shapely.geometry import Point
import geopandas as gpd
import requests


class Evaluator:
    """
    Evaluates anomaly detection results using Mass-Volume (MV) and Excess-Mass (EM) curves.
    """
    def __init__(self):
        self.mv_em_curves = None

    def approximate_mv_em_curves(self, real_scores: np.ndarray, random_scores: np.ndarray, n_thresholds=100) -> pd.DataFrame:
        combined = np.concatenate([real_scores, random_scores])
        t_min, t_max = np.min(combined), np.max(combined)
        thresholds = np.linspace(t_min, t_max, n_thresholds)
        masses = []
        volumes = []
        ems = []
        n_real = len(real_scores)
        n_rand = len(random_scores)
        for t in thresholds:
            mass = np.sum(real_scores >= t) / n_real
            volume = np.sum(random_scores >= t) / n_rand
            em = mass - volume
            masses.append(mass)
            volumes.append(volume)
            ems.append(em)
        df = pd.DataFrame({
            'threshold': thresholds,
            'mass': masses,
            'volume': volumes,
            'em': ems
        })
        df = df.sort_values('threshold', ascending=False).reset_index(drop=True)
        self.mv_em_curves = df
        return df

    def sample_random_uniform(self, X: np.ndarray, n_samples=10000, random_state=42) -> np.ndarray:
        rng = np.random.RandomState(random_state)
        mins = X.min(axis=0)
        maxs = X.max(axis=0)
        random_samples = rng.uniform(low=mins, high=maxs, size=(n_samples, X.shape[1]))
        return random_samples


class AnomalyDetector:
    """Detect anomalies using IsolationForest with spatial features."""

    def __init__(self, feature_cols: list, contamination: float = 0.1, n_estimators: int = 100, max_samples: float = 0.7,
                 use_density: bool = True, density_neighbors: int = 5, random_state: int = 42, config_path: str = None):
        self.feature_cols = feature_cols
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.use_density = use_density
        self.density_neighbors = density_neighbors
        self.random_state = random_state
        self.spatial_preprocessor = SpatialPreprocessor(lat_col='centroid_lat', lon_col='centroid_lon')
        self.model = None
        self.evaluator = Evaluator()
        self.scaler = StandardScaler()
        self.mv_em_df = None
        self.mv_area = None
        self.em_area = None
        self.input_example = None
        self.signature = None
        self.df_proc_ = None

        # Load artifact file names from YAML config
        if config_path is None:
            config_path = str(Path(__file__).parent.parent / "configs" / "artifacts.yaml")
        try:
            with open(config_path, "r") as f:
                artifact_config = yaml.safe_load(f)
        except Exception:
            artifact_config = {}
        self.preproc_path = artifact_config.get("preproc_path", "spatial_preprocessor.pkl")
        self.scaler_path = artifact_config.get("scaler_path", "scaler.pkl")
        self.curves_csv = artifact_config.get("curves_csv", "mv_em_curves.csv")
        self.sample_csv = artifact_config.get("sample_csv", "processed_data_sample.csv")
        self.indicators_parquet = artifact_config.get("indicators_parquet", "indicators.parquet")

    def fit(self, df: pd.DataFrame):
        # 1. Spatial preprocessing
        df_proc = self.spatial_preprocessor.fit_transform(df)
        if self.use_density:
            df_proc['local_density'] = self.spatial_preprocessor.compute_local_density(df_proc, n_neighbors=self.density_neighbors)
        else:
            df_proc['local_density'] = np.nan
        # 2. Feature selection
        features = [col for col in self.feature_cols if col in df_proc.columns]
        features += ['x_scaled', 'y_scaled']
        if self.use_density:
            features.append('local_density')
        X = df_proc[features].fillna(0)
        # 3. Scaling
        X_scaled_array = self.scaler.fit_transform(X)
        X_scaled = pd.DataFrame(X_scaled_array, columns=X.columns, index=X.index)
        # 4. Model training
        self.model = IsolationForest(
            random_state=self.random_state,
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            max_samples=self.max_samples,
            n_jobs=-1
        )
        self.model.fit(X_scaled)
        df_proc['is_anomaly'] = pd.Series(self.model.predict(X_scaled)).apply(lambda x: 1 if x == -1 else 0).values
        df_proc['anomaly_score'] = self.model.decision_function(X_scaled)
        # 5. Evaluation
        real_scores = -df_proc['anomaly_score'].values
        random_X = self.evaluator.sample_random_uniform(X_scaled, n_samples=5000, random_state=self.random_state)
        random_scores = -self.model.decision_function(random_X)
        self.mv_em_df = self.evaluator.approximate_mv_em_curves(real_scores, random_scores, n_thresholds=100)
        self.mv_area = self.mv_em_df["mass"].sum()
        self.em_area = self.mv_em_df["em"].sum()
        # 6. Save artifacts to disk
        self.input_example = X_scaled.head(5)
        self.signature = infer_signature(X_scaled, self.model.predict(X_scaled))
        with open(self.preproc_path, 'wb') as f:
            pickle.dump(self.spatial_preprocessor, f)
        with open(self.scaler_path, 'wb') as f:
            pickle.dump(self.scaler, f)
        self.mv_em_df.to_csv(self.curves_csv, index=False)
        df_proc.head(100).to_csv(self.sample_csv, index=False)
        self.df_proc_ = df_proc
        return df_proc, X_scaled

    @staticmethod
    def summarize(df: pd.DataFrame) -> pd.DataFrame:
        """
        Summarizes anomaly results by date, rush hour, hot location, and demand increase.
        Downloads NYC Taxi Zones GeoJSON if missing.
        Returns a DataFrame with columns matching h3_uber.py logic.
        """
        # Ensure taxi_zones.geojson exists and is valid (not empty, not corrupt)
        geojson_url = "https://data.cityofnewyork.us/resource/8meu-9t5y.geojson"
        geojson_path = Path("resources") / "taxi_zones.geojson"
        if not geojson_path.parent.exists():
            geojson_path.parent.mkdir(parents=True, exist_ok=True)
        need_download = False
        # Check if file exists and is non-empty
        if not geojson_path.exists() or geojson_path.stat().st_size < 1000:
            need_download = True
        else:
            # Try to read file, if error or empty, re-download
            try:
                gdf = gpd.read_file(geojson_path)
                if gdf.empty or 'geometry' not in gdf.columns:
                    need_download = True
            except Exception:
                need_download = True
        if need_download:
            print(f"Downloading {geojson_url} to {geojson_path} ...")
            resp = requests.get(geojson_url)
            resp.raise_for_status()
            with open(geojson_path, "wb") as f:
                f.write(resp.content)
            print("Download complete.")
        # Load zones GeoDataFrame
        zones_gdf = gpd.read_file(geojson_path)[['zone', 'geometry']]

        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date

        # 1. Aggregate daily sums and rush hour
        daily = (
            df
            .groupby('date')
            .agg(
                sum_trips=('value', 'sum'),
                sum_anomalies=('is_anomaly', 'sum'),
                rush_hour=('Hour', lambda s: int(s.value_counts().idxmax()) if not s.empty else None)
            )
            .reset_index()
        )

        # 2. Determine hot location per day by max rolling mean
        hot = (
            df
            .loc[df.groupby('date')['value'].idxmax()]
            .loc[:, ['date', 'centroid_lon', 'centroid_lat']]
            .rename(columns={'centroid_lon': 'lon', 'centroid_lat': 'lat'})
        )
        hot['geometry'] = [Point(xy) for xy in zip(hot.lon, hot.lat)]
        hot_gdf = gpd.GeoDataFrame(hot, geometry='geometry', crs=zones_gdf.crs)
        joined = gpd.sjoin(hot_gdf, zones_gdf, how='left', predicate='within')
        hot['hot_location'] = joined['zone']
        hot = hot[['date', 'hot_location']]

        # 3. Merge daily with hot location
        daily = daily.merge(hot, on='date', how='left')

        # 4. Compute week-over-week increase: current 7-day sum vs previous 7-day
        daily = daily.sort_values('date')
        daily['trips_7d'] = daily['sum_trips'].rolling(window=7, min_periods=1).sum()
        daily['trips_7d_prev'] = daily['trips_7d'].shift(1)
        daily['increased_demand'] = daily['trips_7d'] - daily['trips_7d_prev']
        daily['increased_demand_pct'] = np.where(
            daily['trips_7d_prev'] == 0,
            0,
            (daily['increased_demand'] / daily['trips_7d_prev'] * 100).round(2)
        )

        # 5. Final selection
        df_final = daily[['date', 'sum_trips', 'sum_anomalies', 'rush_hour', 'hot_location', 'increased_demand_pct']]
        return df_final

    def save_partitioned_parquet(self,
                                 df: pd.DataFrame,
                                 df_summary: pd.DataFrame,
                                 base_dir: str,
                                 anomaly_col: str = 'is_anomaly',
                                 time_col: str = 'timestamp',
                                 summary_path: str = None):
        """
        Saves DataFrame to partitioned parquet files based on anomaly status and date.
        Also saves summary indicators.parquet (configurable) in a separate directory or path.
        """
        df = df.copy()
        df[time_col] = pd.to_datetime(df[time_col])
        df['date_code'] = df[time_col].dt.strftime('%Y-%m-%d')
        df['type_code'] = df[anomaly_col].apply(lambda x: 'anomalous' if x == 1 else 'non_anomalous')
        ensure_dir(Path(base_dir))
        pq.write_to_dataset(
            pa.Table.from_pandas(df),
            root_path=str(base_dir),
            partition_cols=['type_code', 'date_code'],
            basename_template='part-{i}.parquet'
        )
        # Save summary to the correct summary_path if provided, else fallback to old behavior
        if summary_path:
            summary_dir = Path(summary_path)
            ensure_dir(summary_dir)
            pq.write_table(
                pa.Table.from_pandas(df_summary),
                str(summary_dir / self.indicators_parquet)
            )
            print(f"Summary saved to {summary_dir / self.indicators_parquet}")
        else:
            fallback_dir = Path(f"{base_dir}_summarize")
            ensure_dir(fallback_dir)
            pq.write_table(
                pa.Table.from_pandas(df_summary),
                str(fallback_dir / self.indicators_parquet)
            )
            print(f"Summary saved to {fallback_dir / self.indicators_parquet}")
        print(f"Data saved to partitioned parquet in {base_dir}")
