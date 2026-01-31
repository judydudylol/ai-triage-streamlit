"""
Validator Module
Tests scenarios.json and cases_send_decision.json against dispatch engine.

Validates that the dispatch engine produces expected decisions for all test cases.
Uses normalized labels for comparison and provides detailed mismatch analysis.

Run with: python validator.py
"""

from typing import List, Dict, Tuple
from dataclasses import dataclass, field
import json
from datetime import datetime
import logging

from .data_loader import load_scenarios, load_cases
from .dispatch_engine import dispatch, DispatchResult

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """
    Result of a single validation test.
    
    Attributes:
        id: Test identifier
        name: Test case name
        expected: Expected decision (DOCTOR_DRONE or AMBULANCE)
        actual: Actual decision from engine
        match: Whether expected matches actual
        details: Additional test details and reasoning
    """
    id: str
    name: str
    expected: str
    actual: str
    match: bool
    details: Dict = field(default_factory=dict)


@dataclass
class ValidationReport:
    """
    Summary report of validation run.
    
    Attributes:
        source: Data source (scenarios or cases)
        total: Total number of tests
        matches: Number of matching results
        mismatches: Number of mismatching results
        results: List of individual test results
        timestamp: When validation was run
    """
    source: str
    total: int
    matches: int
    mismatches: int
    results: List[ValidationResult]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def accuracy(self) -> float:
        """Calculate accuracy percentage."""
        return (self.matches / self.total * 100) if self.total > 0 else 0.0
    
    @property
    def pass_rate(self) -> str:
        """Get pass rate as formatted string."""
        return f"{self.matches}/{self.total}"


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_scenarios() -> ValidationReport:
    """
    Validate all entries in scenarios.json.
    
    Tests each scenario against the dispatch engine and compares
    the actual decision with the expected decision.
    
    Returns:
        ValidationReport with detailed results
    """
    logger.info("Starting scenarios validation...")
    
    scenarios = load_scenarios()
    results = []
    
    for scenario in scenarios:
        # Run dispatch with scenario parameters
        result = dispatch(
            weather_risk_pct=scenario["weather_risk_pct"],
            harm_threshold_min=scenario["harm_threshold_min"],
            ground_eta_min=scenario["ground_eta_min"],
            air_eta_min=scenario["air_eta_min"],
        )
        
        # Compare decisions (both are normalized)
        expected = scenario["expected_decision"]
        actual = result.response_mode
        match = (expected == actual)
        
        # Build detailed information
        details = {
            "rule_triggered": result.rule_triggered,
            "confidence": result.confidence,
            "weather_risk_pct": scenario["weather_risk_pct"],
            "harm_threshold_min": scenario["harm_threshold_min"],
            "ground_eta_min": scenario["ground_eta_min"],
            "air_eta_min": scenario["air_eta_min"],
            "time_delta_min": result.time_delta_min,
            "exceeds_weather": result.exceeds_weather,
            "exceeds_harm": result.exceeds_harm,
            "exceeds_efficiency": result.exceeds_efficiency,
            "expected_rationale": scenario.get("rationale", ""),
            "actual_reasons": result.reasons,
        }
        
        results.append(ValidationResult(
            id=f"Scenario {scenario['scenario_id']}",
            name=scenario["emergency_case"],
            expected=expected,
            actual=actual,
            match=match,
            details=details,
        ))
    
    matches = sum(1 for r in results if r.match)
    
    logger.info(f"Scenarios validation complete: {matches}/{len(results)} passed")
    
    return ValidationReport(
        source="scenarios.json",
        total=len(results),
        matches=matches,
        mismatches=len(results) - matches,
        results=results,
    )


def validate_cases() -> ValidationReport:
    """
    Validate all entries in cases_send_decision.json.
    
    Tests each case against the dispatch engine and compares
    the actual decision with the expected decision.
    
    Returns:
        ValidationReport with detailed results
    """
    logger.info("Starting cases validation...")
    
    cases = load_cases()
    results = []
    
    for case in cases:
        # Run dispatch with case parameters
        result = dispatch(
            weather_risk_pct=case["weather_risk_pct"],
            harm_threshold_min=case["harm_threshold_min"],
            ground_eta_min=case["ground_eta_min"],
            air_eta_min=case["air_eta_min"],
        )
        
        # Compare decisions (both are normalized)
        expected = case["expected_decision"]
        actual = result.response_mode
        match = (expected == actual)
        
        # Build detailed information
        details = {
            "rule_triggered": result.rule_triggered,
            "confidence": result.confidence,
            "weather_risk_pct": case["weather_risk_pct"],
            "harm_threshold_min": case["harm_threshold_min"],
            "ground_eta_min": case["ground_eta_min"],
            "air_eta_min": case["air_eta_min"],
            "time_delta_min": result.time_delta_min,
            "exceeds_weather": result.exceeds_weather,
            "exceeds_harm": result.exceeds_harm,
            "exceeds_efficiency": result.exceeds_efficiency,
            "expected_reasoning": case.get("reasoning", ""),
            "actual_reasons": result.reasons,
        }
        
        results.append(ValidationResult(
            id=f"Case {case['case_id']}",
            name=case["case_name"],
            expected=expected,
            actual=actual,
            match=match,
            details=details,
        ))
    
    matches = sum(1 for r in results if r.match)
    
    logger.info(f"Cases validation complete: {matches}/{len(results)} passed")
    
    return ValidationReport(
        source="cases_send_decision.json",
        total=len(results),
        matches=matches,
        mismatches=len(results) - matches,
        results=results,
    )


def run_full_validation() -> Tuple[ValidationReport, ValidationReport]:
    """
    Run validation on both scenarios and cases.
    
    Returns:
        Tuple of (scenarios_report, cases_report)
    """
    logger.info("Running full validation suite...")
    
    scenarios_report = validate_scenarios()
    cases_report = validate_cases()
    
    return scenarios_report, cases_report


# =============================================================================
# REPORTING & ANALYSIS
# =============================================================================

def print_validation_report(
    report: ValidationReport,
    show_matches: bool = False,
    show_details: bool = False,
) -> None:
    """
    Print formatted validation report to console.
    
    Args:
        report: ValidationReport to print
        show_matches: Whether to show passing tests (default: False)
        show_details: Whether to show detailed parameters (default: False)
    """
    print(f"\n{'='*80}")
    print(f"{report.source} Validation Report")
    print(f"{'='*80}")
    print(f"Timestamp: {report.timestamp}")
    print(f"Results: {report.pass_rate} ({report.accuracy:.1f}% accuracy)")
    print(f"  ✓ Matches: {report.matches}")
    print(f"  ✗ Mismatches: {report.mismatches}")
    
    # Show mismatches (always)
    if report.mismatches > 0:
        print(f"\n{'─'*80}")
        print("MISMATCHES:")
        print(f"{'─'*80}")
        
        for r in report.results:
            if not r.match:
                print(f"\n  ✗ {r.id}: {r.name}")
                print(f"      Expected: {r.expected}")
                print(f"      Got: {r.actual} (Rule: {r.details.get('rule_triggered')})")
                
                if show_details:
                    print(f"      Parameters:")
                    print(f"        Weather: {r.details.get('weather_risk_pct'):.1f}%")
                    print(f"        Ground ETA: {r.details.get('ground_eta_min'):.1f} min")
                    print(f"        Air ETA: {r.details.get('air_eta_min'):.1f} min")
                    print(f"        Harm Limit: {r.details.get('harm_threshold_min')} min")
                    print(f"        Time Delta: {r.details.get('time_delta_min'):.1f} min")
                    print(f"      Thresholds:")
                    print(f"        Weather: {r.details.get('exceeds_weather')}")
                    print(f"        Harm: {r.details.get('exceeds_harm')}")
                    print(f"        Efficiency: {r.details.get('exceeds_efficiency')}")
    
    # Show matches (optional)
    if show_matches and report.matches > 0:
        print(f"\n{'─'*80}")
        print("MATCHES:")
        print(f"{'─'*80}")
        
        for r in report.results:
            if r.match:
                print(f"  ✓ {r.id}: {r.name}")
                print(f"      Decision: {r.actual} (Rule: {r.details.get('rule_triggered')})")


def analyze_mismatches(report: ValidationReport) -> Dict:
    """
    Analyze mismatch patterns to identify systematic issues.
    
    Args:
        report: ValidationReport to analyze
    
    Returns:
        Dictionary with analysis results
    """
    if report.mismatches == 0:
        return {"no_mismatches": True}
    
    mismatches = [r for r in report.results if not r.match]
    
    # Count by rule that was actually triggered
    rules_used = {}
    for m in mismatches:
        rule = m.details.get('rule_triggered', 'UNKNOWN')
        rules_used[rule] = rules_used.get(rule, 0) + 1
    
    # Count by expected vs actual decision
    direction_errors = {
        "expected_drone_got_ambulance": 0,
        "expected_ambulance_got_drone": 0,
    }
    
    for m in mismatches:
        if m.expected == "DOCTOR_DRONE" and m.actual == "AMBULANCE":
            direction_errors["expected_drone_got_ambulance"] += 1
        elif m.expected == "AMBULANCE" and m.actual == "DOCTOR_DRONE":
            direction_errors["expected_ambulance_got_drone"] += 1
    
    # Calculate average threshold exceedances for mismatches
    avg_weather = sum(m.details.get('weather_risk_pct', 0) for m in mismatches) / len(mismatches)
    avg_time_delta = sum(m.details.get('time_delta_min', 0) for m in mismatches) / len(mismatches)
    
    return {
        "total_mismatches": len(mismatches),
        "rules_triggered": rules_used,
        "direction_errors": direction_errors,
        "avg_weather_risk": round(avg_weather, 1),
        "avg_time_delta": round(avg_time_delta, 1),
    }


def export_report_json(report: ValidationReport, filename: str) -> None:
    """
    Export validation report to JSON file.
    
    Args:
        report: ValidationReport to export
        filename: Output filename
    """
    data = {
        "source": report.source,
        "timestamp": report.timestamp,
        "summary": {
            "total": report.total,
            "matches": report.matches,
            "mismatches": report.mismatches,
            "accuracy": report.accuracy,
        },
        "results": [
            {
                "id": r.id,
                "name": r.name,
                "expected": r.expected,
                "actual": r.actual,
                "match": r.match,
                "details": r.details,
            }
            for r in report.results
        ],
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"Report exported to {filename}")


def print_combined_summary(
    scenarios_report: ValidationReport,
    cases_report: ValidationReport,
) -> None:
    """
    Print combined summary of both validation reports.
    
    Args:
        scenarios_report: Scenarios validation report
        cases_report: Cases validation report
    """
    total = scenarios_report.total + cases_report.total
    matches = scenarios_report.matches + cases_report.matches
    mismatches = scenarios_report.mismatches + cases_report.mismatches
    accuracy = (matches / total * 100) if total > 0 else 0.0
    
    print(f"\n{'='*80}")
    print("COMBINED VALIDATION SUMMARY")
    print(f"{'='*80}")
    print(f"Total Tests: {total}")
    print(f"  Scenarios: {scenarios_report.pass_rate} ({scenarios_report.accuracy:.1f}%)")
    print(f"  Cases: {cases_report.pass_rate} ({cases_report.accuracy:.1f}%)")
    print(f"\nOverall Accuracy: {matches}/{total} ({accuracy:.1f}%)")
    
    if mismatches == 0:
        print(f"\n🎉 ALL TESTS PASSED! 🎉")
        print("The dispatch engine matches all expected decisions.")
    else:
        print(f"\n⚠️  {mismatches} mismatch(es) found")
        print("\nPossible causes:")
        print("  • Dataset inconsistency (expected decision doesn't follow D1.md rules)")
        print("  • Threshold values may need adjustment")
        print("  • Edge cases at decision boundaries")
        
        # Analyze patterns
        print("\nMismatch Analysis:")
        
        if scenarios_report.mismatches > 0:
            analysis = analyze_mismatches(scenarios_report)
            print(f"\n  Scenarios:")
            print(f"    Rules triggered: {analysis.get('rules_triggered', {})}")
            print(f"    Direction errors: {analysis.get('direction_errors', {})}")
        
        if cases_report.mismatches > 0:
            analysis = analyze_mismatches(cases_report)
            print(f"\n  Cases:")
            print(f"    Rules triggered: {analysis.get('rules_triggered', {})}")
            print(f"    Direction errors: {analysis.get('direction_errors', {})}")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("SAHM DISPATCH ENGINE VALIDATION")
    print("=" * 80)
    print("\nValidating dispatch decisions against test datasets...")
    print("D1.md Specification: 3-step rule-based logic")
    
    try:
        # Run full validation
        scenarios_report, cases_report = run_full_validation()
        
        # Print individual reports
        print_validation_report(
            scenarios_report,
            show_matches=False,
            show_details=True
        )
        
        print_validation_report(
            cases_report,
            show_matches=False,
            show_details=True
        )
        
        # Print combined summary
        print_combined_summary(scenarios_report, cases_report)
        
        # Export if there are any mismatches
        if scenarios_report.mismatches > 0:
            export_report_json(scenarios_report, "scenarios_validation.json")
            print(f"\n📄 Scenarios report exported to scenarios_validation.json")
        
        if cases_report.mismatches > 0:
            export_report_json(cases_report, "cases_validation.json")
            print(f"📄 Cases report exported to cases_validation.json")
        
        # Exit code
        total_mismatches = scenarios_report.mismatches + cases_report.mismatches
        if total_mismatches == 0:
            print("\n" + "=" * 80)
            print("✓ VALIDATION PASSED - All tests successful")
            print("=" * 80)
            exit(0)
        else:
            print("\n" + "=" * 80)
            print(f"✗ VALIDATION FAILED - {total_mismatches} mismatch(es)")
            print("=" * 80)
            exit(1)
    
    except FileNotFoundError as e:
        print(f"\n✗ FILE ERROR: {e}")
        print("\nRequired files:")
        print("  - /Files/scenarios.json")
        print("  - /Files/cases_send_decision.json")
        exit(2)
    
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(3)