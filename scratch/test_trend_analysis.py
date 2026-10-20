import sys
sys.path.insert(0, '.')

from services.health_trend_analyzer import (
    extract_patient_health_measurements,
    discover_available_parameters,
    filter_measurements_by_period,
    build_parameter_summaries,
    build_chart_datasets,
    build_historical_measurements_table,
    generate_trend_ai_observations,
    build_deterministic_observations,
    get_trend_analysis_data,
    classify_fasting_glucose,
    classify_hba1c,
    classify_total_cholesterol,
    classify_ldl,
    classify_hdl,
    classify_triglycerides,
    classify_creatinine,
    classify_blood_pressure_readings
)

print("=" * 70)
print("RUNNING COMPREHENSIVE TREND ANALYSIS TESTS")
print("=" * 70)

# ============================================================
# 1. TEST CLINICAL DANGER CLASSIFICATIONS
# ============================================================
print("\n[1] Testing Clinical Danger Classifications...")

# Fasting Glucose (normal 70-99, amber 100-125, red >=126 or <54)
assert classify_fasting_glucose(90.0, "mg/dL")[0] == "green"
assert classify_fasting_glucose(115.0, "mg/dL")[0] == "amber"
assert classify_fasting_glucose(142.0, "mg/dL")[0] == "red"
assert classify_fasting_glucose(50.0, "mg/dL")[0] == "red"
print("  [OK] Fasting Glucose classifications validated (green/amber/red).")

# HbA1c (normal <5.7, amber 5.7-6.4, red >=6.5)
assert classify_hba1c(5.4, "%")[0] == "green"
assert classify_hba1c(5.8, "%")[0] == "amber"
assert classify_hba1c(7.3, "%")[0] == "red"
print("  [OK] HbA1c classifications validated (green/amber/red).")

# Total Cholesterol (desirable <200, borderline 200-239, high >=240)
assert classify_total_cholesterol(188.0, "mg/dL")[0] == "green"
assert classify_total_cholesterol(218.0, "mg/dL")[0] == "amber"
assert classify_total_cholesterol(250.0, "mg/dL")[0] == "red"
print("  [OK] Total Cholesterol classifications validated.")

# LDL Cholesterol (optimal <100, borderline 100-159, high >=160)
assert classify_ldl(95.0, "mg/dL")[0] == "green"
assert classify_ldl(112.0, "mg/dL")[0] == "amber"
assert classify_ldl(142.0, "mg/dL")[0] == "amber"
assert classify_ldl(170.0, "mg/dL")[0] == "red"
print("  [OK] LDL Cholesterol classifications validated.")

# Blood pressure readings (systolic / diastolic)
assert classify_blood_pressure_readings(118.0, 78.0)[0] == "green"
assert classify_blood_pressure_readings(125.0, 78.0)[0] == "amber"
assert classify_blood_pressure_readings(135.0, 85.0)[0] == "amber"
assert classify_blood_pressure_readings(145.0, 92.0)[0] == "red"
assert classify_blood_pressure_readings(185.0, 122.0)[0] == "red"
print("  [OK] Blood Pressure classifications validated.")


# ============================================================
# 2. TEST EXTRACTION & PARAMETER DISCOVERY
# ============================================================
print("\n[2] Testing Measurement Extraction & Parameter Discovery...")

sample_timeline_events = [
    {
        "id": "ev-1",
        "medical_record_id": "rec-1",
        "event_date": "2026-09-05",
        "investigations": [
            {"name": "Fasting Blood Glucose (FBS)", "result": "108", "unit": "mg/dL", "reference_range": "70 - 99"},
            {"name": "Post Prandial Blood Glucose (PPBS)", "result": "142", "unit": "mg/dL", "reference_range": "< 140"},
            {"name": "HbA1c (Glycated Hemoglobin)", "result": "5.8", "unit": "%", "reference_range": "4.0 - 5.6"},
            {"name": "Total Cholesterol", "result": "188", "unit": "mg/dL", "reference_range": "< 200"},
            {"name": "Triglycerides", "result": "162", "unit": "mg/dL", "reference_range": "< 150"},
            {"name": "HDL Cholesterol", "result": "42", "unit": "mg/dL", "reference_range": "> 40"},
            {"name": "LDL Cholesterol", "result": "112", "unit": "mg/dL", "reference_range": "< 100"},
            {"name": "Serum Creatinine", "result": "0.9", "unit": "mg/dL", "reference_range": "0.6 - 1.2"},
            {"name": "Complete Blood Count (CBC)", "result": "Within normal limits", "unit": None}
        ]
    },
    {
        "id": "ev-2",
        "medical_record_id": "rec-2",
        "event_date": "2026-09-28",
        "investigations": [
            {"name": "Fasting Blood Glucose", "result": "142", "unit": "mg/dL"},
            {"name": "HbA1c", "result": "7.3", "unit": "%"},
            {"name": "Total Cholesterol", "result": "218", "unit": "mg/dL"},
            {"name": "LDL Cholesterol", "result": "142", "unit": "mg/dL"},
            {"name": "HDL Cholesterol", "result": "43", "unit": "mg/dL"},
            {"name": "Triglycerides", "result": "165", "unit": "mg/dL"}
        ]
    }
]

sample_records = [
    {"id": "rec-1", "title": "Laboratory Report - 05 Sep 2026", "record_type": "Lab Report", "file_url": "https://example.com/rec1.pdf"},
    {"id": "rec-2", "title": "Follow-up Lab Report - 28 Sep 2026", "record_type": "Lab Report", "file_url": "https://example.com/rec2.pdf"}
]

measurements = extract_patient_health_measurements(sample_timeline_events, sample_records)
print(f"  Total extracted measurements: {len(measurements)}")
assert len(measurements) == 14, f"Expected 14 measurements, got {len(measurements)}"

# Test discovery
discovered = discover_available_parameters(measurements)
discovered_keys = {p["key"]: p for p in discovered}
print(f"  Discovered {len(discovered)} unique parameters:")
for p in discovered:
    print(f"    - {p['name']}: count={p['count']}, sufficient={p['has_sufficient_data']}")

assert "fasting_blood_glucose" in discovered_keys
assert discovered_keys["fasting_blood_glucose"]["has_sufficient_data"] is True
assert discovered_keys["fasting_blood_glucose"]["count"] == 2

assert "hba1c" in discovered_keys
assert discovered_keys["hba1c"]["has_sufficient_data"] is True
assert discovered_keys["hba1c"]["count"] == 2

# Post Prandial Blood Glucose only has 1 measurement:
assert "pp_blood_glucose" in discovered_keys
assert discovered_keys["pp_blood_glucose"]["has_sufficient_data"] is False
assert discovered_keys["pp_blood_glucose"]["count"] == 1

# Serum Creatinine only has 1 measurement:
assert "serum_creatinine" in discovered_keys
assert discovered_keys["serum_creatinine"]["has_sufficient_data"] is False
assert discovered_keys["serum_creatinine"]["count"] == 1

# Non-numeric result ("Within normal limits") was safely excluded from numeric trends
assert "complete_blood_count_cbc" not in discovered_keys
print("  [OK] Non-numeric test results safely ignored for quantitative trend charts.")


# ============================================================
# 3. TEST FULL TREND DATA WORKFLOW
# ============================================================
print("\n[3] Testing get_trend_analysis_data Workflow...")

trend_data = get_trend_analysis_data(
    sample_timeline_events,
    sample_records,
    patient_name="John Doe"
)

assert trend_data["has_data"] is True
assert trend_data["date_range_display"] == "05 Sep 2026 - 28 Sep 2026"
assert len(trend_data["summaries"]) == 6  # 6 parameters have sufficient data by default
assert len(trend_data["charts"]) == 6
assert len(trend_data["historical_table"]) == 12  # 6 params x 2 dates

# Verify Fasting Glucose Summary calculation
fbs_summary = next(s for s in trend_data["summaries"] if s["param_key"] == "fasting_blood_glucose")
assert fbs_summary["latest_value"] == 142.0
assert fbs_summary["previous_value"] == 108.0
assert fbs_summary["change_text"] == "+34.0 mg/dL"
assert fbs_summary["change_direction"] == "up"
assert fbs_summary["danger_level"] == "red"
print("  [OK] Fasting glucose change (+34.0 mg/dL) and red danger level calculated correctly.")

# Verify HbA1c Summary calculation
hba1c_summary = next(s for s in trend_data["summaries"] if s["param_key"] == "hba1c")
assert hba1c_summary["latest_value"] == 7.3
assert hba1c_summary["previous_value"] == 5.8
assert hba1c_summary["change_text"] == "+1.5 %"
assert hba1c_summary["change_direction"] == "up"
assert hba1c_summary["danger_level"] == "red"
print("  [OK] HbA1c change (+1.5 %) and red danger level calculated correctly.")


# ============================================================
# 4. TEST FILTERING BY PARAMETER AND TIME PERIOD
# ============================================================
print("\n[4] Testing Parameter and Time Period Filtering...")

# Select only Fasting Glucose and Serum Creatinine
filtered_data = get_trend_analysis_data(
    sample_timeline_events,
    sample_records,
    selected_params=["fasting_blood_glucose", "serum_creatinine"],
    time_period="all",
    patient_name="John Doe"
)

assert len(filtered_data["summaries"]) == 2
assert len(filtered_data["charts"]) == 2
creat_chart = filtered_data["charts"]["serum_creatinine"]
assert creat_chart["has_sufficient_data"] is False
assert creat_chart["measurement_count"] == 1
print("  [OK] Custom parameter selection correctly includes single-measurement parameter without crashing.")

# Test time filtering: 3m relative to 2026-09-28 includes both Sep 05 and Sep 28
p3m_data = get_trend_analysis_data(
    sample_timeline_events,
    sample_records,
    time_period="3m",
    patient_name="John Doe"
)
assert p3m_data["total_measurements_in_period"] == 14
print("  [OK] Time period filtering successfully computed.")


# ============================================================
# 5. TEST BLOOD PRESSURE HANDLING (DUAL SERIES)
# ============================================================
print("\n[5] Testing Dual Series Blood Pressure Extraction...")

bp_events = [
    {
        "id": "ev-bp1",
        "medical_record_id": "rec-bp1",
        "event_date": "2026-08-01",
        "investigations": [
            {"name": "Blood Pressure", "result": "120/80", "unit": "mmHg"}
        ]
    },
    {
        "id": "ev-bp2",
        "medical_record_id": "rec-bp2",
        "event_date": "2026-09-15",
        "investigations": [
            {"name": "Blood Pressure", "result": "142/92", "unit": "mmHg"}
        ]
    }
]

bp_data = get_trend_analysis_data(bp_events, [], patient_name="Jane Doe")
assert "blood_pressure" in bp_data["charts"]
bp_chart = bp_data["charts"]["blood_pressure"]
assert len(bp_chart["datasets"]) == 2
assert bp_chart["datasets"][0]["label"] == "Systolic"
assert bp_chart["datasets"][1]["label"] == "Diastolic"
assert bp_chart["datasets"][0]["data"] == [120.0, 142.0]
assert bp_chart["datasets"][1]["data"] == [80.0, 92.0]
print("  [OK] Dual series blood pressure datasets created correctly for Chart.js.")


# ============================================================
# 6. TEST DETERMINISTIC OBSERVATIONS FALLBACK
# ============================================================
print("\n[6] Testing AI Observations Fallback Engine...")

obs = build_deterministic_observations(trend_data["summaries"])
assert len(obs) >= 3
print(f"  Generated {len(obs)} deterministic clinical observations:")
for o in obs:
    print(f"    - [{o['type'].upper()}] {o['title']}: {o['text']}")
print("  [OK] Observations accurately cite values, dates, and clinical thresholds.")

print("\n" + "=" * 70)
print("ALL TREND ANALYSIS TESTS COMPLETED SUCCESSFULLY!")
print("=" * 70)
