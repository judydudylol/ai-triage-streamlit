# SAHM (سهم): The Complete Project

## The Problem - A National Infrastructure Challenge

Saudi Arabia is experiencing explosive growth. By 2034, the country will host the **FIFA World Cup**. In 2030, it's hosting the **World Expo**. Tourism is expanding rapidly. Cities are growing. Major events like Hajj already bring millions of people into concentrated spaces.

This creates a medical emergency crisis that traditional ambulance systems cannot solve:

**The Current Reality:**
- Urban traffic delays ambulances by 12-25+ minutes
- Event crowds make roads completely impassable
- Remote areas have no fast emergency coverage
- During cardiac arrest, brain death begins in 4-6 minutes
- For stroke, every minute of delay increases permanent disability
- For severe allergic reactions or trauma, the window is even tighter

**The Math Doesn't Work:**
- Ambulance average response time in Riyadh traffic: **15-25 minutes**
- Time to irreversible harm for most critical emergencies: **4-10 minutes**
- Gap: **People die waiting**

During World Cup 2034, with roads blocked for security and crowds, this gap becomes catastrophic. Saudi Arabia needs emergency infrastructure that operates **above traffic**, not through it.

This isn't a "nice to have" tech demo. It's a **national necessity** for a country aiming to lead globally without compromising the safety of its people.

---

## The Solution - SAHM: Smart Aerial Human-Medic

SAHM is a complete **AI-powered emergency response system** that delivers trained human medics to critical patients by air in **2-4 minutes**.

### The Core Innovation

Most "medical drone" projects deliver equipment: an AED, an EpiPen, a first aid kit. SAHM's key differentiator is:

**A trained human medic, not just equipment, reaches the patient.**

The drone is transportation. The value is the **professional medical intervention** delivered at life-saving speed.

---

## How The System Works - The Full Stack

When someone calls emergency services for a critical situation, SAHM executes this workflow:

### **Step 1: Emergency Call Received**
- Standard emergency call comes in: someone reports a person collapsed, having chest pain, severe allergic reaction, etc.
- A human operator takes the call and enters it into the system
- The emergency request enters SAHM

### **Step 2: AI Triage - Intelligent Case Analysis**

The AI triage layer immediately analyzes multiple factors:

**Medical Analysis:**
- **Symptoms**: What's happening to the patient?
- **Severity**: How critical is this? (Level 1-4)
- **Category**: Cardiac, respiratory, trauma, neurological, allergic, etc.
- **Voice cues**: Is the caller panicked? Extremely distressed? This indicates urgency even if they're downplaying symptoms

**Real-Time Context:**
- **Traffic**: Current congestion on routes to the location
- **Crowd density**: Is this during an event? In a packed area? Roads blocked?
- **Weather**: Wind speed, visibility, sandstorm risk
- **Accessibility**: Can a ground vehicle even reach this location? (Crowded stadium, remote area, blocked roads)

**Output**: A complete emergency profile with:
- Medical category
- Severity level
- Time to irreversible harm (harm window)
- Confidence score

### **Step 3: The Dispatch Brain - Choosing the Response Mode**

This is the core decision engine - the part we built for the hackathon.

The system evaluates three strict rules **in priority order**:

#### **Rule 1: Safety Filter (Weather)**
- **Check**: Is `weather_risk > 35%`?
- **If YES**: Immediately default to **Ground Ambulance**
- **Why**: Drones cannot operate safely in high winds, sandstorms, or low visibility
- **Non-negotiable**: Safety first, always

#### **Rule 2: Emergency Override (Harm Window)**
- **Check**: Will the ambulance arrive after the harm window closes?
- **Math**: Is `predicted_ground_ETA > harm_threshold_minutes`?
- **If YES**: Deploy **Doctor Drone immediately**
- **Example**: Cardiac arrest has a 4-6 minute window. If ambulance ETA is 18 minutes, the patient will suffer brain death before help arrives. Drone override triggers automatically.

#### **Rule 3: Efficiency Optimization (Traffic)**
- **Check**: Does the drone save significant time?
- **Math**: Is `(ground_ETA - air_ETA) > 10 minutes`?
- **If YES**: Deploy **Doctor Drone**
- **Why**: In a city-wide system, saving 10+ minutes per call means more lives saved across all emergencies
- **Context**: Considers traffic on Northern Ring Road, crowd density, time of day

#### **Rule 4: Default**
- If none of the above trigger: **Ground Ambulance**
- It's safe, sufficient, and lower cost

**Possible Outputs:**
1. **AMBULANCE** (weather unsafe, or time advantage isn't significant)
2. **DOCTOR_DRONE** (life-saving speed needed)
3. **COMBINED** (drone stabilizes immediately, ambulance follows for transport)

**Critical Design Choice**: These are **hard rules, not learned behavior**. Every decision is explainable. Regulators, doctors, and families can audit exactly why a choice was made.

### **Step 4: Ultra-Fast Medic Matching** (< 3 seconds)

Once the system decides on a Doctor Drone response, it immediately selects which medic to deploy:

**Matching Criteria:**
- **Specialty**: Cardiac emergency? Send a cardiac-trained medic. Trauma? Send trauma specialist.
- **Availability**: Who's not currently on a call?
- **GPS Location**: Who's closest to the patient right now?
- **Equipment**: Does this medic have the right gear already staged?

**Speed**: The system claims this happens in **under 3 seconds** - essentially instant.

**Why This Matters**: 
- You don't just get "a doctor" - you get the **right doctor** for your specific emergency
- A pediatric cardiac arrest gets a pediatric cardiac specialist
- A severe bleeding case gets someone trained in trauma and blood loss

### **Step 5: Automatic Loadout Preparation**

Based on the emergency category, the system auto-prepares the medical loadout:

**Examples:**
- **Cardiac Arrest**: AED (defibrillator), oxygen, cardiac medications, CPR equipment
- **Severe Allergic Reaction**: EpiPen, antihistamines, oxygen, airway management
- **Major Trauma/Bleeding**: Trauma kit, hemostatic dressings, tourniquets, IV fluids
- **Stroke**: Stroke assessment tools, oxygen, time-critical medications
- **Respiratory Emergency**: Oxygen, nebulizer, emergency inhalers, airway equipment

This happens automatically while the drone is being prepped - no delay.

### **Step 6: Deployment, Stabilization, and Handoff**

#### **Drone Launch:**
- The selected medic boards the medical eVTOL (electric vertical takeoff and landing aircraft)
- The drone lifts off and flies direct to the emergency
- **No traffic. No roads. No delays.**

#### **Landing Zone Selection:**
- The system has pre-mapped every safe landing zone in the coverage area (Al Ghadir has multiple: rooftops, parking lots, open courtyards)
- Algorithm picks the **nearest safe zone** to the patient's exact location
- Example: Patient at 7319 Al Humaid St → Nearest zone is 150m away at a parking area

#### **Arrival and Care:**
- **Time**: 2-4 minutes from initial call (in Al Ghadir scenario: ~3.6 minutes flight time)
- Medic lands, grabs equipment, reaches patient
- **Immediate professional intervention**:
  - Cardiac arrest: Start CPR, apply AED, administer medications
  - Stroke: Assess using stroke protocol, provide oxygen, prepare for rapid transport
  - Trauma: Stop bleeding, stabilize injuries, manage shock
  - Allergic reaction: Administer EpiPen, manage airway, monitor vitals

#### **Coordination with Ground Team:**
- While the aerial medic is stabilizing the patient, the ground ambulance is en route
- The aerial medic communicates directly: patient status, treatments given, what's needed next
- When ambulance arrives (8-15 minutes later), there's a clean handoff
- Ambulance transports the **already-stabilized patient** to hospital
- Survival rate: dramatically higher

---

## The Technology Stack - What Makes This Work

### **Layer 1: AI Triage Engine**
- Rule-based symptom scoring system
- Voice stress analysis (caller panic level)
- Red flag detection (immediate critical symptoms)
- Category classification (respiratory, cardiac, neuro, trauma, etc.)
- Severity scoring (0-3 scale)
- Confidence estimation

**What We Built**: Full working triage engine with:
- 40+ symptoms with point values
- Red flag instant escalation
- Score-to-severity mapping
- Follow-up question generator for insufficient info

### **Layer 2: Dispatch Decision Engine** 
- Three-rule priority system (weather → harm → efficiency)
- Real-time weather monitoring integration
- Traffic and crowd density assessment
- ETA calculation for both modes
- Medical harm window database

**What We Built**: Complete dispatch brain with:
- Hard-coded thresholds from D1.md spec
- Weather risk normalization (handles different data formats)
- Harm threshold lookup from medical reference database
- Time delta calculation
- Rule trigger tracking + explainable output

### **Layer 3: Medical Reference Database**
- 50+ emergency case types
- Time-to-irreversible-harm for each
- Required equipment lists
- Intervention protocols for first 5 minutes
- Severity classifications

**What We Built**: Complete categorizer with:
- Case name matching (exact + fuzzy)
- Harm threshold extraction with range parsing
- Category grouping
- Equipment recommendations

### **Layer 4: Geographic Intelligence**
- Pre-mapped landing zones throughout coverage area
- Distance calculations (haversine formula for GPS)
- Ground route vs air route comparison
- Landing zone capacity and safety ratings
- Real-time zone availability

**What We Built**: Landing zone system with:
- Al Ghadir neighborhood zone database
- Distance-to-target calculation
- Nearest zone selection algorithm
- Multi-zone sorting and display

### **Layer 5: Vehicle Performance Models**
- Ambulance: 35 km/h average (weighted for siren + traffic)
- Drone: 120 km/h cruise speed (constant)
- Ground routes: 1.5x aerial distance (road layout factor)
- Al Ghadir specific: Ground = 4.8 km, Air = 3.2 km

**What We Built**: ETA calculators using these constants

### **Layer 6: Validation & Logging**
- Test scenario database
- Expected vs actual decision tracking
- Accuracy scoring
- Full decision audit trail (downloadable JSON logs)

**What We Built**: Validator that runs through scenarios and cases, computes match rate, exports results

---

---

### **The Medical Harm Windows Are Real**
These aren't guesses - they're from emergency medicine:
- **Cardiac arrest**: 4-6 minutes to brain damage
- **Stroke**: 10-15 minutes to irreversible loss (but "golden hour" matters)
- **Severe bleeding**: 5-10 minutes to shock/death (arterial)
- **Anaphylaxis**: 3-5 minutes to airway closure

The system uses actual medical thresholds from the categorizer database.

### **The Geography Is Real**
- Al Ghadir is a real neighborhood in Riyadh
- Target location: 7319 Al Humaid St (24.7745° N, 46.6575° E)
- Landing zones are actual rooftops, parking areas, courtyards in the area
- Distance and speed calculations match real-world constraints

### **The Weather Constraints Are Real**
- 35% weather risk threshold is based on actual drone operational limits
- High winds (>40 km/h): unsafe
- Low visibility (<1 km): unsafe
- Sandstorms: complete grounding

SAHM combines proven concepts: aerial medical response (helicopters) + drone speed + AI dispatch.

---

## The Expected Impact - Why This Matters

### **Lives Saved**
- **Current system**: 15-25 min response → many deaths in cardiac/stroke cases
- **SAHM system**: 2-4 min response → survival rates match hospital standards
- **Evidence**: Every 1-minute reduction in cardiac arrest response time = ~10% survival increase

### **Mega-Event Readiness**
- **World Cup 2034**: Stadiums with 80,000 people, roads closed for security
  - Ambulances: blocked, 30+ min response
  - SAHM: flies over crowds, 2-3 min response
- **Hajj**: 2 million+ people in Mecca, extreme density
  - Ground vehicles: gridlock
  - Aerial medics: direct access
- **Expo 2030**: International visitors, high expectations for safety

### **National Coverage**
- Urban areas: defeat traffic
- Remote areas: defeat distance
- Border regions: provide coverage where ground infrastructure is weak
- Tourism destinations: protect visitors

### **Scalable Model**
- Start with Al Ghadir (proof of concept)
- Expand to all of Riyadh
- Deploy in Mecca, Medina, Jeddah
- Eventually: national network

---


---

## The Pitch - Why SAHM Wins

### **Problem Scope**: National infrastructure challenge for a rapidly growing country facing World Cup 2034, Expo 2030, and massive tourism expansion

### **Solution**: AI-powered aerial medical response that delivers trained human medics in 2-4 minutes, operating above traffic

### **Differentiation**: Not a flying first-aid kit - a flying doctor with professional medical intervention

### **Feasibility**: Built on existing drone tech, proven medical protocols, and real geographic data

### **Impact**: Transforms emergency response survival rates during the exact period when Saudi Arabia needs it most

### **Demonstration**: Working prototype proves the decision engine works, with transparent, auditable, medically-grounded logic

### **Vision**: From Al Ghadir neighborhood demo to national emergency infrastructure

---

## The Bottom Line

**SAHM is Uber for emergency doctors, except the Uber is a drone, the decision to send it is made by AI in milliseconds using medical harm windows and weather safety rules, and the outcome is you survive a heart attack because a trained medic reached you in 3 minutes instead of 20.**

It's not a future concept. It's a **now necessity** for Saudi Arabia's immediate infrastructure needs.

And we built the brain that makes it work.