"""
UI Utilities for SAHM Application.
Contains timeline visualization for dispatch decisions.
"""

import streamlit as st
from streamlit_timeline import timeline
from datetime import datetime, timedelta


def render_response_timeline(ground_eta: float, air_eta: float, harm_threshold: float):
    """
    Render a timeline of response vs harm window.
    
    Args:
        ground_eta: Ambulance ETA in minutes
        air_eta: Drone ETA in minutes  
        harm_threshold: Time to irreversible harm in minutes
    """
    base_time = datetime(2024, 1, 1, 12, 0, 0)
    
    events = [
        {
            "start_date": {"year": "2024", "month": "1", "day": "1", "hour": "12", "minute": "0", "second": "0"},
            "text": {"headline": "Emergency Call", "text": "T=0: System Activation"},
            "group": "Events"
        }
    ]
    
    
    drone_time = base_time + timedelta(minutes=air_eta)
    events.append({
        "start_date": {
            "year": str(drone_time.year), "month": str(drone_time.month), "day": str(drone_time.day),
            "hour": str(drone_time.hour), "minute": str(drone_time.minute), "second": str(drone_time.second)
        },
        "text": {"headline": "Drone Arrival", "text": f"T+{air_eta:.1f} min: Immediate Care"},
        "group": "Response"
    })
    
    
    harm_time = base_time + timedelta(minutes=harm_threshold)
    events.append({
        "start_date": {
            "year": str(harm_time.year), "month": str(harm_time.month), "day": str(harm_time.day),
            "hour": str(harm_time.hour), "minute": str(harm_time.minute), "second": str(harm_time.second)
        },
        "text": {"headline": "Harm Threshold", "text": f"T+{harm_threshold:.0f} min: Irreversible Damage Begins"},
        "group": "Critical Limits"
    })
    
    
    amb_time = base_time + timedelta(minutes=ground_eta)
    events.append({
        "start_date": {
            "year": str(amb_time.year), "month": str(amb_time.month), "day": str(amb_time.day),
            "hour": str(amb_time.hour), "minute": str(amb_time.minute), "second": str(amb_time.second)
        },
        "text": {"headline": "Ambulance Arrival", "text": f"T+{ground_eta:.1f} min: Ground Transport"},
        "group": "Response"
    })
    
    data = {"events": events}
    
    
    timeline(data, height=300)
