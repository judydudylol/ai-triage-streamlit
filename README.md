# SAHM (سهم) - AI Emergency Response System

**Smart Aerial Human-Medic** - Rule-based triage and dispatch prototype for Al Ghadir, Riyadh.

> ⚠️ **HACKATHON DEMO** - Not for clinical use. Rule-based prototype, no ML training.

## Quick Start

```bash
cd /Users/fawaz/Downloads/ai-triage-streamlit
pip install -r requirements.txt
streamlit run app.py
```

## Data Files (Source of Truth)

All decision logic is driven by JSON files in `/Files`:

| File | Description |
|------|-------------|
| `D1.md` | Dispatch specification with rules and thresholds |
| `more_info.md` | Additional technical specifications |
| `scenarios.json` | 3 pre-defined test scenarios |
| `cases_send_decision.json` | 10 dispatch test cases |
| `Al_Ghadir_Landing_Zones.json` | 8 drone landing zones |
| `Catergorizer.json` | 48 medical case definitions |

## Dispatch Rules (from D1.md)

Rules applied in priority order:

| Priority | Rule | Condition | Result |
|----------|------|-----------|--------|
| 1 | SAFETY_FILTER | `weather_risk > 35%` | AMBULANCE |
| 2 | EMERGENCY_OVERRIDE | `ground_ETA > harm_threshold` | DOCTOR_DRONE |
| 3 | EFFICIENCY_OPTIMIZATION | `(ground_ETA - air_ETA) > 10 min` | DOCTOR_DRONE |
| 4 | DEFAULT | None of above | AMBULANCE |

## Data Normalization

The datasets use inconsistent formats. `data_loader.py` normalizes them:

### Weather Risk

```python
# scenarios.json uses strings: "10%"
# cases.json uses decimals: 0.88

# Normalization to 0-100 percent:
"10%" → 10.0
0.88  → 88.0
35    → 35.0
```

### Decision Labels

```python
# scenarios.json: "AI Decision": "DOCTOR DRONE"
# cases.json: "AI Dispatch": "🚀 Doctor Drone"

# Normalization to standard format:
"DOCTOR DRONE"    → "DOCTOR_DRONE"
"🚀 Doctor Drone" → "DOCTOR_DRONE"
"Ambulance"       → "AMBULANCE"
```

### Harm Threshold Parsing

```python
# Catergorizer.json: "time_to_irreversible_harm": "4-6 m"

# Parse into (min, max) minutes:
"4-6 m"    → (4, 6)
"30 min"   → (30, 30)
">60 m"    → (60, 60)
```

### Case Name Matching

Emergency case names differ between datasets. Matching uses:
1. Exact match after normalization (lowercase, no punctuation)
2. Token overlap with Jaccard similarity
3. Top 3 alternatives shown in UI for disambiguation

## UI Demo Modes (3 Tabs)

### 1. Scenario Mode
- Select from `scenarios.json` entries
- Shows Expected vs Actual decision
- Highlights matches/mismatches

### 2. Case Mode
- Select from `cases_send_decision.json`
- Displays normalized weather risk (from decimal to %)
- Shows reasoning from dataset

### 3. Manual Mode
- Adjust sliders: Weather Risk, Ground ETA, Air ETA, Harm Threshold
- Optional case selection from Catergorizer.json (auto-fills harm threshold)
- Real-time dispatch decision

## Common UI Elements

- **Decision Card**: Visual display of AMBULANCE or DOCTOR_DRONE
- **"Why this decision?"**: Expandable reasons with numeric thresholds
- **Landing Zone Panel**: Shown when drone dispatched (nearest zone by haversine)
- **Debug Mode**: Toggle to show raw normalized inputs/outputs
- **Download**: Export full run log as JSON

## Validation

Built-in validation tests:

```
Scenarios: 3/3 ✓
Cases: 10/10 ✓
Overall: 13/13 (100% accuracy)
```

Run standalone validation:
```bash
python3 validator.py
```

## Project Structure

```
ai-triage-streamlit/
├── app.py                   # Streamlit UI (3 tabs)
├── data_loader.py           # JSON loading + normalization
├── dispatch_engine.py       # D1.md rule-based dispatch
├── categorizer_engine.py    # Fuzzy case name matching
├── landing_zone.py          # Haversine zone selection
├── validator.py             # Scenario/case validation
├── Files/                   # Data files (source of truth)
│   ├── D1.md
│   ├── more_info.md
│   ├── scenarios.json
│   ├── cases_send_decision.json
│   ├── Al_Ghadir_Landing_Zones.json
│   └── Catergorizer.json
└── requirements.txt
```

## Geographic Constants

From D1.md:

- **Target Location**: 24.7745°N, 46.6575°E (Al Humaid St)
- **Ground Distance**: 4.8 km
- **Air Distance**: 3.2 km
- **Ambulance Speed**: 35 km/h
- **Drone Speed**: 120 km/h
- **Default Air ETA**: 3.6 min

---

