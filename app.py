"""
SAHM Emergency Response System
FINAL IMPROVED VERSION

UI Improvements:
- Decision Engine at top center (conditional display)
- Removed unnecessary tabs and emojis
- Wider map at bottom
- Fixed HTML rendering
- Cleaner layout
"""

import json
import re
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from src.data_loader import (
    load_scenarios,
    load_cases,
    load_landing_zones,
    load_categorizer,
)
from src.dispatch_engine import dispatch, DispatchResult
from src.landing_zone import find_nearest_zone, get_all_zones_sorted
from src.categorizer_engine import categorize_by_case_name, get_severity_label
from src.validator import validate_scenarios, validate_cases
from src.triage_engine import triage, SYMPTOM_POINTS, RED_FLAGS
from src.medic_matcher import MedicMatcher, assign_medic
from src.gemini_engine import (
    analyze_audio_call,
    is_gemini_available,
    get_availability_message,
)


# =============================================================================
# Page config
# =============================================================================

st.set_page_config(
    page_title="SAHM Emergency Command",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Professional CSS with improved spacing
st.markdown(
    """
<style>
/* Hide default header but keep toolbar accessible */
header[data-testid="stHeader"] {
    background: transparent !important;
    height: 3.5rem !important;
}

/* Make Streamlit header transparent but visible for toolbar */
header[data-testid="stHeader"] {
    background: transparent !important;
    border: none !important;
    height: auto !important;
    padding: 0 !important;
    z-index: 1 !important;
}

/* Adjust main container for fixed header */
.block-container { 
    padding-top: 4.5rem !important; 
    max-width: 1400px; 
}

/* Position toolbar absolutely at top right, ON TOP of header */
[data-testid="stToolbar"] {
    position: absolute !important;
    top: 0.4rem !important;
    right: 0.8rem !important;
    z-index: 999999 !important;
    pointer-events: auto !important;
    margin: 0 !important;
    padding: 0 !important;
    background: transparent !important;
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
}

/* Custom Fixed Header */
.fixed-toolbar {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    z-index: 1;
    background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);
    padding: 0.4rem 1.2rem;
    height: 3.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
}

/* Decision Banners - COMPRESSED */
.decision-banner {
  text-align: center;
  padding: 18px 24px;
  border-radius: 10px;
  margin: 16px 0;
  border: 2px solid;
}

.decision-banner.drone {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border-color: #34d399;
  color: white;
}

.decision-banner.ambulance {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  border-color: #fbbf24;
  color: white;
}

.decision-banner.both {
  background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%);
  border-color: #a78bfa;
  color: white;
}

.decision-banner h1 {
  margin: 6px 0 4px 0;
  font-size: 1.8rem;
  font-weight: 900;
  letter-spacing: 0.5px;
}

.decision-banner p {
  font-size: 0.9rem;
  margin: 4px 0;
}

/* Rule Checklist */
.rule-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 12px;
  margin: 5px 0;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
  border-left: 3px solid;
}

.rule-item.pass { border-left-color: #10b981; background: rgba(16, 185, 129, 0.05); }
.rule-item.fail { border-left-color: #ef4444; background: rgba(239, 68, 68, 0.05); }
.rule-item.trigger { border-left-color: #f59e0b; background: rgba(245, 158, 11, 0.05); }

.rule-icon {
  font-size: 1.3rem;
  min-width: 26px;
  text-align: center;
}

/* Mission Profile */
.profile-section {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 14px;
  margin: 12px 0;
}

.profile-header {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  opacity: 0.7;
  margin-bottom: 6px;
}

.profile-value {
  font-size: 1.15rem;
  font-weight: 700;
  color: #10b981;
  margin-bottom: 4px;
}

.loadout-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 10px;
  margin: 3px 0;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 5px;
  border-left: 3px solid #3b82f6;
  font-size: 0.85rem;
}

/* Match Score Progress Bars - HORIZONTAL */
.match-progress-container {
  margin: 8px 0;
}

.match-progress-item {
  margin: 6px 0;
}

.match-progress-label {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  margin-bottom: 3px;
  opacity: 0.9;
}

.match-progress-bar {
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.match-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #34d399);
  border-radius: 3px;
  transition: width 0.3s ease;
}

/* Metrics */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 10px;
  margin: 16px 0;
}

.metric-box {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 10px;
  text-align: center;
}

.metric-label {
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  opacity: 0.6;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 1.4rem;
  font-weight: 800;
  color: #3b82f6;
}

/* Comparison */
.comparison-card {
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 14px;
  border-radius: 10px;
  margin: 16px 0;
  border: 2px solid;
}

.comparison-card.match {
  background: rgba(16, 185, 129, 0.05);
  border-color: #10b981;
}

.comparison-card.mismatch {
  background: rgba(239, 68, 68, 0.05);
  border-color: #ef4444;
}

.comparison-label {
  font-size: 0.7rem;
  opacity: 0.7;
  margin-bottom: 3px;
}

.comparison-value {
  font-size: 1.05rem;
  font-weight: 700;
}

/* Badges */
.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 5px;
  font-weight: 700;
  font-size: 0.75rem;
  letter-spacing: 0.3px;
  text-transform: uppercase;
}

.badge-critical { background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid #ef4444; }
.badge-high { background: rgba(245, 158, 11, 0.2); color: #fcd34d; border: 1px solid #f59e0b; }
.badge-success { background: rgba(16, 185, 129, 0.2); color: #6ee7b7; border: 1px solid #10b981; }

/* Voice Stress Indicator */
.stress-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.75rem;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.stress-low { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid #10b981; }
.stress-medium { background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid #f59e0b; }
.stress-high { background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid #ef4444; }

/* Cards */
.info-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 12px 14px;
  margin: 10px 0;
}

/* Section Spacing - IMPROVED */
.section-spacer {
  height: 24px;
}

/* Utilities */
hr { border: none; border-top: 1px solid rgba(255, 255, 255, 0.1); margin: 24px 0; }
.muted { opacity: 0.7; font-size: 0.9rem; }

/* Compact symptom tags */
.symptom-tag {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  padding: 3px 8px;
  border-radius: 12px;
  margin: 2px 4px 2px 0;
  display: inline-block;
  border: 1px solid rgba(59, 130, 246, 0.3);
  font-size: 0.8em;
}
</style>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# Data Loading
# =============================================================================

@st.cache_data(show_spinner=False)
def load_all_data() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        data = {
            "scenarios": load_scenarios(),
            "cases": load_cases(),
            "landing_zones": load_landing_zones(),
            "categorizer": load_categorizer(),
        }
        return data, None
    except FileNotFoundError as e:
        return None, str(e)
    except Exception as e:
        return None, f"Unexpected error: {e}"


# =============================================================================
# Utilities
# =============================================================================


def parse_harm_string(val: Any) -> Optional[float]:
    if val is None:
        return None
    s = str(val).lower().replace(">", "").replace("<", "").replace("min", "").replace("m", "")
    nums = [float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", s)]
    return min(nums) if nums else None

def normalize_expected(x: Any) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip().upper()
    if "DRONE" in s:
        return "DOCTOR_DRONE"
    if "AMB" in s:
        return "AMBULANCE"
    return None

def to_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default

def to_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


# =============================================================================
# Mission Profile Logic (THE DIFFERENTIATOR)
# =============================================================================

def get_mission_profile(category: str, severity: int) -> Dict[str, Any]:
    """
    Returns specialized human medic and equipment loadout.
    Core differentiator: "trained human medic delivery, not just equipment"
    """
    cat = str(category).lower()
    
    if "cardiac" in cat:
        return {
            "medic": "Dr. Sarah Al-Rashid",
            "specialty": "Advanced Cardiac Life Support",
            "loadout": ["AED Pro", "Cardiac Medications", "Advanced Airway Kit", "Portable ECG Monitor"],
            "priority": "CRITICAL",
            "intervention": "Immediate CPR, defibrillation, cardiac stabilization",
        }
    elif "trauma" in cat or "bleeding" in cat:
        return {
            "medic": "Paramedic Ali Hassan",
            "specialty": "Emergency Trauma Care",
            "loadout": ["Tourniquet Pack", "Hemostatic Gauze", "IV Fluids", "Splint Kit", "Pressure Dressings"],
            "priority": "CRITICAL",
            "intervention": "Hemorrhage control, fluid resuscitation, fracture stabilization",
        }
    elif "respiratory" in cat:
        return {
            "medic": "Nurse Layla Ahmed",
            "specialty": "Airway & Respiratory Management",
            "loadout": ["Portable Oxygen", "Nebulizer", "Bronchodilators", "Intubation Kit", "BiPAP"],
            "priority": "HIGH",
            "intervention": "Oxygen therapy, bronchodilator administration, airway management",
        }
    elif "allergic" in cat or "anaphylaxis" in cat:
        return {
            "medic": "EMT Omar Khalid",
            "specialty": "Anaphylaxis Response",
            "loadout": ["EpiPen Auto-Injectors (×3)", "Antihistamines", "Oxygen", "IV Steroids"],
            "priority": "CRITICAL",
            "intervention": "Immediate epinephrine, airway protection, fluid support",
        }
    elif "neuro" in cat or "stroke" in cat:
        return {
            "medic": "Dr. Fatima Al-Dosari",
            "specialty": "Stroke & Neurological Emergency",
            "loadout": ["Stroke Assessment Kit", "Neuroprotective Meds", "Oxygen", "Glucose Monitor"],
            "priority": "CRITICAL",
            "intervention": "Rapid stroke protocol, time-critical medication, neuro assessment",
        }
    else:
        return {
            "medic": "Duty Paramedic Khalid",
            "specialty": "General Emergency Medicine",
            "loadout": ["Standard ALS Kit", "Vital Signs Monitor", "First Aid Trauma Bag", "IV Access Kit"],
            "priority": "MEDIUM",
            "intervention": "Patient assessment, vital stabilization, basic life support",
        }


# =============================================================================
# UI Components
# =============================================================================

def render_header():
    st.markdown(
        """
<div class="fixed-toolbar">
  <div style="display: flex; align-items: center; gap: 12px;">
    <div style="font-size: 1.1rem; font-weight: 700; color: white; letter-spacing: -0.5px;">SAHM</div>
    <div style="height: 16px; width: 1px; background: rgba(255,255,255,0.2);"></div>
    <div style="font-size: 0.85rem; color: rgba(255,255,255,0.8); font-weight: 400;">
      Smart Aerial Human-Medic <span style="opacity: 0.5; margin: 0 4px;">|</span> Al Ghadir Dispatch Center
    </div>
  </div>
  <div style="display: flex; align-items: center; gap: 6px; white-space: nowrap;">
    <div style="font-size: 0.75rem; color: #10b981; font-weight: 600; background: rgba(16, 185, 129, 0.1); padding: 2px 8px; border-radius: 12px; border: 1px solid rgba(16, 185, 129, 0.2);">LIVE SYSTEM</div>
    <div style="font-size: 1rem; font-weight: 700; color: white;">سهم</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

def render_rule_checklist(result: DispatchResult):
    """Visual rule evaluation"""
    
    # Rule 1: Weather
    weather_pass = not result.exceeds_weather
    rule1_icon = "✓" if weather_pass else "✗"
    rule1_class = "pass" if weather_pass else "fail"
    rule1_text = f"Weather safe ({result.weather_risk_pct:.0f}% ≤ 35%)" if weather_pass else f"Weather unsafe ({result.weather_risk_pct:.0f}% > 35%)"
    
    # Rule 2: Harm threshold
    harm_trigger = result.exceeds_harm
    rule2_icon = "!" if harm_trigger else "✓"
    rule2_class = "trigger" if harm_trigger else "pass"
    rule2_text = f"Ground ETA ({result.ground_eta_min:.1f} min) {'>' if harm_trigger else '≤'} Harm limit ({result.harm_threshold_min:.1f} min)"
    
    # Rule 3: Efficiency
    efficiency_trigger = result.exceeds_efficiency
    rule3_icon = "⚡" if efficiency_trigger else "○"
    rule3_class = "trigger" if efficiency_trigger else "pass"
    rule3_text = f"Time saved ({result.time_delta_min:.1f} min) {'>' if efficiency_trigger else '≤'} 10 min threshold"
    
    st.markdown("### Decision Logic Evaluation")
    
    st.markdown(
        f"""
<div class="rule-item {rule1_class}">
  <span class="rule-icon">{rule1_icon}</span>
  <div>
    <strong>Rule 1: Safety Filter</strong><br/>
    <span class="muted">{rule1_text}</span>
  </div>
</div>

<div class="rule-item {rule2_class}">
  <span class="rule-icon">{rule2_icon}</span>
  <div>
    <strong>Rule 2: Emergency Override</strong><br/>
    <span class="muted">{rule2_text}</span>
  </div>
</div>

<div class="rule-item {rule3_class}">
  <span class="rule-icon">{rule3_icon}</span>
  <div>
    <strong>Rule 3: Efficiency Optimization</strong><br/>
    <span class="muted">{rule3_text}</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

def render_decision_banner(result: DispatchResult):
    """Main decision display - COMPRESSED"""
    
    if result.response_mode == "BOTH":
        st.markdown(
            f"""
<div class="decision-banner both">
  <h1>SIMULTANEOUS RESPONSE</h1>
  <p>CRITICAL: Drone (Immediate Aid) + Ambulance (Transport)</p>
  <div style="margin-top: 10px;">
    <span class="badge badge-success">{result.rule_triggered}</span>
    <span class="badge badge-success" style="margin-left: 8px;">Confidence: {result.confidence*100:.0f}%</span>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
    elif result.response_mode == "DOCTOR_DRONE":
        st.markdown(
            f"""
<div class="decision-banner drone">
  <h1>DOCTOR DRONE AUTHORIZED</h1>
  <p>Aerial Medical Unit | Immediate Takeoff Cleared</p>
  <div style="margin-top: 10px;">
    <span class="badge badge-success">{result.rule_triggered}</span>
    <span class="badge badge-success" style="margin-left: 8px;">Confidence: {result.confidence*100:.0f}%</span>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
    else:  # AMBULANCE
        st.markdown(
            f"""
<div class="decision-banner ambulance">
  <h1>GROUND AMBULANCE DISPATCH</h1>
  <p>Standard Emergency Response Protocol</p>
  <div style="margin-top: 10px;">
    <span class="badge badge-high">{result.rule_triggered}</span>
    <span class="badge badge-high" style="margin-left: 8px;">Confidence: {result.confidence*100:.0f}%</span>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

def render_mission_profile(category: str, severity: int):
    """Render medic + loadout assignment"""
    
    profile = get_mission_profile(category, severity)
    
    st.markdown("### Mission Profile")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown(
            f"""
<div class="profile-section">
  <div class="profile-header">Assigned Medical Specialist</div>
  <div class="profile-value">{profile['medic']}</div>
  <div class="muted">{profile['specialty']}</div>
  <div style="margin-top: 10px;">
    <span class="badge badge-{profile['priority'].lower()}">{profile['priority']}</span>
  </div>
</div>

<div class="profile-section">
  <div class="profile-header">First 5-Minute Intervention</div>
  <div style="font-size: 0.9rem; line-height: 1.5; margin-top: 6px;">
    {profile['intervention']}
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
    
    with col2:
        st.markdown('<div class="profile-section"><div class="profile-header">Equipment Loadout</div><div style="margin-top: 6px;">', unsafe_allow_html=True)
        
        for item in profile['loadout']:
            st.markdown(f'<div class="loadout-item">✓ {item}</div>', unsafe_allow_html=True)
        
        st.markdown("</div></div>", unsafe_allow_html=True)


def render_medic_assignment(assignment: Dict[str, Any], category: str):
    """Render matched medic assignment with horizontal progress bars"""
    
    if assignment.get("status") != "success" or not assignment.get("assigned_medic"):
        if assignment.get("reasoning"):
            st.info(f"Medic Assignment: {assignment['reasoning']}")
        return
    
    medic = assignment["assigned_medic"]
    breakdown = assignment.get("match_breakdown", {})
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        # Status badge styling
        status = medic.get("status", "Available")
        status_color = "#10b981" if status == "En Route" else "#3b82f6" if status == "Available" else "#f59e0b"
        status_bg = f"rgba({16 if status == 'En Route' else 59}, {185 if status == 'En Route' else 130}, {129 if status == 'En Route' else 246}, 0.2)"
        
        st.markdown(
            f"""
<div class="profile-section">
  <div class="profile-header">Matched Medic</div>
  <div class="profile-value">{medic['name']}</div>
  <div class="muted">{medic['specialty'].replace('_', ' ').title()}</div>
  <div style="margin-top: 10px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
    <span style="background: {status_bg}; color: {status_color}; padding: 5px 12px; border-radius: 5px; font-weight: 700; font-size: 0.8rem; border: 1px solid {status_color};">{status.upper()}</span>
    <span class="badge badge-success">{medic['certification'].upper()}</span>
    <span style="opacity: 0.8;">⭐ {medic['rating']}/5.0</span>
  </div>
</div>

<div class="profile-section">
  <div class="profile-header">Response Details</div>
  <div class="metrics-grid" style="grid-template-columns: 1fr 1fr;">
    <div class="metric-box">
      <div class="metric-label">Distance</div>
      <div class="metric-value">{medic['distance_km']:.1f} km</div>
    </div>
    <div class="metric-box">
      <div class="metric-label">ETA</div>
      <div class="metric-value" style="color: #10b981;">{medic['eta_minutes']:.1f} min</div>
    </div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
    
    with col2:
        # Match score breakdown with HORIZONTAL PROGRESS BARS
        distance_score = breakdown.get('distance_score', 0)
        specialty_score = breakdown.get('specialty_score', 0)
        workload_score = breakdown.get('workload_score', 0)
        rating_score = breakdown.get('rating_score', 0)
        
        st.markdown(f'<div class="profile-section"><div class="profile-header">Match Score: {assignment.get("match_score", 0):.2f}</div>', unsafe_allow_html=True)
        st.markdown('<div class="match-progress-container">', unsafe_allow_html=True)
        
        # Distance
        st.markdown(f'''
<div class="match-progress-item">
  <div class="match-progress-label">
    <span>Distance</span>
    <span>{distance_score:.0%}</span>
  </div>
  <div class="match-progress-bar">
    <div class="match-progress-fill" style="width: {distance_score*100}%;"></div>
  </div>
</div>
''', unsafe_allow_html=True)
        
        # Specialty
        st.markdown(f'''
<div class="match-progress-item">
  <div class="match-progress-label">
    <span>Specialty</span>
    <span>{specialty_score:.0%}</span>
  </div>
  <div class="match-progress-bar">
    <div class="match-progress-fill" style="width: {specialty_score*100}%;"></div>
  </div>
</div>
''', unsafe_allow_html=True)
        
        # Workload
        st.markdown(f'''
<div class="match-progress-item">
  <div class="match-progress-label">
    <span>Workload</span>
    <span>{workload_score:.0%}</span>
  </div>
  <div class="match-progress-bar">
    <div class="match-progress-fill" style="width: {workload_score*100}%;"></div>
  </div>
</div>
''', unsafe_allow_html=True)
        
        # Rating
        st.markdown(f'''
<div class="match-progress-item">
  <div class="match-progress-label">
    <span>Rating</span>
    <span>{rating_score:.0%}</span>
  </div>
  <div class="match-progress-bar">
    <div class="match-progress-fill" style="width: {rating_score*100}%;"></div>
  </div>
</div>
''', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="muted" style="margin-top: 8px;">Languages: {", ".join(medic.get("languages", ["ar"]))}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Alternatives expander with status
        alternatives = assignment.get("alternatives", [])
        if alternatives:
            with st.expander(f"Alternative Medics ({len(alternatives)})", expanded=False):
                for alt in alternatives[:3]:
                    alt_status = alt.get("status", "Available")
                    alt_color = "#10b981" if alt_status == "Available" else "#f59e0b"
                    st.markdown(
                        f"""<div style="padding: 8px; margin: 4px 0; background: rgba(255,255,255,0.02); border-radius: 6px; border-left: 3px solid {alt_color};">
  <strong>{alt['name']}</strong> <span style="opacity: 0.7;">({alt.get('specialty', 'general').replace('_', ' ').title()})</span><br/>
  <span style="font-size: 0.85rem;">Score: {alt['score']:.2f} | ETA: {alt['eta_minutes']:.1f} min | <span style="color: {alt_color};">{alt_status}</span></span>
</div>""",
                        unsafe_allow_html=True
                    )
    
    # Match timing footer
    st.caption(f"Match completed in {assignment.get('match_time_seconds', 0):.3f}s | Patient: {assignment.get('patient_location', {}).get('latitude', 0):.4f}°N, {assignment.get('patient_location', {}).get('longitude', 0):.4f}°E")
    
    # Live Medic Map - WIDER AT BOTTOM
    all_medics = assignment.get("all_medics", [])
    patient_loc = assignment.get("patient_location", {})
    
    if all_medics and patient_loc:
        st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
        with st.expander("Live Medic Map", expanded=True):
            # Build map data
            map_data = []
            
            # Add patient location (red marker via size)
            map_data.append({
                "lat": patient_loc.get("latitude", 24.7136),
                "lon": patient_loc.get("longitude", 46.6753),
                "name": "PATIENT",
                "size": 800,
                "color": "#ef4444",
            })
            
            # Add all medics
            for m in all_medics:
                gps = m.get("gps_location", (24.7136, 46.6753))
                is_assigned = m.get("status") == "En Route"
                map_data.append({
                    "lat": gps[0],
                    "lon": gps[1],
                    "name": m["name"],
                    "size": 400 if is_assigned else 200,
                    "color": "#10b981" if is_assigned else "#3b82f6" if m.get("status") == "Available" else "#f59e0b",
                })
            
            df_map = pd.DataFrame(map_data)
            st.map(df_map, latitude="lat", longitude="lon", size="size", color="color", zoom=12)
            
            # Legend
            st.markdown(
                """<div style="display: flex; gap: 16px; font-size: 0.8rem; opacity: 0.8; margin-top: 8px;">
  <span>🔴 Patient</span>
  <span>🟢 En Route</span>
  <span>🔵 Available</span>
  <span>🟠 On Mission</span>
</div>""",
                unsafe_allow_html=True
            )


def render_landing_zone(zones: List[Any]):
    """Landing zone display"""
    
    nearest = find_nearest_zone(zones)
    if not nearest:
        st.warning("No landing zones available")
        return
    
    st.markdown("### Landing Zone Assigned")
    
    st.markdown(
        f"""
<div class="profile-section">
  <div style="display: flex; justify-content: space-between; align-items: start;">
    <div>
      <div class="profile-header">Target Zone</div>
      <div class="profile-value">{nearest.name}</div>
      <div class="muted">
        {nearest.latitude:.4f}°N, {nearest.longitude:.4f}°E<br/>
        {nearest.distance_km:.2f} km from emergency site<br/>
        Landing area: {nearest.area}
      </div>
    </div>
    <div style="text-align: right;">
      <span class="badge badge-success">Available</span>
      <div class="muted" style="margin-top: 6px;">
        ETA: ~{(nearest.distance_km / 2):.1f} min
      </div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )
    
    df_map = pd.DataFrame([{"lat": nearest.latitude, "lon": nearest.longitude}])
    st.map(df_map, zoom=14)

def render_metrics(result: DispatchResult):
    """Metrics display"""
    
    st.markdown(
        f"""
<div class="metrics-grid">
  <div class="metric-box">
    <div class="metric-label">Weather Risk</div>
    <div class="metric-value">{result.weather_risk_pct:.0f}%</div>
  </div>
  <div class="metric-box">
    <div class="metric-label">Harm Window</div>
    <div class="metric-value">{result.harm_threshold_min:.0f} min</div>
  </div>
  <div class="metric-box">
    <div class="metric-label">Ground ETA</div>
    <div class="metric-value">{result.ground_eta_min:.1f} min</div>
  </div>
  <div class="metric-box">
    <div class="metric-label">Air ETA</div>
    <div class="metric-value">{result.air_eta_min:.1f} min</div>
  </div>
  <div class="metric-box">
    <div class="metric-label">Time Saved</div>
    <div class="metric-value" style="color: #10b981;">{result.time_delta_min:.1f} min</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

def render_comparison(result: DispatchResult, expected: Optional[str]):
    """Expected vs Actual comparison"""
    
    if not expected:
        return
    
    is_match = (result.response_mode == expected)
    card_class = "match" if is_match else "mismatch"
    icon = "✓" if is_match else "✗"
    status = "VALIDATED" if is_match else "MISMATCH"
    
    st.markdown(
        f"""
<div class="comparison-card {card_class}">
  <div style="font-size: 1.6rem;">{icon}</div>
  <div style="text-align: center;">
    <div class="comparison-label">Expected</div>
    <div class="comparison-value">{expected}</div>
  </div>
  <div style="font-size: 1.2rem;">{'=' if is_match else '≠'}</div>
  <div style="text-align: center;">
    <div class="comparison-label">Actual</div>
    <div class="comparison-value">{result.response_mode}</div>
  </div>
  <div>
    <span class="badge badge-{'success' if is_match else 'critical'}">{status}</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


# =============================================================================
# Quick Trigger Scenarios
# =============================================================================

def get_quick_scenarios() -> List[Dict[str, Any]]:
    return [
        {
            "name": "Safety Filter",
            "desc": "High weather risk forces ground response",
            "weather_risk_pct": 88.0,
            "harm_threshold_min": 10.0,
            "ground_eta_min": 15.0,
            "air_eta_min": 3.6,
            "expected": "AMBULANCE",
        },
        {
            "name": "Emergency Override",
            "desc": "Ground too slow, drone saves life",
            "weather_risk_pct": 14.0,
            "harm_threshold_min": 4.0,
            "ground_eta_min": 29.8,
            "air_eta_min": 3.6,
            "expected": "DOCTOR_DRONE",
        },
        {
            "name": "Efficiency Optimization",
            "desc": "Drone saves 13+ minutes",
            "weather_risk_pct": 6.0,
            "harm_threshold_min": 15.0,
            "ground_eta_min": 17.0,
            "air_eta_min": 3.6,
            "expected": "DOCTOR_DRONE",
        },
    ]


# =============================================================================
# Views
# =============================================================================

def render_live_command(data: Dict[str, Any]):
    """Main live demo view with quick triggers"""
    
    st.markdown("## Quick Demonstration")
    st.caption("Click any button to instantly demonstrate each decision rule")
    
    # Quick triggers
    quick_scenarios = get_quick_scenarios()
    cols = st.columns(3)
    selected_quick = None
    
    for i, (col, scenario) in enumerate(zip(cols, quick_scenarios)):
        with col:
            if st.button(
                f"**{scenario['name']}**\n{scenario['desc']}",
                use_container_width=True,
                key=f"quick_{i}",
            ):
                selected_quick = scenario
    
    st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
    
    # Main layout
    left, right = st.columns([1, 1.1], gap="large")
    
    with left:
        st.markdown("### Emergency Call Analysis")
        
        # Scenario selector
        if not selected_quick:
            scenario_options = {
                f"#{s['scenario_id']}: {s['emergency_case']}": s 
                for s in data["scenarios"]
            }
            selected_name = st.selectbox("Select Scenario", options=list(scenario_options.keys()))
            scenario = scenario_options[selected_name]
            expected = normalize_expected(scenario.get("expected_decision"))
            
            # Voice stress indicator
            voice_stress = scenario.get("voice_stress_score", 0.0)
            if voice_stress >= 0.8:
                stress_class, stress_label = "stress-high", "HIGH"
            elif voice_stress >= 0.5:
                stress_class, stress_label = "stress-medium", "MEDIUM"
            else:
                stress_class, stress_label = "stress-low", "LOW"
            
            st.markdown(
                f"""
<div class="info-card">
  <div style="display: flex; justify-content: space-between; align-items: center;">
    <div>
      <strong>{scenario['emergency_case']}</strong>
      <div class="muted">{scenario['location']} | {scenario['time_of_day']}</div>
    </div>
    <div style="text-align: right;">
      <div style="font-size: 0.7rem; opacity: 0.6; margin-bottom: 3px;">VOICE STRESS</div>
      <span class="stress-badge {stress_class}">{stress_label} ({voice_stress:.0%})</span>
    </div>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )
            
            weather_risk_pct = float(scenario["weather_risk_pct"])
            harm_threshold_min = float(scenario["harm_threshold_min"])
            ground_eta_min = float(scenario["ground_eta_min"])
            air_eta_min = float(scenario["air_eta_min"])
        else:
            st.info(f"Quick Demo: **{selected_quick['name']}** - {selected_quick['desc']}")
            expected = selected_quick["expected"]
            weather_risk_pct = selected_quick["weather_risk_pct"]
            harm_threshold_min = selected_quick["harm_threshold_min"]
            ground_eta_min = selected_quick["ground_eta_min"]
            air_eta_min = selected_quick["air_eta_min"]
        
        # Inputs
        st.markdown("### Dispatch Parameters")
        
        col1, col2 = st.columns(2)
        with col1:
            weather_risk_pct = st.number_input("Weather Risk (%)", 0.0, 100.0, weather_risk_pct, 1.0)
            ground_eta_min = st.number_input("Ground ETA (min)", 0.5, 240.0, ground_eta_min, 0.5)
        
        with col2:
            harm_threshold_min = st.number_input("Harm Threshold (min)", 1.0, 120.0, harm_threshold_min, 1.0)
            air_eta_min = st.number_input("Air ETA (min)", 0.5, 60.0, air_eta_min, 0.1)
        
        st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
        
        # Run dispatch
        result = dispatch(weather_risk_pct, harm_threshold_min, ground_eta_min, air_eta_min)
        
        st.markdown("### Situation Metrics")
        render_metrics(result)
        
        st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
        render_rule_checklist(result)
    
    with right:
        st.markdown("### Dispatch Decision")
        
        render_decision_banner(result)
        
        if expected:
            render_comparison(result, expected)
        
        st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
        
        if result.response_mode == "DOCTOR_DRONE":
            st.markdown("### Assigned Medical Specialist")
            
            # Build inputs for medic matcher
            decision_output = {
                "response_mode": "aerial_only",
            }
            category = "cardiac"
            if not selected_quick and "emergency_case" in scenario:
                case_lower = scenario["emergency_case"].lower()
                if "cardiac" in case_lower or "heart" in case_lower or "chest pain" in case_lower:
                    category = "cardiac"
                elif "trauma" in case_lower or "bleed" in case_lower:
                    category = "trauma_bleeding"
                elif "respiratory" in case_lower or "breath" in case_lower:
                    category = "respiratory"
                elif "stroke" in case_lower or "neuro" in case_lower:
                    category = "neuro"
            
            triage_output = {
                "severity_level": 3,
                "category": category,
            }
            
            scenario_id = scenario.get("scenario_id", 1) if not selected_quick else 999
            assignment = assign_medic(decision_output, triage_output, scenario_seed=scenario_id)
            render_medic_assignment(assignment, category)
            
            st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
            render_landing_zone(data["landing_zones"])
        
        st.markdown("### Decision Reasoning")
        for reason in result.reasons:
            if "unsafe" in reason.lower() or "exceeds" in reason.lower():
                st.error(f"• {reason}")
            elif "saves" in reason.lower() or "survival" in reason.lower():
                st.success(f"• {reason}")
            else:
                st.info(f"• {reason}")


def render_scenarios_tab(data: Dict[str, Any]):
    """Full scenarios testing view"""
    
    st.subheader("Scenario Testing")
    
    with st.expander("All Scenarios", expanded=False):
        df = pd.DataFrame(
            [
                {
                    "ID": s["scenario_id"],
                    "Case": s["emergency_case"],
                    "Severity": s["severity"],
                    "Weather": f"{s['weather_risk_pct']}%",
                    "Ground": f"{s['ground_eta_min']} min",
                    "Air": f"{s['air_eta_min']} min",
                    "Expected": s["expected_decision"],
                }
                for s in data["scenarios"]
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    left, right = st.columns([1, 1], gap="large")
    
    with left:
        scenario_options = {f"#{s['scenario_id']}: {s['emergency_case']}": s for s in data["scenarios"]}
        selected = st.selectbox("Select Scenario", options=list(scenario_options.keys()))
        scenario = scenario_options[selected]
        
        w = st.number_input("Weather (%)", 0.0, 100.0, float(scenario["weather_risk_pct"]), 1.0)
        h = st.number_input("Harm (min)", 1.0, 120.0, float(scenario["harm_threshold_min"]), 1.0)
        g = st.number_input("Ground (min)", 0.5, 240.0, float(scenario["ground_eta_min"]), 0.5)
        a = st.number_input("Air (min)", 0.5, 60.0, float(scenario["air_eta_min"]), 0.1)
    
    with right:
        result = dispatch(w, h, g, a)
        render_decision_banner(result)
        render_comparison(result, normalize_expected(scenario.get("expected_decision")))
        
        st.markdown("### Reasoning")
        for r in result.reasons:
            st.write(f"• {r}")


def render_test_cases_tab(data: Dict[str, Any]):
    """Test cases validation view"""
    
    st.subheader("Test Case Validation")
    
    left, right = st.columns([1, 1], gap="large")
    
    with left:
        case_options = {f"#{c['case_id']}: {c['case_name']}": c for c in data["cases"]}
        selected = st.selectbox("Select Test Case", options=list(case_options.keys()))
        case = case_options[selected]
        
        # Voice stress indicator
        voice_stress = case.get("voice_stress_score", 0.0)
        if voice_stress >= 0.8:
            stress_class, stress_label = "stress-high", "HIGH"
        elif voice_stress >= 0.5:
            stress_class, stress_label = "stress-medium", "MEDIUM"
        else:
            stress_class, stress_label = "stress-low", "LOW"
        
        st.markdown(
            f"""
<div class="info-card">
  <div style="display: flex; justify-content: space-between; align-items: center;">
    <div><strong>{case['case_name']}</strong></div>
    <div>
      <span style="font-size: 0.7rem; opacity: 0.6; margin-right: 6px;">VOICE STRESS</span>
      <span class="stress-badge {stress_class}">{stress_label} ({voice_stress:.0%})</span>
    </div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )
        
        w = st.number_input("Weather (%)", 0.0, 100.0, float(case["weather_risk_pct"]), 1.0, key="case_w")
        h = st.number_input("Harm (min)", 1.0, 120.0, float(case["harm_threshold_min"]), 1.0, key="case_h")
        g = st.number_input("Ground (min)", 0.5, 240.0, float(case["ground_eta_min"]), 0.5, key="case_g")
        a = st.number_input("Air (min)", 0.5, 60.0, float(case["air_eta_min"]), 0.1, key="case_a")
    
    with right:
        result = dispatch(w, h, g, a)
        render_decision_banner(result)
        render_comparison(result, normalize_expected(case.get("expected_decision")))
        
        st.caption(f"Expected reasoning: {case.get('reasoning', '')}")


def render_triage_tab(data: Dict[str, Any]):
    """AI Triage view - DECISION ENGINE AT TOP CENTER (CONDITIONAL)"""
    
    st.subheader("AI Triage + Dispatch")
    
    # Initialize AI session state
    if 'ai_symptoms' not in st.session_state:
        st.session_state.ai_symptoms = []
    if 'ai_transcription' not in st.session_state:
        st.session_state.ai_transcription = ""
    if 'ai_stress' not in st.session_state:
        st.session_state.ai_stress = 0.5
    if 'ai_severity' not in st.session_state:
        st.session_state.ai_severity = "MEDIUM"
    if 'ai_reasoning' not in st.session_state:
        st.session_state.ai_reasoning = ""
    if 'ai_caller_intent' not in st.session_state:
        st.session_state.ai_caller_intent = ""
    if 'ai_medical_summary' not in st.session_state:
        st.session_state.ai_medical_summary = ""
    if 'ai_duration' not in st.session_state:
        st.session_state.ai_duration = 10
    if 'ai_stress_indicators' not in st.session_state:
        st.session_state.ai_stress_indicators = ""
    
    # DECISION ENGINE AT TOP (CONDITIONAL)
    if st.session_state.ai_medical_summary:
        st.markdown("### Live Decision Engine")
        
        # Get environment params from session or defaults
        weather = st.session_state.get('env_weather', 15.0)
        ground = st.session_state.get('env_ground', 20.0)
        air = st.session_state.get('env_air', 3.6)
        
        symptoms = st.session_state.ai_symptoms
        free_text = st.session_state.ai_medical_summary
        duration = st.session_state.ai_duration
        voice_stress = st.session_state.ai_stress
        
        triage_result = triage(symptoms, free_text, duration, voice_stress)
        sev = to_int(triage_result.get("severity_level"), 0)
        cat = str(triage_result.get("category", "other_unclear"))
        
        category_harm_map = {
            "cardiac": 5, "respiratory": 5, "neuro": 10,
            "trauma_bleeding": 5, "allergic": 3, "infection_fever": 30,
            "gi_dehydration": 30, "mental_health": 60, "other_unclear": 15,
        }
        harm = category_harm_map.get(cat, 15)
        if sev == 3:
            harm = min(harm, 5)
        elif sev == 2:
            harm = min(harm, 10)
        
        result = dispatch(weather, harm, ground, air)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            st.info(f"**Category:** {cat}")
        with col2:
            st.info(f"**Severity:** {sev}")
        with col3:
            st.info(f"**Confidence:** {triage_result['confidence']*100:.0f}%")
        
        render_decision_banner(result)
        
        st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
        
        # Show medic assignment if drone authorized
        if result.response_mode in ["DOCTOR_DRONE", "BOTH"]:
            mode_map = {"DOCTOR_DRONE": "aerial_only", "AMBULANCE": "ground_only", "BOTH": "combined"}
            matcher_mode = mode_map.get(str(result.response_mode), "aerial_only")
            
            decision_output = {"response_mode": matcher_mode}
            triage_output = {
                "severity_level": sev,
                "category": cat,
            }
            
            triage_seed = hash(cat) % 1000 + sev
            assignment = assign_medic(decision_output, triage_output, scenario_seed=triage_seed)
            
            st.markdown("### Assigned Medical Specialist")
            render_medic_assignment(assignment, cat)
        
        st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
    
    # ENVIRONMENT SETUP + VOICE INTAKE (BELOW DECISION ENGINE)
    left, right = st.columns([1, 1], gap="large")
    
    with left:
        st.markdown("### Environment Setup")
        weather = st.slider("Weather Risk (%)", 0.0, 100.0, 15.0, 1.0)
        col1, col2 = st.columns(2)
        with col1:
            ground = st.slider("Ground ETA (min)", 1.0, 60.0, 20.0, 0.5)
        with col2:
            air = st.slider("Air ETA (min)", 1.0, 15.0, 3.6, 0.1)
        
        # Store in session state for decision engine
        st.session_state.env_weather = weather
        st.session_state.env_ground = ground
        st.session_state.env_air = air
    
    with right:
        st.markdown("### Voice Intake")
        
        if is_gemini_available():
            st.caption("Record or upload an emergency call for AI analysis")
        else:
            st.warning(f"{get_availability_message()}")
            st.caption("Manual input mode - AI analysis disabled")
        
        audio_val = st.audio_input("Record Emergency Call", key="triage_audio")
        
        if audio_val and is_gemini_available():
            # Fix: Prevent infinite loop by checking if this audio was already processed
            audio_bytes = audio_val.read()
            # Create a simple hash of the bytes to identify changes
            import hashlib
            audio_hash = hashlib.md5(audio_bytes).hexdigest()
            
            # Retrieve last processed hash
            last_hash = st.session_state.get("last_processed_audio_id")
            
            if audio_hash != last_hash:
                with st.spinner("Analyzing Audio..."):
                    mime_type = "audio/wav"
                    
                    ai_result = analyze_audio_call(
                        audio_bytes, 
                        mime_type,
                        env_context={"weather": weather, "ground_eta": ground, "air_eta": air}
                    )
                    
                    if ai_result:
                        st.session_state.ai_transcription = ai_result.get("transcription", "")
                        st.session_state.ai_symptoms = ai_result.get("symptoms", [])
                        st.session_state.ai_stress = float(ai_result.get("voiceStressScore", 0.5))
                        st.session_state.ai_severity = ai_result.get("severityLevel", "MEDIUM")
                        st.session_state.ai_reasoning = ai_result.get("reasoning", "")
                        st.session_state.ai_caller_intent = ai_result.get("callerIntent", "")
                        st.session_state.ai_medical_summary = ai_result.get("medicalSummary", "")
                        st.session_state.ai_duration = int(ai_result.get("symptomDurationMinutes", 10))
                        st.session_state.ai_stress_indicators = ai_result.get("voiceStressIndicators", "")
                        
                        # Mark as processed
                        st.session_state.last_processed_audio_id = audio_hash
                        
                        st.success(f"AI Analysis Complete: {ai_result.get('callerIntent', 'Emergency analyzed')}")
                        st.rerun()
                    else:
                        st.error("AI analysis failed. Please try again or enter symptoms manually.")
        
        if st.session_state.ai_transcription:
            st.markdown(
                f"""
<div style="background:rgba(59, 130, 246, 0.1); padding:12px; border-radius:8px; border-left:3px solid #3b82f6; margin:12px 0;">
  <small style="opacity:0.7; text-transform:uppercase; letter-spacing:0.5px;">Transcription</small><br/>
  <span style="font-style:italic;">"{st.session_state.ai_transcription}"</span>
</div>
""",
                unsafe_allow_html=True,
            )
            
            with st.expander("AI Analysis Details", expanded=False):
                if st.session_state.ai_stress_indicators:
                    st.markdown(f"**Voice Stress Indicators:** {st.session_state.ai_stress_indicators}")
                if st.session_state.ai_reasoning:
                    st.write(st.session_state.ai_reasoning)
    
    # AI FINDINGS (BELOW ENVIRONMENT/VOICE)
    if st.session_state.ai_medical_summary:
        st.markdown("<div class='section-spacer'></div>", unsafe_allow_html=True)
        st.markdown("### AI Findings")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**Symptoms Detected:**")
            symptoms = st.session_state.ai_symptoms
            if symptoms:
                tags_html = "".join([
                    f"<span class='symptom-tag'>{s.replace('_', ' ').title()} ({SYMPTOM_POINTS.get(s, 0)} pts)</span>"
                    for s in symptoms
                ])
                st.markdown(tags_html, unsafe_allow_html=True)
            else:
                st.info("No symptoms detected")
            
            rf = set(symptoms) & RED_FLAGS
            if rf:
                st.error(f"RED FLAGS: {', '.join([s.replace('_', ' ').title() for s in rf])}")
            
            st.markdown("**Medical Summary:**")
            st.info(st.session_state.ai_medical_summary)
        
        with col2:
            voice_stress = st.session_state.ai_stress
            st.metric("Voice Stress Score", f"{voice_stress:.2f}")
            st.progress(voice_stress)
            
            duration = st.session_state.ai_duration
            if duration < 0:
                st.metric("Duration", "Unknown")
            else:
                st.metric("Duration", f"{duration} min")


def render_data_explorer(data: Dict[str, Any]):
    """Data explorer view"""
    
    st.subheader("Data Explorer")
    
    tab1, tab2 = st.tabs(["Medical Reference", "Landing Zones"])
    
    with tab1:
        if isinstance(data["categorizer"], list):
            df = pd.DataFrame(data["categorizer"])
            st.dataframe(df, use_container_width=True, hide_index=True)
    
    with tab2:
        zones = get_all_zones_sorted(data["landing_zones"])
        df = pd.DataFrame(
            [
                {
                    "Name": z.name,
                    "Area": z.area,
                    "Distance (km)": f"{z.distance_km:.2f}",
                    "Latitude": z.latitude,
                    "Longitude": z.longitude,
                }
                for z in zones
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)


# =============================================================================
# Main App
# =============================================================================

def main():
    render_header()
    
    data, error = load_all_data()
    if error:
        st.error(f"Data Loading Error: {error}")
        st.info("Ensure these files exist in /Files directory")
        st.stop()
    
    # Sidebar
    with st.sidebar:
        st.markdown("### System Control")
        
        view_mode = st.radio(
            "View Mode",
            ["AI Triage", "Live Command Center", "Scenarios", "Test Cases", "Data Explorer"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        st.caption("**System Status**")
        st.markdown(f"Medical Protocols: {len(data['categorizer'])}")
        st.markdown(f"Landing Zones: {len(data['landing_zones'])}")
        st.markdown(f"Coverage: Al Ghadir, Riyadh")
        
        st.markdown("---")
        
        with st.expander("Validation"):
            if st.button("Run Validation", use_container_width=True):
                with st.spinner("Validating..."):
                    s_rep = validate_scenarios()
                    c_rep = validate_cases()
                    total = s_rep.total + c_rep.total
                    matches = s_rep.matches + c_rep.matches
                    accuracy = (matches / total * 100) if total > 0 else 0
                    
                    st.success(f"Scenarios: {s_rep.matches}/{s_rep.total}")
                    st.success(f"Cases: {c_rep.matches}/{c_rep.total}")
                    st.metric("Accuracy", f"{accuracy:.1f}%")
        
        st.markdown("---")
        st.caption("Prototype System | Rule-based decision engine")
    
    # Main content
    if view_mode == "Live Command Center":
        render_live_command(data)
    elif view_mode == "Scenarios":
        render_scenarios_tab(data)
    elif view_mode == "Test Cases":
        render_test_cases_tab(data)
    elif view_mode == "AI Triage":
        render_triage_tab(data)
    elif view_mode == "Data Explorer":
        render_data_explorer(data)


if __name__ == "__main__":
    main()