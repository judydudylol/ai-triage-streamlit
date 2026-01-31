# Technical Specifications: Al Ghadir Dispatch AI Prototype																									
																									
## 1. System Constants (Al Ghadir Neighborhood)																									
- **Base Ambulance Speed:** 35 km/h (weighted for city sirens).																									
- **Constant Drone Speed:** 120 km/h (eVTOL cruise speed).																									
- **Ground Distance:** 4.8 km (Road path to Al Humaid St).																									
- **Air Distance:** 3.2 km (Straight-line vector).																									
																									
## 2. Dispatch Decision Logic (The Algorithm)																									
The prototype must implement the following three-step logic:																									
																									
1. **Safety Filter:** If `Weather_Risk` > 35% -> **Always Dispatch Ambulance**.																									
2. **Survival Logic:** If `Predicted_Ground_Time` > `Medical_Harm_Threshold` -> **Dispatch Doctor Drone**.																									
3. **Efficiency Logic:** If `(Ground_Time - Air_Time)` > 10 minutes -> **Dispatch Doctor Drone**.																									
4. **Default State:** If none of the above are met, dispatch **Ambulance**.																									
																									
## 3. Implementation Goals																									
- **Processing Speed:** AI decision must be calculated in <100ms once inputs are received.																									
- **Data Integration:** The system should map the `Emergency_Case` from the incoming signal to the `Harm_Threshold` provided in the medical reference table.																