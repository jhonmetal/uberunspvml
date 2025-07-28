
"""
MLflowAdapter implements MLflowPort for experiment tracking and model registry.
"""
import mlflow
from anomaly_detector.domain.ports import MLflowPort


class MLflowAdapter(MLflowPort):
    def __init__(self, experiment_name: str, tracking_uri: str = None):
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
        self.client = mlflow.tracking.MlflowClient()
        self.experiment_name = experiment_name

    def log_run(self, sk_model, params: dict, metrics: dict, artifacts: list, input_example=None, signature=None, registered_model_name=None):
        """
        Logs all params, metrics, model, and artifacts in a single MLflow run context.
        """
        with mlflow.start_run() as run:
            if params:
                mlflow.log_params(params)
            if metrics:
                mlflow.log_metrics(metrics)
            if sk_model is not None:
                mlflow.sklearn.log_model(
                    sk_model=sk_model,
                    artifact_path="model",
                    input_example=input_example,
                    signature=signature,
                    registered_model_name=registered_model_name
                )
            if artifacts:
                for path in artifacts:
                    if path:
                        mlflow.log_artifact(path)
            return run.info.run_id

    def log_model(self, sk_model, artifact_path, input_example, signature, registered_model_name=None):
        with mlflow.start_run():
            mlflow.sklearn.log_model(
                sk_model=sk_model,
                artifact_path=artifact_path,
                input_example=input_example,
                signature=signature,
                registered_model_name=registered_model_name
            )

    def log_params(self, params: dict):
        with mlflow.start_run():
            mlflow.log_params(params)

    def log_metrics(self, metrics: dict):
        with mlflow.start_run():
            mlflow.log_metrics(metrics)

    def log_artifact(self, path: str):
        with mlflow.start_run():
            mlflow.log_artifact(path)

    def register_model(self, model, name: str):
        with mlflow.start_run():
            mlflow.sklearn.log_model(model, name)

    def promote_model(self, name: str, stage: str):
        self.client.transition_model_version_stage(name, stage)
