
"""
Entrypoint for running the anomaly detection pipeline from the domain layer.
"""

from .feature_engineering import TimestampProcessor, SpatialIndexer, Aggregator, FeatureEngineer, SpatialPreprocessor
from .anomaly_detection import AnomalyDetector, Evaluator
from .visualization import Visualizer
from .services import run_pipeline
from .data_loader import extract_and_concat_uber_csvs
import pandas as pd
import sys
import os


def main():
    # If a directory is provided, auto-detect and process Uber CSVs (zipped or unzipped)
    if len(sys.argv) < 2:
        print("Usage: python -m anomaly_detector.domain <data_dir>")
        sys.exit(1)
    data_dir = sys.argv[1]
    if not os.path.exists(data_dir):
        print(f"Directory not found: {data_dir}")
        sys.exit(1)
    print(f"Detecting and loading Uber NYC trip data from {data_dir} ...")
    df = extract_and_concat_uber_csvs(data_dir)
    print(f"Loaded {len(df)} rows. Running pipeline...")
    results = run_pipeline(df)
    print("Pipeline complete.")
    # Optionally print summary
    if results and len(results) > 0:
        df_processed = results[0]
        print("Processed DataFrame head:")
        print(df_processed.head())

if __name__ == "__main__":
    main()
