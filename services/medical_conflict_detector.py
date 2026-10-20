import re
from datetime import datetime


# ============================================================
# MEDICATION NORMALIZATION
# ============================================================

def normalize_medicine_name(name):
    """
    Normalize medicine names so that the same medicine
    can be compared across different medical records.
    """

    if not name:
        return ""

    name = str(name).lower().strip()

    # Remove common dosage-form prefixes
    name = re.sub(
        r"^(tab\.?|tablet|cap\.?|capsule|syrup)\s+",
        "",
        name
    )

    # Remove dosage values
    name = re.sub(
        r"\b\d+(?:\.\d+)?\s*(mg|mcg|g|ml|iu)\b",
        "",
        name
    )

    # Normalize spaces
    name = re.sub(r"\s+", " ", name)

    return name.strip()


def normalize_value(value):
    """
    Normalize values before comparison.
    """

    if value is None:
        return ""

    value = str(value).strip().lower()

    value = re.sub(r"\s+", " ", value)

    return value


# ============================================================
# DATE NORMALIZATION
# ============================================================

def parse_event_date(value):
    """
    Convert event date into a comparable datetime object.

    Supports:
    YYYY-MM-DD
    ISO timestamps
    """

    if not value:
        return None

    try:
        value = str(value).strip()

        # Standard date
        if len(value) == 10:
            return datetime.strptime(
                value,
                "%Y-%m-%d"
            )

        # ISO timestamp
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

    except Exception:
        return None


# ============================================================
# MEDICATION SIGNATURE
# ============================================================

def medication_signature(entry):
    """
    Create a normalized signature representing
    the documented medication instructions.
    """

    return (
        normalize_value(entry.get("dose")),
        normalize_value(entry.get("frequency")),
        normalize_value(entry.get("duration")),
        normalize_value(entry.get("instructions"))
    )


# ============================================================
# BUILD MEDICATION ENTRY
# ============================================================

def build_medication_entry(event, medication):
    """
    Convert a timeline medication into a normalized
    comparison object.
    """

    return {
        "name": medication.get("name"),
        "dose": medication.get("dose"),
        "frequency": medication.get("frequency"),
        "duration": medication.get("duration"),
        "instructions": medication.get("instructions"),

        "event_date": event.get("event_date"),
        "event_type": event.get("event_type"),

        "provider_name": event.get("provider_name"),
        "hospital_name": event.get("hospital_name"),

        "medical_record_id": event.get("medical_record_id")
    }


# ============================================================
# MEDICATION CHANGE DETECTION
# ============================================================

def detect_medication_changes(entries):
    """
    Detect medication changes across different dates.

    A difference across different dates is treated as a
    POSSIBLE MEDICATION CHANGE rather than an immediate conflict.

    The system does not decide whether the change was clinically
    intentional.
    """

    changes = []

    if len(entries) < 2:
        return changes

    # Sort oldest → newest
    sorted_entries = sorted(
        entries,
        key=lambda item: (
            parse_event_date(item.get("event_date"))
            or datetime.min
        )
    )

    for index in range(1, len(sorted_entries)):

        previous = sorted_entries[index - 1]
        current = sorted_entries[index]

        previous_signature = medication_signature(
            previous
        )

        current_signature = medication_signature(
            current
        )

        # No difference
        if previous_signature == current_signature:
            continue

        previous_date = previous.get("event_date")
        current_date = current.get("event_date")

        # ----------------------------------------------------
        # POSSIBLE MEDICATION CHANGE
        # ----------------------------------------------------

        changes.append({
            "conflict_type": "medication_change",
            "severity": "medium",

            "title": "Possible Medication Change",

            "description": (
                f"The documented details for "
                f"{current.get('name') or previous.get('name')} "
                f"changed between medical records."
            ),

            "medication_name": (
                current.get("name")
                or previous.get("name")
            ),

            "change_from": previous,
            "change_to": current,

            # Keep both records so the doctor can verify them
            "records": [
                previous,
                current
            ],

            "previous_date": previous_date,
            "current_date": current_date
        })

    return changes


# ============================================================
# MAIN CONFLICT DETECTOR
# ============================================================

def detect_medical_conflicts(timeline_events):
    """
    Detect possible medication inconsistencies and laboratory
    discrepancies across a patient's authorized timeline.

    All findings are potential discrepancies requiring doctor
    verification. Different values do not automatically mean
    a medical error.
    """

    conflicts = []
    medication_history = {}

    # ========================================================
    # 1. COLLECT MEDICATION HISTORY
    # ========================================================

    for event in timeline_events:
        medications = event.get("medications") or []

        if not isinstance(medications, list):
            continue

        for medication in medications:
            if not isinstance(medication, dict):
                continue

            name = medication.get("name")
            if not name:
                continue

            normalized_name = normalize_medicine_name(name)
            if not normalized_name:
                continue

            medication_data = build_medication_entry(
                event, medication
            )

            medication_history.setdefault(
                normalized_name, []
            ).append(medication_data)

    # ========================================================
    # 2. EXISTING MEDICATION CONFLICT DETECTION
    # ========================================================

    for normalized_name, entries in medication_history.items():
        if len(entries) < 2:
            continue

        medication_name = entries[0].get("name") or normalized_name
        date_groups = {}

        for entry in entries:
            event_date = entry.get("event_date")
            if event_date:
                date_groups.setdefault(event_date, []).append(entry)

        for event_date, same_date_entries in date_groups.items():
            if len(same_date_entries) < 2:
                continue

            signatures = {}

            for entry in same_date_entries:
                signature = medication_signature(entry)
                signatures.setdefault(signature, []).append(entry)

            if len(signatures) > 1:
                conflicts.append({
                    "conflict_type": "same_day_medication_conflict",
                    "severity": "high",
                    "title": "Possible Same-Day Medication Conflict",
                    "description": (
                        f"{medication_name} has different documented "
                        f"instructions on {event_date}."
                    ),
                    "medication_name": medication_name,
                    "records": same_date_entries
                })

            elif len(signatures) == 1:
                conflicts.append({
                    "conflict_type": "possible_duplicate_medication",
                    "severity": "low",
                    "title": "Possible Duplicate Medication Entry",
                    "description": (
                        f"{medication_name} appears more than once "
                        f"with the same documented details on {event_date}."
                    ),
                    "medication_name": medication_name,
                    "records": same_date_entries
                })

        conflicts.extend(detect_medication_changes(entries))

    # ========================================================
    # 3. COLLECT LABORATORY RESULTS
    # ========================================================

    lab_history = {}

    # Canonical test names and common aliases.
    lab_aliases = {
        "fasting blood glucose": "fasting_blood_glucose",
        "fasting glucose": "fasting_blood_glucose",
        "fbs": "fasting_blood_glucose",
        "fasting blood sugar": "fasting_blood_glucose",

        "post prandial blood glucose": "postprandial_blood_glucose",
        "postprandial blood glucose": "postprandial_blood_glucose",
        "ppbs": "postprandial_blood_glucose",

        "blood glucose": "blood_glucose",
        "random blood glucose": "random_blood_glucose",
        "random blood sugar": "random_blood_glucose",
        "rbs": "random_blood_glucose",

        "hba1c": "hba1c",
        "glycated hemoglobin": "hba1c",
        "glycosylated hemoglobin": "hba1c",

        "total cholesterol": "total_cholesterol",
        "cholesterol": "total_cholesterol",
        "ldl cholesterol": "ldl_cholesterol",
        "ldl": "ldl_cholesterol",
        "hdl cholesterol": "hdl_cholesterol",
        "hdl": "hdl_cholesterol",
        "triglycerides": "triglycerides",
        "triglyceride": "triglycerides",

        "serum creatinine": "serum_creatinine",
        "creatinine": "serum_creatinine"
    }

    def normalize_test_name(name):
        import re

        cleaned = re.sub(
            r"[^a-z0-9]+", " ",
            str(name).lower()
        ).strip()

        return lab_aliases.get(cleaned)

    def extract_lab_items(event):
        """
        Accept common structured result formats.
        Adapt this function if your timeline uses another schema.
        """
        items = []

        for field in ("investigations", "lab_results", "test_results"):
            value = event.get(field)

            if isinstance(value, list):
                items.extend(
                    item for item in value
                    if isinstance(item, dict)
                )

            elif isinstance(value, dict):
                for name, result in value.items():
                    if isinstance(result, dict):
                        item = dict(result)
                        item.setdefault("name", name)
                        items.append(item)
                    else:
                        items.append({
                            "name": name,
                            "value": result
                        })

        return items

    import re

    for event in timeline_events:
        event_date = (
            event.get("event_date")
            or event.get("created_at")
            or event.get("uploaded_at")
        )

        for item in extract_lab_items(event):
            test_name = (
                item.get("name")
                or item.get("test_name")
                or item.get("test")
                or item.get("parameter")
            )

            if not test_name:
                continue

            canonical_name = normalize_test_name(test_name)
            if not canonical_name:
                continue

            raw_value = (
                item.get("value")
                if item.get("value") is not None
                else item.get("result")
            )

            if raw_value is None:
                continue

            # Extract a numeric value and optional unit.
            match = re.search(
                r"[-+]?\d*\.?\d+",
                str(raw_value).replace(",", "")
            )

            if not match:
                continue

            try:
                numeric_value = float(match.group())
            except (ValueError, TypeError):
                continue

            unit = str(
                item.get("unit")
                or item.get("units")
                or ""
            ).strip().lower()

            # If the unit is embedded in the result, retain it.
            if not unit:
                unit_match = re.search(
                    r"[-+]?\d*\.?\d+\s*([a-zA-Z%/]+(?:\s*[a-zA-Z]+)?)",
                    str(raw_value)
                )
                if unit_match:
                    unit = unit_match.group(1).strip().lower()

            record = {
                "test_name": str(test_name),
                "value": numeric_value,
                "unit": unit,
                "event_date": event_date,
                "medical_record_id": (
                    item.get("medical_record_id")
                    or event.get("medical_record_id")
                    or event.get("record_id")
                ),
                "provider_name": (
                    item.get("provider_name")
                    or event.get("provider_name")
                ),
                "hospital_name": (
                    item.get("hospital_name")
                    or event.get("hospital_name")
                ),
                "raw_value": str(raw_value)
            }

            lab_history.setdefault(
                canonical_name, []
            ).append(record)

    # ========================================================
    # 4. COMPARE LAB RESULTS ACROSS RECORDS
    # ========================================================

    for test_name, entries in lab_history.items():
        if len(entries) < 2:
            continue

        # Do not compare results with incompatible units.
        by_unit = {}

        for entry in entries:
            by_unit.setdefault(
                entry["unit"], []
            ).append(entry)

        for unit, unit_entries in by_unit.items():
            if len(unit_entries) < 2:
                continue

            # Avoid duplicate alerts for repeated identical results.
            distinct_values = {
                entry["value"] for entry in unit_entries
            }

            if len(distinct_values) < 2:
                continue

            # Sort chronologically when dates are available.
            dated_entries = sorted(
                unit_entries,
                key=lambda entry: str(entry.get("event_date") or "")
            )

            first = dated_entries[0]
            latest = dated_entries[-1]

            # These are discrepancies for review, not proof of error.
            conflicts.append({
                "conflict_type": "lab_result_discrepancy",
                "severity": "medium",
                "title": "Laboratory Results Differ Across Records",
                "description": (
                    f"{test_name.replace('_', ' ').title()} has "
                    f"different recorded values: "
                    f"{first['raw_value']} and {latest['raw_value']}. "
                    "Review test dates, units, testing conditions, "
                    "and the original reports before interpreting "
                    "the difference."
                ),
                "medication_name": None,
                "lab_test_name": test_name,
                "records": dated_entries
            })

    return conflicts
