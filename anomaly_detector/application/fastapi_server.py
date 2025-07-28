"""
FastAPI server for model serving, orchestrating domain and adapters.
"""

import os
import logging
import yaml
import pandas as pd
import mlflow
import time
import jwt
from mlflow.tracking import MlflowClient
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from anomaly_detector.domain.models import (
    BatchPredictRequest, BatchPredictResponse, HealthResponse,
    ModelInfoResponse, MetricsResponse
)
from anomaly_detector.domain.services import run_pipeline
from anomaly_detector.application.ports import APIPort
from anomaly_detector.adapters.metrics_adapter import MetricsAdapter
from anomaly_detector.adapters.ml_adapter import MLflowAdapter
from prometheus_client import generate_latest


# JWT secret and algorithm (should be loaded from env/config in prod)
JWT_SECRET = os.environ.get("ANOMALY_JWT_SECRET", "dev_secret")
JWT_ALGORITHM = "HS256"

# Security dependency
security = HTTPBearer()

# Circuit breaker and rate limiter middleware
class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_failures=5, reset_timeout=60):
        super().__init__(app)
        self.failures = 0
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.last_failure = 0

    async def dispatch(self, request, call_next):
        now = time.time()
        if self.failures >= self.max_failures and (now - self.last_failure) < self.reset_timeout:
            return JSONResponse(status_code=503, content={"detail": "Service temporarily unavailable (circuit breaker)"})
        try:
            response = await call_next(request)
            if response.status_code >= 500:
                self.failures += 1
                self.last_failure = now
            else:
                self.failures = 0
            return response
        except Exception as e:
            self.failures += 1
            self.last_failure = now
            return JSONResponse(status_code=500, content={"detail": str(e)})

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests=20, window_seconds=10):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}

    async def dispatch(self, request, call_next):
        ip = request.client.host
        now = time.time()
        window = int(now // self.window_seconds)
        key = f"{ip}:{window}"
        self.requests.setdefault(key, 0)
        self.requests[key] += 1
        if self.requests[key] > self.max_requests:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
        return await call_next(request)

middleware = [
    Middleware(CircuitBreakerMiddleware),
    Middleware(RateLimiterMiddleware)
]

app = FastAPI(middleware=middleware)
metrics = MetricsAdapter()

logger = logging.getLogger("anomaly_detector.api")
logging.basicConfig(level=logging.INFO)


# Load config from YAML
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "train.yaml")
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded config from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}


class APIService(APIPort):
    def __init__(self):
        self.config = load_config()
        train_config = self.config or {}
        mlflow_experiment = train_config.get("mlflow_experiment", "Uber_Anomaly_Detection_NY_City_Trips")
        mlflow_tracking_uri = train_config.get("mlflow_tracking_uri", None)
        self.ml_adapter = MLflowAdapter(experiment_name=mlflow_experiment, tracking_uri=mlflow_tracking_uri)
        self.model_name = "UberAnomalyIForest"
        self.model_version = None
        self.model_metrics = {}
        self.model = None
        self.load_best_model()

    def load_best_model(self):
        try:
            client = self.ml_adapter.client
            versions = client.search_model_versions(f"name='{self.model_name}'")
            versions = sorted(versions, key=lambda v: v.last_updated_timestamp, reverse=True)
            if versions:
                best_version = versions[0]
                self.model_version = best_version.version
                self.model = mlflow.sklearn.load_model(best_version.source)
                run = client.get_run(best_version.run_id)
                self.model_metrics = run.data.metrics
                logger.info(f"Loaded model version {self.model_version} for {self.model_name}")
            else:
                self.model = None
                self.model_version = None
                self.model_metrics = {}
        except Exception as e:
            logger.warning(f"Could not load best/latest model: {e}")

    def performance_trends(self):
        # Load MLflow experiment and runs
        train_config = self.config or {}
        mlflow_experiment = train_config.get("mlflow_experiment", "Uber_Anomaly_Detection_NY_City_Trips")
        mlflow_tracking_uri = train_config.get("mlflow_tracking_uri", None)
        mlflow.set_tracking_uri(mlflow_tracking_uri) if mlflow_tracking_uri else None
        client = MlflowClient()
        experiment = client.get_experiment_by_name(mlflow_experiment)
        if not experiment:
            return {"error": f"No MLflow experiment found: {mlflow_experiment}"}
        runs = client.search_runs([experiment.experiment_id], order_by=["start_time DESC"])
        if not runs:
            return {"error": "No MLflow runs found."}
        # Find best run (lowest EM min or custom logic)
        best_run = runs[0]
        for run in runs:
            if "em_min" in run.data.metrics and run.data.metrics["em_min"] < best_run.data.metrics.get("em_min", float("inf")):
                best_run = run
        run_info = best_run.info
        run_data = best_run.data
        params = run_data.params
        metrics = run_data.metrics
        # Parse start_time as ISO string
        start_time = None
        if hasattr(run_info, "start_time") and run_info.start_time:
            try:
                import datetime
                start_time = datetime.datetime.fromtimestamp(run_info.start_time / 1000).isoformat()
            except Exception:
                start_time = str(run_info.start_time)
        # Calculate training_time from run start/end
        training_time = None
        if hasattr(run_info, "start_time") and hasattr(run_info, "end_time") and run_info.start_time and run_info.end_time:
            training_time = round((run_info.end_time - run_info.start_time) / 1000, 2)
        # Load EM/MV curve from artifact
        mv_em_curve = None
        for artifact in client.list_artifacts(run_info.run_id):
            if artifact.path.endswith("em_curves.csv"):
                mv_em_curve_path = client.download_artifacts(run_info.run_id, artifact.path)
                mv_em_curve = pd.read_csv(mv_em_curve_path).to_dict(orient="records")
                break
        best_run_dict = {
            "run_id": run_info.run_id,
            "run_name": params.get("run_name", run_info.run_id),
            "model_type": params.get("model_type", "Isolation Forest"),
            "start_time": start_time,
            "status": params.get("status", "completed"),
            "training_time": training_time,
            "train_size": metrics.get("train_size", metrics.get("num_rows", None)),
            "num_anomalies": metrics.get("num_anomalies", None),
            "em_mv_curve": mv_em_curve
        }
        return {"best_run": best_run_dict}

    def batch_predict(self, data):
        metrics.inc_count()
        try:
            df = pd.DataFrame(data)
            # Use loaded model if available, else fallback to pipeline            
            params = self.config.get("model", {})
            df_processed, X_train, viz, ad = run_pipeline(
                df,
                hex_resolution=params.get("hex_resolution", 7),
                rolling_window=params.get("rolling_window", 168),
                model_features=params.get("model_features"),
                contamination=params.get("contamination", 0.22),
                n_estimators=params.get("n_estimators", 50),
                max_samples=params.get("max_samples", 0.25)
            )
            # After a successful run, reload best/latest model
            self.load_best_model()
            preds = df_processed['is_anomaly'].tolist()
            scores = df_processed['anomaly_score'].tolist() if 'anomaly_score' in df_processed else [0.0]*len(preds)
            return BatchPredictResponse(
                predictions=preds,
                anomaly_scores=scores,
                value=df_processed["value"].tolist() if "value" in df_processed.columns else [],
                timestamp=df_processed["timestamp"].astype(str).tolist() if "timestamp" in df_processed.columns else [],
                centroid_lat=df_processed["centroid_lat"].tolist() if "centroid_lat" in df_processed.columns else [],
                centroid_lon=df_processed["centroid_lon"].tolist() if "centroid_lon" in df_processed.columns else [],
                h3_index=df_processed["h3_index"].tolist() if "h3_index" in df_processed.columns else [],
                hex_resolution=params.get("hex_resolution", 7)
            )
        except Exception as e:
            metrics.inc_error()
            logger.error("Batch predict error: %s", e)
            raise HTTPException(status_code=500, detail=str(e))

    def health(self):
        # Check if model is loaded
        status = "ok" if self.model else "degraded"
        return HealthResponse(status=status)

    def model_info(self):
        return ModelInfoResponse(
            name=self.model_name,
            version=str(self.model_version) if self.model_version else "unknown",
            metrics=self.model_metrics or {}
        )

    def metrics(self):
        # Return Prometheus metrics as text
        try:
            metrics_text = generate_latest().decode("utf-8")
            return MetricsResponse(metrics={"prometheus": metrics_text})
        except Exception as e:
            logger.error(f"Metrics error: {e}")
            return MetricsResponse(metrics={})


api_service = APIService()


@app.get("/health", response_model=HealthResponse)
def health():
    return api_service.health()


@app.get("/model-info", response_model=ModelInfoResponse)
def model_info():
    return api_service.model_info()


@app.get("/metrics", response_model=MetricsResponse)
def get_metrics():
    return api_service.metrics()

# Performance Trends endpoint

# API endpoint for performance trends
@app.get("/performance-trends")
def performance_trends():
    return api_service.performance_trends()

# JWT-protected endpoint
def jwt_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or missing JWT token")


@app.post("/batch_predict", response_model=BatchPredictResponse)
def batch_predict(request: BatchPredictRequest, user=Depends(jwt_auth)):
    return api_service.batch_predict(request.data)
