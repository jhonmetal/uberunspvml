
import json
from polars import DataFrame, Date, col, concat_list, lit, Utf8
from ...infrastructure import TripsRepository
from ...utils import enum

class TripsService:

    async def get_trips(self, date_code:str):

        cols = ["timestamp","centroid_lat","centroid_lon","type_code","value"]
        df_anomalous = await TripsRepository().get_trips(enum.TYPE_TRIP.Anomalous.value, date_code)
        df_anomalous = df_anomalous.with_columns( type_code = lit(enum.TYPE_TRIP.Anomalous.value, Utf8))
        df_anomalous = df_anomalous.select(cols)
        df_anomalous = df_anomalous.rename({
            "timestamp":"time_index",
            "centroid_lat": "latitud",
            "centroid_lon": "longitud",
            "value":"data"
        })

        df_non_anomalous = await TripsRepository().get_trips(enum.TYPE_TRIP.NoAnomalous.value, date_code)
        df_non_anomalous = df_non_anomalous.with_columns( type_code = lit(enum.TYPE_TRIP.NoAnomalous.value, Utf8))
        df_non_anomalous = df_non_anomalous.select(cols)
        df_non_anomalous = df_non_anomalous.rename({
            "timestamp":"time_index",
            "centroid_lat": "latitud",
            "centroid_lon": "longitud",
            "value":"data"
        })

       
        df_data:DataFrame = df_anomalous.extend(df_non_anomalous)
        df_data = df_data.with_columns( data = concat_list(["latitud","longitud"]))
        df_data = df_data.group_by("type_code","time_index").agg("data")

        dict_anomalous =  df_data.filter(col("type_code") == enum.TYPE_TRIP.Anomalous.value).select("time_index","data").to_dict()
        dict_non_anomalous = df_data.filter(col("type_code") == enum.TYPE_TRIP.NoAnomalous.value).select("time_index","data").to_dict()

        dict_anomalous = {k: v.to_list() for k, v in dict_anomalous.items()}
        dict_non_anomalous = {k: v.to_list() for k, v in dict_non_anomalous.items()}

        data_js = {}
        data_js[enum.TYPE_TRIP.Anomalous.value] =  dict_anomalous
        data_js[enum.TYPE_TRIP.NoAnomalous.value] = dict_non_anomalous

        return data_js
    

    async def get_indicators(self, date_code:str):

        df_indicators = await TripsRepository().get_indicators()
 
        df_indicators = df_indicators.sort(["date"], descending=[True])
        df_indicators = df_indicators.filter(col("date") <= lit(date_code).str.strptime(Date))

        data_js = {}
        data_js["date"] = date_code
        data_js["total_trips"] = None
        data_js["total_anomalies"] = None
        data_js["increased_demand_pct"] = None
        data_js["hot_location"] = None
        data_js["rush_hour"] = None

        if df_indicators.height > 0:
            df_indicators = df_indicators.head(7)
        
            df_indicators_sum = df_indicators.select([
                            col("sum_trips").sum().alias("total_trips")
                            ,col("sum_anomalies").sum().alias("total_anomalies")
                            ,col("increased_demand_pct").mean().alias("increased_demand_pct")
                        ])

            df_indicators_max = df_indicators.sort(["sum_trips"], descending=[True])
            df_indicators_max = df_indicators_max.head(1)
            df_indicators_max = df_indicators_max.select("hot_location","rush_hour")
                    

            data_js["total_trips"] = df_indicators_sum[0]["total_trips"].item()
            data_js["total_anomalies"] = df_indicators_sum[0]["total_anomalies"].item()
            data_js["increased_demand_pct"] = df_indicators_sum[0]["increased_demand_pct"].item()
            data_js["hot_location"] = df_indicators_max[0]["hot_location"].item()
            data_js["rush_hour"] = df_indicators_max[0]["rush_hour"].item()

        return data_js
    

    async def get_summary_trips(self, date_code:str):

        df_indicators = await TripsRepository().get_indicators()
 
        df_indicators = df_indicators.sort(["date"], descending=[True])
        df_indicators = df_indicators.filter(col("date") <= lit(date_code).str.strptime(Date))

        data_js = []
        if df_indicators.height > 0:
            df_indicators = df_indicators.head(7)
        
            df_indicators = df_indicators.with_columns(
                total_normal = col("sum_trips") - col("sum_anomalies")
            )

            df_indicators = df_indicators.rename({
                "sum_anomalies": "total_anomalies"
            })

            df_indicators = df_indicators.select("date","total_normal","total_anomalies")

            data_js = df_indicators.to_dicts()
            

        return data_js
    