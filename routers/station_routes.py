from fastapi import APIRouter, Query
from difflib import get_close_matches
import csv
import os

router = APIRouter(prefix="/stations", tags=["Stations"])

# Loading station data from CSV
def load_station_data(csv_file="stations.csv"):
    stations = []
    try:
        with open(csv_file, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                stations.append({
                    "stationName": row["stationName"],
                    "crsCode": row["crsCode"]
                })
    except Exception as e:
        print(f"Error loading stations CSV: {e}")
    return stations

# Caching the loaded station list
station_list = load_station_data()

@router.get("/search")
def search_stations(name: str = Query(..., min_length=2)):
    name_lower = name.lower()

    # Substring match
    matches = [
        s for s in station_list
        if name_lower in s["stationName"].lower()
    ]

    # If no substring matches found, use fuzzy matching
    if not matches:
        station_names = [s["stationName"] for s in station_list]
        close_names = get_close_matches(name, station_names, n=5, cutoff=0.4)
        matches = [s for s in station_list if s["stationName"] in close_names]

    return matches