import os
import csv
from dotenv import load_dotenv
from zeep import Client, xsd
from datetime import datetime

load_dotenv()

class TrainScheduleFetcher:
    def __init__(self, csv_file='stations.csv'):
        self.api_key = os.getenv("NRE_API_KEY")
        self.wsdl_url = "https://lite.realtime.nationalrail.co.uk/OpenLDBWS/wsdl.aspx"
        self.client = Client(wsdl=self.wsdl_url)
        
        # Loading CSV mapping CRS codes to station names
        self.station_map = self.load_station_map(csv_file)

        # Creating reverse map: station name -> CRS code (lowercased for case-insensitive lookup)
        self.name_to_crs_map = {v.lower(): k for k, v in self.station_map.items()}

        # Creating SOAP header
        header_type = xsd.ComplexType([xsd.Element('TokenValue', xsd.String())])
        self.access_token = xsd.Element('AccessToken', header_type)(TokenValue=self.api_key)

    def load_station_map(self, csv_file):
        """
        Load the CRS to station name mapping from a CSV file.
        """
        station_map = {}
        try:
            with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    crs_code = row['crsCode']
                    station_name = row['stationName']
                    station_map[crs_code] = station_name
        except Exception as e:
            print(f"Error loading CSV file: {e}")
        return station_map

    def get_crs_from_station_name(self, name: str):
        """
        Look up the CRS code for a given station name (case-insensitive).
        """
        return self.name_to_crs_map.get(name.lower())

    def fetch_station_name(self, station_code: str):
        """
        Fetch the station name from the CRS code using the loaded CSV data.
        """
        return self.station_map.get(station_code, station_code)  # Returning CRS code if not found

    def fetch_schedule(self, station_input: str):
        """
        Fetch schedule data for the given station input (can be CRS or station name).
        """
        # Determining if the input is a CRS code or a station name
        if len(station_input) == 3 and station_input.upper() in self.station_map:
            crs_code = station_input.upper()
        else:
            crs_code = self.get_crs_from_station_name(station_input)
            if not crs_code:
                return {"error": f"Station '{station_input}' not found."}

        # Fetching station name
        station_name = self.fetch_station_name(crs_code)

        try:
            raw_response = self.client.service.GetDepartureBoard(
                numRows=10,
                crs=crs_code,
                _soapheaders=[self.access_token]
            )

            services = []
            if hasattr(raw_response, "trainServices") and raw_response.trainServices:
                service_list = raw_response.trainServices.service
                if not isinstance(service_list, list):
                    service_list = [service_list]

                for service in service_list:
                    service_data = service.__values__

                    origin_name = station_name

                    # Destination station
                    destination_name = "Unknown"
                    destination_data = service_data.get("destination", {})
                    if destination_data:
                        locations = destination_data.__values__.get("location", [])
                        if locations:
                            destination_name = locations[0].__values__.get("locationName", "Unknown")

                    # Scheduled departure time (used for sorting)
                    scheduled_departure = service_data.get("std", "Unknown")
                    try:
                        scheduled_departure_time = datetime.strptime(scheduled_departure, '%H:%M').time()
                    except ValueError:
                        scheduled_departure_time = None

                    services.append({
                        "origin": origin_name,
                        "destination": destination_name,
                        "scheduledDeparture": scheduled_departure,
                        "scheduledDepartureTime": scheduled_departure_time,
                        "estimatedDeparture": service_data.get("etd", "Unknown"),
                        "platform": service_data.get("platform", "N/A"),
                        "operator": service_data.get("operator", "Unknown"),
                        "operatorCode": service_data.get("operatorCode", ""),
                        "isCancelled": service_data.get("isCancelled", False),
                        "delayReason": service_data.get("delayReason", None),
                        "cancelReason": service_data.get("cancelReason", None),
                        "coachCount": service_data.get("length", None),
                        "serviceID": service_data.get("serviceID", "Unknown")
                    })

            # Sorting services by scheduled departure time
            services.sort(key=lambda x: x['scheduledDepartureTime'] if x['scheduledDepartureTime'] else datetime.max.time())

            return {
                "station": station_name,
                "generatedAt": getattr(raw_response, "generatedAt", "Unknown Time"),
                "departures": services
            }

        except Exception as e:
            return {"error": str(e)}

    def fetch_service_details(self, service_id: str, origin_name=None, scheduled_time=None, estimated_time=None, platform=None):
        """
        Fetch detailed service information, including calling points.
        """
        try:
            raw_details = self.client.service.GetServiceDetails(
                serviceID=service_id,
                _soapheaders=[self.access_token]
            )

            calling_points = []

            for attr in ["previousCallingPoints", "subsequentCallingPoints"]:
                group = getattr(raw_details, attr, None)
                if not group:
                    continue

                cp_lists = getattr(group, "callingPointList", None)
                if not cp_lists:
                    continue

                if not isinstance(cp_lists, list):
                    cp_lists = [cp_lists]

                for cp_list in cp_lists:
                    points = getattr(cp_list, "callingPoint", None)
                    if not points:
                        continue

                    if not isinstance(points, list):
                        points = [points]

                    for point in points:
                        cp = point.__values__ if hasattr(point, '__values__') else point
                        calling_points.append({
                            "locationName": cp.get("locationName", "Unknown"),
                            "crs": cp.get("crs", "UNK"),
                            "scheduledTime": cp.get("st", "Unknown"),
                            "estimatedTime": cp.get("et", "Unknown"),
                            "actualTime": cp.get("at", None),
                            "platform": cp.get("platform", "N/A")
                        })

            # Injecting origin station if not in list
            if origin_name and calling_points:
                found = any(cp["locationName"] == origin_name for cp in calling_points)
                if not found:
                    injected_cp = {
                        "locationName": origin_name,
                        "crs": "UNK",
                        "scheduledTime": scheduled_time or "Unknown",
                        "estimatedTime": estimated_time or "—",
                        "actualTime": None,
                        "platform": platform or "N/A"
                    }
                    # Inserting based on time
                    insert_index = 0
                    for i, cp in enumerate(calling_points):
                        if (scheduled_time and cp['scheduledTime'] != "Unknown" and 
                                datetime.strptime(scheduled_time, '%H:%M').time() < datetime.strptime(cp['scheduledTime'], '%H:%M').time()):
                            insert_index = i
                            break
                    calling_points.insert(insert_index, injected_cp)

            # Sorting calling points by scheduled time
            calling_points.sort(key=lambda x: x['scheduledTime'] if x['scheduledTime'] != "Unknown" else datetime.max.time())

            origin = calling_points[0]["locationName"] if calling_points else "Unknown"
            destination = calling_points[-1]["locationName"] if calling_points else "Unknown"

            return {
                "generatedAt": getattr(raw_details, "generatedAt", "Unknown"),
                "origin": origin,
                "destination": destination,
                "callingPoints": calling_points
            }

        except Exception as e:
            return {"error": str(e)}