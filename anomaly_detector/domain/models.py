"""
Pydantic models for request/response schemas and domain entities.
"""

from pydantic import BaseModel
from typing import List, Optional

class BatchPredictRequest(BaseModel):
    data: List[dict]

class BatchPredictResponse(BaseModel):
    predictions: List[int]
    anomaly_scores: List[float]
    timestamp: List[str]
    value: List[float]
    centroid_lat: List[float]
    centroid_lon: List[float]
    h3_index: List[str] = []
    hex_resolution: Optional[int] = None

class HealthResponse(BaseModel):
    status: str

class ModelInfoResponse(BaseModel):
    name: str
    version: str
    metrics: dict

class MetricsResponse(BaseModel):
    metrics: dict
