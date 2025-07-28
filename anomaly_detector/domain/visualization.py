
"""
Visualization logic for hexmap, MV/EM curves, etc.
"""

import h3
import pandas as pd
import numpy as np
import folium
from folium import Map, CircleMarker, GeoJson
from folium.plugins import HeatMap
import ipywidgets as widgets
from IPython.display import display, clear_output
from matplotlib import pyplot as plt

class Visualizer:
    """Interactive visualization for H3 aggregated data and anomalies, with heatmap for normals."""
    def __init__(self, df: pd.DataFrame, time_col: str = 'timestamp', h3_col: str = 'h3_index', value_col: str = 'value', anomaly_col: str = 'is_anomaly'):
        self.df = df.copy()
        self.time_col = time_col
        self.h3_col = h3_col
        self.value_col = value_col
        self.anomaly_col = anomaly_col
        self.df[self.time_col] = pd.to_datetime(self.df[self.time_col])
        self.df['timestamp_hour'] = self.df[self.time_col].dt.floor('H')
        self.df['date_only'] = self.df['timestamp_hour'].dt.date

    def interactive_hexmap(self, resolution: int = 7):
        available_dates = sorted(self.df['date_only'].unique())
        if not available_dates:
            print("No timestamps available.")
            return
        start_date = min(available_dates)
        end_date = max(available_dates)
        date_picker = widgets.DatePicker(description='Select date', value=start_date, min=start_date, max=end_date)
        hour_slider = widgets.IntSlider(value=0, min=0, max=23, step=1, description='Hour', continuous_update=False)
        out = widgets.Output()

        def plot_for_selection(date, hour):
            ts = pd.Timestamp(date) + pd.Timedelta(hours=hour)
            df_sel = self.df[self.df['timestamp_hour'] == ts]
            with out:
                clear_output()
                if df_sel.empty:
                    print(f"No data for {ts}")
                    return
                center_lat = df_sel['centroid_lat'].mean() if 'centroid_lat' in df_sel.columns else df_sel['lat'].mean()
                center_lon = df_sel['centroid_lon'].mean() if 'centroid_lon' in df_sel.columns else df_sel['lon'].mean()
                m = Map(location=[center_lat, center_lon], zoom_start=12)
                max_count = df_sel[self.value_col].max()
                for _, row in df_sel.iterrows():
                    hex_idx = row[self.h3_col]
                    count = row[self.value_col]
                    boundary_latlon = h3.cell_to_boundary(hex_idx)
                    boundary_geojson = [[lon, lat] for lat, lon in boundary_latlon]
                    opacity = count / max_count if max_count > 0 else 0
                    def style_func(feature, op=opacity):
                        return {'fillColor': 'red', 'color': 'gray', 'weight': 1, 'fillOpacity': op * 0.8}
                    properties = {
                        'Weekday': row['Weekday'],
                        'Hour': row['Hour'],
                        'Day': row['Month_day'],
                        'Month': row['Month'],
                        'Value': row['value'],
                        'Outliers': row['is_anomaly']
                    }
                    geojson_feature = {
                        'type': 'Feature',
                        'geometry': {'type': 'Polygon', 'coordinates': [boundary_geojson]},
                        'properties': properties
                    }
                    tooltip = folium.GeoJsonTooltip(
                        fields=['Weekday', 'Hour', 'Day', 'Month', 'Value', 'Outliers'],
                        aliases=['Weekday:', 'Hour:', 'Day:', 'Month:', 'Value:', 'Outliers:'],
                        localize=True,
                        sticky=False,
                        labels=True,
                        style="""
                            background-color: #F0EFEF;
                            border: 2px solid black;
                            border-radius: 3px;
                            box-shadow: 3px;
                        """,
                        max_width=800,
                    )
                    gj = folium.GeoJson(
                        geojson_feature,
                        style_function=style_func,
                        tooltip=tooltip
                    )
                    gj.add_to(m)
                df_norm = df_sel.copy()
                if not df_norm.empty:
                    data_norm = df_norm[['centroid_lat', 'centroid_lon', self.value_col]].values.tolist()
                    HeatMap(data_norm, radius=40, max_opacity=0.8).add_to(m)
                df_anom = df_sel[df_sel[self.anomaly_col] == 1]
                if not df_anom.empty:
                    for _, row in df_anom.iterrows():
                        fol_lat = row.get('centroid_lat', None)
                        fol_lon = row.get('centroid_lon', None)
                        if fol_lat is not None and fol_lon is not None:
                            CircleMarker(location=(fol_lat, fol_lon), radius=6, color='blue', fill=True, fill_opacity=0.9, popup=f"Anomaly: {row[self.value_col]}").add_to(m)
                display(m)

        date_picker.observe(lambda change: plot_for_selection(date_picker.value, hour_slider.value), names='value')
        hour_slider.observe(lambda change: plot_for_selection(date_picker.value, hour_slider.value), names='value')
        display(widgets.VBox([date_picker, hour_slider]), out)
        plot_for_selection(date_picker.value, hour_slider.value)

    @staticmethod
    def plot_mv_em_curves(df_curve: pd.DataFrame):
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        axes[0].plot(df_curve['volume'], df_curve['mass'], label='IF')
        axes[0].set_xlabel('Volume (approx.)')
        axes[0].set_ylabel('Mass')
        axes[0].set_title('Mass-Volume Curves')
        axes[0].legend()
        axes[1].plot(df_curve['threshold'], df_curve['em'], label='IF')
        axes[1].set_xlabel('Threshold')
        axes[1].set_ylabel('EM = mass - volume')
        axes[1].set_title('Excess-Mass Curves')
        axes[1].legend()
        plt.tight_layout()
        plt.show()
