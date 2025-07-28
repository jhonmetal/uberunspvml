from typing import TypeVar
from pydantic import BaseModel

class TripsRequest(BaseModel):
    date_code: str

