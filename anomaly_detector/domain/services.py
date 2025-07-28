
"""
Domain services for anomaly detection pipeline (Hexagonal Architecture)
"""

import os
import yaml
import pandas as pd
from .feature_engineering import TimestampProcessor, SpatialIndexer, Aggregator, FeatureEngineer, SpatialPreprocessor
from .anomaly_detection import AnomalyDetector, Evaluator
from anomaly_detector.adapters.ml_adapter import MLflowAdapter
from .visualization import Visualizer


def run_pipeline(raw_df: pd.DataFrame, hex_resolution: int = 7, rolling_window: int = 168, model_features=None, contamination: float = 0.22, n_estimators: int = 50, max_samples: float = 0.25, parquet_layer: str = "gold", storage_adapter=None):
    if model_features is None:
        model_features = ['value', 'Lag', 'Rolling_Mean', 'hour_sin', 'hour_cos', 'dow_sin', 'month_sin', 'month_cos']
    # Given raw_df with columns ['Date/Time', 'Lat', 'Lon'], rename to standard cols:
    raw_df = raw_df.rename(columns={'Date/Time': 'timestamp', 'Lat': 'lat', 'Lon': 'lon'})    
    # 1. Timestamp processing
    ts_proc = TimestampProcessor(datetime_col='timestamp')
    df_ts = ts_proc.floor_to_hour(raw_df)
    # 2. Spatial indexing
    indexer = SpatialIndexer(lat_col='lat', lon_col='lon', resolution=hex_resolution)
    df_indexed = indexer.add_h3_index(df_ts)
    centroids = indexer.compute_centroids(df_indexed['h3_index'].unique())
    # 3. Aggregate hourly
    aggregator = Aggregator(time_col='timestamp_hour', h3_col='h3_index', value_col='value')
    df_agg = aggregator.aggregate_hourly(df_indexed)
    df_agg = df_agg.merge(centroids, how='left', on='h3_index')
    # 4. Feature engineering
    fe = FeatureEngineer(rolling_window=rolling_window, time_col='timestamp', value_col='value', group_col='h3_index')
    df_feat_result = fe.add_time_features(df_agg)
    df_feat_result = df_feat_result[df_feat_result['value'] > 0]
    df_feat_result = fe.add_lag_and_rolling(df_feat_result)
    df_feat = fe.add_cyclic_features(df_feat_result, drop_original=False)
    # 5. Anomaly detection with MLflow experiment tracking
    mlflow_config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "train.yaml")
    with open(mlflow_config_path, "r") as f:
        train_config = yaml.safe_load(f)
    mlflow_experiment = train_config.get("mlflow_experiment", "Uber_Anomaly_Detection_NY_City_Trips")
    mlflow_tracking_uri = train_config.get("mlflow_tracking_uri", None)
    ml_adapter = MLflowAdapter(experiment_name=mlflow_experiment, tracking_uri=mlflow_tracking_uri)
    ad = AnomalyDetector(feature_cols=model_features, contamination=contamination, n_estimators=n_estimators, max_samples=max_samples)
    df_processed, X_train = ad.fit(df_feat)
    # Log all params, metrics, model, and artifacts in a single MLflow run
    ml_adapter.log_run(
        sk_model=ad.model,
        params={
            "hex_resolution": hex_resolution,
            "rolling_window": rolling_window,
            "model_features": model_features,
            "contamination": contamination,
            "n_estimators": n_estimators,
            "max_samples": max_samples
        },
        metrics={
            "num_rows": len(df_processed),
            "num_anomalies": df_processed["is_anomaly"].sum(),
            "mv_area": getattr(ad, "mv_area", None),
            "em_area": getattr(ad, "em_area", None)
        },
        artifacts=[ad.preproc_path, ad.scaler_path, ad.curves_csv, ad.sample_csv],
        input_example=ad.input_example,
        signature=ad.signature,
        registered_model_name='UberAnomalyIForest'
    )
    # 6. Summarize
    summarize_df = ad.summarize(df_processed)
    # 7. Parquet layering
    config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "parquet_layers.yaml")
    with open(config_path, "r") as f:
        layers_config = yaml.safe_load(f)
    # Get base_dir for selected parquet_layer
    layer_info = layers_config["layers"].get(parquet_layer, {})
    base_dir = layer_info.get("path", f"trips_uber_{parquet_layer}")
    # Get summary_dir and gold_summary_path from gold_summary config
    gold_summary_cfg = layers_config["layers"].get("gold_summary", {})
    print("Gold Summary Config:", gold_summary_cfg)
    gold_summary_path = gold_summary_cfg.get("path", None)
    summary_dir = os.path.dirname(gold_summary_path) if gold_summary_path else f"{base_dir}_summarize"
    ad.save_partitioned_parquet(
        df_processed,
        summarize_df,
        base_dir=base_dir,
        anomaly_col='is_anomaly',
        time_col='timestamp',
        summary_path=gold_summary_path
    )
    # 8. S3 upload (if adapter provided)
    if storage_adapter:
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                local_path = os.path.join(root, file)
                s3_key = os.path.relpath(local_path, base_dir)
                storage_adapter.upload(local_path, s3_key)
        # Also upload indicators.parquet (summary) to gold_summary path from config
        indicators_path = os.path.join(summary_dir, "indicators.parquet")
        if os.path.exists(indicators_path) and gold_summary_path:
            storage_adapter.upload(indicators_path, gold_summary_path)
    # 9. Visualization (optional)
    viz = Visualizer(df_feat.assign(is_anomaly=df_processed['is_anomaly']))
    return df_processed, X_train, viz, ad
