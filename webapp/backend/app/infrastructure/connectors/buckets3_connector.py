import boto3
import json
from os import environ
from polars import DataFrame,read_parquet,read_csv
from typing import Sequence
from .parse_connector import *
import io

class BucketS3Connector:
    def __init__(self, envBucket):
        
        parse = ParseConnector(envBucket)
        parsecnx = parse.get_cnx()
        self.conn = boto3.client(parsecnx["host"]
                        ,region_name=parsecnx["port"]
                        ,aws_access_key_id=parsecnx["user"]
                        ,aws_secret_access_key=parsecnx["password"]
                        )
        self.bucketName = parsecnx["database"]

    def get_text_object(self,s3_key):            
        response = self.conn.get_object(Bucket=self.bucketName, Key=s3_key)
        data_text = response['Body'].read().decode("utf-8")
        return data_text
    
    def get_json_object(self,s3_key):
        response = self.conn.get_object(Bucket=self.bucketName, Key=s3_key)
        data_json = json.load(response['Body'])
        return data_json

    def get_df_parquet_object(self,s3_key):
        s3_keys = [s3_key]
        if(s3_key.endswith("/")):
            '''
                filer parquet files from s3_key        
            '''
            objects  = self.conn.list_objects_v2(Bucket=self.bucketName, Prefix=s3_key)
            s3_keys = [item['Key'] for item in objects ['Contents'] if item['Key'].endswith('.parquet')]
            if not s3_keys:
                raise Exception('No parquet found in'+ s3_key)
            
        '''
            read parquet files from s3_keys
        '''
        
        df:DataFrame = None

        for s3_key in s3_keys:
            response = self.conn.get_object(Bucket=self.bucketName, Key=s3_key)
            response = io.BytesIO(response['Body'].read())

            if(df is None):
                df = read_parquet(response)
            else:
                df = df.vstack(read_parquet(response))

        return df
    