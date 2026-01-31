"""
Landing Zone Selection Module
Finds the nearest drone landing zones to patient location in Al Ghadir, Riyadh.

Uses the Haversine formula for accurate great-circle distance calculation
on Earth's surface, accounting for the spherical shape of the planet.

Default patient location: 7319 Al Humaid St, Al Ghadir
Coordinates: 24.7745°N, 46.6575°E (from D1.md specification)
"""

import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Default patient location from D1.md: Al Humaid St, Al Ghadir, Riyadh
DEFAULT_PATIENT_LAT = 24.7745
DEFAULT_PATIENT_LON = 46.6575

# Earth's mean radius in kilometers
EARTH_RADIUS_KM = 6371.0

# Reasonable bounds for Al Ghadir neighborhood
AL_GHADIR_BOUNDS = {
    "lat_min": 24.76,
    "lat_max": 24.78,
    "lon_min": 46.64,
    "lon_max": 46.67,
}


@dataclass
class LandingZoneResult:
    """
    Result of landing zone selection with distance calculation.
    
    Attributes:
        name: Landing zone name
        latitude: Zone latitude (degrees)
        longitude: Zone longitude (degrees)
        area: Landing area dimensions (e.g., "20 x 20 m")
        distance_km: Distance from patient (kilometers)
        bearing: Compass bearing from patient to zone (degrees, 0-360)
        estimated_flight_time: Estimated drone flight time (minutes)
    """
    name: str
    latitude: float
    longitude: float
    area: str
    distance_km: float
    bearing: float = 0.0
    estimated_flight_time: float = 0.0


# =============================================================================
# DISTANCE CALCULATIONS
# =============================================================================

def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    Calculate the great-circle distance between two points on Earth.
    
    Uses the Haversine formula which accounts for Earth's spherical shape:
    
    a = sin²(Δφ/2) + cos(φ1) * cos(φ2) * sin²(Δλ/2)
    c = 2 * atan2(√a, √(1−a))
    d = R * c
    
    where:
    - φ is latitude
    - λ is longitude
    - R is Earth's radius (6371 km)
    
    Args:
        lat1, lon1: First point coordinates in degrees
        lat2, lon2: Second point coordinates in degrees
    
    Returns:
        Distance in kilometers
    
    Examples:
        >>> # Al Ghadir Park to Patient location
        >>> haversine_distance(24.7703, 46.6529, 24.7745, 46.6575)
        0.55
    """
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = (
        math.sin(dlat / 2) ** 2 +
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = EARTH_RADIUS_KM * c
    
    return distance


def calculate_bearing(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:
    """
    Calculate the initial compass bearing from point 1 to point 2.
    
    Formula:
    θ = atan2(sin(Δλ) * cos(φ2), cos(φ1) * sin(φ2) − sin(φ1) * cos(φ2) * cos(Δλ))
    
    Args:
        lat1, lon1: Starting point coordinates in degrees
        lat2, lon2: Destination point coordinates in degrees
    
    Returns:
        Bearing in degrees (0-360), where 0° = North, 90° = East
    
    Examples:
        >>> calculate_bearing(24.7745, 46.6575, 24.7703, 46.6529)
        225.5  # Southwest direction
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    
    x = math.sin(dlon) * math.cos(lat2_rad)
    y = (
        math.cos(lat1_rad) * math.sin(lat2_rad) -
        math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)
    )
    
    initial_bearing = math.atan2(x, y)
    
    # Convert from radians to degrees and normalize to 0-360
    bearing = (math.degrees(initial_bearing) + 360) % 360
    
    return bearing


def estimate_flight_time(
    distance_km: float,
    drone_speed_kmh: float = 120.0
) -> float:
    """
    Estimate drone flight time based on distance.
    
    Args:
        distance_km: Distance to travel (kilometers)
        drone_speed_kmh: Drone cruise speed (default: 120 km/h from D1.md)
    
    Returns:
        Flight time in minutes
    
    Examples:
        >>> estimate_flight_time(3.2)  # 3.2 km at 120 km/h
        1.6  # minutes
    """
    if distance_km <= 0 or drone_speed_kmh <= 0:
        return 0.0
    
    time_hours = distance_km / drone_speed_kmh
    time_minutes = time_hours * 60
    
    return time_minutes


def bearing_to_cardinal(bearing: float) -> str:
    """
    Convert bearing degrees to cardinal direction.
    
    Args:
        bearing: Bearing in degrees (0-360)
    
    Returns:
        Cardinal direction (N, NE, E, SE, S, SW, W, NW)
    
    Examples:
        >>> bearing_to_cardinal(45)
        'NE'
        >>> bearing_to_cardinal(180)
        'S'
    """
    directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    index = round(bearing / 45) % 8
    return directions[index]


# =============================================================================
# LANDING ZONE SELECTION
# =============================================================================

def find_nearest_zone(
    zones: List[Dict],
    patient_lat: float = DEFAULT_PATIENT_LAT,
    patient_lon: float = DEFAULT_PATIENT_LON,
) -> Optional[LandingZoneResult]:
    """
    Find the nearest landing zone to the patient location.
    
    Args:
        zones: List of landing zones from data_loader.load_landing_zones()
        patient_lat: Patient latitude in degrees (default: Al Humaid St)
        patient_lon: Patient longitude in degrees (default: Al Ghadir)
    
    Returns:
        LandingZoneResult with nearest zone details, or None if no zones
    
    Examples:
        >>> zones = load_landing_zones()
        >>> nearest = find_nearest_zone(zones)
        >>> nearest.name
        'Al Ghadir Park'
        >>> nearest.distance_km < 1.0
        True
    """
    if not zones:
        logger.warning("No landing zones provided")
        return None
    
    # Validate patient coordinates
    if not _validate_coordinates(patient_lat, patient_lon):
        logger.warning(f"Invalid patient coordinates: {patient_lat}, {patient_lon}")
    
    nearest = None
    min_distance = float('inf')
    
    for zone in zones:
        zone_lat = zone.get("latitude", 0)
        zone_lon = zone.get("longitude", 0)
        
        # Skip invalid zones
        if not _validate_coordinates(zone_lat, zone_lon):
            logger.warning(f"Invalid zone coordinates: {zone.get('name', 'Unknown')}")
            continue
        
        # Calculate distance
        distance = haversine_distance(patient_lat, patient_lon, zone_lat, zone_lon)
        
        if distance < min_distance:
            min_distance = distance
            
            # Calculate additional metrics
            bearing = calculate_bearing(patient_lat, patient_lon, zone_lat, zone_lon)
            flight_time = estimate_flight_time(distance)
            
            nearest = LandingZoneResult(
                name=zone.get("name", "Unknown Zone"),
                latitude=zone_lat,
                longitude=zone_lon,
                area=zone.get("area", "Unknown"),
                distance_km=round(distance, 2),
                bearing=round(bearing, 1),
                estimated_flight_time=round(flight_time, 1),
            )
    
    if nearest:
        logger.info(f"Nearest zone: {nearest.name} at {nearest.distance_km} km")
    else:
        logger.warning("No valid landing zones found")
    
    return nearest


def get_all_zones_sorted(
    zones: List[Dict],
    patient_lat: float = DEFAULT_PATIENT_LAT,
    patient_lon: float = DEFAULT_PATIENT_LON,
) -> List[LandingZoneResult]:
    """
    Get all landing zones sorted by distance to patient.
    
    Args:
        zones: List of landing zones
        patient_lat: Patient latitude
        patient_lon: Patient longitude
    
    Returns:
        List of LandingZoneResult sorted by distance (ascending)
    """
    results = []
    
    for zone in zones:
        zone_lat = zone.get("latitude", 0)
        zone_lon = zone.get("longitude", 0)
        
        # Skip invalid zones
        if not _validate_coordinates(zone_lat, zone_lon):
            continue
        
        distance = haversine_distance(patient_lat, patient_lon, zone_lat, zone_lon)
        bearing = calculate_bearing(patient_lat, patient_lon, zone_lat, zone_lon)
        flight_time = estimate_flight_time(distance)
        
        results.append(LandingZoneResult(
            name=zone.get("name", "Unknown Zone"),
            latitude=zone_lat,
            longitude=zone_lon,
            area=zone.get("area", "Unknown"),
            distance_km=round(distance, 2),
            bearing=round(bearing, 1),
            estimated_flight_time=round(flight_time, 1),
        ))
    
    return sorted(results, key=lambda z: z.distance_km)


def get_zones_within_radius(
    zones: List[Dict],
    radius_km: float,
    patient_lat: float = DEFAULT_PATIENT_LAT,
    patient_lon: float = DEFAULT_PATIENT_LON,
) -> List[LandingZoneResult]:
    """
    Get all landing zones within a specified radius.
    
    Args:
        zones: List of landing zones
        radius_km: Maximum distance in kilometers
        patient_lat: Patient latitude
        patient_lon: Patient longitude
    
    Returns:
        List of zones within radius, sorted by distance
    """
    all_zones = get_all_zones_sorted(zones, patient_lat, patient_lon)
    return [z for z in all_zones if z.distance_km <= radius_km]


# =============================================================================
# VALIDATION & UTILITIES
# =============================================================================

def _validate_coordinates(lat: float, lon: float) -> bool:
    """
    Validate latitude and longitude values.
    
    Args:
        lat: Latitude in degrees
        lon: Longitude in degrees
    
    Returns:
        True if coordinates are valid
    """
    # Basic range check
    if not (-90 <= lat <= 90):
        return False
    if not (-180 <= lon <= 180):
        return False
    
    # Check for placeholder zeros
    if lat == 0 and lon == 0:
        return False
    
    return True


def get_zone_stats(zones: List[Dict]) -> Dict:
    """
    Get statistics about landing zones.
    
    Args:
        zones: List of landing zones
    
    Returns:
        Dictionary with statistics
    """
    if not zones:
        return {"count": 0}
    
    all_sorted = get_all_zones_sorted(zones)
    
    distances = [z.distance_km for z in all_sorted]
    
    return {
        "count": len(all_sorted),
        "nearest_distance": min(distances) if distances else 0,
        "farthest_distance": max(distances) if distances else 0,
        "average_distance": sum(distances) / len(distances) if distances else 0,
        "nearest_zone": all_sorted[0].name if all_sorted else None,
    }


# =============================================================================
# TESTING & VALIDATION
# =============================================================================

if __name__ == "__main__":
    from data_loader import load_landing_zones
    
    print("=" * 80)
    print("LANDING ZONE SELECTION TEST SUITE")
    print("=" * 80)
    
    print(f"\nDefault patient location:")
    print(f"  7319 Al Humaid St, Al Ghadir, Riyadh")
    print(f"  Coordinates: {DEFAULT_PATIENT_LAT}°N, {DEFAULT_PATIENT_LON}°E")
    
    try:
        zones = load_landing_zones()
        print(f"\n✓ Loaded {len(zones)} landing zones")
        
        # Test 1: Find nearest zone
        print("\n" + "=" * 80)
        print("TEST 1: Find Nearest Zone")
        print("=" * 80)
        
        nearest = find_nearest_zone(zones)
        if nearest:
            print(f"\n✓ Nearest Landing Zone:")
            print(f"  Name: {nearest.name}")
            print(f"  Coordinates: {nearest.latitude:.4f}°N, {nearest.longitude:.4f}°E")
            print(f"  Landing Area: {nearest.area}")
            print(f"  Distance: {nearest.distance_km} km")
            print(f"  Bearing: {nearest.bearing}° ({bearing_to_cardinal(nearest.bearing)})")
            print(f"  Est. Flight Time: {nearest.estimated_flight_time} min")
        else:
            print("\n✗ No nearest zone found")
        
        # Test 2: All zones sorted
        print("\n" + "=" * 80)
        print("TEST 2: All Zones Sorted by Distance")
        print("=" * 80)
        
        all_sorted = get_all_zones_sorted(zones)
        print(f"\nAll {len(all_sorted)} zones (sorted by distance):")
        for i, zone in enumerate(all_sorted, 1):
            direction = bearing_to_cardinal(zone.bearing)
            print(f"  {i}. {zone.name}")
            print(f"     Distance: {zone.distance_km} km {direction}")
            print(f"     Flight Time: {zone.estimated_flight_time} min")
        
        # Test 3: Zones within radius
        print("\n" + "=" * 80)
        print("TEST 3: Zones Within 1 km Radius")
        print("=" * 80)
        
        nearby = get_zones_within_radius(zones, radius_km=1.0)
        print(f"\nFound {len(nearby)} zones within 1 km:")
        for zone in nearby:
            print(f"  - {zone.name}: {zone.distance_km} km")
        
        # Test 4: Statistics
        print("\n" + "=" * 80)
        print("TEST 4: Zone Statistics")
        print("=" * 80)
        
        stats = get_zone_stats(zones)
        print(f"\nStatistics:")
        print(f"  Total zones: {stats['count']}")
        print(f"  Nearest: {stats['nearest_zone']} ({stats['nearest_distance']:.2f} km)")
        print(f"  Farthest: {stats['farthest_distance']:.2f} km")
        print(f"  Average distance: {stats['average_distance']:.2f} km")
        
        # Test 5: Distance validation
        print("\n" + "=" * 80)
        print("TEST 5: Distance Formula Validation")
        print("=" * 80)
        
        # Known test case: roughly 0.55 km from patient to Al Ghadir Park
        test_lat, test_lon = 24.7703, 46.6529
        test_distance = haversine_distance(DEFAULT_PATIENT_LAT, DEFAULT_PATIENT_LON, test_lat, test_lon)
        print(f"\nTest distance calculation:")
        print(f"  From: {DEFAULT_PATIENT_LAT}°N, {DEFAULT_PATIENT_LON}°E")
        print(f"  To: {test_lat}°N, {test_lon}°E")
        print(f"  Distance: {test_distance:.2f} km")
        print(f"  Expected: ~0.55 km")
        
        if 0.5 <= test_distance <= 0.6:
            print("  ✓ Distance calculation validated")
        else:
            print("  ⚠ Distance outside expected range")
        
        print("\n" + "=" * 80)
        print("✓ ALL TESTS COMPLETED")
        print("=" * 80)
        
    except FileNotFoundError as e:
        print(f"\n✗ FILE ERROR: {e}")
        print("Ensure Al_Ghadir_Landing_Zones.json is in /Files directory")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()