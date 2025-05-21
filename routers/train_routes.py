from fastapi import APIRouter, Query
from services.train_schedule_fetcher import TrainScheduleFetcher

router = APIRouter()
fetcher = TrainScheduleFetcher()

@router.get("/trains/{station_code}")
def get_train_info(station_code: str):
    return fetcher.fetch_schedule(station_code)

@router.get("/trains/details/{service_id}")
def get_train_details(
    service_id: str,
    originName: str = Query(None),
    scheduledTime: str = Query(None),
    estimatedTime: str = Query(None),
    platform: str = Query(None)
):
    return fetcher.fetch_service_details(
        service_id,
        origin_name=originName,
        scheduled_time=scheduledTime,
        estimated_time=estimatedTime,
        platform=platform
    )