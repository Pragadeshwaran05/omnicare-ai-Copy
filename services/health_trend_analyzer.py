# ============================================================
# OMNICARE AI — HEALTH TREND ANALYZER SERVICE
# ============================================================

import os
import re
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

# Optional Gemini client for AI trend observations
try:
    from google import genai
    from google.genai import types

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_API_KEY:
        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options={"timeout": 30000}
        )
    else:
        gemini_client = None
except Exception:
    gemini_client = None

GEMINI_MODEL = "gemini-3.5-flash-lite"


# ============================================================
# CLINICAL PARAMETER DEFINITIONS & VALIDATION RULES
# ============================================================

# Registry of supported parameters with canonical keys, display names,
# default units, matching regex patterns, and validated clinical threshold rules.

PARAMETER_REGISTRY = {
    "fasting_blood_glucose": {
        "display_name": "Fasting Blood Glucose",
        "short_name": "FBS",
        "default_unit": "mg/dL",
        "category": "Glycemic",
        "aliases": [
            r"fasting\s+blood\s+(?:glucose|sugar)",
            r"fasting\s+(?:glucose|sugar)",
            r"\bfbs\b",
            r"glucose\s*[-–]\s*fasting",
            r"blood\s+sugar\s*[-–]\s*fasting"
        ],
        "ref_range_text": "70 – 99 mg/dL",
        "classifier": lambda val, unit: classify_fasting_glucose(val, unit)
    },
    "pp_blood_glucose": {
        "display_name": "Post Prandial Blood Glucose",
        "short_name": "PPBS",
        "default_unit": "mg/dL",
        "category": "Glycemic",
        "aliases": [
            r"post\s+prandial\s+blood\s+(?:glucose|sugar)",
            r"post\s+prandial\s+(?:glucose|sugar)",
            r"\bppbs\b",
            r"glucose\s*[-–]\s*post\s+prandial",
            r"post\s*prandial",
            r"pp\s+glucose"
        ],
        "ref_range_text": "< 140 mg/dL",
        "classifier": lambda val, unit: classify_pp_glucose(val, unit)
    },
    "random_blood_glucose": {
        "display_name": "Random Blood Glucose",
        "short_name": "RBS",
        "default_unit": "mg/dL",
        "category": "Glycemic",
        "aliases": [
            r"random\s+blood\s+(?:glucose|sugar)",
            r"\brbs\b",
            r"glucose\s*[-–]\s*random"
        ],
        "ref_range_text": "70 – 139 mg/dL",
        "classifier": lambda val, unit: classify_pp_glucose(val, unit)
    },
    "blood_glucose": {
        "display_name": "Blood Glucose",
        "short_name": "Glucose",
        "default_unit": "mg/dL",
        "category": "Glycemic",
        "aliases": [
            r"^blood\s+(?:glucose|sugar)$",
            r"^serum\s+glucose$",
            r"^glucose$"
        ],
        "ref_range_text": "70 – 139 mg/dL",
        "classifier": lambda val, unit: classify_pp_glucose(val, unit)
    },
    "hba1c": {
        "display_name": "HbA1c",
        "short_name": "HbA1c",
        "default_unit": "%",
        "category": "Glycemic",
        "aliases": [
            r"hba1c",
            r"glycated\s+hemoglobin",
            r"glycohemoglobin",
            r"hemoglobin\s+a1c"
        ],
        "ref_range_text": "4.0 – 5.6 %",
        "classifier": lambda val, unit: classify_hba1c(val, unit)
    },
    "total_cholesterol": {
        "display_name": "Total Cholesterol",
        "short_name": "Total Chol",
        "default_unit": "mg/dL",
        "category": "Lipid Profile",
        "aliases": [
            r"total\s+cholesterol",
            r"cholesterol,?\s*total",
            r"serum\s+cholesterol"
        ],
        "ref_range_text": "< 200 mg/dL",
        "classifier": lambda val, unit: classify_total_cholesterol(val, unit)
    },
    "ldl_cholesterol": {
        "display_name": "LDL Cholesterol",
        "short_name": "LDL",
        "default_unit": "mg/dL",
        "category": "Lipid Profile",
        "aliases": [
            r"ldl\s+cholesterol",
            r"ldl\s*[-–]?\s*c",
            r"low\s+density\s+lipoprotein",
            r"\bldl\b"
        ],
        "ref_range_text": "< 100 mg/dL",
        "classifier": lambda val, unit: classify_ldl(val, unit)
    },
    "hdl_cholesterol": {
        "display_name": "HDL Cholesterol",
        "short_name": "HDL",
        "default_unit": "mg/dL",
        "category": "Lipid Profile",
        "aliases": [
            r"hdl\s+cholesterol",
            r"hdl\s*[-–]?\s*c",
            r"high\s+density\s+lipoprotein",
            r"\bhdl\b"
        ],
        "ref_range_text": "≥ 40 mg/dL",
        "classifier": lambda val, unit: classify_hdl(val, unit)
    },
    "triglycerides": {
        "display_name": "Triglycerides",
        "short_name": "TG",
        "default_unit": "mg/dL",
        "category": "Lipid Profile",
        "aliases": [
            r"triglycerides?",
            r"serum\s+triglycerides?",
            r"\btg\b"
        ],
        "ref_range_text": "< 150 mg/dL",
        "classifier": lambda val, unit: classify_triglycerides(val, unit)
    },
    "serum_creatinine": {
        "display_name": "Serum Creatinine",
        "short_name": "Creatinine",
        "default_unit": "mg/dL",
        "category": "Renal Function",
        "aliases": [
            r"serum\s+creatinine",
            r"creatinine,?\s*serum",
            r"\bcreatinine\b"
        ],
        "ref_range_text": "0.6 – 1.2 mg/dL",
        "classifier": lambda val, unit: classify_creatinine(val, unit)
    },
    "hemoglobin": {
        "display_name": "Hemoglobin",
        "short_name": "Hb",
        "default_unit": "g/dL",
        "category": "Hematology",
        "aliases": [
            r"^hemoglobin\b(?!\s*a1c)",
            r"^haemoglobin\b(?!\s*a1c)",
            r"\bhgb\b",
            r"^hb\b(?!\s*a1c)"
        ],
        "ref_range_text": "12.0 – 17.5 g/dL",
        "classifier": lambda val, unit: classify_hemoglobin(val, unit)
    },
    "blood_pressure": {
        "display_name": "Blood Pressure",
        "short_name": "BP",
        "default_unit": "mmHg",
        "category": "Vitals",
        "aliases": [
            r"blood\s+pressure",
            r"\bbp\b"
        ],
        "ref_range_text": "< 120/80 mmHg",
        "classifier": None  # Handled as dual systolic/diastolic series
    },
    "heart_rate": {
        "display_name": "Heart Rate",
        "short_name": "Pulse",
        "default_unit": "bpm",
        "category": "Vitals",
        "aliases": [
            r"heart\s+rate",
            r"pulse\s+rate",
            r"\bpulse\b",
            r"\bhr\b"
        ],
        "ref_range_text": "60 – 100 bpm",
        "classifier": lambda val, unit: classify_heart_rate(val, unit)
    },
    "weight": {
        "display_name": "Weight",
        "short_name": "Weight",
        "default_unit": "kg",
        "category": "Anthropometric",
        "aliases": [
            r"body\s+weight",
            r"\bweight\b",
            r"\bwt\b"
        ],
        "ref_range_text": "Target varies",
        "classifier": lambda val, unit: ("gray", "Baseline", "Body weight requires clinical evaluation and BMI context.")
    }
}


# ============================================================
# CLINICAL CLASSIFICATION FUNCTIONS
# ============================================================

def classify_fasting_glucose(val: float, unit: str) -> Tuple[str, str, str]:
    """Classifies fasting glucose based on standard ADA guidelines."""
    # Convert mmol/L to mg/dL if needed
    if "mmol" in unit.lower():
        val = val * 18.0182

    if val < 54.0:
        return ("red", "Critical Low", "Severe hypoglycemia (<54 mg/dL) requires immediate medical attention.")
    elif val < 70.0:
        return ("amber", "Low", "Mild hypoglycemia (54–69 mg/dL). Review diet and hypoglycemic therapy.")
    elif val <= 99.0:
        return ("green", "In Range", "Normal fasting glucose within recommended range (70–99 mg/dL).")
    elif val <= 125.0:
        return ("amber", "Borderline High", "Impaired fasting glucose / prediabetic range (100–125 mg/dL).")
    else:
        return ("red", "Elevated", "Fasting glucose exceeds diabetic diagnostic threshold (≥126 mg/dL).")


def classify_pp_glucose(val: float, unit: str) -> Tuple[str, str, str]:
    """Classifies post-prandial or random blood glucose."""
    if "mmol" in unit.lower():
        val = val * 18.0182

    if val < 54.0:
        return ("red", "Critical Low", "Severe hypoglycemia (<54 mg/dL).")
    elif val < 70.0:
        return ("amber", "Low", "Below standard normal fasting glucose range.")
    elif val < 140.0:
        return ("green", "In Range", "Normal post-prandial glucose (<140 mg/dL).")
    elif val <= 199.0:
        return ("amber", "Borderline High", "Impaired glucose tolerance (140–199 mg/dL).")
    else:
        return ("red", "Elevated", "Markedly elevated glucose (≥200 mg/dL).")


def classify_hba1c(val: float, unit: str) -> Tuple[str, str, str]:
    """Classifies Glycated Hemoglobin (HbA1c)."""
    if val < 4.0:
        return ("amber", "Low", "Subnormal HbA1c (<4.0%).")
    elif val <= 5.6:
        return ("green", "In Range", "Normal HbA1c range (<5.7%).")
    elif val <= 6.4:
        return ("amber", "Borderline High", "Prediabetic range (5.7%–6.4%). Increased risk for progression.")
    elif val <= 8.0:
        return ("red", "Elevated", "Above diabetes diagnostic threshold (≥6.5%). Requires glycemic management.")
    else:
        return ("red", "Critical High", "Significantly elevated HbA1c (>8.0%). High risk of long-term complications.")


def classify_total_cholesterol(val: float, unit: str) -> Tuple[str, str, str]:
    """Classifies Total Cholesterol."""
    if "mmol" in unit.lower():
        val = val * 38.67

    if val < 200.0:
        return ("green", "In Range", "Desirable total cholesterol level (<200 mg/dL).")
    elif val <= 239.0:
        return ("amber", "Borderline High", "Borderline high total cholesterol (200–239 mg/dL).")
    else:
        return ("red", "Elevated", "High total cholesterol (≥240 mg/dL). Cardiovascular risk factor.")


def classify_ldl(val: float, unit: str) -> Tuple[str, str, str]:
    """Classifies LDL Cholesterol."""
    if "mmol" in unit.lower():
        val = val * 38.67

    if val < 100.0:
        return ("green", "In Range", "Optimal LDL cholesterol (<100 mg/dL).")
    elif val <= 159.0:
        return ("amber", "Borderline High", "Above optimal / borderline high LDL (100–159 mg/dL).")
    else:
        return ("red", "Elevated", "High LDL cholesterol (≥160 mg/dL). Elevated atherogenic risk.")


def classify_hdl(val: float, unit: str) -> Tuple[str, str, str]:
    """Classifies HDL Cholesterol (protective lipid)."""
    if "mmol" in unit.lower():
        val = val * 38.67

    if val >= 50.0:
        return ("green", "In Range", "Optimal protective HDL cholesterol (≥50 mg/dL).")
    elif val >= 40.0:
        return ("green", "Acceptable", "Acceptable HDL level (≥40 mg/dL for men, 40-49 for women).")
    elif val >= 35.0:
        return ("amber", "Borderline Low", "Borderline low HDL (35–39 mg/dL).")
    else:
        return ("red", "Low", "Low HDL (<35 mg/dL). Significant cardiovascular risk marker.")


def classify_triglycerides(val: float, unit: str) -> Tuple[str, str, str]:
    """Classifies Triglycerides."""
    if "mmol" in unit.lower():
        val = val * 88.57

    if val < 150.0:
        return ("green", "In Range", "Normal triglyceride level (<150 mg/dL).")
    elif val <= 199.0:
        return ("amber", "Borderline High", "Borderline high triglycerides (150–199 mg/dL).")
    elif val <= 499.0:
        return ("red", "Elevated", "High triglycerides (200–499 mg/dL).")
    else:
        return ("red", "Critical High", "Very high triglycerides (≥500 mg/dL). Acute pancreatitis risk.")


def classify_creatinine(val: float, unit: str) -> Tuple[str, str, str]:
    """Classifies Serum Creatinine."""
    if val < 0.5:
        return ("amber", "Low", "Low serum creatinine (<0.5 mg/dL).")
    elif val <= 1.2:
        return ("green", "In Range", "Normal renal clearance (0.6–1.2 mg/dL).")
    elif val <= 1.9:
        return ("amber", "Borderline High", "Mildly elevated creatinine (1.3–1.9 mg/dL). Renal review recommended.")
    else:
        return ("red", "Elevated", "Elevated serum creatinine (≥2.0 mg/dL), indicative of impaired kidney function.")


def classify_hemoglobin(val: float, unit: str) -> Tuple[str, str, str]:
    """Classifies Hemoglobin."""
    if val < 8.0:
        return ("red", "Critical Low", "Severe anemia (<8.0 g/dL). Requires urgent clinical investigation.")
    elif val < 12.0:
        return ("amber", "Low", "Mild to moderate anemia (8.0–11.9 g/dL).")
    elif val <= 17.5:
        return ("green", "In Range", "Normal hemoglobin range (12.0–17.5 g/dL).")
    elif val <= 18.5:
        return ("amber", "Borderline High", "Elevated hemoglobin (17.6–18.5 g/dL).")
    else:
        return ("red", "Elevated", "Polycythemia (>18.5 g/dL).")


def classify_heart_rate(val: float, unit: str) -> Tuple[str, str, str]:
    """Classifies Resting Heart Rate."""
    if val < 50.0:
        return ("red", "Critical Low", "Bradycardia (<50 bpm).")
    elif val < 60.0:
        return ("amber", "Low", "Mild resting bradycardia (50–59 bpm).")
    elif val <= 100.0:
        return ("green", "In Range", "Normal resting heart rate (60–100 bpm).")
    elif val <= 120.0:
        return ("amber", "Borderline High", "Mild tachycardia (101–120 bpm).")
    else:
        return ("red", "Critical High", "Significant tachycardia (>120 bpm).")


def classify_blood_pressure_readings(sys_val: float, dia_val: float) -> Tuple[str, str, str]:
    """Classifies dual Blood Pressure readings according to ACC/AHA guidelines."""
    if sys_val >= 180.0 or dia_val >= 120.0:
        return ("red", "Hypertensive Crisis", f"Critical blood pressure ({int(sys_val)}/{int(dia_val)} mmHg). Immediate medical review required.")
    elif sys_val >= 140.0 or dia_val >= 90.0:
        return ("red", "Stage 2 High", f"Stage 2 Hypertension ({int(sys_val)}/{int(dia_val)} mmHg).")
    elif (130.0 <= sys_val <= 139.0) or (80.0 <= dia_val <= 89.0):
        return ("amber", "Stage 1 High", f"Stage 1 Hypertension ({int(sys_val)}/{int(dia_val)} mmHg).")
    elif (120.0 <= sys_val <= 129.0) and dia_val < 80.0:
        return ("amber", "Elevated", f"Elevated systolic BP ({int(sys_val)}/{int(dia_val)} mmHg).")
    elif (90.0 <= sys_val < 120.0) and (60.0 <= dia_val < 80.0):
        return ("green", "In Range", f"Normal blood pressure ({int(sys_val)}/{int(dia_val)} mmHg).")
    elif sys_val < 90.0 or dia_val < 60.0:
        return ("amber", "Low", f"Hypotension ({int(sys_val)}/{int(dia_val)} mmHg).")
    else:
        return ("gray", "Unclassified", f"Blood pressure: {int(sys_val)}/{int(dia_val)} mmHg.")


# ============================================================
# EXTRACTION & NORMALIZATION
# ============================================================

def parse_date(date_val: Any) -> Optional[datetime]:
    """Parses date string or ISO timestamp into timezone-aware datetime."""
    if not date_val:
        return None
    try:
        s = str(date_val).strip()
        if len(s) == 10 and re.match(r"^\d{4}-\d{2}-\d{2}$", s):
            return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def extract_numeric_value(val_str: Any) -> Optional[float]:
    """Extracts a valid floating-point number from a test result string."""
    if val_str is None:
        return None
    s = str(val_str).strip()
    # If standard number (e.g. "142", "7.3", "0.9")
    m = re.search(r"^[-+]?([0-9]+(?:\.[0-9]+)?)$", s)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    # If text like "< 140" or "> 40", do not treat as exact measurement
    # If format like "142 mg/dL", extract leading number
    m2 = re.search(r"^([0-9]+(?:\.[0-9]+)?)\s*[a-zA-Z/%]+", s)
    if m2:
        try:
            return float(m2.group(1))
        except ValueError:
            return None
    return None


def match_canonical_parameter(name: str) -> Optional[str]:
    """Matches an extracted investigation name against canonical parameters."""
    if not name:
        return None
    name_clean = re.sub(r"\s+", " ", name.strip().lower())
    
    for key, spec in PARAMETER_REGISTRY.items():
        for alias_pattern in spec["aliases"]:
            if re.search(alias_pattern, name_clean, re.IGNORECASE):
                return key
    return None


def extract_bp_from_string(text: str) -> Optional[Tuple[float, float]]:
    """Extracts systolic and diastolic values from text like '120/80 mmHg'."""
    if not text:
        return None
    m = re.search(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b", str(text))
    if m:
        try:
            sys_val = float(m.group(1))
            dia_val = float(m.group(2))
            if 50 <= sys_val <= 260 and 30 <= dia_val <= 160:
                return sys_val, dia_val
        except ValueError:
            pass
    return None


def extract_patient_health_measurements(
    timeline_events: List[Dict[str, Any]],
    medical_records: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Extracts, normalizes, and classifies all valid structured health
    measurements from authorized patient timeline events and records.
    """
    # Create lookup map for medical records
    record_map = {
        str(r.get("id")): r
        for r in medical_records
        if r.get("id")
    }

    measurements = []

    for event in timeline_events:
        event_date_raw = event.get("event_date")
        dt = parse_date(event_date_raw)
        if not dt:
            continue

        date_iso = dt.strftime("%Y-%m-%d")
        record_id = str(event.get("medical_record_id") or "")
        record_info = record_map.get(record_id, {})
        record_title = record_info.get("title") or "Medical Record"
        record_type = record_info.get("record_type") or "Medical Document"
        file_url = record_info.get("file_url")

        # 1. Process structured investigations
        investigations = event.get("investigations") or []
        bp_found_in_investigations = False

        for inv in investigations:
            if not isinstance(inv, dict):
                continue

            test_name = (inv.get("name") or "").strip()
            raw_result = inv.get("result")
            raw_unit = (inv.get("unit") or "").strip()
            ref_range = (inv.get("reference_range") or "").strip()

            if not test_name:
                continue

            # Check for Blood Pressure in investigations
            canonical_key = match_canonical_parameter(test_name)
            if canonical_key == "blood_pressure" or "blood pressure" in test_name.lower() or test_name.lower() == "bp":
                bp_vals = extract_bp_from_string(str(raw_result))
                if bp_vals:
                    sys_v, dia_v = bp_vals
                    bp_found_in_investigations = True
                    danger_lvl, danger_lbl, danger_rsn = classify_blood_pressure_readings(sys_v, dia_v)
                    measurements.append({
                        "param_key": "blood_pressure",
                        "param_name": "Blood Pressure",
                        "short_name": "BP",
                        "category": "Vitals",
                        "value": f"{int(sys_v)}/{int(dia_v)}",
                        "systolic": sys_v,
                        "diastolic": dia_v,
                        "unit": "mmHg",
                        "date": date_iso,
                        "datetime_obj": dt,
                        "reference_range": "< 120/80 mmHg",
                        "danger_level": danger_lvl,
                        "danger_label": danger_lbl,
                        "danger_reason": danger_rsn,
                        "medical_record_id": record_id,
                        "record_title": record_title,
                        "record_type": record_type,
                        "file_url": file_url,
                        "timeline_event_id": str(event.get("id") or "")
                    })
                continue

            # Extract numeric value
            num_val = extract_numeric_value(raw_result)
            if num_val is None:
                # Non-numeric result (e.g. "Within normal limits")
                continue

            if canonical_key and canonical_key in PARAMETER_REGISTRY:
                reg_spec = PARAMETER_REGISTRY[canonical_key]
                display_name = reg_spec["display_name"]
                unit = raw_unit or reg_spec["default_unit"]
                category = reg_spec["category"]
                standard_ref = reg_spec["ref_range_text"]

                # Run validated classifier
                classifier = reg_spec.get("classifier")
                if classifier:
                    danger_lvl, danger_lbl, danger_rsn = classifier(num_val, unit)
                else:
                    danger_lvl, danger_lbl, danger_rsn = ("gray", "Unclassified", "No validated threshold.")

                measurements.append({
                    "param_key": canonical_key,
                    "param_name": display_name,
                    "short_name": reg_spec["short_name"],
                    "category": category,
                    "value": num_val,
                    "unit": unit,
                    "date": date_iso,
                    "datetime_obj": dt,
                    "reference_range": ref_range or standard_ref,
                    "danger_level": danger_lvl,
                    "danger_label": danger_lbl,
                    "danger_reason": danger_rsn,
                    "medical_record_id": record_id,
                    "record_title": record_title,
                    "record_type": record_type,
                    "file_url": file_url,
                    "timeline_event_id": str(event.get("id") or "")
                })
            else:
                # Dynamically discovered lab measurement outside built-in registry
                # If lab report provided a reference range, check if within range
                danger_lvl = "gray"
                danger_lbl = "Laboratory Test"
                danger_rsn = f"Measured {num_val} {raw_unit}".strip()
                
                # Create slug key for parameter
                slug_key = re.sub(r"[^a-z0-9]+", "_", test_name.lower()).strip("_")
                if len(slug_key) >= 2:
                    measurements.append({
                        "param_key": slug_key,
                        "param_name": test_name.title(),
                        "short_name": test_name[:12],
                        "category": "Laboratory",
                        "value": num_val,
                        "unit": raw_unit or "",
                        "date": date_iso,
                        "datetime_obj": dt,
                        "reference_range": ref_range or "Not specified",
                        "danger_level": danger_lvl,
                        "danger_label": danger_lbl,
                        "danger_reason": danger_rsn,
                        "medical_record_id": record_id,
                        "record_title": record_title,
                        "record_type": record_type,
                        "file_url": file_url,
                        "timeline_event_id": str(event.get("id") or "")
                    })

        # 2. Check clinical findings for vitals (e.g. BP) if not in investigations
        findings_text = str(event.get("clinical_findings") or "")
        summary_text = str(event.get("clinical_summary") or "")
        combined_text = f"{findings_text} {summary_text}".strip()

        if not bp_found_in_investigations and combined_text:
            bp_match = re.search(r"\b(?:bp|blood\s+pressure)\s*[:=]?\s*(\d{2,3})\s*/\s*(\d{2,3})\s*(?:mmhg)?\b", combined_text, re.IGNORECASE)
            if bp_match:
                sys_v = float(bp_match.group(1))
                dia_v = float(bp_match.group(2))
                if 50 <= sys_v <= 260 and 30 <= dia_v <= 160:
                    danger_lvl, danger_lbl, danger_rsn = classify_blood_pressure_readings(sys_v, dia_v)
                    measurements.append({
                        "param_key": "blood_pressure",
                        "param_name": "Blood Pressure",
                        "short_name": "BP",
                        "category": "Vitals",
                        "value": f"{int(sys_v)}/{int(dia_v)}",
                        "systolic": sys_v,
                        "diastolic": dia_v,
                        "unit": "mmHg",
                        "date": date_iso,
                        "datetime_obj": dt,
                        "reference_range": "< 120/80 mmHg",
                        "danger_level": danger_lvl,
                        "danger_label": danger_lbl,
                        "danger_reason": danger_rsn,
                        "medical_record_id": record_id,
                        "record_title": record_title,
                        "record_type": record_type,
                        "file_url": file_url,
                        "timeline_event_id": str(event.get("id") or "")
                    })

    # Sort all measurements chronologically (oldest to newest)
    measurements.sort(key=lambda m: (m["date"], m.get("timeline_event_id", "")))
    return measurements


# ============================================================
# PARAMETER DISCOVERY & FILTERING
# ============================================================

def discover_available_parameters(measurements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Groups measurements by parameter and returns available parameters
    present in the patient's actual medical records.
    """
    param_counts: Dict[str, Dict[str, Any]] = {}

    for m in measurements:
        key = m["param_key"]
        if key not in param_counts:
            param_counts[key] = {
                "key": key,
                "name": m["param_name"],
                "short_name": m.get("short_name", m["param_name"]),
                "category": m.get("category", "General"),
                "unit": m["unit"],
                "count": 0,
                "latest_date": m["date"],
                "latest_value": m["value"],
                "latest_danger_level": m["danger_level"],
                "has_sufficient_data": False
            }
        
        param_counts[key]["count"] += 1
        param_counts[key]["latest_date"] = m["date"]
        param_counts[key]["latest_value"] = m["value"]
        param_counts[key]["latest_danger_level"] = m["danger_level"]

    result = list(param_counts.values())

    # Mark data sufficiency (at least 2 observations needed for a trend)
    for p in result:
        p["has_sufficient_data"] = p["count"] >= 2

    # Sort: multi-measurement trends first, then alphabetically
    result.sort(key=lambda p: (-p["count"], p["name"]))
    return result


def filter_measurements_by_period(
    measurements: List[Dict[str, Any]],
    time_period: str
) -> List[Dict[str, Any]]:
    """
    Filters measurements by time period relative to the most recent measurement.
    Supported: '3m' (90 days), '6m' (180 days), '1y' (365 days), 'all'.
    """
    if not measurements or time_period == "all":
        return measurements

    # Determine reference date: latest measurement date or current date
    latest_dt = max(m["datetime_obj"] for m in measurements)
    
    days_map = {
        "3m": 90,
        "6m": 180,
        "1y": 365
    }
    
    cutoff_days = days_map.get(time_period)
    if not cutoff_days:
        return measurements

    cutoff_date = latest_dt - timedelta(days=cutoff_days)
    return [m for m in measurements if m["datetime_obj"] >= cutoff_date]


# ============================================================
# SUMMARY CARDS & CHART SERIES BUILDER
# ============================================================

def build_parameter_summaries(
    filtered_measurements: List[Dict[str, Any]],
    selected_keys: List[str]
) -> List[Dict[str, Any]]:
    """
    Builds clinical summary cards for each selected parameter based on
    actual measurements in the active date range.
    """
    by_param: Dict[str, List[Dict[str, Any]]] = {k: [] for k in selected_keys}

    for m in filtered_measurements:
        if m["param_key"] in by_param:
            by_param[m["param_key"]].append(m)

    summaries = []

    for key in selected_keys:
        items = by_param.get(key, [])
        if not items:
            continue

        # Sort chronologically
        items.sort(key=lambda x: x["date"])
        latest = items[-1]
        count = len(items)

        # Previous measurement
        previous = items[-2] if count >= 2 else None
        
        # Calculate change if applicable
        change_text = None
        change_direction = "stable"  # "up", "down", "stable"
        pct_change = None

        if previous is not None and isinstance(latest["value"], (int, float)) and isinstance(previous["value"], (int, float)):
            diff = round(latest["value"] - previous["value"], 2)
            if diff > 0:
                change_text = f"+{diff} {latest['unit']}"
                change_direction = "up"
            elif diff < 0:
                change_text = f"{diff} {latest['unit']}"
                change_direction = "down"
            else:
                change_text = f"0.0 {latest['unit']}"
                change_direction = "stable"

            if previous["value"] != 0:
                pct = round((diff / previous["value"]) * 100.0, 1)
                pct_change = f"{'+' if pct > 0 else ''}{pct}%"
        elif previous is not None and latest["param_key"] == "blood_pressure":
            # Blood pressure string difference
            sys_diff = int(latest["systolic"] - previous["systolic"])
            dia_diff = int(latest["diastolic"] - previous["diastolic"])
            change_text = f"{'+' if sys_diff > 0 else ''}{sys_diff}/{'+' if dia_diff > 0 else ''}{dia_diff} mmHg"
            if sys_diff > 0 or dia_diff > 0:
                change_direction = "up"
            elif sys_diff < 0 or dia_diff < 0:
                change_direction = "down"

        # Format latest display date
        latest_date_formatted = format_display_date(latest["date"])
        prev_date_formatted = format_display_date(previous["date"]) if previous else None

        summaries.append({
            "param_key": key,
            "param_name": latest["param_name"],
            "short_name": latest.get("short_name", latest["param_name"]),
            "category": latest.get("category", "General"),
            "latest_value": latest["value"],
            "unit": latest["unit"],
            "reference_range": latest.get("reference_range", "N/A"),
            "danger_level": latest["danger_level"],
            "danger_label": latest["danger_label"],
            "danger_reason": latest["danger_reason"],
            "latest_date": latest["date"],
            "latest_date_formatted": latest_date_formatted,
            "previous_value": previous["value"] if previous else None,
            "previous_date": previous["date"] if previous else None,
            "previous_date_formatted": prev_date_formatted,
            "change_text": change_text,
            "pct_change": pct_change,
            "change_direction": change_direction,
            "measurement_count": count,
            "has_sufficient_data": count >= 2,
            "source_record_id": latest["medical_record_id"],
            "source_record_title": latest["record_title"],
            "source_record_type": latest["record_type"],
            "file_url": latest.get("file_url")
        })

    return summaries


def build_chart_datasets(
    filtered_measurements: List[Dict[str, Any]],
    selected_keys: List[str]
) -> Dict[str, Any]:
    """
    Constructs Chart.js compatible payload for each selected parameter.
    """
    charts_data: Dict[str, Any] = {}

    # Color mapping for danger levels
    point_color_map = {
        "green": "#10b981",   # Emerald
        "amber": "#f59e0b",   # Amber / Orange
        "red": "#ef4444",     # Crimson Red
        "gray": "#6b7280"     # Slate Gray
    }

    by_param: Dict[str, List[Dict[str, Any]]] = {k: [] for k in selected_keys}
    for m in filtered_measurements:
        if m["param_key"] in by_param:
            by_param[m["param_key"]].append(m)

    for key in selected_keys:
        items = by_param.get(key, [])
        if not items:
            continue

        items.sort(key=lambda x: x["date"])
        count = len(items)

        # Labels (dates)
        labels = [format_display_date(item["date"]) for item in items]
        dates_raw = [item["date"] for item in items]

        if key == "blood_pressure":
            # Dual dataset for systolic and diastolic
            sys_values = [item["systolic"] for item in items]
            dia_values = [item["diastolic"] for item in items]

            charts_data[key] = {
                "type": "line",
                "param_key": key,
                "param_name": "Blood Pressure",
                "unit": "mmHg",
                "labels": labels,
                "dates_raw": dates_raw,
                "has_sufficient_data": count >= 2,
                "measurement_count": count,
                "reference_range": "< 120/80 mmHg",
                "datasets": [
                    {
                        "label": "Systolic",
                        "data": sys_values,
                        "borderColor": "#ef4444",
                        "backgroundColor": "rgba(239, 68, 68, 0.12)",
                        "pointBackgroundColor": [point_color_map.get(it["danger_level"], "#ef4444") for it in items],
                        "pointBorderColor": "#ffffff",
                        "pointRadius": 6,
                        "pointHoverRadius": 8,
                        "tension": 0.35,
                        "fill": False
                    },
                    {
                        "label": "Diastolic",
                        "data": dia_values,
                        "borderColor": "#0284c7",
                        "backgroundColor": "rgba(2, 132, 199, 0.12)",
                        "pointBackgroundColor": [point_color_map.get(it["danger_level"], "#0284c7") for it in items],
                        "pointBorderColor": "#ffffff",
                        "pointRadius": 6,
                        "pointHoverRadius": 8,
                        "tension": 0.35,
                        "fill": False
                    }
                ],
                "meta": [
                    {
                        "date": it["date"],
                        "formatted_date": format_display_date(it["date"]),
                        "value": it["value"],
                        "danger_level": it["danger_level"],
                        "danger_label": it["danger_label"],
                        "danger_reason": it["danger_reason"],
                        "record_title": it["record_title"],
                        "record_type": it["record_type"],
                        "record_id": it["medical_record_id"]
                    }
                    for it in items
                ]
            }
        else:
            values = [item["value"] for item in items]
            point_bg_colors = [point_color_map.get(item["danger_level"], "#6b7280") for item in items]
            
            # Line stroke color: teal theme (#168b83)
            stroke_color = "#168b83"
            area_fill = "rgba(22, 139, 131, 0.08)"

            charts_data[key] = {
                "type": "line",
                "param_key": key,
                "param_name": items[0]["param_name"],
                "unit": items[0]["unit"],
                "labels": labels,
                "dates_raw": dates_raw,
                "has_sufficient_data": count >= 2,
                "measurement_count": count,
                "reference_range": items[0].get("reference_range", "N/A"),
                "latest_value": items[-1]["value"],
                "latest_danger_level": items[-1]["danger_level"],
                "latest_danger_label": items[-1]["danger_label"],
                "latest_danger_reason": items[-1]["danger_reason"],
                "datasets": [
                    {
                        "label": items[0]["param_name"],
                        "data": values,
                        "borderColor": stroke_color,
                        "backgroundColor": area_fill,
                        "pointBackgroundColor": point_bg_colors,
                        "pointBorderColor": "#ffffff",
                        "pointBorderWidth": 2,
                        "pointRadius": 6,
                        "pointHoverRadius": 9,
                        "tension": 0.3,
                        "fill": True
                    }
                ],
                "meta": [
                    {
                        "date": it["date"],
                        "formatted_date": format_display_date(it["date"]),
                        "value": it["value"],
                        "unit": it["unit"],
                        "danger_level": it["danger_level"],
                        "danger_label": it["danger_label"],
                        "danger_reason": it["danger_reason"],
                        "record_title": it["record_title"],
                        "record_type": it["record_type"],
                        "record_id": it["medical_record_id"]
                    }
                    for it in items
                ]
            }

    return charts_data


def build_historical_measurements_table(
    filtered_measurements: List[Dict[str, Any]],
    selected_keys: List[str]
) -> List[Dict[str, Any]]:
    """
    Prepares rows for the Historical Measurements table sorted newest-first.
    """
    rows = []
    # Filter for only selected parameters
    matching = [m for m in filtered_measurements if m["param_key"] in selected_keys]
    
    # Sort newest first
    matching.sort(key=lambda m: (m["date"], m.get("timeline_event_id", "")), reverse=True)

    for m in matching:
        rows.append({
            "param_key": m["param_key"],
            "param_name": m["param_name"],
            "date": m["date"],
            "formatted_date": format_display_date(m["date"]),
            "value": m["value"],
            "unit": m["unit"],
            "reference_range": m.get("reference_range") or "—",
            "danger_level": m["danger_level"],
            "danger_label": m["danger_label"],
            "danger_reason": m["danger_reason"],
            "record_id": m["medical_record_id"],
            "record_title": m["record_title"],
            "record_type": m["record_type"],
            "file_url": m.get("file_url")
        })

    return rows


# ============================================================
# AI-GENERATED TREND OBSERVATIONS
# ============================================================

def generate_trend_ai_observations(
    filtered_measurements: List[Dict[str, Any]],
    summaries: List[Dict[str, Any]],
    patient_name: str = "the patient"
) -> List[Dict[str, Any]]:
    """
    Generates concise clinical AI trend observations using Gemini,
    with a deterministic clinical rule-based fallback.
    """
    if not filtered_measurements or not summaries:
        return [{
            "type": "info",
            "title": "No Observations Available",
            "text": "No health measurements are recorded for the selected parameters and time period.",
            "source": "System"
        }]

    # Try Gemini generation if client is available
    if gemini_client:
        try:
            # Build structured context of validated facts
            context_items = []
            for s in summaries:
                item_desc = (
                    f"Parameter: {s['param_name']}\n"
                    f"Latest Value: {s['latest_value']} {s['unit']} on {s['latest_date_formatted']} ({s['danger_label']}: {s['danger_reason']})\n"
                )
                if s["has_sufficient_data"] and s["previous_value"] is not None:
                    item_desc += (
                        f"Previous Value: {s['previous_value']} {s['unit']} on {s['previous_date_formatted']}\n"
                        f"Change: {s['change_text']} ({s.get('pct_change', '')})\n"
                    )
                else:
                    item_desc += "Historical data: Only 1 measurement available (insufficient for historical trajectory).\n"
                context_items.append(item_desc)

            context_str = "\n".join(context_items)

            prompt = f"""You are OmniCare AI's Clinical Trend Observer.
Review the following validated clinical measurements recorded for {patient_name}:

{context_str}

IMPORTANT RULES:
1. Base your observations strictly and ONLY on the numbers, dates, units, and categories provided above.
2. Do NOT invent diagnoses, diseases, medications, causes, or treatments.
3. Highlight significant increases or decreases between recorded dates, levels outside reference ranges, and parameters with only a single measurement.
4. Keep each observation professional, factual, and concise (1-2 sentences per point).
5. State the exact dates, units, and values supporting each observation.
6. Provide exactly 3 to 4 clinical observations.

Return your response strictly as a JSON array of objects with the following schema:
[
  {{
    "type": "alert" | "warning" | "positive" | "info",
    "title": "Short title (3-5 words)",
    "text": "Factual observation stating exact dates and values."
  }}
]"""

            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )

            if response and response.text:
                parsed = json.loads(response.text)
                if isinstance(parsed, list) and len(parsed) > 0:
                    for p in parsed:
                        p["source"] = "OmniCare AI Engine"
                    return parsed
        except Exception as e:
            print("[OmniCare AI] Gemini Trend Observations error:", repr(e))

    # Safe deterministic fallback
    return build_deterministic_observations(summaries)


def build_deterministic_observations(summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Clinically validated deterministic observation builder when Gemini
    is not reachable or rate-limited.
    """
    observations = []

    # 1. Glycemic parameters check (Glucose / HbA1c)
    glucose_summary = next((s for s in summaries if "glucose" in s["param_key"]), None)
    hba1c_summary = next((s for s in summaries if s["param_key"] == "hba1c"), None)

    if glucose_summary and glucose_summary["has_sufficient_data"]:
        chg = glucose_summary.get("change_text", "")
        if glucose_summary["change_direction"] == "up":
            observations.append({
                "type": "alert",
                "title": f"Elevated {glucose_summary['param_name']} Trajectory",
                "text": f"{glucose_summary['param_name']} increased from {glucose_summary['previous_value']} {glucose_summary['unit']} on {glucose_summary['previous_date_formatted']} to {glucose_summary['latest_value']} {glucose_summary['unit']} on {glucose_summary['latest_date_formatted']} ({chg}), crossing into the elevated range.",
                "source": "Clinical Rules Engine"
            })
        elif glucose_summary["change_direction"] == "down":
            observations.append({
                "type": "positive",
                "title": f"Decreasing {glucose_summary['param_name']}",
                "text": f"{glucose_summary['param_name']} decreased from {glucose_summary['previous_value']} to {glucose_summary['latest_value']} {glucose_summary['unit']} ({chg}) between {glucose_summary['previous_date_formatted']} and {glucose_summary['latest_date_formatted']}.",
                "source": "Clinical Rules Engine"
            })

    if hba1c_summary and hba1c_summary["has_sufficient_data"]:
        chg = hba1c_summary.get("change_text", "")
        if hba1c_summary["change_direction"] == "up":
            observations.append({
                "type": "alert",
                "title": "Glycated Hemoglobin (HbA1c) Elevation",
                "text": f"HbA1c rose from {hba1c_summary['previous_value']}% on {hba1c_summary['previous_date_formatted']} to {hba1c_summary['latest_value']}% on {hba1c_summary['latest_date_formatted']} ({chg}), indicating cumulative glycemic progression over the preceding months.",
                "source": "Clinical Rules Engine"
            })

    # 2. Lipid profile checks (Cholesterol / LDL / Triglycerides)
    lipid_summaries = [s for s in summaries if s["param_key"] in {"total_cholesterol", "ldl_cholesterol", "triglycerides"}]
    elevated_lipids = [s for s in lipid_summaries if s["danger_level"] in {"amber", "red"}]
    if elevated_lipids:
        names = ", ".join(s["param_name"] for s in elevated_lipids)
        observations.append({
            "type": "warning",
            "title": "Lipid Profile Elevation",
            "text": f"Measurements for {names} remain outside standard optimal cutoffs as of the latest test on {elevated_lipids[0]['latest_date_formatted']}.",
            "source": "Clinical Rules Engine"
        })

    # 3. Parameters with single measurements (data sufficiency check)
    single_meas = [s for s in summaries if not s["has_sufficient_data"]]
    if single_meas:
        param_list = ", ".join(f"{s['param_name']} ({s['latest_value']} {s['unit']})" for s in single_meas[:3])
        observations.append({
            "type": "info",
            "title": "Single Measurement Notice",
            "text": f"Historical trajectory cannot be determined for {param_list} as only one recorded measurement exists. Follow-up testing is required to establish a trend.",
            "source": "Clinical Rules Engine"
        })

    # If empty, add general summary
    if not observations:
        observations.append({
            "type": "info",
            "title": "Recorded Health Metrics",
            "text": f"Total of {len(summaries)} parameter(s) evaluated across the available medical records. Values reflect documented findings from processed laboratory and clinical reports.",
            "source": "Clinical Rules Engine"
        })

    return observations


# ============================================================
# MASTER COORDINATOR
# ============================================================

def format_val(val: Any) -> Any:
    """Format numeric values cleanly (e.g. 142 instead of 142.0)."""
    if isinstance(val, float) and val.is_integer():
        return int(val)
    return val


def format_display_date(date_str: str) -> str:
    """Formats YYYY-MM-DD into '05 Sep 2026'."""
    if not date_str:
        return "N/A"
    try:
        parts = str(date_str).strip()[:10].split("-")
        if len(parts) == 3:
            dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
            return dt.strftime("%d %b %Y")
    except Exception:
        pass
    return str(date_str)


def get_trend_analysis_data(
    timeline_events: List[Dict[str, Any]],
    medical_records: List[Dict[str, Any]],
    selected_params: Optional[List[str]] = None,
    time_period: str = "all",
    patient_name: str = "Patient"
) -> Dict[str, Any]:
    """
    Main entry point for calculating and assembling the complete Trend Analysis
    payload for the OmniCare AI Patient Workspace.
    """
    # 1. Extract all structured health measurements
    all_measurements = extract_patient_health_measurements(
        timeline_events,
        medical_records
    )

    # 2. Discover available parameters from actual patient data
    available_parameters = discover_available_parameters(all_measurements)

    # Date range across all records (using clean ascii dash)
    if all_measurements:
        earliest_date = min(m["date"] for m in all_measurements)
        latest_date = max(m["date"] for m in all_measurements)
        date_range_display = f"{format_display_date(earliest_date)} - {format_display_date(latest_date)}"
    else:
        date_range_display = "No dated measurements"

    # 3. Determine active parameters
    available_keys = [p["key"] for p in available_parameters]
    sufficient_keys = [p["key"] for p in available_parameters if p["has_sufficient_data"]]

    if selected_params:
        # Validate that requested parameters actually exist in patient's data
        active_keys = [k for k in selected_params if k in available_keys]
    else:
        # Default: all parameters with sufficient data, or all available if none have >= 2
        active_keys = sufficient_keys if sufficient_keys else available_keys

    # 4. Filter measurements by time period
    period_filtered = filter_measurements_by_period(all_measurements, time_period)

    # 5. Build summary cards
    summaries = build_parameter_summaries(period_filtered, active_keys)

    # 6. Build chart datasets
    charts = build_chart_datasets(period_filtered, active_keys)

    # 7. Build historical measurements table
    historical_table = build_historical_measurements_table(period_filtered, active_keys)

    # 8. Generate AI observations
    ai_observations = generate_trend_ai_observations(period_filtered, summaries, patient_name)

    return {
        "has_data": len(all_measurements) > 0,
        "is_empty_period": len(all_measurements) > 0 and len(period_filtered) == 0,
        "total_measurements_all_time": len(all_measurements),
        "total_measurements_in_period": len(period_filtered),
        "date_range_display": date_range_display,
        "available_parameters": available_parameters,
        "default_selected_keys": sufficient_keys if sufficient_keys else available_keys,
        "active_keys": active_keys,
        "time_period": time_period,
        "summaries": summaries,
        "charts": charts,
        "historical_table": historical_table,
        "ai_observations": ai_observations
    }
