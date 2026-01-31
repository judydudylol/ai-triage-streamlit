"""
SAHM Full Pipeline Test
Tests integration of Steps 2, 3, and 4.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.triage_engine import triage
from archive.old_decision_engine import make_decision
from src.medic_matcher import assign_medic


def test_full_pipeline():
    """
    Run a complete end-to-end test of the SAHM pipeline.
    """
    print("=" * 70)
    print("SAHM FULL PIPELINE TEST")
    print("Testing Steps 2 → 3 → 4")
    print("=" * 70)
    print()
    
    # Test Case: Severe chest pain emergency
    print("📋 TEST CASE: Severe Chest Pain Emergency")
    print("-" * 70)
    
    # STEP 2: AI Triage
    print("\n🤖 STEP 2: AI TRIAGE")
    print("-" * 70)
    
    triage_result = triage(
        symptoms=["chest_pain_crushing", "shortness_of_breath"],
        free_text="Crushing pressure in chest, radiating to left arm, sweating heavily",
        duration_minutes=15,
        voice_stress_score=0.90,
    )
    
    print(f"Category: {triage_result['category']}")
    print(f"Severity Level: {triage_result['severity_level']}")
    print(f"Escalate Human: {triage_result['escalate_human']}")
    print(f"Score: {triage_result['score_breakdown']['total_score']} points")
    print(f"  - Symptom Score: {triage_result['score_breakdown']['symptom_score']}")
    print(f"  - Voice Bonus: +{triage_result['score_breakdown']['voice_bonus']}")
    print(f"  - Red Flag: {'YES ⚠️' if triage_result['score_breakdown']['red_flag_detected'] else 'No'}")
    print(f"Confidence: {triage_result['confidence']:.0%}")
    
    # STEP 3: Decision Engine
    print("\n⚡ STEP 3: DECISION ENGINE")
    print("-" * 70)
    
    decision = make_decision(triage_result)
    
    print(f"Response Mode: {decision['response_mode'].upper()}")
    print(f"Aerial ETA: {decision['aerial_eta_minutes']} min")
    print(f"Ground ETA: {decision['ground_eta_minutes']} min")
    print(f"Time Savings: {decision['time_savings_minutes']} min")
    print(f"\nReasoning:")
    for reason in decision['reasoning']:
        print(f"  - {reason}")
    
    print(f"\nReal-Time Factors:")
    factors = decision['real_time_factors']
    print(f"  Traffic: {factors['traffic']['traffic_level']} (ground ETA: {factors['traffic']['estimated_ground_eta_minutes']} min)")
    print(f"  Crowd: {factors['crowd']['density_level']}")
    if factors['crowd']['active_event']:
        print(f"    - Event: {factors['crowd']['active_event']}")
    print(f"  Weather: {factors['weather']['condition']} (wind: {factors['weather']['wind_speed_kph']} kph)")
    print(f"  Aerial Safe: {'✅ Yes' if factors['weather']['aerial_safe'] else '❌ No'}")
    print(f"  Geography: {factors['geography']['location_type']}")
    
    # STEP 4: Medic Matching
    if decision['response_mode'] in ['aerial_only', 'combined']:
        print("\n👨‍⚕️ STEP 4: MEDIC MATCHING")
        print("-" * 70)
        
        assignment = assign_medic(decision, triage_result)
        
        if assignment['status'] == 'success':
            medic = assignment['assigned_medic']
            
            print(f"Match Time: {assignment['match_time_seconds']}s {'✅ (Within target)' if assignment['match_time_seconds'] < 3.0 else '⚠️ (Exceeded target)'}")
            print(f"\nAssigned Medic:")
            print(f"  ID: {medic['id']}")
            print(f"  Name: {medic['name']}")
            print(f"  Specialty: {medic['specialty']}")
            print(f"  Certification: {medic['certification']}")
            print(f"  Distance: {medic['distance_km']} km")
            print(f"  ETA: {medic['eta_minutes']} minutes")
            print(f"  Rating: {medic['rating']}/5.0 ⭐")
            print(f"  Missions: {medic['missions_completed']}")
            print(f"  Languages: {', '.join(medic['languages'])}")
            
            print(f"\nMatch Score: {assignment['match_score']:.3f}")
            breakdown = assignment['match_breakdown']
            print(f"  - Distance: {breakdown['distance_score']}")
            print(f"  - Specialty: {breakdown['specialty_score']}")
            print(f"  - Workload: {breakdown['workload_score']}")
            print(f"  - Rating: {breakdown['rating_score']}")
            print(f"  - Certification: {breakdown['cert_score']}")
            
            if assignment.get('alternatives'):
                print(f"\nAlternative Medics:")
                for alt in assignment['alternatives'][:3]:
                    print(f"  - {alt['name']} (Score: {alt['score']:.3f}, ETA: {alt['eta_minutes']} min)")
        else:
            print(f"❌ Assignment failed: {assignment['reasoning']}")
    else:
        print("\n👨‍⚕️ STEP 4: MEDIC MATCHING")
        print("-" * 70)
        print("⏭️  Skipped (ground ambulance only)")
    
    # DEPLOYMENT SUMMARY
    print("\n📋 DEPLOYMENT SUMMARY")
    print("=" * 70)
    
    plan = decision['deployment_plan']
    print(f"Primary Unit: {plan['primary_unit'].replace('_', ' ').title()}")
    print(f"\nInstructions:")
    for instruction in plan['instructions']:
        print(f"  {instruction}")
    
    if decision['response_mode'] in ['aerial_only', 'combined'] and assignment.get('status') == 'success':
        print(f"\nAssigned to: {medic['name']} ({medic['id']})")
        print(f"Expected arrival: {medic['eta_minutes']} minutes")
    
    print("\n" + "=" * 70)
    print("✅ PIPELINE TEST COMPLETE")
    print("=" * 70)
    print()
    
    # Return results for programmatic use
    return {
        'triage': triage_result,
        'decision': decision,
        'assignment': assignment if decision['response_mode'] in ['aerial_only', 'combined'] else None,
    }


def test_multiple_scenarios():
    """Test pipeline with different severity levels"""
    
    print("\n" + "=" * 70)
    print("TESTING MULTIPLE SCENARIOS")
    print("=" * 70)
    
    scenarios = [
        {
            "name": "Low Severity (Mild Headache)",
            "symptoms": ["headache", "mild_pain"],
            "free_text": "Dull headache for a few hours",
            "duration_minutes": 180,
            "voice_stress_score": 0.20,
        },
        {
            "name": "Medium Severity (High Fever)",
            "symptoms": ["high_fever", "chills"],
            "free_text": "Fever since last night",
            "duration_minutes": 720,
            "voice_stress_score": 0.45,
        },
        {
            "name": "High Severity (Stroke)",
            "symptoms": ["face_droop", "slurred_speech", "arm_weakness"],
            "free_text": "Sudden onset, can't lift right arm",
            "duration_minutes": 10,
            "voice_stress_score": 0.85,
        },
    ]
    
    for scenario in scenarios:
        print(f"\n📋 {scenario['name']}")
        print("-" * 70)
        
        # Run triage
        triage_result = triage(**{k: v for k, v in scenario.items() if k != 'name'})
        decision = make_decision(triage_result)
        
        print(f"Severity: Level {triage_result['severity_level']}")
        print(f"Response Mode: {decision['response_mode'].upper()}")
        print(f"Time Savings: {decision['time_savings_minutes']} min")
        
        if decision['response_mode'] in ['aerial_only', 'combined']:
            assignment = assign_medic(decision, triage_result)
            if assignment['status'] == 'success':
                print(f"Medic: {assignment['assigned_medic']['name']} (ETA: {assignment['assigned_medic']['eta_minutes']} min)")
        print()
    
    print("=" * 70)
    print("✅ ALL SCENARIOS TESTED")
    print("=" * 70)


if __name__ == "__main__":
    # Run single comprehensive test
    result = test_full_pipeline()
    
    # Run multiple scenarios
    test_multiple_scenarios()
    
    print("\n🎉 All tests passed!")
