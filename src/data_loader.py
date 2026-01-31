"""
Data Loader Module
Loads and normalizes JSON data files from /Files directory.
Implements MANDATORY normalization rules per specification.

Handles multiple input formats and ensures consistent output schema.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base directory for data files
FILES_DIR = Path(__file__).parent.parent / "data"


# =============================================================================
# NORMALIZATION UTILITIES
# =============================================================================

def normalize_weather_risk(value: Any) -> float:
    """
    Normalize weather risk to 0-100 percent float.
    
    Conversion Rules:
    - String with '%': parse number (e.g., "10%" -> 10.0)
    - Numeric <= 1.0: multiply by 100 (e.g., 0.88 -> 88.0)
    - Numeric > 1.0: assume already in percent (e.g., 35 -> 35.0)
    - None/invalid: return 0.0
    
    Args:
        value: Input value (string, int, float, or None)
    
    Returns:
        Float in range 0-100 (clamped)
    
    Examples:
        >>> normalize_weather_risk("10%")
        10.0
        >>> normalize_weather_risk(0.88)
        88.0
        >>> normalize_weather_risk(35)
        35.0
        >>> normalize_weather_risk(None)
        0.0
    """
    if value is None:
        return 0.0
    
    try:
        if isinstance(value, str):
            # Remove % symbol and whitespace
            clean = value.replace('%', '').strip()
            num = float(clean)
        elif isinstance(value, (int, float)):
            num = float(value)
        else:
            logger.warning(f"Unexpected weather risk type: {type(value)}, defaulting to 0")
            return 0.0
        
        # Convert fraction to percentage if needed
        if num <= 1.0:
            num *= 100.0
        
        # Clamp to valid range
        return max(0.0, min(100.0, num))
    
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse weather risk '{value}': {e}, defaulting to 0")
        return 0.0


def normalize_decision_label(decision: str) -> str:
    """
    Normalize AI decision/dispatch labels to standard format.
    
    Standard Outputs:
    - "DOCTOR_DRONE": For drone/aerial response
    - "AMBULANCE": For ground ambulance response
    
    Handled Input Variations:
    - "DOCTOR DRONE", "Doctor Drone", "🚀 Doctor Drone" -> "DOCTOR_DRONE"
    - "AMBULANCE", "Ambulance", "🚑 Ambulance" -> "AMBULANCE"
    - Empty/None -> "AMBULANCE" (safe default)
    
    Args:
        decision: Raw decision string from data
    
    Returns:
        Normalized decision label
    
    Examples:
        >>> normalize_decision_label("🚀 Doctor Drone")
        'DOCTOR_DRONE'
        >>> normalize_decision_label("Ambulance")
        'AMBULANCE'
        >>> normalize_decision_label("")
        'AMBULANCE'
    """
    if not decision:
        return "AMBULANCE"
    
    # Remove all non-alphanumeric except spaces
    clean = re.sub(r'[^\w\s]', '', str(decision)).strip().upper()
    # Replace spaces with underscores
    clean = re.sub(r'\s+', '_', clean)
    
    # Check for drone/doctor keywords
    if 'DRONE' in clean or 'DOCTOR' in clean or 'AERIAL' in clean or 'AIR' in clean:
        return "DOCTOR_DRONE"
    else:
        return "AMBULANCE"


def parse_harm_time(time_str: str) -> Tuple[int, int]:
    """
    Parse time_to_irreversible_harm field into (min, max) minutes.
    
    Supported Formats:
    - Range: "4-6 m" -> (4, 6)
    - Range: "15-30 min" -> (15, 30)
    - Single: "30 min" -> (30, 30)
    - Greater than: ">60 m" -> (60, 60)
    - Invalid: returns (30, 30) as safe default
    
    Args:
        time_str: Raw time string from data
    
    Returns:
        Tuple of (harm_min, harm_max) in minutes
    
    Examples:
        >>> parse_harm_time("4-6 m")
        (4, 6)
        >>> parse_harm_time("30 min")
        (30, 30)
        >>> parse_harm_time(">60 m")
        (60, 60)
        >>> parse_harm_time("invalid")
        (30, 30)
    """
    if not time_str or not isinstance(time_str, str):
        logger.warning(f"Invalid harm time input: {time_str}, using default (30, 30)")
        return (30, 30)
    
    # Remove common unit variations
    clean = time_str.strip()
    clean = re.sub(r'[mM]in(utes?)?', '', clean)
    clean = re.sub(r'\s*[mM]\s*$', '', clean)
    clean = clean.strip()
    
    # Handle ">" prefix (e.g., ">60")
    clean = clean.lstrip('>')
    
    # Check for range (e.g., "4-6")
    if '-' in clean:
        parts = clean.split('-')
        try:
            harm_min = int(float(parts[0].strip()))
            harm_max = int(float(parts[1].strip()))
            
            # Validate range
            if harm_min > harm_max:
                harm_min, harm_max = harm_max, harm_min
            
            return (harm_min, harm_max)
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse range '{time_str}': {e}, using default")
            return (30, 30)
    
    # Single value
    try:
        val = int(float(clean))
        return (max(1, val), max(1, val))  # Ensure at least 1 minute
    except ValueError as e:
        logger.warning(f"Failed to parse harm time '{time_str}': {e}, using default")
        return (30, 30)


def normalize_severity_level(severity: str) -> int:
    """
    Convert severity string to numeric level.
    
    Severity Scale:
    - 0: Low/Minor
    - 1: Moderate/Medium
    - 2: High/Serious
    - 3: Critical/Life-threatening
    
    Args:
        severity: Severity string from data
    
    Returns:
        Integer severity level 0-3
    
    Examples:
        >>> normalize_severity_level("Critical")
        3
        >>> normalize_severity_level("High")
        2
        >>> normalize_severity_level("unknown")
        2
    """
    if not severity:
        return 2  # Default to High
    
    severity_map = {
        'critical': 3,
        'life-threatening': 3,
        'emergency': 3,
        'high': 2,
        'serious': 2,
        'medium': 1,
        'moderate': 1,
        'low': 0,
        'minor': 0,
    }
    
    normalized = severity.lower().strip()
    return severity_map.get(normalized, 2)  # Default to High if unknown


def normalize_case_name(name: str) -> str:
    """
    Normalize case name for fuzzy matching.
    
    Transformations:
    - Convert to lowercase
    - Remove punctuation (except spaces)
    - Collapse multiple spaces
    - Trim whitespace
    
    Args:
        name: Raw case name
    
    Returns:
        Normalized case name for matching
    
    Examples:
        >>> normalize_case_name("Cardiac Arrest!")
        'cardiac arrest'
        >>> normalize_case_name("  COPD   Exacerbation  ")
        'copd exacerbation'
    """
    if not name:
        return ""
    
    # Lowercase and trim
    clean = str(name).lower().strip()
    
    # Remove punctuation except spaces and hyphens
    clean = re.sub(r'[^\w\s-]', '', clean)
    
    # Collapse whitespace
    clean = re.sub(r'\s+', ' ', clean)
    
    return clean.strip()


def validate_required_fields(data: Dict[str, Any], required: List[str], context: str = "") -> bool:
    """
    Validate that required fields are present in data.
    
    Args:
        data: Data dictionary to validate
        required: List of required field names
        context: Context string for error messages
    
    Returns:
        True if all required fields present, False otherwise
    """
    missing = [field for field in required if field not in data or data[field] is None]
    
    if missing:
        logger.error(f"Missing required fields in {context}: {missing}")
        return False
    
    return True


# =============================================================================
# DATA LOADERS
# =============================================================================

def load_scenarios() -> List[Dict[str, Any]]:
    """
    Load and normalize scenarios.json.
    
    Expected Structure:
    - List of scenario objects with scenario_id, emergency_case, etc.
    
    Returns:
        List of normalized scenario dictionaries
    
    Raises:
        FileNotFoundError: If scenarios.json not found
        json.JSONDecodeError: If file is not valid JSON
    """
    path = FILES_DIR / "scenarios.json"
    
    if not path.exists():
        raise FileNotFoundError(f"Scenarios file not found: {path}")
    
    logger.info(f"Loading scenarios from {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    
    if not isinstance(raw, list):
        raise ValueError(f"Expected list of scenarios, got {type(raw)}")
    
    normalized = []
    for idx, s in enumerate(raw, 1):
        try:
            # Parse harm threshold (support both old and new field names)
            harm_val = s.get("harm_threshold_min", s.get("Harm Threshold (min)", 30))
            if isinstance(harm_val, str):
                harm_min, harm_max = parse_harm_time(harm_val)
            else:
                harm_min = harm_max = int(harm_val) if harm_val else 30
            
            # Get weather risk (support both old % and new decimal format)
            weather_raw = s.get("weather_risk_score", s.get("Weather Risk", 0))
            weather_pct = normalize_weather_risk(weather_raw)
            
            # Get traffic level (support both old % and new decimal format)
            traffic_raw = s.get("traffic_level_score", s.get("Traffic Level", 0))
            traffic_pct = normalize_weather_risk(traffic_raw)
            
            normalized_scenario = {
                # Identifiers
                "scenario_id": s.get("scenario_id", s.get("Scenario ID", idx)),
                
                # Location & Timing
                "location": s.get("location", s.get("Location", "Unknown")),
                "time_of_day": s.get("time_of_day", s.get("Time of Day", "Unknown")),
                
                # Emergency Details
                "emergency_case": s.get("emergency_case", s.get("Emergency Case", "Unknown Emergency")),
                "severity": s.get("severity", s.get("Severity", "High")),
                "severity_level": normalize_severity_level(s.get("severity", s.get("Severity", "High"))),
                
                # Environmental Factors (normalized to percent)
                "weather_risk_pct": weather_pct,
                "traffic_level_pct": traffic_pct / 100 if traffic_pct > 1 else traffic_pct,
                
                # Time Parameters
                "harm_threshold_min": harm_min,
                "harm_threshold_max": harm_max,
                "ground_eta_min": float(s.get("ground_time_min", s.get("Ground Time (min)", 20))),
                "air_eta_min": float(s.get("air_time_min", s.get("Air Time (min)", 3.6))),
                
                # Voice Stress Score (0.0-1.0)
                "voice_stress_score": float(s.get("voice_stress_score", 0.0)),
                
                # Expected Decision (normalized)
                "expected_decision": normalize_decision_label(s.get("ai_decision", s.get("AI Decision", ""))),
                "rationale": s.get("rationale", s.get("Rationale", "")),
                
                # Raw data for debugging
                "_raw": s,
            }
            
            normalized.append(normalized_scenario)
        
        except Exception as e:
            logger.error(f"Error processing scenario {idx}: {e}")
            logger.debug(f"Problematic data: {s}")
            continue
    
    logger.info(f"Loaded {len(normalized)} scenarios")
    return normalized


def load_cases() -> List[Dict[str, Any]]:
    """
    Load and normalize cases_send_decision.json.
    
    Expected Structure:
    - Nested: {"sheets": {"Sheet1": [...]}}
    - Or flat list of case objects
    
    Returns:
        List of normalized case dictionaries
    
    Raises:
        FileNotFoundError: If cases file not found
        json.JSONDecodeError: If file is not valid JSON
    """
    path = FILES_DIR / "cases_send_decision.json"
    
    if not path.exists():
        raise FileNotFoundError(f"Cases file not found: {path}")
    
    logger.info(f"Loading cases from {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    
    # Handle nested structure
    if isinstance(raw, dict) and "sheets" in raw:
        sheet = raw.get("sheets", {}).get("Sheet1", [])
    elif isinstance(raw, list):
        sheet = raw
    else:
        raise ValueError(f"Unexpected cases file structure: {type(raw)}")
    
    normalized = []
    for idx, c in enumerate(sheet, 1):
        try:
            # Parse harm threshold (support both old and new field names)
            harm_val = c.get("harm_threshold_min", c.get("Harm Limit (Min)", 30))
            if isinstance(harm_val, str):
                harm_min, harm_max = parse_harm_time(harm_val)
            else:
                harm_min = harm_max = int(harm_val) if harm_val else 30
            
            # Get weather risk (support both old % and new decimal format)
            weather_raw = c.get("weather_risk_score", c.get("Weather Risk", 0))
            weather_pct = normalize_weather_risk(weather_raw)
            
            # Get traffic flow (support both old and new field names)
            traffic_raw = c.get("traffic_flow_score", c.get("Traffic Flow", 0.5))
            traffic_flow = float(traffic_raw) if traffic_raw else 0.5
            
            normalized_case = {
                # Identifiers
                "case_id": idx,
                "case_name": c.get("case_name", c.get("Case", "Unknown Case")),
                
                # Medical Classification
                "severity": c.get("severity", c.get("Severity", "High")),
                "severity_level": normalize_severity_level(c.get("severity", c.get("Severity", "High"))),
                
                # Environmental Factors (normalized)
                "weather_risk_pct": weather_pct,
                "traffic_flow": traffic_flow,
                
                # Time Parameters
                "harm_threshold_min": harm_min,
                "harm_threshold_max": harm_max,
                "ground_eta_min": float(c.get("ground_eta_min", c.get("Ground ETA", 20))),
                "air_eta_min": float(c.get("air_eta_min", c.get("Air ETA", 3.6))),
                
                # Voice Stress Score (0.0-1.0)
                "voice_stress_score": float(c.get("voice_stress_score", 0.0)),
                
                # Expected Decision (normalized)
                "expected_decision": normalize_decision_label(c.get("ai_dispatch_prediction", c.get("AI Dispatch", ""))),
                "reasoning": c.get("reasoning", c.get("Reasoning", "")),
                
                # Raw data for debugging
                "_raw": c,
            }
            
            normalized.append(normalized_case)
        
        except Exception as e:
            logger.error(f"Error processing case {idx}: {e}")
            logger.debug(f"Problematic data: {c}")
            continue
    
    logger.info(f"Loaded {len(normalized)} cases")
    return normalized


def load_landing_zones() -> List[Dict[str, Any]]:
    """
    Load and normalize Al_Ghadir_Landing_Zones.json.
    
    Expected Structure:
    - Nested: {"sheets": {"Al Ghadir Landing Zones": [...]}}
    - List of zone objects with Place Name, coordinates, etc.
    
    Returns:
        List of normalized landing zone dictionaries
    
    Raises:
        FileNotFoundError: If landing zones file not found
    """
    path = FILES_DIR / "Al_Ghadir_Landing_Zones.json"
    
    if not path.exists():
        raise FileNotFoundError(f"Landing zones file not found: {path}")
    
    logger.info(f"Loading landing zones from {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    
    # Handle nested structure
    if isinstance(raw, dict) and "sheets" in raw:
        sheet = raw.get("sheets", {}).get("Al Ghadir Landing Zones", [])
    elif isinstance(raw, list):
        sheet = raw
    else:
        raise ValueError(f"Unexpected landing zones file structure: {type(raw)}")
    
    normalized = []
    for idx, z in enumerate(sheet, 1):
        try:
            normalized_zone = {
                "id": idx,
                "name": z.get("Place Name", f"Zone {idx}"),
                "area": z.get("Estimated Landing Area", "Unknown"),
                "latitude": float(z.get("Latitude", 0)),
                "longitude": float(z.get("Longitude", 0)),
                "_raw": z,
            }
            
            # Validate coordinates
            if not (-90 <= normalized_zone["latitude"] <= 90):
                logger.warning(f"Invalid latitude for {normalized_zone['name']}: {normalized_zone['latitude']}")
            if not (-180 <= normalized_zone["longitude"] <= 180):
                logger.warning(f"Invalid longitude for {normalized_zone['name']}: {normalized_zone['longitude']}")
            
            normalized.append(normalized_zone)
        
        except Exception as e:
            logger.error(f"Error processing landing zone {idx}: {e}")
            logger.debug(f"Problematic data: {z}")
            continue
    
    logger.info(f"Loaded {len(normalized)} landing zones")
    return normalized


def load_categorizer() -> List[Dict[str, Any]]:
    """
    Load and normalize Catergorizer.json (note spelling).
    
    Expected Structure:
    - List of medical case objects with id, case_name, category, etc.
    
    Returns:
        List of normalized categorizer dictionaries
    
    Raises:
        FileNotFoundError: If categorizer file not found
    """
    path = FILES_DIR / "medical_protocols.json"
    
    if not path.exists():
        raise FileNotFoundError(f"Categorizer file not found: {path}")
    
    logger.info(f"Loading categorizer from {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    
    if not isinstance(raw, list):
        raise ValueError(f"Expected list of medical cases, got {type(raw)}")
    
    normalized = []
    for c in raw:
        try:
            # Parse harm time range
            harm_min, harm_max = parse_harm_time(c.get("time_to_irreversible_harm", "30 m"))
            
            normalized_case = {
                "id": c.get("id", 0),
                "case_name": c.get("case_name", "Unknown Case"),
                "case_name_normalized": normalize_case_name(c.get("case_name", "")),
                "category": c.get("category", "Unknown"),
                "description": c.get("description", ""),
                
                # Medical Classification
                "severity": c.get("severity", "High"),
                "severity_level": normalize_severity_level(c.get("severity", "High")),
                "ctas": c.get("ctas", 2),  # Canadian Triage and Acuity Scale
                
                # Harm Threshold
                "harm_threshold_min": harm_min,
                "harm_threshold_max": harm_max,
                "harm_threshold_raw": c.get("time_to_irreversible_harm", ""),
                
                # Clinical Information
                "intervention": c.get("intervention_first_5m", ""),
                "equipment": c.get("required_core_equipments", ""),
                
                # Raw data for debugging
                "_raw": c,
            }
            
            normalized.append(normalized_case)
        
        except Exception as e:
            logger.error(f"Error processing categorizer case {c.get('id', 'unknown')}: {e}")
            logger.debug(f"Problematic data: {c}")
            continue
    
    logger.info(f"Loaded {len(normalized)} categorizer cases")
    return normalized


def load_all() -> Dict[str, List[Dict[str, Any]]]:
    """
    Load all data files at once.
    
    Returns:
        Dictionary with keys: scenarios, cases, landing_zones, categorizer
    
    Raises:
        FileNotFoundError: If any required file is missing
        ValueError: If any file has invalid structure
    """
    logger.info("Loading all data files...")
    
    data = {
        "scenarios": load_scenarios(),
        "cases": load_cases(),
        "landing_zones": load_landing_zones(),
        "categorizer": load_categorizer(),
    }
    
    logger.info(f"Successfully loaded all data: "
                f"{len(data['scenarios'])} scenarios, "
                f"{len(data['cases'])} cases, "
                f"{len(data['landing_zones'])} zones, "
                f"{len(data['categorizer'])} medical cases")
    
    return data


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("SAHM Data Loader - Validation & Testing")
    print("=" * 80)
    
    # Test normalization functions
    print("\n1. Weather Risk Normalization Tests:")
    test_cases = [
        ("'10%'", "10%", 10.0),
        ("0.88", 0.88, 88.0),
        ("35", 35, 35.0),
        ("'95%'", "95%", 95.0),
        ("None", None, 0.0),
    ]
    for desc, input_val, expected in test_cases:
        result = normalize_weather_risk(input_val)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {desc:20} -> {result:6.1f} (expected {expected})")
    
    print("\n2. Decision Label Normalization Tests:")
    test_cases = [
        ("'DOCTOR DRONE'", "DOCTOR DRONE", "DOCTOR_DRONE"),
        ("'🚀 Doctor Drone'", "🚀 Doctor Drone", "DOCTOR_DRONE"),
        ("'Ambulance'", "Ambulance", "AMBULANCE"),
        ("'🚑 AMBULANCE'", "🚑 AMBULANCE", "AMBULANCE"),
        ("Empty string", "", "AMBULANCE"),
    ]
    for desc, input_val, expected in test_cases:
        result = normalize_decision_label(input_val)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {desc:25} -> {result:15} (expected {expected})")
    
    print("\n3. Harm Time Parsing Tests:")
    test_cases = [
        ("'4-6 m'", "4-6 m", (4, 6)),
        ("'30 min'", "30 min", (30, 30)),
        ("'>60 m'", ">60 m", (60, 60)),
        ("'15-30 min'", "15-30 min", (15, 30)),
        ("Invalid", "xyz", (30, 30)),
    ]
    for desc, input_val, expected in test_cases:
        result = parse_harm_time(input_val)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {desc:20} -> {result} (expected {expected})")
    
    print("\n" + "=" * 80)
    print("Loading actual data files...")
    print("=" * 80)
    
    try:
        data = load_all()
        
        print(f"\n✓ Scenarios: {len(data['scenarios'])} loaded")
        if data['scenarios']:
            s = data['scenarios'][0]
            print(f"    Sample: {s['emergency_case']}")
            print(f"    Weather: {s['weather_risk_pct']:.1f}%")
            print(f"    Expected: {s['expected_decision']}")
        
        print(f"\n✓ Cases: {len(data['cases'])} loaded")
        if data['cases']:
            c = data['cases'][0]
            print(f"    Sample: {c['case_name']}")
            print(f"    Weather: {c['weather_risk_pct']:.1f}%")
            print(f"    Expected: {c['expected_decision']}")
        
        print(f"\n✓ Landing Zones: {len(data['landing_zones'])} loaded")
        if data['landing_zones']:
            z = data['landing_zones'][0]
            print(f"    Sample: {z['name']}")
            print(f"    Coords: {z['latitude']:.4f}°N, {z['longitude']:.4f}°E")
        
        print(f"\n✓ Medical Cases: {len(data['categorizer'])} loaded")
        if data['categorizer']:
            m = data['categorizer'][0]
            print(f"    Sample: {m['case_name']}")
            print(f"    Category: {m['category']}")
            print(f"    Harm: {m['harm_threshold_min']}-{m['harm_threshold_max']} min")
        
        print("\n" + "=" * 80)
        print("✓ ALL DATA LOADED AND NORMALIZED SUCCESSFULLY!")
        print("=" * 80)
    
    except FileNotFoundError as e:
        print(f"\n✗ FILE NOT FOUND: {e}")
        print("\nEnsure all JSON files are in the /Files directory:")
        print("  - scenarios.json")
        print("  - cases_send_decision.json")
        print("  - Al_Ghadir_Landing_Zones.json")
        print("  - Catergorizer.json")
    
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()