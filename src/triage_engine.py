"""
AI Triage Engine - Rule-Based Severity Scoring
Implements explicit point-based system matching flowchart logic.
"""

from typing import Optional

# RED FLAGS: Immediate Level 3 escalation
RED_FLAGS = {
    "trouble_breathing",
    "choking",
    "turning_blue",
    "chest_pain_crushing",
    "unconscious",
    "not_responding",
    "seizure_now",
    "face_droop",
    "slurred_speech",
    "arm_weakness",
    "severe_bleeding",
    "heavy_bleeding",
    "anaphylaxis_signs",
    "severe_allergy_swelling",
}

# SYMPTOM POINT VALUES: Explicit scoring system
SYMPTOM_POINTS = {
    # 5-point symptoms (critical)
    "unconscious": 5,
    "not_responding": 5,
    "fainting": 5,
    "severe_bleeding": 5,
    "heavy_bleeding": 5,
    "face_droop": 5,
    "slurred_speech": 5,
    "arm_weakness": 5,
    "stroke_signs": 5,
    "severe_allergy_swelling": 5,
    "anaphylaxis_signs": 5,
    
    # 4-point symptoms (urgent)
    "trouble_breathing": 4,
    "shortness_of_breath": 4,
    "chest_pain": 4,
    "chest_pain_crushing": 4,
    "choking": 4,
    "turning_blue": 4,
    
    # 3-point symptoms (concerning)
    "moderate_bleeding": 3,
    "seizure_now": 3,
    "major_trauma": 3,
    "head_injury": 3,
    "confusion": 3,
    
    # 2-point symptoms (moderate)
    "high_fever": 2,
    "fever": 2,
    "vomiting_severe": 2,
    "diarrhea_severe": 2,
    "dehydration": 2,
    "palpitations": 2,
    "wheezing": 2,
    
    # 1-point symptoms (mild)
    "mild_pain": 1,
    "headache": 1,
    "rash": 1,
    "chills": 1,
    "nausea": 1,
    "vomiting": 1,
    "diarrhea": 1,
    "panic": 1,
    "severe_distress": 1,
    "swelling_face_lips": 1,
}

# CATEGORY RULES: Maps symptoms to medical categories
CATEGORY_RULES = {
    "trauma_bleeding": {
        "severe_bleeding", "heavy_bleeding", "moderate_bleeding",
        "major_trauma", "head_injury"
    },
    "cardiac": {
        "chest_pain", "chest_pain_crushing", "palpitations"
    },
    "respiratory": {
        "shortness_of_breath", "wheezing", "choking",
        "trouble_breathing", "turning_blue"
    },
    "neuro": {
        "seizure_now", "fainting", "face_droop", "slurred_speech",
        "arm_weakness", "stroke_signs", "confusion", "unconscious",
        "not_responding"
    },
    "allergic": {
        "rash", "swelling_face_lips", "anaphylaxis_signs",
        "severe_allergy_swelling"
    },
    "infection_fever": {
        "fever", "high_fever", "chills"
    },
    "gi_dehydration": {
        "vomiting", "vomiting_severe", "diarrhea", "diarrhea_severe",
        "dehydration", "nausea"
    },
    "mental_health": {
        "panic", "severe_distress"
    },
}

# CATEGORY PRIORITY: In case of multiple matches, pick highest priority
PRIORITY = [
    "trauma_bleeding",
    "cardiac",
    "respiratory",
    "neuro",
    "allergic",
    "infection_fever",
    "gi_dehydration",
    "mental_health",
]

# FOLLOW-UP QUESTIONS: Asked when Level 0 (insufficient info)
FOLLOWUP_QUESTIONS = [
    "What is the main symptom?",
    "How long has it been happening?",
    "Is the person conscious and breathing normally?",
    "Is there any bleeding or visible injury?",
    "Can the person speak in full sentences?",
]


def pick_category(symptoms: set[str]) -> str:
    """
    Assign category based on symptom matching.
    Uses priority order if multiple categories match.
    """
    hits = []
    for cat, symptom_set in CATEGORY_RULES.items():
        if symptoms & symptom_set:
            hits.append(cat)
    
    if not hits:
        return "other_unclear"
    
    # Return highest priority match
    for cat in PRIORITY:
        if cat in hits:
            return cat
    
    return hits[0]


def calculate_symptom_score(symptoms: set[str]) -> int:
    """
    Calculate total symptom score based on point values.
    Each symptom contributes its assigned points.
    """
    score = 0
    for symptom in symptoms:
        score += SYMPTOM_POINTS.get(symptom, 0)
    return score


def map_score_to_severity(score: int) -> int:
    """
    Map symptom score to severity level.
    
    Mapping:
    - 0 points → Level 0 (insufficient info)
    - 1-2 points → Level 1 (low)
    - 3-4 points → Level 2 (medium)
    - 5+ points → Level 3 (high/emergency)
    """
    if score == 0:
        return 0
    elif score <= 2:
        return 1
    elif score <= 4:
        return 2
    else:
        return 3


def compute_severity(
    symptoms: set[str],
    voice_stress_score: Optional[float],
) -> tuple[int, bool]:
    """
    Compute severity level and escalation flag.
    
    Logic:
    1. Red flag present → Level 3, escalate immediately
    2. Calculate symptom score
    3. Add +1 if voice stress ≥ 0.80 AND score > 0
    4. Map score to severity level
    5. Escalate if Level 3
    
    Returns:
        (severity_level, escalate_flag)
    """
    # Fast path: red flag detected
    if symptoms & RED_FLAGS:
        return 3, True
    
    # Calculate base symptom score
    score = calculate_symptom_score(symptoms)
    
    # Add voice stress bonus (only if symptoms present)
    if score > 0 and voice_stress_score is not None and voice_stress_score >= 0.80:
        score += 1
    
    # Map to severity level
    severity = map_score_to_severity(score)
    
    # Escalate if Level 3
    escalate = (severity == 3)
    
    return severity, escalate


def triage(
    symptoms: list[str],
    free_text: str,
    duration_minutes: Optional[int] = None,
    voice_stress_score: Optional[float] = None,
) -> dict:
    """
    Main triage function.
    
    Args:
        symptoms: List of symptom identifiers
        free_text: Optional text description
        duration_minutes: How long symptoms have been present
        voice_stress_score: 0.0 to 1.0, from voice analysis
    
    Returns:
        Dict with:
        - category: medical category
        - severity_level: 0-3
        - escalate_human: bool
        - confidence: 0.0-1.0
        - followup_questions: list (if Level 0)
        - score_breakdown: dict with scoring details
    """
    sym = set(symptoms)
    
    # Level 0: Insufficient information
    if not sym and not (free_text or "").strip():
        return {
            "category": "other_unclear",
            "severity_level": 0,
            "escalate_human": False,
            "confidence": 0.0,
            "followup_questions": FOLLOWUP_QUESTIONS,
            "score_breakdown": {
                "symptom_score": 0,
                "voice_bonus": 0,
                "total_score": 0,
                "red_flag_detected": False,
                "duration_minutes": duration_minutes,
            },
        }
    
    # Assign category
    category = pick_category(sym)
    
    # Calculate severity and escalation
    severity, escalate = compute_severity(sym, voice_stress_score)
    
    # Calculate score breakdown for transparency
    base_score = calculate_symptom_score(sym)
    voice_bonus = 1 if (base_score > 0 and voice_stress_score is not None and voice_stress_score >= 0.80) else 0
    total_score = base_score + voice_bonus
    red_flag = bool(sym & RED_FLAGS)
    
    # Confidence heuristic
    if severity == 0:
        confidence = 0.0
    elif red_flag or severity == 3:
        confidence = 0.90
    elif severity == 2:
        confidence = 0.75
    else:
        confidence = 0.65
    
    return {
        "category": category,
        "severity_level": severity,
        "escalate_human": escalate,
        "confidence": confidence,
        "followup_questions": [] if severity > 0 else FOLLOWUP_QUESTIONS,
        "score_breakdown": {
            "symptom_score": base_score,
            "voice_bonus": voice_bonus,
            "total_score": total_score,
            "red_flag_detected": red_flag,
            "duration_minutes": duration_minutes,
        },
    }