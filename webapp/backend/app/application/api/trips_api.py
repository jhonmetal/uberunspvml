import traceback
from fastapi import APIRouter, HTTPException
from ..services.trips_service import TripsService
from ..dto.base_dto import Response
from ..dto.trips_dto import TripsRequest

router = APIRouter(
    prefix="/api/uber-trips",
    tags=["uber"],
    responses={404: {"description": "Not found"}}
)


@router.post("/values")
async def get_trips(request:TripsRequest) -> Response:
    print("post trips")
    try:
        
        result = await TripsService().get_trips(request.date_code)
        response = Response(status_code=200, status_name="OK", message="Complete", result=result)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:      
        traceback.print_exc()
        raise HTTPException(status_code=501, detail=str(e))

    return response


@router.post("/indicators")
async def get_trips(request:TripsRequest) -> Response:
    print("post indicators")
    try:
        
        result = await TripsService().get_indicators(request.date_code)
        response = Response(status_code=200, status_name="OK", message="Complete", result=result)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:      
        traceback.print_exc()
        raise HTTPException(status_code=501, detail=str(e))

    return response

@router.post("/history_events")
async def get_trips(request:TripsRequest) -> Response:
    print("post indicators")
    try:
        
        result = await TripsService().get_summary_trips(request.date_code)
        response = Response(status_code=200, status_name="OK", message="Complete", result=result)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:      
        traceback.print_exc()
        raise HTTPException(status_code=501, detail=str(e))

    return response