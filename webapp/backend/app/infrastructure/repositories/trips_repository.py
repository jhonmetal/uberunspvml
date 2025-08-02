from ..connectors.buckets3_connector import BucketS3Connector
from polars import DataFrame

class TripsRepository:

    def __init__(self) -> None:
        self.bucket = BucketS3Connector("BUCKET_UBER")

    async def get_trips(self, type_code:str, date_code:str) -> DataFrame:
        data = self.bucket.get_df_parquet_object(f"trips_uber/type_code={type_code}/date_code={date_code}/")
        
        return data
    
    async def get_indicators(self) -> DataFrame:
        data = self.bucket.get_df_parquet_object(f"trips_uber_summary/indicators.parquet")
        
        return data