"""
SAHM Step 4: Medic Matching System
Ultra-fast medic assignment (<3 seconds) based on location, specialty, and availability.
"""

import random
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class Medic:
    """Represents a human medic in the SAHM system"""
    id: str
    name: str
    specialty: str  # cardiac, trauma, respiratory, general, pediatric
    certification_level: str  # paramedic, emt_advanced, critical_care
    gps_location: tuple[float, float]  # (latitude, longitude)
    status: str  # available, on_mission, off_duty
    current_load: int  # 0-100, workload percentage
    missions_completed: int
    rating: float  # 0.0 - 5.0
    languages: List[str]  # ["ar", "en", "ur"]


class MedicDatabase:
    """Mock database of available medics (in production: SQL/NoSQL)"""
    
    # Riyadh GPS coordinates (approximate)
    RIYADH_CENTER = (24.7136, 46.6753)
    
    # Specialty mapping to medical categories
    SPECIALTY_MAP = {
        "cardiac": ["cardiac", "chest_pain"],
        "trauma": ["trauma_bleeding", "major_injury"],
        "respiratory": ["respiratory", "breathing"],
        "neuro": ["neuro", "neurological", "stroke"],
        "pediatric": ["pediatric", "child"],
        "general": ["infection_fever", "gi_dehydration", "allergic", "other_unclear", "mental_health"],
    }
    
    def __init__(self, seed: int = 42):
        """Initialize with fixed seed for deterministic medic generation"""
        self._rng = random.Random(seed)
        self.medics = self._generate_mock_medics()
    
    def _generate_mock_medics(self) -> List[Medic]:
        """Generate realistic mock medic profiles (deterministic with seed)"""""
        
        names = [
            "Dr. Ahmed Al-Rashid", "Dr. Fatima Al-Zahrani", "Mohammed Al-Qahtani",
            "Sara Al-Mutairi", "Dr. Khalid Al-Dosari", "Noura Al-Shehri",
            "Abdullah Al-Harbi", "Layla Al-Otaibi", "Dr. Omar Al-Ghamdi",
            "Aisha Al-Fadel", "Dr. Saleh Al-Subaie", "Reem Al-Mansour",
            "Faisal Al-Juhani", "Maha Al-Tamimi", "Dr. Yasser Al-Anazi",
        ]
        
        specialties = ["cardiac", "trauma", "respiratory", "neuro", "pediatric", "general"]
        certifications = ["paramedic", "emt_advanced", "critical_care"]
        
        medics = []
        for i, name in enumerate(names):
            # Deterministic GPS within ~20km of Riyadh center
            lat = self.RIYADH_CENTER[0] + self._rng.uniform(-0.18, 0.18)
            lon = self.RIYADH_CENTER[1] + self._rng.uniform(-0.18, 0.18)
            
            # Most medics available, some on mission
            status_pool = ["available"] * 7 + ["on_mission"] * 2 + ["off_duty"] * 1
            
            medic = Medic(
                id=f"MED-{1000 + i}",
                name=name,
                specialty=specialties[i % len(specialties)],  # Deterministic specialty
                certification_level=certifications[i % len(certifications)],  # Deterministic cert
                gps_location=(round(lat, 6), round(lon, 6)),
                status=self._rng.choice(status_pool),
                current_load=self._rng.randint(0, 80),
                missions_completed=self._rng.randint(15, 250),
                rating=round(self._rng.uniform(4.2, 5.0), 1),
                languages=self._rng.sample(["ar", "en", "ur", "fr"], k=self._rng.randint(2, 3)),
            )
            medics.append(medic)
        
        return medics
    
    def get_available_medics(self) -> List[Medic]:
        """Return only medics with 'available' status"""
        return [m for m in self.medics if m.status == "available"]
    
    def get_by_id(self, medic_id: str) -> Optional[Medic]:
        """Retrieve specific medic by ID"""
        for medic in self.medics:
            if medic.id == medic_id:
                return medic
        return None
    
    def update_status(self, medic_id: str, new_status: str):
        """Update medic availability status"""
        medic = self.get_by_id(medic_id)
        if medic:
            medic.status = new_status


class MedicMatcher:
    """
    Core matching algorithm.
    Finds optimal medic in <3 seconds based on multiple factors.
    """
    
    def __init__(self):
        self.db = MedicDatabase()
    
    def _calculate_distance(
        self,
        loc1: tuple[float, float],
        loc2: tuple[float, float]
    ) -> float:
        """
        Calculate approximate distance in kilometers.
        Uses simplified Haversine formula.
        """
        lat1, lon1 = loc1
        lat2, lon2 = loc2
        
        # Simplified distance (good enough for mock)
        lat_diff = abs(lat2 - lat1)
        lon_diff = abs(lon2 - lon1)
        
        # Rough conversion: 1 degree ≈ 111 km
        distance_km = ((lat_diff ** 2 + lon_diff ** 2) ** 0.5) * 111
        return round(distance_km, 2)
    
    def _estimate_eta(self, distance_km: float, mode: str) -> float:
        """
        Estimate time to reach patient.
        
        Args:
            distance_km: Distance to patient
            mode: "aerial" or "ground"
        
        Returns:
            Estimated minutes to arrival
        """
        if mode == "aerial":
            # Aerial speed: ~120 km/h average
            speed_kmh = 120
        else:
            # Ground speed: ~40 km/h with traffic
            speed_kmh = 40
        
        eta_minutes = (distance_km / speed_kmh) * 60
        return round(eta_minutes, 1)
    
    def _calculate_specialty_match(
        self,
        medic_specialty: str,
        case_category: str
    ) -> float:
        """
        Score specialty match (0.0 to 1.0).
        1.0 = perfect match, 0.5 = general can handle, 0.0 = mismatch
        """
        # Perfect match
        if medic_specialty in self.db.SPECIALTY_MAP:
            if case_category in self.db.SPECIALTY_MAP[medic_specialty]:
                return 1.0
        
        # General medics can handle anything at reduced score
        if medic_specialty == "general":
            return 0.7
        
        # Partial match (e.g., cardiac for respiratory)
        return 0.4
    
    def _calculate_match_score(
        self,
        medic: Medic,
        case_category: str,
        patient_location: tuple[float, float],
        severity: int,
        mode: str,
    ) -> Dict:
        """
        Calculate composite match score.
        
        Factors:
        - Distance (40% weight)
        - Specialty match (30% weight)
        - Workload (15% weight)
        - Rating (10% weight)
        - Certification (5% weight)
        """
        distance = self._calculate_distance(medic.gps_location, patient_location)
        eta = self._estimate_eta(distance, mode)
        specialty_score = self._calculate_specialty_match(medic.specialty, case_category)
        
        # Normalize scores to 0-1
        distance_score = max(0, 1 - (distance / 20))  # 20km max range
        workload_score = 1 - (medic.current_load / 100)
        rating_score = medic.rating / 5.0
        cert_score = {"paramedic": 0.7, "emt_advanced": 0.85, "critical_care": 1.0}[medic.certification_level]
        
        # Weighted composite score
        composite_score = (
            distance_score * 0.40 +
            specialty_score * 0.30 +
            workload_score * 0.15 +
            rating_score * 0.10 +
            cert_score * 0.05
        )
        
        return {
            "medic_id": medic.id,
            "composite_score": round(composite_score, 3),
            "distance_km": distance,
            "eta_minutes": eta,
            "specialty_match": specialty_score,
            "breakdown": {
                "distance_score": round(distance_score, 2),
                "specialty_score": round(specialty_score, 2),
                "workload_score": round(workload_score, 2),
                "rating_score": round(rating_score, 2),
                "cert_score": round(cert_score, 2),
            }
        }
    
    def find_best_match(
        self,
        decision_output: Dict,
        triage_output: Dict,
        patient_location: tuple[float, float] = None,
        scenario_seed: int = None,
    ) -> Dict:
        """
        Main matching function.
        Finds optimal medic in <3 seconds.
        
        Args:
            decision_output: Result from Step 3 (Decision Engine)
            triage_output: Result from Step 2 (AI Triage)
            patient_location: (lat, lon) or None for derived location
            scenario_seed: Optional seed for deterministic patient location
        
        Returns:
            Dict with assigned medic details and match reasoning
        """
        start_time = time.time()
        
        # Extract key info
        response_mode = decision_output["response_mode"]
        severity = triage_output["severity_level"]
        category = triage_output["category"]
        
        # Derive patient location deterministically
        if patient_location is None:
            # Use scenario_seed for deterministic location, or fallback to fixed default
            seed = scenario_seed if scenario_seed is not None else 1
            loc_rng = random.Random(seed)
            patient_location = (
                self.db.RIYADH_CENTER[0] + loc_rng.uniform(-0.15, 0.15),
                self.db.RIYADH_CENTER[1] + loc_rng.uniform(-0.15, 0.15),
            )
        
        # Only match if aerial or combined deployment
        if response_mode == "ground_only":
            return {
                "assigned_medic": None,
                "reasoning": "Ground ambulance only, no aerial medic needed",
                "match_time_seconds": round(time.time() - start_time, 3),
            }
        
        # Get available medics
        available = self.db.get_available_medics()
        
        if not available:
            return {
                "assigned_medic": None,
                "reasoning": "No medics currently available",
                "match_time_seconds": round(time.time() - start_time, 3),
                "status": "error",
            }
        
        # Calculate match scores
        mode = "aerial" if response_mode in ["aerial_only", "combined"] else "ground"
        scores = []
        
        for medic in available:
            score_data = self._calculate_match_score(
                medic, category, patient_location, severity, mode
            )
            scores.append({
                "medic": medic,
                "score_data": score_data,
            })
        
        # Sort by composite score (highest first)
        scores.sort(key=lambda x: x["score_data"]["composite_score"], reverse=True)
        
        # Select best match
        best = scores[0]
        best_medic = best["medic"]
        best_score = best["score_data"]
        
        # NOTE: Don't update medic status here - it would make matching non-deterministic
        # In production, this would be handled by a separate dispatch confirmation step
        
        # Build result
        match_time = round(time.time() - start_time, 3)
        
        return {
            "assigned_medic": {
                "id": best_medic.id,
                "name": best_medic.name,
                "specialty": best_medic.specialty,
                "certification": best_medic.certification_level,
                "rating": best_medic.rating,
                "languages": best_medic.languages,
                "distance_km": best_score["distance_km"],
                "eta_minutes": best_score["eta_minutes"],
                "missions_completed": best_medic.missions_completed,
                "status": "En Route",  # Assigned medic is now en route
                "gps_location": best_medic.gps_location,
            },
            "match_score": best_score["composite_score"],
            "match_breakdown": best_score["breakdown"],
            "reasoning": [
                f"Specialty match: {best_medic.specialty} for {category} case",
                f"Distance: {best_score['distance_km']} km (ETA {best_score['eta_minutes']} min)",
                f"Certification: {best_medic.certification_level}",
                f"Rating: {best_medic.rating}/5.0 ({best_medic.missions_completed} missions)",
            ],
            "alternatives": [
                {
                    "id": alt["medic"].id,
                    "name": alt["medic"].name,
                    "score": alt["score_data"]["composite_score"],
                    "eta_minutes": alt["score_data"]["eta_minutes"],
                    "specialty": alt["medic"].specialty,
                    "status": alt["medic"].status.replace('_', ' ').title(),
                    "gps_location": alt["medic"].gps_location,
                }
                for alt in scores[1:4]  # Top 3 alternatives
            ] if len(scores) > 1 else [],
            "all_medics": [
                {
                    "id": m.id,
                    "name": m.name,
                    "specialty": m.specialty,
                    "status": m.status.replace('_', ' ').title() if m.id != best_medic.id else "En Route",
                    "gps_location": m.gps_location,
                }
                for m in self.db.medics
            ],
            "match_time_seconds": match_time,
            "patient_location": {
                "latitude": round(patient_location[0], 6),
                "longitude": round(patient_location[1], 6),
            },
            "status": "success",
        }

# Singleton instance for session consistency
_matcher_instance: Optional[MedicMatcher] = None

def get_matcher() -> MedicMatcher:
    """Get or create singleton MedicMatcher instance for deterministic results"""
    global _matcher_instance
    if _matcher_instance is None:
        _matcher_instance = MedicMatcher()
    return _matcher_instance


# Convenience function
def assign_medic(
    decision_output: Dict,
    triage_output: Dict,
    patient_location: tuple[float, float] = None,
    scenario_seed: int = None,
) -> Dict:
    """
    Wrapper function for easy integration.
    Uses singleton MedicMatcher for consistent results across calls.
    
    Args:
        decision_output: Result from Decision Engine
        triage_output: Result from AI Triage
        patient_location: Optional explicit (lat, lon)
        scenario_seed: Optional seed for deterministic patient location
    
    Usage:
        from medic_matcher import assign_medic
        assignment = assign_medic(decision_result, triage_result, scenario_seed=scenario_id)
    """
    matcher = get_matcher()
    return matcher.find_best_match(decision_output, triage_output, patient_location, scenario_seed)
