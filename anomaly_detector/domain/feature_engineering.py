
"""
Feature engineering and transformation logic (from h3_uber.py)
"""

import h3
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors


class TimestampProcessor:
    """Handle timestamp processing."""
    def __init__(self, datetime_col: str = 'timestamp'):
        self.datetime_col = datetime_col

    def floor_to_hour(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df[self.datetime_col] = pd.to_datetime(df[self.datetime_col])
        df['timestamp_hour'] = df[self.datetime_col].dt.floor('H')
        return df


class SpatialIndexer:
    """Assign H3 indices and compute centroids."""
    def __init__(self, lat_col: str = 'lat', lon_col: str = 'lon', resolution: int = 7):
        self.lat_col = lat_col
        self.lon_col = lon_col
        self.resolution = resolution

    def add_h3_index(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['h3_index'] = df.apply(lambda row: h3.latlng_to_cell(row[self.lat_col], row[self.lon_col], self.resolution), axis=1)
        return df

    def compute_centroids(self, h3_indexes: pd.Series) -> pd.DataFrame:
        centroids = []
        for idx in h3_indexes:
            lat, lon = h3.cell_to_latlng(idx)
            centroids.append({'h3_index': idx, 'centroid_lat': lat, 'centroid_lon': lon})
        return pd.DataFrame(centroids)


class Aggregator:
    """Aggregate counts per hour and H3 cell."""
    def __init__(self, time_col: str = 'timestamp_hour', h3_col: str = 'h3_index', value_col: str = 'value'):
        self.time_col = time_col
        self.h3_col = h3_col
        self.value_col = value_col

    def aggregate_hourly(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df[self.time_col] = pd.to_datetime(df[self.time_col])
        agg = df.groupby([self.time_col, self.h3_col]).agg(
            **{self.value_col: (self.h3_col, 'count')}
        ).reset_index().rename(columns={self.time_col: 'timestamp'})
        all_hours = pd.date_range(start=agg['timestamp'].min(), end=agg['timestamp'].max(), freq='H')
        all_cells = agg[self.h3_col].unique()
        mi = pd.MultiIndex.from_product([all_hours, all_cells], names=['timestamp', self.h3_col])
        full = pd.DataFrame(index=mi).reset_index()
        full = full.merge(agg, how='left', on=['timestamp', self.h3_col])
        full[self.value_col] = full[self.value_col].fillna(0)
        return full


class FeatureEngineer:
    """Add time features, lags, and rolling stats."""
    def __init__(self, rolling_window: int = 24, time_col: str = 'timestamp', value_col: str = 'value', group_col: str = 'h3_index'):
        self.rolling_window = rolling_window
        self.time_col = time_col
        self.value_col = value_col
        self.group_col = group_col

    def add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['Weekday'] = df[self.time_col].dt.day_name()
        df['Hour'] = df[self.time_col].dt.hour
        df['Day'] = df[self.time_col].dt.dayofweek
        df['Month_day'] = df[self.time_col].dt.day
        df['Month'] = df[self.time_col].dt.month
        df['Year'] = df[self.time_col].dt.year
        return df

    def add_lag_and_rolling(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = df.sort_values([self.group_col, self.time_col])
        df['Lag'] = df.groupby(self.group_col)[self.value_col].shift(1).fillna(0)
        df['Rolling_Mean'] = (
            df.groupby(self.group_col)[self.value_col]
            .rolling(window=self.rolling_window, min_periods=1)
            .mean()
            .reset_index(level=0, drop=True)
        )
        return df

    def add_cyclic_features(self, df: pd.DataFrame, drop_original: bool = True) -> pd.DataFrame:
        df_encoded = df.copy()
        df_encoded[self.time_col] = pd.to_datetime(df_encoded[self.time_col])
        ts = df_encoded[self.time_col].dt
        df_encoded['hour_sin'] = np.sin(2 * np.pi * ts.hour / 24)
        df_encoded['hour_cos'] = np.cos(2 * np.pi * ts.hour / 24)
        df_encoded['dow_sin'] = np.sin(2 * np.pi * ts.dayofweek / 7)
        df_encoded['dow_cos'] = np.cos(2 * np.pi * ts.dayofweek / 7)
        df_encoded['month_sin'] = np.sin(2 * np.pi * (ts.month - 1) / 12)
        df_encoded['month_cos'] = np.cos(2 * np.pi * (ts.month - 1) / 12)
        if drop_original:
            cols_to_drop = ['Hour', 'Day', 'Month_day', 'Month']
            for col in cols_to_drop:
                if col in df_encoded.columns:
                    df_encoded = df_encoded.drop(columns=[col])
        return df_encoded


class SpatialPreprocessor:
    """Prepare spatial features for anomaly detection."""
    def __init__(self, lat_col: str = 'lat', lon_col: str = 'lon'):
        self.lat_col = lat_col
        self.lon_col = lon_col
        self.scaler = None
        self.mean_lat = None
        self.mean_lon = None

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        self.mean_lat = df[self.lat_col].mean()
        self.mean_lon = df[self.lon_col].mean()
        mean_lat_rad = np.deg2rad(self.mean_lat)
        lat_to_m = 110574
        lon_to_m = 111320 * np.cos(mean_lat_rad)
        df['x'] = (df[self.lon_col] - self.mean_lon) * lon_to_m
        df['y'] = (df[self.lat_col] - self.mean_lat) * lat_to_m
        self.scaler = StandardScaler()
        df[['x_scaled', 'y_scaled']] = self.scaler.fit_transform(df[['x', 'y']])
        return df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if self.mean_lat is None or self.scaler is None:
            raise ValueError("SpatialPreprocessor not fitted. Call fit_transform first.")
        mean_lat_rad = np.deg2rad(self.mean_lat)
        lat_to_m = 110574
        lon_to_m = 111320 * np.cos(mean_lat_rad)
        df['x'] = (df[self.lon_col] - self.mean_lon) * lon_to_m
        df['y'] = (df[self.lat_col] - self.mean_lat) * lat_to_m
        df[['x_scaled', 'y_scaled']] = self.scaler.transform(df[['x', 'y']])
        return df

    def compute_local_density(self, df: pd.DataFrame, n_neighbors: int = 5) -> pd.Series:
        coords = df[['x_scaled', 'y_scaled']].values
        neigh = NearestNeighbors(n_neighbors=n_neighbors + 1)
        neigh.fit(coords)
        distances, _ = neigh.kneighbors(coords)
        kth_dist = distances[:, -1]
        eps = 1e-6
        density = 1.0 / (kth_dist + eps)
        return pd.Series(density, index=df.index)
