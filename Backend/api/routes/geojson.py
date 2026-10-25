from __future__ import annotations
import math
from typing import Dict, Any, List

def create_hex_polygon(lat: float, lon: float, radius_km: float = 0.95) -> List[List[float]]:
    """Creates a regular hexagon polygon around (lat, lon) in [lon, lat] GeoJSON format."""
    coords = []
    # 1 deg lat approx 111 km, 1 deg lon approx 111 * cos(lat) km
    lat_deg_per_km = 1.0 / 111.0
    lon_deg_per_km = 1.0 / (111.0 * math.cos(math.radians(lat)))

    for i in range(7):
        angle = math.radians(60.0 * i + 30.0)
        d_lat = radius_km * math.sin(angle) * lat_deg_per_km
        d_lon = radius_km * math.cos(angle) * lon_deg_per_km
        coords.append([round(lon + d_lon, 6), round(lat + d_lat, 6)])

    return coords

def generate_risk_geojson(zones_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generates standard RFC 7946 GeoJSON FeatureCollection for map visualization."""
    features = []
    for z in zones_data:
        lat = z.get("lat", 19.06)
        lon = z.get("lon", 72.86)
        poly = create_hex_polygon(lat, lon)

        features.append({
            "type": "Feature",
            "id": z.get("zone_id", z.get("id")),
            "geometry": {
                "type": "Polygon",
                "coordinates": [poly]
            },
            "properties": {
                "zone_id": z.get("zone_id", z.get("id")),
                "name": z.get("name", ""),
                "state": z.get("state", "NORMAL"),
                "confidence": z.get("confidence", "HIGH"),
                "evidence_coverage": z.get("evidence_coverage", 0.95),
                "p24": z.get("p", {}).get("24", 0.0),
                "elevation_m": z.get("elevation_m", 5.0),
                "population": z.get("population", 50000),
                "provenance": "MODELLED"
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }
