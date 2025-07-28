"""
Domain ports (interfaces) for adapters (Hexagonal Architecture)
"""
from abc import ABC, abstractmethod
from typing import Any, List

class StoragePort(ABC):
    @abstractmethod
    def read(self, *args, **kwargs) -> Any:
        pass
    @abstractmethod
    def write(self, *args, **kwargs) -> None:
        pass
    @abstractmethod
    def list_partitions(self, *args, **kwargs) -> List[str]:
        pass
    @abstractmethod
    def list_files(self, *args, **kwargs) -> List[str]:
        pass
    @abstractmethod
    def upload(self, *args, **kwargs) -> None:
        pass

class MLflowPort(ABC):
    @abstractmethod
    def log_params(self, params: dict):
        pass
    @abstractmethod
    def log_metrics(self, metrics: dict):
        pass
    @abstractmethod
    def log_artifact(self, path: str):
        pass
    @abstractmethod
    def register_model(self, model: Any, name: str):
        pass
    @abstractmethod
    def promote_model(self, name: str, stage: str):
        pass

class APIPort(ABC):
    @abstractmethod
    def batch_predict(self, data: Any) -> Any:
        pass
    @abstractmethod
    def health(self) -> str:
        pass
    @abstractmethod
    def model_info(self) -> dict:
        pass
    @abstractmethod
    def metrics(self) -> dict:
        pass
