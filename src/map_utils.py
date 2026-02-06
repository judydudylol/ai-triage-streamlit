import folium
from streamlit_folium import st_folium
import streamlit as st
from typing import List, Dict, Any, Optional


CENTER_LAT = 24.7745
CENTER_LON = 46.6575


def _zone_field(zone: Any, key: str, default: Any = None):
    """
    Read field from either dict-like zone payloads or dataclass-style objects.
    """
    if zone is None:
        return default
    if isinstance(zone, dict):
        return zone.get(key, default)
    return getattr(zone, key, default)


def render_mission_map(
    patient_location: Dict[str, float],
    landing_zone: Optional[Any] = None,
    medics: List[Dict[str, Any]] = None,
    selected_medic: Optional[Dict[str, Any]] = None,
    height: int = 400
):
    """
    Render a Mission Map with Folium.
    
    Args:
        patient_location: {'latitude': float, 'longitude': float}
        landing_zone: Selected landing zone object/dict
        medics: List of medic dicts (position, status, etc)
        selected_medic: Assigned medic dict used to draw direct response route
    """
    
    p_lat = patient_location.get("latitude", 24.7745)
    p_lon = patient_location.get("longitude", 46.6575)
    
    
    m = folium.Map(location=[p_lat, p_lon], zoom_start=14, tiles="CartoDB dark_matter")
    
    
    folium.Marker(
        [p_lat, p_lon],
        popup="<b>PATIENT</b><br>Critical Request",
        tooltip="Patient Location",
        icon=folium.Icon(color="red", icon="user", prefix="fa")
    ).add_to(m)
    
    folium.Circle(
        radius=50,
        location=[p_lat, p_lon],
        color="#ef4444",
        fill=True,
        fill_opacity=0.2
    ).add_to(m)
    
    
    if landing_zone:
        lz_lat = _zone_field(landing_zone, "latitude")
        lz_lon = _zone_field(landing_zone, "longitude")
        lz_name = _zone_field(landing_zone, "name", "Landing Zone")
        if lz_lat is None or lz_lon is None:
            lz_lat = CENTER_LAT
            lz_lon = CENTER_LON
        
        folium.Marker(
            [lz_lat, lz_lon],
            popup=f"<b>LANDING ZONE</b><br>{lz_name}",
            tooltip="Designated Landing Zone",
            icon=folium.Icon(color="green", icon="plane", prefix="fa")
        ).add_to(m)
        
        
        folium.PolyLine(
            locations=[[p_lat, p_lon], [lz_lat, lz_lon]],
            color="#10b981",
            weight=3,
            opacity=0.8,
            dash_array="10"
        ).add_to(m)
        
        
        folium.Marker(
            location=[(p_lat + lz_lat)/2, (p_lon + lz_lon)/2],
            icon=folium.DivIcon(html=f'<div style="font-size: 10pt; color: #10b981; font-weight: bold;">FLIGHT PATH</div>')
        ).add_to(m)

        if selected_medic:
            medic_gps = selected_medic.get("gps_location")
            if isinstance(medic_gps, (list, tuple)) and len(medic_gps) == 2:
                folium.PolyLine(
                    locations=[[medic_gps[0], medic_gps[1]], [lz_lat, lz_lon]],
                    color="#f59e0b",
                    weight=3,
                    opacity=0.85,
                    dash_array="6",
                ).add_to(m)
                folium.Marker(
                    location=[(medic_gps[0] + lz_lat) / 2, (medic_gps[1] + lz_lon) / 2],
                    icon=folium.DivIcon(
                        html='<div style="font-size: 9pt; color: #f59e0b; font-weight: bold;">MEDIC TRANSFER</div>'
                    ),
                ).add_to(m)
    elif selected_medic:
        medic_gps = selected_medic.get("gps_location")
        if isinstance(medic_gps, (list, tuple)) and len(medic_gps) == 2:
            folium.PolyLine(
                locations=[[medic_gps[0], medic_gps[1]], [p_lat, p_lon]],
                color="#f59e0b",
                weight=3,
                opacity=0.85,
                dash_array="6",
            ).add_to(m)
            folium.Marker(
                location=[(medic_gps[0] + p_lat) / 2, (medic_gps[1] + p_lon) / 2],
                icon=folium.DivIcon(
                    html='<div style="font-size: 9pt; color: #f59e0b; font-weight: bold;">MEDIC ROUTE</div>'
                ),
            ).add_to(m)

    
    if medics:
        selected_id = selected_medic.get("id") if selected_medic else None
        selected_chain_eta = None
        if landing_zone is not None:
            selected_chain_eta = _zone_field(landing_zone, "chain_eta_min")
        for medic in medics:
            gps = medic.get("gps_location")
            if not gps: 
                continue
                
            status = medic.get("status", "Available")
            color = "green" if status == "En Route" else "blue"
            
            
            eta = medic.get("eta_minutes")
            if selected_id and medic.get("id") == selected_id and selected_chain_eta is not None:
                eta = float(selected_chain_eta)
            if eta is None or eta == 0:
                dist = ((gps[0] - p_lat)**2 + (gps[1] - p_lon)**2)**0.5 * 111
                
                speed = 120 if status == "En Route" else 40 
                eta = (dist / speed) * 60
            
            folium.Marker(
                gps,
                popup=f"<b>{medic['name']}</b><br>Status: {status}",
                tooltip=f"{medic['name']} ({eta:.1f} min)",
                icon=folium.Icon(color=color, icon="user-md", prefix="fa")
            ).add_to(m)

    
    st_folium(m, width="100%", height=height)
