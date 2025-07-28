
import folium
from folium import Map, CircleMarker, GeoJson
from folium.plugins import HeatMap
import pandas as pd
import streamlit as st
from datetime import datetime

def render_hexmap(df: pd.DataFrame, hex_resolution: int = 7):
    """
    Build a folium.Map object for the given DataFrame and hex_resolution.
    Adds Streamlit widgets to select date and hour, and only renders data for that hour.
    Expects columns: timestamp, centroid_lat, centroid_lon, h3_index, value, is_anomaly
    """
    if df is None or df.empty:
        return None
    # Parse timestamp column to datetime if not already
    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['date_only'] = df['timestamp'].dt.date
    df['hour'] = df['timestamp'].dt.hour
    # Find the (date, hour) with the most anomalies
    if 'is_anomaly' in df.columns:
        group = df.groupby(['date_only', 'hour'])['is_anomaly'].sum().reset_index()
        if not group.empty:
            max_idx = group['is_anomaly'].idxmax()
            best_date = group.loc[max_idx, 'date_only']
            best_hour = group.loc[max_idx, 'hour']
            df_sel = df[(df['date_only'] == best_date) & (df['hour'] == best_hour)]
            st.info(f"Showing anomalies for {best_date} hour {best_hour} (most anomalies)")
        else:
            st.info("No anomalies found in data.")
            return None
    else:
        # fallback: just pick the first available hour
        if df.empty:
            st.info("No data available.")
            return None
        best_date = df['date_only'].iloc[0]
        best_hour = df['hour'].iloc[0]
        df_sel = df[(df['date_only'] == best_date) & (df['hour'] == best_hour)]
        st.info(f"Showing data for {best_date} hour {best_hour}")
    if df_sel.empty:
        st.info(f"No data for {best_date} hour {best_hour}.")
        return None
    center_lat = df_sel['centroid_lat'].mean() if 'centroid_lat' in df_sel.columns else None
    center_lon = df_sel['centroid_lon'].mean() if 'centroid_lon' in df_sel.columns else None
    if center_lat is None or center_lon is None:
        return None
    m = Map(location=[center_lat, center_lon], zoom_start=12)
    max_count = df_sel['value'].max() if 'value' in df_sel.columns else 1
    for _, row in df_sel.iterrows():
        hex_idx = row.get('h3_index', None)
        count = row.get('value', 0)
        if not hex_idx:
            continue
        try:
            import h3
            boundary_latlon = h3.cell_to_boundary(hex_idx)
            boundary_geojson = [[lon, lat] for lat, lon in boundary_latlon]
            opacity = count / max_count if max_count > 0 else 0
            def style_func(feature, op=opacity):
                return {'fillColor': 'red', 'color': 'gray', 'weight': 1, 'fillOpacity': op * 0.8}
            properties = {
                'Value': row.get('value', 0),
                'Outliers': row.get('is_anomaly', 0)
            }
            geojson_feature = {
                'type': 'Feature',
                'geometry': {'type': 'Polygon', 'coordinates': [boundary_geojson]},
                'properties': properties
            }
            tooltip = folium.GeoJsonTooltip(
                fields=['Value', 'Outliers'],
                aliases=['Value:', 'Outliers:'],
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
        except Exception:
            continue
    if 'centroid_lat' in df_sel.columns and 'centroid_lon' in df_sel.columns and 'value' in df_sel.columns:
        data_norm = df_sel[['centroid_lat', 'centroid_lon', 'value']].values.tolist()
        HeatMap(data_norm, radius=40, max_opacity=0.8).add_to(m)
    df_anom = df_sel[df_sel.get('is_anomaly', 0) == 1] if 'is_anomaly' in df_sel.columns else pd.DataFrame()
    if not df_anom.empty:
        for _, row in df_anom.iterrows():
            fol_lat = row.get('centroid_lat', None)
            fol_lon = row.get('centroid_lon', None)
            if fol_lat is not None and fol_lon is not None:
                CircleMarker(location=(fol_lat, fol_lon), radius=6, color='blue', fill=True, fill_opacity=0.9, popup=f"Anomaly: {row.get('value', 0)}").add_to(m)
    return m
