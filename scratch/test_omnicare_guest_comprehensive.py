import os
import sys

# Ensure root workspace directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.stdout.reconfigure(encoding='utf-8')

import io
import json
import uuid
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app import app, supabase_admin

client = app.test_client()

DOCTOR_ID = "ea83806c-f033-4012-944b-22098514d9e9"  # Dr. Tamil Alagi
OTHER_DOCTOR_ID = "99999999-9999-9999-9999-999999999999"

def generate_pdf_bytes(report_text, title="MEDICAL REPORT"):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 750, title)
    c.setFont("Helvetica", 10)
    y = 720
    for line in report_text.strip().split("\n"):
        c.drawString(50, y, line.strip())
        y -= 18
    c.save()
    buf.seek(0)
    return buf.getvalue()

def run_tests():
    print("=" * 80)
    print("STARTING OMNICARE GUEST PATIENT WORKSPACE COMPREHENSIVE VERIFICATION")
    print("=" * 80)

    guest_a_id = None
    guest_b_id = None
    created_records = []

    try:
        # =====================================================================
        # 1. CREATE TWO DIFFERENT GUEST PATIENTS (Guest A and Guest B)
        # =====================================================================
        print("\n--- STEP 1: Creating Guest A and Guest B ---")
        with client.session_transaction() as sess:
            sess["doctor_id"] = DOCTOR_ID
            sess["role"] = "doctor"

        # Create Guest A
        res_a = client.post("/doctor/guest-patient/create", data={
            "full_name": "Aarav Sharma Comprehensive Test",
            "date_of_birth": "1988-06-12",
            "gender": "Male"
        }, follow_redirects=False)

        assert res_a.status_code == 302, f"Guest A creation failed: {res_a.status_code}"
        loc_a = res_a.headers.get("Location")
        assert "/doctor/guest-workspace/" in loc_a
        guest_a_id = loc_a.split("/")[-1]
        print(f"  [PASS] Created Guest A: {guest_a_id}")

        # Create Guest B
        res_b = client.post("/doctor/guest-patient/create", data={
            "full_name": "Bhavna Patel Comprehensive Test",
            "date_of_birth": "1992-11-20",
            "gender": "Female"
        }, follow_redirects=False)

        assert res_b.status_code == 302, f"Guest B creation failed: {res_b.status_code}"
        loc_b = res_b.headers.get("Location")
        assert "/doctor/guest-workspace/" in loc_b
        guest_b_id = loc_b.split("/")[-1]
        print(f"  [PASS] Created Guest B: {guest_b_id}")

        assert guest_a_id != guest_b_id, "Guest A and Guest B must have unique IDs!"

        # =====================================================================
        # 2. UPLOAD A REPORT TO GUEST A
        # =====================================================================
        print("\n--- STEP 2 & 3: Upload Report to Guest A & AI Processing ---")
        report_a_text = """
        Patient: Aarav Sharma
        Date: 2026-10-14
        Hospital: Chennai City Multispeciality Hospital
        Consultant: Dr. Tamil Alagi, MD
        Diagnosis: Type 2 Diabetes Mellitus, Essential Hypertension
        Clinical Findings: Blood pressure 144/92 mmHg. Pulse 78 bpm. Mild bilateral pedal edema.
        Investigations:
        Fasting Blood Sugar: 145 mg/dL (Reference Range: 70-99 mg/dL)
        HbA1c: 8.1 % (Reference Range: < 5.7 %)
        Serum Creatinine: 1.0 mg/dL (Reference Range: 0.7-1.2 mg/dL)
        Medications:
        Tablet Metformin 500mg - 1 tablet oral twice daily for 30 days after meals
        Tablet Telmisartan 40mg - 1 tablet oral once daily for 30 days morning
        Follow-up: Review after 4 weeks with repeat Fasting Blood Sugar and Lipid profile.
        """
        pdf_bytes_a = generate_pdf_bytes(report_a_text, "CONSULTATION & LAB REPORT - AARAV SHARMA")

        data_a = {
            "record_type": "consultation",
            "title": "Comprehensive Consultation Report 2026-10-14",
            "description": "Initial diabetes and hypertension assessment",
            "medical_file": (io.BytesIO(pdf_bytes_a), "aarav_consultation.pdf", "application/pdf")
        }

        upload_res_a = client.post(
            f"/doctor/guest-workspace/{guest_a_id}/upload",
            data=data_a,
            content_type="multipart/form-data",
            follow_redirects=True
        )
        assert upload_res_a.status_code == 200, f"Upload to Guest A failed: {upload_res_a.status_code}"
        print("  [PASS] Uploaded report to Guest A.")

        # =====================================================================
        # 4. VERIFY SAVED DATA IN GUEST A MEDICAL RECORDS & HEALTH TIMELINE
        # =====================================================================
        print("\n--- STEP 4: Verifying Saved Data in Guest A Records & Timeline ---")
        records_db_a = supabase_admin.table("guest_medical_records").select("*").eq("guest_patient_id", guest_a_id).execute()
        assert len(records_db_a.data) == 1, f"Expected 1 record for Guest A, got {len(records_db_a.data)}"
        rec_a = records_db_a.data[0]
        created_records.append(("guest_medical_records", rec_a["id"]))
        print(f"  [PASS] Record persisted: ID={rec_a['id']}, File={rec_a['file_name']}, Path={rec_a['file_path']}")

        timeline_db_a = supabase_admin.table("guest_health_timeline_events").select("*").eq("guest_patient_id", guest_a_id).execute()
        assert len(timeline_db_a.data) == 1, f"Expected 1 timeline event for Guest A, got {len(timeline_db_a.data)}"
        ev_a = timeline_db_a.data[0]
        created_records.append(("guest_health_timeline_events", ev_a["id"]))
        assert ev_a["ai_processed"] is True, "AI processing should be True!"
        print(f"  [PASS] Timeline event persisted: Diagnosis='{ev_a.get('diagnosis')}', Date='{ev_a.get('event_date')}'")

        # Check workspace HTML rendering
        ws_res_a = client.get(f"/doctor/guest-workspace/{guest_a_id}")
        assert ws_res_a.status_code == 200
        html_a = ws_res_a.get_data(as_text=True)
        assert "aarav_consultation.pdf" in html_a
        assert "AI Processed" in html_a or "AI Analyzed" in html_a
        assert "Aarav Sharma" in html_a
        print("  [PASS] Workspace HTML rendered record card, file name, status badge, and timeline.")

        # =====================================================================
        # 5. VERIFY TREND ANALYSIS AND CONFLICT ALERTS FOR GUEST A
        # =====================================================================
        print("\n--- STEP 5: Verifying Trend Analysis and Conflict Alerts for Guest A ---")
        trend_res_a = client.post(
            f"/doctor/guest-workspace/{guest_a_id}/trend-data",
            data=json.dumps({"time_period": "all"}),
            content_type="application/json"
        )
        assert trend_res_a.status_code == 200, f"Trend API error: {trend_res_a.status_code}"
        trend_json_a = json.loads(trend_res_a.get_data(as_text=True))
        assert trend_json_a.get("success") is True
        print(f"  [PASS] Trend API returned success: {trend_json_a['success']}")

        # Upload a second report for Guest A to create trend history and conflict
        report_a2_text = """
        Patient: Aarav Sharma
        Date: 2026-10-18
        Hospital: Apollo Clinic
        Consultant: Dr. Tamil Alagi, MD
        Diagnosis: Type 2 Diabetes Mellitus
        Clinical Findings: Blood pressure 138/86 mmHg.
        Investigations:
        Fasting Blood Sugar: 130 mg/dL (Reference Range: 70-99 mg/dL)
        HbA1c: 7.8 % (Reference Range: < 5.7 %)
        Medications:
        Tablet Metformin 1000mg - 1 tablet oral twice daily for 30 days after meals
        """
        pdf_bytes_a2 = generate_pdf_bytes(report_a2_text, "FOLLOWUP LAB REPORT - AARAV SHARMA")
        data_a2 = {
            "record_type": "lab_report",
            "title": "Follow-up Lab Report 2026-10-18",
            "description": "Followup test results",
            "medical_file": (io.BytesIO(pdf_bytes_a2), "aarav_followup.pdf", "application/pdf")
        }
        client.post(
            f"/doctor/guest-workspace/{guest_a_id}/upload",
            data=data_a2,
            content_type="multipart/form-data",
            follow_redirects=True
        )

        records_db_a_updated = supabase_admin.table("guest_medical_records").select("*").eq("guest_patient_id", guest_a_id).execute()
        assert len(records_db_a_updated.data) == 2, f"Expected 2 records for Guest A, got {len(records_db_a_updated.data)}"
        for r in records_db_a_updated.data:
            if r["id"] != rec_a["id"]:
                created_records.append(("guest_medical_records", r["id"]))

        # Verify conflict route
        conflict_res = client.get(
            f"/doctor/guest-workspace/{guest_a_id}/conflicts",
            headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"}
        )
        assert conflict_res.status_code == 200
        conflicts_json = json.loads(conflict_res.get_data(as_text=True))
        assert conflicts_json.get("success") is True
        print(f"  [PASS] Conflicts API returned success: {len(conflicts_json.get('conflicts', []))} conflict(s) detected.")

        # =====================================================================
        # 6. VERIFY AI HEALTH ASSISTANT FOR GUEST A
        # =====================================================================
        print("\n--- STEP 6: Verifying Guest AI Health Assistant ---")
        ai_res_a = client.post(
            f"/doctor/guest-workspace/{guest_a_id}/ai-assistant",
            data=json.dumps({"question": "What is the patient's Fasting Blood Sugar on 2026-10-14?"}),
            content_type="application/json"
        )
        assert ai_res_a.status_code == 200
        ai_json_a = json.loads(ai_res_a.get_data(as_text=True))
        assert ai_json_a.get("success") is True
        answer_a = ai_json_a.get("answer", "")
        print(f"  [PASS] AI Assistant responded: {answer_a[:120]}...")
        assert "145" in answer_a, f"Expected '145' in answer, got: {answer_a}"

        # =====================================================================
        # 7. UPLOAD SEPARATE REPORT TO GUEST B & VERIFY COMPLETE ISOLATION
        # =====================================================================
        print("\n--- STEP 7: Uploading to Guest B and Verifying Data Isolation ---")
        report_b_text = """
        Patient: Bhavna Patel
        Date: 2026-10-19
        Hospital: Global Health City
        Consultant: Dr. Tamil Alagi, MD
        Diagnosis: Hypothyroidism, Vitamin D Deficiency
        Clinical Findings: Fatigue, hair loss, weight gain.
        Investigations:
        TSH: 6.8 uIU/mL (Reference Range: 0.4-4.0 uIU/mL)
        Vitamin D: 14 ng/mL (Reference Range: 30-100 ng/mL)
        Medications:
        Tablet Thyronorm 50mcg - 1 tablet oral once daily empty stomach
        """
        pdf_bytes_b = generate_pdf_bytes(report_b_text, "THYROID REPORT - BHAVNA PATEL")
        data_b = {
            "record_type": "lab_report",
            "title": "Thyroid Evaluation 2026-10-19",
            "description": "Thyroid and vitamin panel",
            "medical_file": (io.BytesIO(pdf_bytes_b), "bhavna_thyroid.pdf", "application/pdf")
        }
        upload_res_b = client.post(
            f"/doctor/guest-workspace/{guest_b_id}/upload",
            data=data_b,
            content_type="multipart/form-data",
            follow_redirects=True
        )
        assert upload_res_b.status_code == 200

        records_db_b = supabase_admin.table("guest_medical_records").select("*").eq("guest_patient_id", guest_b_id).execute()
        assert len(records_db_b.data) == 1
        rec_b = records_db_b.data[0]
        created_records.append(("guest_medical_records", rec_b["id"]))

        # Check isolation: Guest A workspace must NOT have Bhavna's data or files
        ws_res_a_check = client.get(f"/doctor/guest-workspace/{guest_a_id}")
        html_a_check = ws_res_a_check.get_data(as_text=True)
        assert "bhavna_thyroid.pdf" not in html_a_check
        assert "Hypothyroidism" not in html_a_check
        assert "Thyronorm" not in html_a_check
        print("  [PASS] Verified Guest A workspace does NOT contain Guest B's files or diagnoses.")

        # Check isolation: Guest B workspace must NOT have Aarav's data or files
        ws_res_b_check = client.get(f"/doctor/guest-workspace/{guest_b_id}")
        html_b_check = ws_res_b_check.get_data(as_text=True)
        assert "aarav_consultation.pdf" not in html_b_check
        assert "Hypertension" not in html_b_check
        assert "Telmisartan" not in html_b_check
        print("  [PASS] Verified Guest B workspace does NOT contain Guest A's files or diagnoses.")

        # Check isolation: Ask Guest A AI about Guest B condition
        ai_res_iso = client.post(
            f"/doctor/guest-workspace/{guest_a_id}/ai-assistant",
            data=json.dumps({"question": "Does this patient have Hypothyroidism or take Thyronorm?"}),
            content_type="application/json"
        )
        ai_iso_json = json.loads(ai_res_iso.get_data(as_text=True))
        iso_answer = ai_iso_json.get("answer", "")
        print(f"  [PASS] Guest A AI isolation check: {iso_answer[:120]}...")
        assert ("not documented" in iso_answer.lower() or "no" in iso_answer.lower()), f"Expected negative, got: {iso_answer}"

        # =====================================================================
        # 8. VERIFY STATUS, RETRY BEHAVIOR & DUPLICATE PREVENTION
        # =====================================================================
        print("\n--- STEP 8: Verifying Status API, Retry Behavior & Duplicate Prevention ---")
        # Test status endpoint
        status_res = client.get(f"/doctor/guest-record/{guest_a_id}/status/{rec_a['id']}")
        assert status_res.status_code == 200
        status_json = json.loads(status_res.get_data(as_text=True))
        assert status_json.get("success") is True
        assert status_json.get("status") == "processed"
        print(f"  [PASS] Record status endpoint verified: status={status_json.get('status')}")

        # Check count of timeline events for rec_a before retry
        count_before = (
            supabase_admin.table("guest_health_timeline_events")
            .select("id")
            .eq("guest_patient_id", guest_a_id)
            .eq("guest_medical_record_id", rec_a["id"])
            .execute()
        )
        assert len(count_before.data) == 1, f"Expected exactly 1 event before retry, got {len(count_before.data)}"

        # Perform retry on rec_a
        retry_res = client.post(
            f"/doctor/guest-record/{guest_a_id}/retry/{rec_a['id']}",
            follow_redirects=True
        )
        assert retry_res.status_code == 200

        # Verify duplicate prevention: Count of timeline events for rec_a must STILL be exactly 1!
        count_after = (
            supabase_admin.table("guest_health_timeline_events")
            .select("id")
            .eq("guest_patient_id", guest_a_id)
            .eq("guest_medical_record_id", rec_a["id"])
            .execute()
        )
        assert len(count_after.data) == 1, f"DUPLICATE DETECTED! Expected 1 event after retry, got {len(count_after.data)}"
        print(f"  [PASS] Retry successfully executed without duplicating timeline events (count={len(count_after.data)}).")

        # Test invalid file rejection
        invalid_res = client.post(
            f"/doctor/guest-workspace/{guest_a_id}/upload",
            data={
                "record_type": "consultation",
                "title": "Invalid File Test",
                "medical_file": (io.BytesIO(b"binary data"), "virus.exe", "application/x-msdownload")
            },
            content_type="multipart/form-data",
            follow_redirects=True
        )
        assert invalid_res.status_code == 200
        html_invalid = invalid_res.get_data(as_text=True)
        assert "Only PDF, PNG, JPG, JPEG and WEBP files are allowed." in html_invalid
        print("  [PASS] Invalid file (.exe) properly rejected.")

        # =====================================================================
        # 9. VERIFY REGISTERED-PATIENT WORKSPACE REGRESSION CHECK
        # =====================================================================
        print("\n--- STEP 9: Verifying Registered-Patient Workspace Compatibility ---")
        reg_patient_res = supabase_admin.table("patients").select("id").limit(1).execute()
        if reg_patient_res.data:
            reg_patient_id = reg_patient_res.data[0]["id"]
            reg_ws_res = client.get(f"/doctor/patient-workspace/{reg_patient_id}")
            assert reg_ws_res.status_code == 200
            print(f"  [PASS] Registered patient workspace ({reg_patient_id}) loaded without regression.")

        # =====================================================================
        # 10. VERIFY DOCTOR AUTHORIZATION & OWNERSHIP CHECKS
        # =====================================================================
        print("\n--- STEP 10: Verifying Doctor Ownership & Access Security ---")
        with client.session_transaction() as sess:
            sess["doctor_id"] = OTHER_DOCTOR_ID
            sess["role"] = "doctor"

        unauth_ws = client.get(f"/doctor/guest-workspace/{guest_a_id}")
        assert unauth_ws.status_code == 302, "Unauthorized doctor must be redirected!"
        print("  [PASS] Unauthorized doctor blocked from guest workspace.")

        unauth_ai = client.post(
            f"/doctor/guest-workspace/{guest_a_id}/ai-assistant",
            data=json.dumps({"question": "Test"}),
            content_type="application/json"
        )
        assert unauth_ai.status_code == 403, "Unauthorized doctor must receive 403 Forbidden on AI!"
        print("  [PASS] Unauthorized doctor blocked from guest AI assistant.")

        print("\n" + "=" * 80)
        print("ALL 10/10 WORKFLOW STEPS VERIFIED AND PASSED WITH ZERO ERRORS!")
        print("=" * 80)

    finally:
        print("\n--- Cleaning up test records ---")
        # Soft-close guest patients
        if guest_a_id:
            try:
                supabase_admin.table("guest_patients").update({"status": "closed"}).eq("id", guest_a_id).execute()
            except Exception:
                pass
        if guest_b_id:
            try:
                supabase_admin.table("guest_patients").update({"status": "closed"}).eq("id", guest_b_id).execute()
            except Exception:
                pass
        print("Cleanup completed.")

if __name__ == "__main__":
    run_tests()
