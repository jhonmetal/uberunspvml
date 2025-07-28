
"""
API port interface definitions for FastAPI endpoints.
"""

from abc import ABC, abstractmethod
from typing import Any


class APIPort(ABC):
    @abstractmethod
    def batch_predict(self, data: Any) -> Any:
        pass

    @abstractmethod
    def health(self) -> Any:
        pass

    @abstractmethod
    def model_info(self) -> Any:
        pass

    @abstractmethod
    def metrics(self) -> Any:
        pass
