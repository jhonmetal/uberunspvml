from typing import Optional, TypeVar, Generic
from pydantic import BaseModel

_T = TypeVar("_T")  # Variable de tipo genérico

class Response(BaseModel):
    status_code: int = 200
    status_name: Optional[str] = "OK"
    message: Optional[str] = None
    result: Optional[_T] = None