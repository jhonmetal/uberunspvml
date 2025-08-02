
from hexmap_utils import render_hexmap
from streamlit_folium import folium_static
import streamlit as st
import requests
import os
import pandas as pd
import random
import plotly.express as px

API_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
JWT_TOKEN = os.environ.get("ANOMALY_JWT_TOKEN", "")

st.set_page_config(page_title="Uber Anomaly Detection DEV Site", layout="wide")

st.title("🚕 Uber Anomaly Detection DEV Site")


# Helper for authenticated requests
def api_get(endpoint):
    headers = {"Authorization": f"Bearer {JWT_TOKEN}"} if JWT_TOKEN else {}
    resp = requests.get(f"{API_URL}{endpoint}", headers=headers)
    if resp.status_code == 200:
        return resp.json()
    st.error(f"API error: {resp.status_code} {resp.text}")
    return None


def api_post(endpoint, data):
    headers = {"Authorization": f"Bearer {JWT_TOKEN}"} if JWT_TOKEN else {}
    resp = requests.post(f"{API_URL}{endpoint}", json=data, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    st.error(f"API error: {resp.status_code} {resp.text}")
    return None


# Sidebar for JWT and API config
st.sidebar.header("API Settings")
API_URL = st.sidebar.text_input("API URL", API_URL)
JWT_TOKEN = st.sidebar.text_area("JWT Token", JWT_TOKEN, height=100)

# Tabs
TABS = ["Heatmap", "Performance Trends", "API Health"]
tab = st.sidebar.radio("Select Tab", TABS)

if tab == "Heatmap":
    st.subheader("Anomaly Heatmap")
    st.write("Upload a CSV with Uber trip data to visualize anomalies.")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded:
        # Try to mimic extract_and_concat_uber_csvs logic for uploaded file
        df = pd.read_csv(uploaded)
        # Standardize columns if needed
        col_map = {"Date/Time": "timestamp", "Lat": "lat", "Lon": "lon", "Base": "base"}
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        # Only keep required columns
        keep_cols = [v for v in col_map.values() if v in df.columns]
        df = df[keep_cols]
        st.write("Sample Data:", df.head())
        if st.button("Run Batch Predict"):
            # Only send rows with required columns
            api_df = df.dropna(subset=["lat", "lon", "timestamp"])
            dev_messages = [
                "🚦 Sending your Uber trips to the anomaly detector...",
                "🧠 Crunching numbers and searching for outliers...",
                "🔍 H3 hexagons are being indexed and analyzed...",
                "🤖 MLflow is loading the best model for you...",
                "⏳ Hold tight! The pipeline is aggregating and scoring trips...",
                "🧬 Feature engineering in progress: lags, stats, and more...",
                "🗺️ Mapping your data to the Uber NYC grid...",
                "🛡️ Security check: JWT validated, IAM roles assumed...",
                "🧪 Model is predicting anomalies, this may take a moment...",
                "🚀 Deploying the anomaly detector microservice..."
            ]
            with st.spinner(random.choice(dev_messages)):
                result = api_post("/batch_predict", {"data": api_df.to_dict(orient="records")})
            if result is not None:
                # Convert API response to DataFrame
                if isinstance(result, dict):
                    result_df = pd.DataFrame({
                        "timestamp": result.get("timestamp", []),
                        "value": result.get("value", []),
                        "centroid_lat": result.get("centroid_lat", []),
                        "centroid_lon": result.get("centroid_lon", []),
                        "h3_index": result.get("h3_index", []),
                        "is_anomaly": result.get("predictions", []),
                        "anomaly_score": result.get("anomaly_scores", [])
                    })
                    try:
                        hex_resolution = result.get("hex_resolution", 7)
                        m = render_hexmap(result_df, hex_resolution=hex_resolution)
                        if m is not None:
                            folium_static(m, width=700, height=500)
                        else:
                            st.info("No data available for selected date/hour.")
                    except Exception as e:
                        st.error(f"Could not display interactive hexmap: {e}")
                    st.write("Predictions:", result_df[result_df["value"] > 10].drop(columns=["h3_index", "date_only", "hour"]).head(20))

                    

elif tab == "Performance Trends":
    st.markdown("## 📈 Model Performance Trends (EM & MV Curves)")
    st.info("""
    📊 This section summarizes model training runs and shows EM (Excess Mass) and MV (Mass-Volume) curves from the API.
    """)
    perf_messages = [
        "🔬 Loading model performance trends from the API...",
        "📊 Fetching EM & MV curves from MLflow backend...",
        "🚀 Querying best run metadata for anomaly detection...",
        "🧠 Analyzing experiment results and metrics...",
        "⏳ Please wait while we summarize the latest model runs..."
    ]
    with st.spinner(random.choice(perf_messages)):
        perf = api_get("/performance-trends")
    if not perf or "best_run" not in perf:
        st.error("No performance trends data found from API.")
    else:
        best_run = perf["best_run"]
        st.success(f"Best run: {best_run.get('run_id', 'N/A')}")
        st.markdown("#### Run Metadata")
        # Parse start_time as date plus hour GMT-5
        import pytz
        from datetime import datetime, timezone, timedelta
        start_time_raw = best_run.get("start_time", None)
        start_time_fmt = None
        if start_time_raw:
            try:
                dt = datetime.fromisoformat(start_time_raw)
                dt_gmt5 = dt.astimezone(pytz.timezone("America/Lima"))
                start_time_fmt = dt_gmt5.strftime("%Y-%m-%d %H:%M (%Z)")
            except Exception:
                start_time_fmt = str(start_time_raw)
        # Format training_time with units
        training_time_val = best_run.get("training_time", None)
        training_time_str = None
        if training_time_val is not None:
            try:
                seconds = float(training_time_val)
                if seconds < 60:
                    training_time_str = f"{seconds:.2f} seconds"
                elif seconds < 3600:
                    minutes = seconds / 60
                    training_time_str = f"{minutes:.2f} minutes ({seconds:.2f} seconds)"
                else:
                    hours = seconds / 3600
                    minutes = (seconds % 3600) / 60
                    training_time_str = f"{hours:.2f} hours ({minutes:.2f} minutes, {seconds:.2f} seconds)"
            except Exception:
                training_time_str = str(training_time_val)
        st.json({
            "run_name": best_run.get("run_name", best_run.get("run_id", "N/A")),
            "model_type": best_run.get("model_type", "Isolation Forest"),
            "start_time": start_time_fmt,
            "status": best_run.get("status", "completed"),
            "training_time": training_time_str,
            "train_size": best_run.get("train_size", None),
            "num_anomalies": best_run.get("num_anomalies", None)
        })
        # EM and MV curves
        mv_em_curve = None
        try:            
            if "em_mv_curve" in best_run:
                try:
                    mv_em_curve = pd.DataFrame(best_run["em_mv_curve"])
                except Exception:
                    mv_em_curve = None
            if mv_em_curve is not None:
                st.markdown("### 📈 EM (Excess Mass) Curve")
                st.info("""
                **How to interpret the EM Curve:**
                - The EM (Excess Mass) curve shows how well the model separates anomalies from normal data.
                - **Higher EM values at lower thresholds** mean the model is good at concentrating anomaly scores in a small region (better separation).
                - A curve that rises quickly and stays high is **good**; a flat or low curve means the model struggles to distinguish anomalies.
                """)
                fig_em = px.line(mv_em_curve, x="threshold", y="em", title="Excess Mass Curve", labels={"threshold": "Threshold", "em": "Excess Mass"})
                st.plotly_chart(fig_em, use_container_width=True)
                st.markdown("### 📈 MV (Mass-Volume) Curve")
                st.info("""
                **How to interpret the MV Curve:**
                - The MV (Mass-Volume) curve shows the trade-off between the fraction of data flagged as anomalies (mass) and the volume of space they occupy.
                - **Lower volume for higher mass** is better: it means the model finds anomalies in compact regions.
                - A curve that stays low and rises slowly is **good**; a steep curve means anomalies are spread out and less well detected.
                """)
                fig_mv = px.line(mv_em_curve, x="volume", y="mass", title="Mass-Volume Curve", labels={"volume": "Volume", "mass": "Mass"})
                st.plotly_chart(fig_mv, use_container_width=True)
            else:
                st.info("No EM/MV curve data found for best run.")
        except Exception as e:
            st.error("Could not display EM/MV curves. 🚀 Please load a new run in Heatmap tab.")

elif tab == "API Health":
    st.markdown("## 🚦 API Health & Model Info")
    st.info("""
    This section shows the current status of the API, model deployment, and key metrics.
    
    **How to interpret the main metrics:**
    - **em_area**: Total area under the Excess Mass curve. Higher values mean the model is better at concentrating anomaly scores and separating anomalies from normal data. Good models have em_area closer to 1.
    - **mv_area**: Total area under the Mass-Volume curve. Lower values are better, indicating anomalies are found in compact regions. Good models have mv_area closer to 0.
    - **num_anomalies**: Number of trips flagged as anomalies. A reasonable number (not too high or low) suggests the model is well-calibrated. Sudden spikes may indicate data drift or issues.
    - **num_rows**: Total number of trips processed. Use this to check if the input data size matches expectations.
    """)
    health_messages = [
        "🩺 Checking API health status...",
        "🔎 Verifying model deployment and readiness...",
        "🛡️ Running security and status checks...",
        "⚡ Fetching live API status..."
    ]
    with st.spinner(random.choice(health_messages)):
        health = api_get("/health")
    with st.spinner(random.choice(health_messages)):
        info = api_get("/model-info")
    col1, col2 = st.columns(2)
    with col1:
        if health:
            status = health.get("status", "unknown")
            if status == "ok":
                st.success(f"API Status: {status}")
            else:
                st.warning(f"API Status: {status}")
            st.json(health)
        else:
            st.error("API health endpoint not available.")
    with col2:
        if info:
            st.success("Model Info Loaded")
            st.json(info)
        else:
            st.error("Model info endpoint not available.")
    # Prometheus metrics
    st.markdown("### 📊 API Metrics (Prometheus)")
    metrics_messages = [
        "📈 Gathering Prometheus metrics from the API...",
        "🔬 Collecting live monitoring data...",
        "⏳ Loading API metrics for observability..."
    ]
    with st.spinner(random.choice(metrics_messages)):
        metrics = api_get("/metrics")
    if metrics and "prometheus" in metrics["metrics"]:
        st.code(metrics["metrics"]["prometheus"], language="text")
    else:
        st.info("No metrics available.")
