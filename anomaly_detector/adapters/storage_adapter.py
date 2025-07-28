"""
StorageAdapter implements StoragePort for reading/writing parquet and uploading to S3.
"""

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import boto3
import os
from anomaly_detector.domain.ports import StoragePort



class StorageAdapter(StoragePort):
    def __init__(self, s3_bucket=None, aws_access_key=None, aws_secret_key=None):
        self.s3_bucket = s3_bucket
        self.s3 = None
        if s3_bucket and aws_access_key and aws_secret_key:
            self.s3 = boto3.client(
                's3',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key
            )

    def read(self, path: str) -> pd.DataFrame:
        return pd.read_parquet(path)

    def write(self, df: pd.DataFrame, path: str):
        table = pa.Table.from_pandas(df)
        pq.write_table(table, path)

    def list_partitions(self, base_dir: str):
        return [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]

    def list_files(self, base_dir: str):
        files = []
        for root, _, filenames in os.walk(base_dir):
            for f in filenames:
                files.append(os.path.join(root, f))
        return files

    def upload(self, local_path: str, s3_key: str):
        if self.s3:
            self.s3.upload_file(local_path, self.s3_bucket, s3_key)
        else:
            raise RuntimeError("S3 client not configured.")
