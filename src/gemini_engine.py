"""
AI Engine for Emergency Audio Analysis

Uses Generative AI (Gemini 3.0) to analyze emergency audio calls,
extracting transcription, voice stress, symptoms, and recommended actions.
"""

import os
import json
from typing import Optional

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# API Key handling
def get_api_key():
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


# Symptom mapping from natural language to triage_engine keys
SYMPTOM_MAPPING = {
    # Cardiac
    "chest pain": "chest_pain",
    "crushing chest pain": "chest_pain_crushing",
    "chest pressure": "chest_pain",
    "heart racing": "palpitations",
    "palpitations": "palpitations",
    
    # Respiratory
    "difficulty breathing": "shortness_of_breath",
    "trouble breathing": "trouble_breathing",
    "shortness of breath": "shortness_of_breath",
    "can't breathe": "trouble_breathing",
    "choking": "choking",
    "wheezing": "wheezing",
    "turning blue": "turning_blue",
    
    # Neuro
    "unconscious": "unconscious",
    "not responding": "not_responding",
    "fainted": "fainting",
    "fainting": "fainting",
    "seizure": "seizure_now",
    "convulsions": "seizure_now",
    "confusion": "confusion",
    "face drooping": "face_droop",
    "slurred speech": "slurred_speech",
    "arm weakness": "arm_weakness",
    "stroke": "stroke_signs",
    
    # Trauma/Bleeding
    "bleeding": "moderate_bleeding",
    "heavy bleeding": "heavy_bleeding",
    "severe bleeding": "severe_bleeding",
    "head injury": "head_injury",
    "trauma": "major_trauma",
    
    # Allergic
    "allergic reaction": "anaphylaxis_signs",
    "anaphylaxis": "anaphylaxis_signs",
    "swelling": "swelling_face_lips",
    "face swelling": "severe_allergy_swelling",
    "throat swelling": "severe_allergy_swelling",
    "hives": "rash",
    "rash": "rash",
    
    # Infection/Fever
    "fever": "fever",
    "high fever": "high_fever",
    "chills": "chills",
    
    # GI
    "vomiting": "vomiting",
    "nausea": "nausea",
    "diarrhea": "diarrhea",
    "dehydration": "dehydration",
    
    # Other
    "headache": "headache",
    "pain": "mild_pain",
    "panic": "panic",
    "distress": "severe_distress",
}


# System instruction for Gemini
SYSTEM_INSTRUCTION = """
You are an expert Emergency Medical Dispatcher AI specializing in audio triage analysis.
Your role is to perform rigorous, clinical-grade analysis of emergency audio calls.

## ANALYSIS PROTOCOL

### 1. TRANSCRIPTION
Provide a verbatim transcription of all spoken content in the audio.

### 2. MEDICAL SUMMARY
Generate a professional dispatch-style summary following this format:
"[Caller type] reporting [primary complaint], [key details], onset [time since symptoms began]."
Example: "Adult female caller reporting severe crushing chest pain radiating to left arm, with shortness of breath, onset approximately 20 minutes ago."

### 3. VOICE STRESS ANALYSIS (Critical - Be Rigorous)
Analyze the ACOUSTIC PROPERTIES of the caller's voice, not just what they say.
Score from 0.0 to 1.0 based on these objective criteria:

**0.0-0.2 (CALM):**
- Normal speech rate (120-150 words/min)
- Steady pitch with minimal variation
- Full sentences, organized thoughts
- Normal breathing patterns between phrases
- No audible distress markers

**0.2-0.4 (MILD CONCERN):**
- Slightly elevated speech rate
- Minor pitch elevation
- Occasional hesitation or repetition
- Slight breathiness

**0.4-0.6 (MODERATE STRESS):**
- Noticeably faster speech (150-180 words/min)
- Pitch elevation with some cracking
- Incomplete sentences, jumping between topics
- Audible sighing or heavy breathing
- Detectable tremor in voice

**0.6-0.8 (HIGH STRESS):**
- Rapid speech (180+ words/min) OR very slow/strained
- Significant pitch instability
- Crying, sobbing, or voice breaking
- Gasping or labored breathing
- Inability to complete thoughts
- Background sounds of distress

**0.8-1.0 (EXTREME DISTRESS/PANIC):**
- Screaming, shrieking, or incoherent
- Complete loss of speech control
- Hyperventilation audible
- Uncontrolled crying
- Terror indicators in voice quality

Provide specific acoustic evidence for your score in voiceStressIndicators.

### 4. SYMPTOM DURATION EXTRACTION
Extract how long symptoms have been present. Listen for explicit phrases like:
- "started X minutes/hours ago"
- "been going on for..."
- "since this morning/yesterday"
- "just started" = estimate 2-5 minutes
- "a few minutes" = estimate 5-10 minutes

**CRITICAL: If the caller does NOT mention duration at all, set symptomDurationMinutes to -1 (unknown).**
Do NOT guess or fabricate a duration. Only output a positive number if the caller explicitly indicates timing.
Output as integer minutes (symptomDurationMinutes). Use -1 for unknown.

### 5. SYMPTOM IDENTIFICATION (CRITICAL - Use Exact Keys)
You MUST output symptoms using ONLY these exact canonical keys. Do NOT invent new symptom names.
If the caller describes something not on this list, pick the CLOSEST match.

**Valid Symptom Keys (use exactly as written):**
- Critical (5 pts): unconscious, not_responding, fainting, severe_bleeding, heavy_bleeding, face_droop, slurred_speech, arm_weakness, stroke_signs, severe_allergy_swelling, anaphylaxis_signs
- Urgent (4 pts): trouble_breathing, shortness_of_breath, chest_pain, chest_pain_crushing, choking, turning_blue
- Concerning (3 pts): moderate_bleeding, seizure_now, major_trauma, head_injury, confusion
- Moderate (2 pts): high_fever, fever, vomiting_severe, diarrhea_severe, dehydration, palpitations, wheezing
- Mild (1 pt): mild_pain, headache, rash, chills, nausea, vomiting, diarrhea, panic, severe_distress, swelling_face_lips

**Mapping Examples:**
- "tightness in chest" → chest_pain
- "pressure on my chest" → chest_pain
- "can't get air" → trouble_breathing
- "about to pass out" → fainting
- "turning purple" → turning_blue
- "he fell and hit his head" → head_injury
- Arabic/dialect descriptions → map to closest English key above

### 6. SEVERITY ASSESSMENT (Use CTAS Scale)
Base your severity on the Canadian Triage and Acuity Scale (CTAS):
- **CRITICAL (CTAS 1)**: Immediate life threat. Cardiac arrest, respiratory failure, anaphylaxis, massive hemorrhage, drowning, choking. Harm window: 2-6 minutes.
- **HIGH (CTAS 2)**: Emergent. Severe chest pain, stroke signs, seizures, major trauma, severe allergic reaction. Harm window: 10-20 minutes.
- **MEDIUM (CTAS 3)**: Urgent. Moderate pain, fever with distress, minor bleeding, breathing difficulty (stable). Can wait 30-60 minutes.
- **LOW (CTAS 4-5)**: Less urgent. Cough, cold symptoms, minor injuries, rashes. Can wait hours.

### 7. RESPONSE RECOMMENDATION (Be Conservative)
**CRITICAL RULE: Drone deployment is expensive and limited. Only recommend DRONE or BOTH for true emergencies.**

- **AMBULANCE** (default): Use for MOST cases including:
  - LOW severity (cough, cold, minor pain, stable fever)
  - MEDIUM severity (moderate symptoms, patient stable)
  - HIGH severity where patient is conscious and breathing adequately
  - Any case where harm window is >15 minutes
  
- **DRONE**: ONLY for CRITICAL cases where:
  - Patient is unconscious, not breathing, or in cardiac arrest
  - Severe anaphylaxis (throat closing, can't breathe)
  - Active massive bleeding requiring immediate intervention
  - Choking with airway obstruction
  - Harm window is <10 minutes AND ground ETA exceeds this
  
- **BOTH**: ONLY for CRITICAL cases that need:
  - Immediate stabilization (drone) AND hospital transport (ambulance)
  - Examples: cardiac arrest, major trauma, respiratory failure

- **NONE**: Not a medical emergency (advice call, information request)

**DO NOT recommend DRONE for:**
- Coughs, colds, flu-like symptoms
- Minor cuts, bruises, sprains
- Stable fever, headache, nausea
- Chest pain where patient is conscious and breathing normally
- Any "worried well" or anxiety-based calls

Output strictly in JSON format matching the schema provided.
"""


def map_symptom_to_key(symptom_text: str) -> Optional[str]:
    """
    Map an AI-detected symptom string to a triage_engine SYMPTOM_POINTS key.
    Uses fuzzy matching for flexibility.
    """
    symptom_lower = symptom_text.lower().strip()
    
    # Direct match
    if symptom_lower in SYMPTOM_MAPPING:
        return SYMPTOM_MAPPING[symptom_lower]
    
    # Partial match - check if any mapping key is contained in the symptom
    for phrase, key in SYMPTOM_MAPPING.items():
        if phrase in symptom_lower or symptom_lower in phrase:
            return key
    
    # Try underscore format (e.g., "chest_pain" -> "chest_pain")
    underscore_version = symptom_lower.replace(" ", "_")
    # Import here to avoid circular imports
    from src.triage_engine import SYMPTOM_POINTS
    if underscore_version in SYMPTOM_POINTS:
        return underscore_version
    
    return None


def map_symptoms_to_keys(ai_symptoms: list[str]) -> list[str]:
    """
    Map a list of AI-detected symptom strings to triage_engine keys.
    Returns only valid, deduplicated keys.
    """
    keys = set()
    for symptom in ai_symptoms:
        key = map_symptom_to_key(symptom)
        if key:
            keys.add(key)
    return list(keys)


def analyze_audio_call(
    audio_bytes: bytes,
    mime_type: str = "audio/wav",
    env_context: Optional[dict] = None
) -> Optional[dict]:
    """
    Send audio bytes to AI Engine for analysis.
    
    Args:
        audio_bytes: Raw audio data
        mime_type: MIME type of audio (audio/wav, audio/webm, audio/mp3, etc.)
    
    Returns:
        Dictionary with analysis results:
        - voiceStressScore: float (0.0-1.0)
        - transcription: str
        - medicalSummary: str
        - symptoms: list[str] (mapped to triage keys)
        - rawSymptoms: list[str] (original AI-detected symptoms)
        - severityLevel: str (LOW/MEDIUM/HIGH/CRITICAL)
        - recommendedAction: str (NONE/DRONE/AMBULANCE/BOTH)
        - callerIntent: str
        - reasoning: str
        
        Returns None if analysis fails.
    """
    if not GENAI_AVAILABLE:
        print("Error: google-genai package not installed")
        return None
    
    api_key = get_api_key()
    if not api_key:
        print("Error: GEMINI_API_KEY or GOOGLE_API_KEY not found in environment")
        return None
    
    try:
        client = genai.Client(api_key=api_key)
        
        # Define the structured output schema
        response_schema = {
            "type": "OBJECT",
            "properties": {
                "voiceStressScore": {
                    "type": "NUMBER",
                    "description": "Voice stress level from 0.0 (calm) to 1.0 (panic)"
                },
                "transcription": {
                    "type": "STRING",
                    "description": "Verbatim transcription of the audio"
                },
                "medicalSummary": {
                    "type": "STRING",
                    "description": "Professional medical summary in dispatch style (e.g. 'Male caller rep. chest pain...')"
                },
                "callerIntent": {
                    "type": "STRING",
                    "description": "Brief summary of what the caller needs"
                },
                "symptoms": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "List of medical symptoms detected"
                },
                "severityLevel": {
                    "type": "STRING",
                    "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
                },
                "recommendedAction": {
                    "type": "STRING",
                    "enum": ["NONE", "DRONE", "AMBULANCE", "BOTH"]
                },
                "voiceStressIndicators": {
                    "type": "STRING",
                    "description": "Specific acoustic evidence for voice stress score (e.g., 'rapid speech ~200wpm, voice trembling, audible crying')"
                },
                "symptomDurationMinutes": {
                    "type": "INTEGER",
                    "description": "Estimated duration of symptoms in minutes (default 10 if unknown)"
                },
                "reasoning": {
                    "type": "STRING",
                    "description": "Brief explanation of the severity and action recommendation"
                }
            },
            "required": [
                "voiceStressScore",
                "voiceStressIndicators",
                "transcription",
                "medicalSummary",
                "callerIntent",
                "symptoms",
                "symptomDurationMinutes",
                "severityLevel",
                "recommendedAction"
            ]
        }
        
        # Prepare context string
        context_str = ""
        if env_context:
            context_str = f"""
## OPERATIONAL CONTEXT
- Weather Risk: {env_context.get('weather', 0)}%
- Ground ETA: {env_context.get('ground_eta', 0)} min
- Air ETA: {env_context.get('air_eta', 0)} min
"""

        # Call AI with audio
        # Using Gemini 3.0 Flash Preview with Thinking Config
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_bytes(data=audio_bytes, mime_type=mime_type),
                        types.Part.from_text(
                            text="Analyze this emergency call audio. "
                                 "Extract the transcription, assess voice stress, "
                                 "generate a medical summary, identify symptoms, and recommend a response."
                                 + context_str
                        )
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(
                    thinking_level="LOW",
                ),
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=response_schema
            )
        )
        
        # Parse response
        result = json.loads(response.text)
        
        # Map AI symptoms to triage engine keys
        raw_symptoms = result.get("symptoms", [])
        mapped_symptoms = map_symptoms_to_keys(raw_symptoms)
        
        return {
            "voiceStressScore": float(result.get("voiceStressScore", 0.5)),
            "voiceStressIndicators": str(result.get("voiceStressIndicators", "")),
            "transcription": str(result.get("transcription", "")),
            "medicalSummary": str(result.get("medicalSummary", "")),
            "callerIntent": str(result.get("callerIntent", "")),
            "symptoms": mapped_symptoms,
            "rawSymptoms": raw_symptoms,
            "symptomDurationMinutes": int(result.get("symptomDurationMinutes", 10)),
            "severityLevel": str(result.get("severityLevel", "MEDIUM")),
            "recommendedAction": {
                "DRONE": "DOCTOR_DRONE", 
                "AMBULANCE": "AMBULANCE", 
                "BOTH": "BOTH", 
                "NONE": "AMBULANCE"
            }.get(str(result.get("recommendedAction", "AMBULANCE")), "AMBULANCE"),
            "reasoning": str(result.get("reasoning", "")),
        }
        
    except Exception as e:
        print(f"AI Engine Error: {e}")
        return None


def is_gemini_available() -> bool:
    """Check if AI API is available and configured."""
    if not GENAI_AVAILABLE:
        return False
    if not get_api_key():
        return False
    return True


def get_availability_message() -> str:
    """Get a user-friendly message about AI availability."""
    if not GENAI_AVAILABLE:
        return "google-genai package not installed. Run: pip install google-genai"
    if not get_api_key():
        return "GEMINI_API_KEY not set. Add it to your .env file or environment."
    return "AI Engine is ready"
