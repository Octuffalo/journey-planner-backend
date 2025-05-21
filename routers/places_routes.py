import os
import requests
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()  # Loading .env variables

router = APIRouter()

GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_KEY")

@router.get("/places")
def get_nearby_places(lat: float, lng: float, type: str = "tourist_attraction"):
    if not GOOGLE_MAPS_KEY:
        raise HTTPException(status_code=500, detail="Google Maps API key not configured")

    try:
        response = requests.get(
            "https://maps.googleapis.com/maps/api/place/nearbysearch/json",
            params={
                "location": f"{lat},{lng}",
                "radius": 1500,
                "type": type,
                "key": GOOGLE_MAPS_KEY
            }
        )
        return JSONResponse(content=response.json())
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))