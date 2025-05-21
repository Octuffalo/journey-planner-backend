from fastapi import APIRouter, Query, HTTPException
from services.train_schedule_fetcher import TrainScheduleFetcher
from datetime import datetime

router = APIRouter()
fetcher = TrainScheduleFetcher()

TRANSFER_BUFFER_MINUTES = 5

def time_to_minutes(time_str: str) -> int:
    t = datetime.strptime(time_str, "%H:%M").time()
    return t.hour * 60 + t.minute

def inject_origin_if_missing(origin_crs, origin_name, scheduled_time, estimated_time, platform, calling_points):
    if not any(cp["crs"] == origin_crs for cp in calling_points):
        injected = {
            "locationName": origin_name,
            "crs": origin_crs,
            "scheduledTime": scheduled_time or "Unknown",
            "estimatedTime": estimated_time or "—",
            "actualTime": None,
            "platform": platform or "N/A"
        }
        try:
            injected_minutes = time_to_minutes(scheduled_time)
            inserted = False
            for i, cp in enumerate(calling_points):
                if cp.get("scheduledTime") and cp["scheduledTime"] != "Unknown":
                    try:
                        cp_minutes = time_to_minutes(cp["scheduledTime"])
                        if injected_minutes < cp_minutes:
                            calling_points.insert(i, injected)
                            inserted = True
                            break
                    except:
                        continue
            if not inserted:
                calling_points.append(injected)
        except:
            calling_points.insert(0, injected)
    return calling_points

@router.get("/optimal-route")
def get_optimal_route(from_station: str = Query(..., alias="from"), to_station: str = Query(..., alias="to")):
    try:
        schedule_from = fetcher.fetch_schedule(from_station)
        if "error" in schedule_from:
            raise HTTPException(status_code=400, detail=schedule_from["error"])

        best_routes = []

        # Collecting all valid direct journeys
        for service in schedule_from["departures"]:
            details = fetcher.fetch_service_details(
                service_id=service["serviceID"],
                origin_name=service["origin"],
                scheduled_time=service["scheduledDeparture"],
                estimated_time=service["estimatedDeparture"],
                platform=service["platform"]
            )

            calling_points = inject_origin_if_missing(
                origin_crs=from_station,
                origin_name=service["origin"],
                scheduled_time=service["scheduledDeparture"],
                estimated_time=service["estimatedDeparture"],
                platform=service["platform"],
                calling_points=details.get("callingPoints", [])
            )

            crs_list = [cp["crs"] for cp in calling_points]
            if to_station in crs_list:
                if from_station in crs_list and crs_list.index(from_station) >= crs_list.index(to_station):
                    continue

                arrival_cp = next(cp for cp in calling_points if cp["crs"] == to_station)
                best_routes.append({
                    "type": "direct",
                    "legs": [{
                        "from": from_station,
                        "to": to_station,
                        "departure": service["scheduledDeparture"],
                        "arrival": arrival_cp["scheduledTime"],
                        "platform": service["platform"],
                        "operator": service["operator"],
                        "callingPoints": calling_points
                    }]
                })

        # Collecting all valid 1-transfer journeys
        for service in schedule_from["departures"]:
            details_a = fetcher.fetch_service_details(
                service_id=service["serviceID"],
                origin_name=service["origin"],
                scheduled_time=service["scheduledDeparture"],
                estimated_time=service["estimatedDeparture"],
                platform=service["platform"]
            )

            calling_points_a = inject_origin_if_missing(
                origin_crs=from_station,
                origin_name=service["origin"],
                scheduled_time=service["scheduledDeparture"],
                estimated_time=service["estimatedDeparture"],
                platform=service["platform"],
                calling_points=details_a.get("callingPoints", [])
            )

            crs_list_a = [cp["crs"] for cp in calling_points_a]
            for cp in calling_points_a:
                transfer_crs = cp["crs"]
                arrival_time_str = cp.get("scheduledTime")
                if not arrival_time_str:
                    continue

                if from_station in crs_list_a and transfer_crs in crs_list_a:
                    if crs_list_a.index(from_station) >= crs_list_a.index(transfer_crs):
                        continue

                try:
                    arrival_minutes = time_to_minutes(arrival_time_str)
                except:
                    continue

                schedule_b = fetcher.fetch_schedule(transfer_crs)
                if "departures" not in schedule_b:
                    continue

                for service_b in schedule_b["departures"]:
                    departure_b_str = service_b.get("scheduledDeparture")
                    if not departure_b_str:
                        continue

                    try:
                        departure_minutes = time_to_minutes(departure_b_str)
                        if departure_minutes < arrival_minutes + TRANSFER_BUFFER_MINUTES:
                            continue
                    except:
                        continue

                    details_b = fetcher.fetch_service_details(
                        service_id=service_b["serviceID"],
                        origin_name=service_b["origin"],
                        scheduled_time=service_b["scheduledDeparture"],
                        estimated_time=service_b["estimatedDeparture"],
                        platform=service_b["platform"]
                    )

                    calling_points_b = inject_origin_if_missing(
                        origin_crs=transfer_crs,
                        origin_name=service_b["origin"],
                        scheduled_time=service_b["scheduledDeparture"],
                        estimated_time=service_b["estimatedDeparture"],
                        platform=service_b["platform"],
                        calling_points=details_b.get("callingPoints", [])
                    )

                    crs_list_b = [cp["crs"] for cp in calling_points_b]
                    if transfer_crs in crs_list_b and to_station in crs_list_b:
                        if crs_list_b.index(transfer_crs) >= crs_list_b.index(to_station):
                            continue
                    else:
                        continue

                    arrival_cp_b = next(cp for cp in calling_points_b if cp["crs"] == to_station)

                    best_routes.append({
                        "type": "indirect",
                        "legs": [
                            {
                                "from": from_station,
                                "to": transfer_crs,
                                "departure": service["scheduledDeparture"],
                                "arrival": arrival_time_str,
                                "platform": service["platform"],
                                "operator": service["operator"],
                                "callingPoints": calling_points_a
                            },
                            {
                                "from": transfer_crs,
                                "to": to_station,
                                "departure": service_b["scheduledDeparture"],
                                "arrival": arrival_cp_b["scheduledTime"],
                                "platform": service_b["platform"],
                                "operator": service_b["operator"],
                                "callingPoints": calling_points_b
                            }
                        ]
                    })

        # Returning earliest arriving route
        if best_routes:
            sorted_routes = sorted(best_routes, key=lambda r: time_to_minutes(r["legs"][-1]["arrival"]))
            return sorted_routes[0]

        raise HTTPException(status_code=404, detail="No direct or indirect route found with valid direction and timing.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))