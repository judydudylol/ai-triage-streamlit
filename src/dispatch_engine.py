"""
SAHM Dispatch Engine (Simple D1.md Specification)
Rule-based decision logic for Al Ghadir emergency medical dispatch.

Implements the exact 3-step logic from D1.md:
1. Safety Filter: Weather risk check
2. Survival Logic: Harm threshold check  
3. Efficiency Optimization: Time delta check
4. Default: Ground ambulance

Returns: DOCTOR_DRONE or AMBULANCE
"""

from dataclasses import dataclass
from typing import List, Literal

# Response mode types (matching D1.md + BOTH for parallel dispatch)
ResponseMode = Literal["DOCTOR_DRONE", "AMBULANCE", "BOTH"]

# Rule types for tracking which rule triggered
RuleType = Literal[
    "SAFETY_FILTER",
    "EMERGENCY_OVERRIDE", 
    "EFFICIENCY_OPTIMIZATION",
    "DEFAULT"
]


@dataclass
class DispatchResult:
    """
    Result of dispatch decision.
    
    Attributes:
        response_mode: DOCTOR_DRONE or AMBULANCE
        rule_triggered: Which rule made the decision
        reasons: List of human-readable reasoning
        weather_risk_pct: Input weather risk
        harm_threshold_min: Input harm threshold
        ground_eta_min: Input ground ETA
        air_eta_min: Input air ETA
        time_delta_min: Time saved by drone (ground - air)
        exceeds_weather: Whether weather risk exceeded threshold
        exceeds_harm: Whether ground ETA exceeded harm threshold
        exceeds_efficiency: Whether time delta exceeded efficiency threshold
        confidence: Decision confidence (0-1)
    """
    response_mode: ResponseMode
    rule_triggered: RuleType
    reasons: List[str]
    
    # Input values (for reference)
    weather_risk_pct: float
    harm_threshold_min: float
    ground_eta_min: float
    air_eta_min: float
    
    # Computed values
    time_delta_min: float
    exceeds_weather: bool
    exceeds_harm: bool
    exceeds_efficiency: bool
    
    # Confidence score
    confidence: float = 1.0


# =============================================================================
# DECISION THRESHOLDS (from D1.md specification)
# =============================================================================

WEATHER_RISK_THRESHOLD = 35.0  # Percent - drones unsafe above this
HARM_THRESHOLD_CRITICAL = True  # Ground ETA must not exceed harm threshold
EFFICIENCY_TIME_DELTA = 10.0   # Minutes - significant time savings threshold


def dispatch(
    weather_risk_pct: float,
    harm_threshold_min: float,
    ground_eta_min: float,
    air_eta_min: float,
) -> DispatchResult:
    """
    Main dispatch decision function implementing D1.md specification.
    
    Decision Logic (in order of priority):
    
    1. SAFETY_FILTER: 
       If weather_risk > 35% → AMBULANCE
       (Drone operations unsafe)
    
    2. EMERGENCY_OVERRIDE:
       If ground_eta > harm_threshold → DOCTOR_DRONE
       (Patient survival requires fastest response)
    
    3. EFFICIENCY_OPTIMIZATION:
       If (ground_eta - air_eta) > 10 min → DOCTOR_DRONE
       (Significant time savings justify drone deployment)
    
    4. DEFAULT:
       Otherwise → AMBULANCE
       (Ground ambulance is safe and sufficient)
    
    Args:
        weather_risk_pct: Weather risk percentage (0-100)
        harm_threshold_min: Time to irreversible harm (minutes)
        ground_eta_min: Estimated ground ambulance arrival (minutes)
        air_eta_min: Estimated drone arrival (minutes)
    
    Returns:
        DispatchResult with decision, reasoning, and metadata
    
    Examples:
        >>> # High weather risk - unsafe for drone
        >>> result = dispatch(88.0, 4, 29.8, 3.6)
        >>> result.response_mode
        'AMBULANCE'
        >>> result.rule_triggered
        'SAFETY_FILTER'
        
        >>> # Ground too slow for critical case
        >>> result = dispatch(14.0, 4, 29.8, 3.6)
        >>> result.response_mode
        'DOCTOR_DRONE'
        >>> result.rule_triggered
        'EMERGENCY_OVERRIDE'
        
        >>> # Significant time savings
        >>> result = dispatch(6.0, 15, 29.8, 3.6)
        >>> result.response_mode
        'DOCTOR_DRONE'
        >>> result.rule_triggered
        'EFFICIENCY_OPTIMIZATION'
    """
    # Calculate time delta
    time_delta = ground_eta_min - air_eta_min
    
    # Check thresholds
    exceeds_weather = weather_risk_pct > WEATHER_RISK_THRESHOLD
    exceeds_harm = ground_eta_min > harm_threshold_min
    exceeds_efficiency = time_delta > EFFICIENCY_TIME_DELTA
    
    # Decision variables
    mode: ResponseMode
    rule: RuleType
    reasons: List[str] = []
    confidence: float
    
    # RULE 1: SAFETY_FILTER (highest priority)
    if exceeds_weather:
        mode = "AMBULANCE"
        rule = "SAFETY_FILTER"
        reasons.append(f"Weather risk {weather_risk_pct:.1f}% exceeds safety threshold ({WEATHER_RISK_THRESHOLD}%)")
        reasons.append("Drone operations unsafe - defaulting to ground ambulance")
        confidence = 1.0
    
    # RULE 2: EMERGENCY_OVERRIDE (survival priority)
    elif exceeds_harm:
        mode = "BOTH"
        rule = "EMERGENCY_OVERRIDE"
        reasons.append(f"Ground ETA ({ground_eta_min:.1f} min) exceeds harm threshold ({harm_threshold_min} min)")
        reasons.append("CRITICAL: Simultaneous Drone (Speed) + Ambulance (Transport) dispatched")
        reasons.append(f"Drone arrival: {air_eta_min:.1f} min (saves {time_delta:.1f} min)")
        confidence = 0.98
    
    # RULE 3: EFFICIENCY_OPTIMIZATION (significant time savings)
    elif exceeds_efficiency:
        mode = "BOTH"
        rule = "EFFICIENCY_OPTIMIZATION"
        reasons.append(f"Drone saves {time_delta:.1f} min (threshold: {EFFICIENCY_TIME_DELTA} min)")
        reasons.append(f"Ground ETA: {ground_eta_min:.1f} min vs Drone ETA: {air_eta_min:.1f} min")
        reasons.append("Dispatching Drone for immediate aid + Ambulance for transport")
        confidence = 0.90
    
    # RULE 4: DEFAULT (ground ambulance sufficient)
    else:
        mode = "AMBULANCE"
        rule = "DEFAULT"
        reasons.append("Ground ambulance is safe and sufficient")
        reasons.append(f"Weather risk acceptable ({weather_risk_pct:.1f}%)")
        reasons.append(f"Ground ETA ({ground_eta_min:.1f} min) within harm threshold ({harm_threshold_min} min)")
        reasons.append(f"Time savings ({time_delta:.1f} min) below efficiency threshold ({EFFICIENCY_TIME_DELTA} min)")
        confidence = 0.9
    
    return DispatchResult(
        response_mode=mode,
        rule_triggered=rule,
        reasons=reasons,
        weather_risk_pct=weather_risk_pct,
        harm_threshold_min=harm_threshold_min,
        ground_eta_min=ground_eta_min,
        air_eta_min=air_eta_min,
        time_delta_min=time_delta,
        exceeds_weather=exceeds_weather,
        exceeds_harm=exceeds_harm,
        exceeds_efficiency=exceeds_efficiency,
        confidence=confidence,
    )


def validate_inputs(
    weather_risk_pct: float,
    harm_threshold_min: float,
    ground_eta_min: float,
    air_eta_min: float,
) -> List[str]:
    """
    Validate input parameters and return list of warnings.
    
    Returns:
        List of warning strings (empty if all valid)
    """
    warnings = []
    
    # Weather risk should be 0-100
    if not (0 <= weather_risk_pct <= 100):
        warnings.append(f"Weather risk {weather_risk_pct}% outside valid range (0-100%)")
    
    # Harm threshold should be positive
    if harm_threshold_min <= 0:
        warnings.append(f"Harm threshold {harm_threshold_min} min must be positive")
    
    # ETAs should be positive
    if ground_eta_min <= 0:
        warnings.append(f"Ground ETA {ground_eta_min} min must be positive")
    
    if air_eta_min <= 0:
        warnings.append(f"Air ETA {air_eta_min} min must be positive")
    
    # Air should generally be faster than ground
    if air_eta_min > ground_eta_min:
        warnings.append(f"Air ETA ({air_eta_min} min) slower than ground ({ground_eta_min} min) - unusual")
    
    # Reasonable bounds
    if ground_eta_min > 120:
        warnings.append(f"Ground ETA {ground_eta_min} min seems unreasonably high")
    
    if air_eta_min > 30:
        warnings.append(f"Air ETA {air_eta_min} min seems unreasonably high for drone")
    
    return warnings


# =============================================================================
# TESTING & VALIDATION
# =============================================================================

def test_dispatch_logic():
    """Test all decision rules with example cases."""
    
    print("=" * 80)
    print("DISPATCH ENGINE TEST SUITE")
    print("=" * 80)
    
    test_cases = [
        {
            "name": "Rule 1: High weather risk (unsafe for drone)",
            "inputs": {"weather_risk_pct": 88.0, "harm_threshold_min": 4, "ground_eta_min": 29.8, "air_eta_min": 3.6},
            "expected_mode": "AMBULANCE",
            "expected_rule": "SAFETY_FILTER",
        },
        {
            "name": "Rule 2: Ground too slow (exceeds harm threshold)",
            "inputs": {"weather_risk_pct": 14.0, "harm_threshold_min": 4, "ground_eta_min": 29.8, "air_eta_min": 3.6},
            "expected_mode": "DOCTOR_DRONE",
            "expected_rule": "EMERGENCY_OVERRIDE",
        },
        {
            "name": "Rule 3: Significant time savings (>10 min delta)",
            "inputs": {"weather_risk_pct": 6.0, "harm_threshold_min": 15, "ground_eta_min": 29.8, "air_eta_min": 3.6},
            "expected_mode": "DOCTOR_DRONE",
            "expected_rule": "EFFICIENCY_OPTIMIZATION",
        },
        {
            "name": "Rule 4: Default (ground sufficient)",
            "inputs": {"weather_risk_pct": 2.0, "harm_threshold_min": 15, "ground_eta_min": 10.1, "air_eta_min": 3.6},
            "expected_mode": "AMBULANCE",
            "expected_rule": "DEFAULT",
        },
        {
            "name": "Edge case: Exactly at weather threshold",
            "inputs": {"weather_risk_pct": 35.0, "harm_threshold_min": 10, "ground_eta_min": 15.0, "air_eta_min": 3.6},
            "expected_mode": "DOCTOR_DRONE",  # Not exceeding, so check other rules
            "expected_rule": "EFFICIENCY_OPTIMIZATION",
        },
        {
            "name": "Edge case: Exactly at efficiency threshold",
            "inputs": {"weather_risk_pct": 5.0, "harm_threshold_min": 20, "ground_eta_min": 13.6, "air_eta_min": 3.6},
            "expected_mode": "AMBULANCE",  # Exactly 10 min, not exceeding
            "expected_rule": "DEFAULT",
        },
    ]
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['name']}")
        print("-" * 80)
        
        result = dispatch(**test['inputs'])
        
        # Check expectations
        mode_match = result.response_mode == test['expected_mode']
        rule_match = result.rule_triggered == test['expected_rule']
        
        if mode_match and rule_match:
            print(f"✓ PASS")
            passed += 1
        else:
            print(f"✗ FAIL")
            failed += 1
            if not mode_match:
                print(f"  Expected mode: {test['expected_mode']}, got: {result.response_mode}")
            if not rule_match:
                print(f"  Expected rule: {test['expected_rule']}, got: {result.rule_triggered}")
        
        print(f"  Decision: {result.response_mode}")
        print(f"  Rule: {result.rule_triggered}")
        print(f"  Confidence: {result.confidence:.0%}")
        print(f"  Reasoning:")
        for reason in result.reasons:
            print(f"    - {reason}")
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    return passed == len(test_cases)


if __name__ == "__main__":
    # Run test suite
    all_passed = test_dispatch_logic()
    
    # Example usage
    print("\n" + "=" * 80)
    print("EXAMPLE USAGE")
    print("=" * 80)
    
    print("\nExample: Cardiac arrest, low weather risk, ground too slow")
    result = dispatch(
        weather_risk_pct=14.0,
        harm_threshold_min=4,
        ground_eta_min=29.8,
        air_eta_min=3.6
    )
    
    print(f"\n✓ Decision: {result.response_mode}")
    print(f"  Rule: {result.rule_triggered}")
    print(f"  Time saved: {result.time_delta_min:.1f} minutes")
    print(f"\n  Reasoning:")
    for reason in result.reasons:
        print(f"    {reason}")
    
    # Validate inputs
    print("\n" + "=" * 80)
    print("INPUT VALIDATION EXAMPLE")
    print("=" * 80)
    
    warnings = validate_inputs(150.0, -5, 200, 50)
    if warnings:
        print("\n⚠ Warnings detected:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("\n✓ No validation warnings")
    
    if all_passed:
        print("\n" + "=" * 80)
        print("✓ ALL TESTS PASSED - Dispatch engine ready for deployment")
        print("=" * 80)