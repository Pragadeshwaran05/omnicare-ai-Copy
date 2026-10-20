import sys

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. doctor_patient_workspace
target1 = '''    doctor_id = session["doctor_id"]

    try:

        # -------------------------------------------------
        # 1. CHECK ACTIVE ACCESS'''

replacement1 = '''    # Route guest patients to guest workspace
    if _is_guest_patient(patient_id):
        return redirect(url_for("doctor_guest_workspace", guest_patient_id=patient_id))

    doctor_id = session["doctor_id"]

    try:

        # -------------------------------------------------
        # 1. CHECK ACTIVE ACCESS'''

assert target1 in content, "target1 not found"
content = content.replace(target1, replacement1, 1)

# 2. doctor_view_medical_record
target2 = '''    doctor_id = session["doctor_id"]

    print("Doctor ID :", doctor_id)
    print("Patient ID:", patient_id)
    print("Record ID :", record_id)


    try:'''

replacement2 = '''    # Route guest patients to guest record viewer
    if _is_guest_patient(patient_id):
        return redirect(url_for("doctor_view_guest_medical_record", guest_patient_id=patient_id, record_id=record_id))

    doctor_id = session["doctor_id"]

    print("Doctor ID :", doctor_id)
    print("Patient ID:", patient_id)
    print("Record ID :", record_id)


    try:'''

assert target2 in content, "target2 not found"
content = content.replace(target2, replacement2, 1)

# 3. doctor_patient_ai_assistant
target3 = '''    doctor_id = session["doctor_id"]


    try:

        # ----------------------------------------------------
        # 2. CHECK ACTIVE PATIENT ACCESS'''

replacement3 = '''    if _is_guest_patient(patient_id):
        return doctor_guest_ai_assistant(patient_id)

    doctor_id = session["doctor_id"]


    try:

        # ----------------------------------------------------
        # 2. CHECK ACTIVE PATIENT ACCESS'''

assert target3 in content, "target3 not found"
content = content.replace(target3, replacement3, 1)

# 4. doctor_patient_ai_sources
target4 = '''def doctor_patient_ai_sources(patient_id):

    # --------------------------------------------------------
    # 1. CHECK DOCTOR LOGIN
    # --------------------------------------------------------

    if "doctor_id" not in session:

        return {
            "success": False,
            "message": "Doctor login required."
        }, 401

    doctor_id = session["doctor_id"]'''

replacement4 = '''def doctor_patient_ai_sources(patient_id):

    # --------------------------------------------------------
    # 1. CHECK DOCTOR LOGIN
    # --------------------------------------------------------

    if "doctor_id" not in session:

        return {
            "success": False,
            "message": "Doctor login required."
        }, 401

    if _is_guest_patient(patient_id):
        return doctor_guest_ai_sources(patient_id)

    doctor_id = session["doctor_id"]'''

assert target4 in content, "target4 not found"
content = content.replace(target4, replacement4, 1)

# 5. doctor_patient_trend_data
target5 = '''def doctor_patient_trend_data(patient_id):
    """
    Secure server-side endpoint for retrieving filtered health trend
    measurements, charts, summaries, and AI observations.
    """
    # --------------------------------------------------------
    # 1. CHECK DOCTOR LOGIN
    # --------------------------------------------------------
    if "doctor_id" not in session:
        return {
            "success": False,
            "message": "Doctor login required."
        }, 401

    doctor_id = session["doctor_id"]'''

replacement5 = '''def doctor_patient_trend_data(patient_id):
    """
    Secure server-side endpoint for retrieving filtered health trend
    measurements, charts, summaries, and AI observations.
    """
    # --------------------------------------------------------
    # 1. CHECK DOCTOR LOGIN
    # --------------------------------------------------------
    if "doctor_id" not in session:
        return {
            "success": False,
            "message": "Doctor login required."
        }, 401

    if _is_guest_patient(patient_id):
        return doctor_guest_trend_data(patient_id)

    doctor_id = session["doctor_id"]'''

assert target5 in content, "target5 not found"
content = content.replace(target5, replacement5, 1)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully injected guest delegates into all 5 registered patient routes in app.py!")
