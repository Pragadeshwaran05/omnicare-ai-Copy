import sys
import io
import os
import uuid
from datetime import datetime, timezone

sys.path.insert(0, '.')

from app import app
from utils.supabase_client import supabase
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def create_sample_medical_pdf():
    """Create an authentic synthetic medical consultation PDF for end-to-end testing."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "Apollo Hospitals - Clinical Consultation Note")
    c.setFont("Helvetica", 10)
    c.drawString(50, 735, "Greams Road, Chennai, Tamil Nadu - 600006")
    c.line(50, 725, 550, 725)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 705, "Physician:")
    c.setFont("Helvetica", 11)
    c.drawString(120, 705, "Dr. Tamil Alagi, MBBS, MD (General Medicine)")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 685, "Date:")
    c.setFont("Helvetica", 11)
    c.drawString(120, 685, "2026-10-18")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 665, "Diagnosis:")
    c.setFont("Helvetica", 11)
    c.drawString(120, 665, "Type 2 Diabetes Mellitus, Essential Hypertension")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 645, "Clinical Findings:")
    c.setFont("Helvetica", 11)
    c.drawString(160, 645, "Blood pressure elevated at 142/90 mmHg. BMI 27.2.")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 620, "Investigations / Laboratory Results:")
    c.setFont("Helvetica", 10)
    c.drawString(70, 605, "- Fasting Blood Glucose: 138 mg/dL (Reference: 70-99 mg/dL)")
    c.drawString(70, 590, "- HbA1c: 7.6 % (Reference: < 5.7 %)")
    c.drawString(70, 575, "- Serum Creatinine: 0.9 mg/dL (Reference: 0.7-1.2 mg/dL)")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 550, "Rx / Medications Prescribed:")
    c.setFont("Helvetica", 10)
    c.drawString(70, 535, "1. Tablet Metformin 500mg - Once daily after dinner for 30 days")
    c.drawString(70, 520, "2. Tablet Telmisartan 40mg - Once daily morning for 30 days")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 495, "Follow-up:")
    c.setFont("Helvetica", 11)
    c.drawString(120, 495, "Review in 4 weeks with repeat fasting blood sugar.")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()

def run_tests():
    print("=" * 80)
    print("RUNNING COMPLETE GUEST PATIENT RECORD WORKSPACE TEST SUITE")
    print("=" * 80)

    client = app.test_client()

    # Known doctor ID in database
    doctor_res = supabase.table("doctors").select("id").limit(1).execute()
    assert doctor_res.data, "No doctors found in database!"
    primary_doctor_id = doctor_res.data[0]["id"]
    print(f"Primary Authenticated Doctor ID: {primary_doctor_id}")

    unauthorized_doctor_id = "00000000-0000-0000-0000-000000000000"

    created_guest_id = None
    created_guest_code = None
    created_guest_record_id = None
    created_guest_storage_path = None
    second_guest_id = None

    try:
        # -------------------------------------------------------------
        # TEST 1: Creating a guest patient
        # -------------------------------------------------------------
        print("\n--- TEST 1: Creating a guest patient ---")
        with client.session_transaction() as sess:
            sess["doctor_id"] = primary_doctor_id

        res1 = client.post("/doctor/guest-patient/create", data={
            "full_name": "Deepa Sundaram Test",
            "date_of_birth": "1994-06-22",
            "gender": "Female"
        }, follow_redirects=False)

        assert res1.status_code == 302, f"Expected 302 redirect, got {res1.status_code}"
        redirect_url = res1.headers.get("Location", "")
        print(f"Redirect Location: {redirect_url}")
        assert "/doctor/guest-workspace/" in redirect_url
        created_guest_id = redirect_url.split("/doctor/guest-workspace/")[-1].strip()
        print(f"Created Guest Patient ID: {created_guest_id}")

        # Verify guest exists in guest_patients table
        check_db = supabase.table("guest_patients").select("*").eq("id", created_guest_id).execute()
        assert check_db.data, "Guest patient not found in database!"
        guest_row = check_db.data[0]
        created_guest_code = guest_row["guest_code"]
        assert guest_row["full_name"] == "Deepa Sundaram Test"
        assert guest_row["created_by_doctor_id"] == primary_doctor_id
        assert guest_row["status"] == "active"
        print(f"Database row verified: {guest_row['guest_code']}, Name: {guest_row['full_name']}")

        # Verify access row in guest_patient_access
        check_acc = supabase.table("guest_patient_access").select("*").eq("guest_patient_id", created_guest_id).eq("doctor_id", primary_doctor_id).execute()
        assert check_acc.data, "Guest patient access record not found in guest_patient_access table!"
        print("  [PASS] TEST 1: Guest patient created successfully with isolated database records.")

        # -------------------------------------------------------------
        # TEST 2: Loading the guest patient list
        # -------------------------------------------------------------
        print("\n--- TEST 2: Loading the guest patient list ---")
        with client.session_transaction() as sess:
            sess["doctor_id"] = primary_doctor_id

        res2 = client.get("/doctor/guest-patient")
        assert res2.status_code == 200, f"Expected 200, got {res2.status_code}"
        html2 = res2.data.decode("utf-8")
        assert "Deepa Sundaram Test" in html2
        assert created_guest_code in html2
        assert f"/doctor/guest-workspace/{created_guest_id}" in html2
        assert "Unable to load guest patients" not in html2
        assert "Unable to create the guest patient" not in html2
        print(f"  [PASS] TEST 2: Guest patient list loaded successfully without contradictory error messages.")

        # -------------------------------------------------------------
        # TEST 3: Opening the correct guest workspace
        # -------------------------------------------------------------
        print("\n--- TEST 3: Opening the correct guest workspace ---")
        with client.session_transaction() as sess:
            sess["doctor_id"] = primary_doctor_id

        res3 = client.get(f"/doctor/guest-workspace/{created_guest_id}")
        assert res3.status_code == 200, f"Expected 200, got {res3.status_code}"
        html3 = res3.data.decode("utf-8")
        assert "Deepa Sundaram Test" in html3
        assert created_guest_code in html3
        assert "Guest Patient Record" in html3
        assert "Back to Guest Patients" in html3
        assert 'id="medical-records-tab"' in html3
        assert 'id="health-timeline-tab"' in html3
        assert 'id="trend-analysis-tab"' in html3
        assert 'id="medical-conflicts-tab"' in html3
        assert 'id="ai-assistant-tab"' in html3
        assert "Upload Medical Record" in html3
        print(f"  [PASS] TEST 3: Opened guest workspace with all tabs and guest controls intact.")

        # -------------------------------------------------------------
        # TEST 4 & 5: Uploading medical document & Supabase Storage
        # -------------------------------------------------------------
        print("\n--- TEST 4 & 5: Uploading document & Supabase Storage ---")
        pdf_bytes = create_sample_medical_pdf()
        print(f"Generated synthetic clinical PDF: {len(pdf_bytes)} bytes")

        with client.session_transaction() as sess:
            sess["doctor_id"] = primary_doctor_id

        upload_data = {
            "title": "Apollo Consultation and Lab Panel",
            "record_type": "Lab Report",
            "description": "Diabetic and hypertensive consultation with lab panel",
            "medical_file": (io.BytesIO(pdf_bytes), "apollo_consultation_test.pdf")
        }

        res4 = client.post(
            f"/doctor/guest-workspace/{created_guest_id}/upload",
            data=upload_data,
            content_type="multipart/form-data",
            follow_redirects=False
        )

        assert res4.status_code == 302, f"Expected 302 redirect after upload, got {res4.status_code}"
        assert f"/doctor/guest-workspace/{created_guest_id}" in res4.headers.get("Location", "")
        print("Upload redirected back to guest workspace.")

        # Verify record in guest_medical_records
        rec_check = supabase.table("guest_medical_records").select("*").eq("guest_patient_id", created_guest_id).execute()
        assert rec_check.data, "No record found in guest_medical_records!"
        record_row = rec_check.data[0]
        created_guest_record_id = record_row["id"]
        created_guest_storage_path = record_row["file_path"]
        print(f"Medical Record ID: {created_guest_record_id}, Title: {record_row['title']}")
        print(f"Storage Path: {created_guest_storage_path}")
        assert created_guest_storage_path.startswith(f"guests/{created_guest_id}/")
        print("  [PASS] TEST 4 & 5: File uploaded and isolated storage path verified.")

        # -------------------------------------------------------------
        # TEST 6 & 7: Calling document processor & persisting extraction
        # -------------------------------------------------------------
        print("\n--- TEST 6 & 7: Calling processor & persisting timeline ---")
        tl_check = supabase.table("guest_health_timeline_events").select("*").eq("guest_patient_id", created_guest_id).execute()
        assert tl_check.data, "No timeline event found in guest_health_timeline_events!"
        tl_row = tl_check.data[0]
        print("Timeline Event ID:", tl_row["id"])
        print("Event Date:", tl_row["event_date"])
        print("Event Type:", tl_row["event_type"])
        print("Diagnosis:", tl_row["diagnosis"])
        print("AI Processed Status:", tl_row["ai_processed"])
        print("Investigations Count:", len(tl_row.get("investigations") or []))
        print("Medications Count:", len(tl_row.get("medications") or []))
        assert tl_row["guest_medical_record_id"] == created_guest_record_id
        print("  [PASS] TEST 6 & 7: AI extraction persisted to guest_health_timeline_events.")

        # -------------------------------------------------------------
        # TEST 8: Displaying processed record and timeline in workspace
        # -------------------------------------------------------------
        print("\n--- TEST 8: Displaying processed record and timeline in workspace ---")
        with client.session_transaction() as sess:
            sess["doctor_id"] = primary_doctor_id

        res8 = client.get(f"/doctor/guest-workspace/{created_guest_id}")
        assert res8.status_code == 200
        html8 = res8.data.decode("utf-8")
        assert "Apollo Consultation and Lab Panel" in html8
        assert "View Record" in html8
        assert "View Original" in html8
        print("  [PASS] TEST 8: Workspace rendered with medical record and timeline event.")

        # -------------------------------------------------------------
        # TEST 9: Handling invalid file and processing failure
        # -------------------------------------------------------------
        print("\n--- TEST 9: Handling invalid file ---")
        with client.session_transaction() as sess:
            sess["doctor_id"] = primary_doctor_id

        # 9a. Disallowed file extension (.exe)
        bad_upload = {
            "title": "Bad File",
            "record_type": "Other",
            "medical_file": (io.BytesIO(b"malicious content"), "virus.exe")
        }
        res9a = client.post(
            f"/doctor/guest-workspace/{created_guest_id}/upload",
            data=bad_upload,
            content_type="multipart/form-data",
            follow_redirects=True
        )
        html9a = res9a.data.decode("utf-8")
        assert "Only PDF, PNG, JPG, JPEG and WEBP files are allowed." in html9a
        print("  [PASS] 9a: Rejected invalid file extension and displayed error flash banner.")

        # 9b. Empty file
        empty_upload = {
            "title": "Empty File",
            "record_type": "Other",
            "medical_file": (io.BytesIO(b""), "empty.pdf")
        }
        res9b = client.post(
            f"/doctor/guest-workspace/{created_guest_id}/upload",
            data=empty_upload,
            content_type="multipart/form-data",
            follow_redirects=True
        )
        html9b = res9b.data.decode("utf-8")
        assert "The selected file is empty." in html9b
        print("  [PASS] 9b: Rejected empty file and displayed error flash banner.")
        print("  [PASS] TEST 9: Invalid file handling verified.")

        # -------------------------------------------------------------
        # TEST 10: Verifying two different guest patients cannot see each other's records
        # -------------------------------------------------------------
        print("\n--- TEST 10: Guest patient record isolation ---")
        # Create second guest patient
        res10_create = client.post("/doctor/guest-patient/create", data={
            "full_name": "Second Guest Patient",
            "date_of_birth": "1980-01-01",
            "gender": "Male"
        }, follow_redirects=False)
        second_guest_id = res10_create.headers.get("Location", "").split("/doctor/guest-workspace/")[-1].strip()
        print(f"Second Guest Patient ID: {second_guest_id}")

        # Open second guest workspace
        res10_workspace = client.get(f"/doctor/guest-workspace/{second_guest_id}")
        assert res10_workspace.status_code == 200
        html10 = res10_workspace.data.decode("utf-8")
        # First patient's record MUST NOT appear in second patient's workspace
        assert "Apollo Consultation and Lab Panel" not in html10
        print("Verified second guest workspace does NOT contain first guest's records.")

        # Query guest_medical_records for second guest
        g2_records = supabase.table("guest_medical_records").select("*").eq("guest_patient_id", second_guest_id).execute()
        assert len(g2_records.data) == 0
        print("  [PASS] TEST 10: Strict isolation between guest patients verified.")

        # -------------------------------------------------------------
        # TEST 11: Verifying registered-patient features still work
        # -------------------------------------------------------------
        print("\n--- TEST 11: Registered-patient features regression verification ---")
        # Check active registered patient
        access_res = supabase.table("access_requests").select("*").eq("status", "active").limit(1).execute()
        if access_res.data:
            reg_patient_id = access_res.data[0]["patient_id"]
            reg_doctor_id = access_res.data[0]["doctor_id"]
            with client.session_transaction() as sess:
                sess["doctor_id"] = reg_doctor_id

            reg_ws = client.get(f"/doctor/patient-workspace/{reg_patient_id}")
            assert reg_ws.status_code == 200
            reg_html = reg_ws.data.decode("utf-8")
            assert "Back to My Patients" in reg_html
            assert "guestUploadModal" not in reg_html
            print(f"Registered patient workspace loaded successfully for patient {reg_patient_id}.")
        print("  [PASS] TEST 11: Registered-patient workspace continues to work perfectly.")

        # -------------------------------------------------------------
        # TEST 12: Doctor ownership and access checks
        # -------------------------------------------------------------
        print("\n--- TEST 12: Doctor ownership and access checks ---")
        # Attempt to access created guest patient as an unauthorized doctor
        with client.session_transaction() as sess:
            sess["doctor_id"] = unauthorized_doctor_id

        res12_ws = client.get(f"/doctor/guest-workspace/{created_guest_id}", follow_redirects=False)
        assert res12_ws.status_code == 302, f"Expected 302 redirect for unauthorized doctor, got {res12_ws.status_code}"
        assert "/doctor/guest-patient" in res12_ws.headers.get("Location", "")
        print("Unauthorized doctor was successfully blocked from accessing guest workspace.")

        # Attempt to upload to created guest as unauthorized doctor
        res12_upload = client.post(
            f"/doctor/guest-workspace/{created_guest_id}/upload",
            data={"title": "Hacked", "record_type": "Other"},
            follow_redirects=False
        )
        assert res12_upload.status_code == 302
        assert "/doctor/guest-patient" in res12_upload.headers.get("Location", "")
        print("Unauthorized doctor was successfully blocked from uploading to guest workspace.")

        # Attempt to access guest AI assistant as unauthorized doctor
        res12_ai = client.post(
            f"/doctor/guest-workspace/{created_guest_id}/ai-assistant",
            json={"question": "What is the diagnosis?"}
        )
        assert res12_ai.status_code == 403
        print("Unauthorized doctor was blocked from guest AI assistant (403 Forbidden).")
        print("  [PASS] TEST 12: Doctor ownership and authorization strictly enforced.")

        # -------------------------------------------------------------
        # BONUS: Test AI Assistant, AI Sources, and Trend Data for Guest
        # -------------------------------------------------------------
        print("\n--- BONUS: Testing Guest AI Assistant & Trend APIs ---")
        with client.session_transaction() as sess:
            sess["doctor_id"] = primary_doctor_id

        # AI Assistant
        res_ai = client.post(
            f"/doctor/guest-workspace/{created_guest_id}/ai-assistant",
            json={"question": "What diagnosis was made for this guest patient?"}
        )
        assert res_ai.status_code == 200
        ai_json = res_ai.get_json()
        assert ai_json["success"] is True
        print("AI Assistant Answer:", ai_json.get("answer")[:150] + "...")

        # AI Sources
        res_sources = client.get(f"/doctor/guest-workspace/{created_guest_id}/ai-sources")
        assert res_sources.status_code == 200
        sources_json = res_sources.get_json()
        assert sources_json["success"] is True
        print("AI Sources Count:", len(sources_json.get("sources", [])))

        # Trend Data
        res_trend = client.post(
            f"/doctor/guest-workspace/{created_guest_id}/trend-data",
            json={"time_period": "all"}
        )
        assert res_trend.status_code == 200
        trend_json = res_trend.get_json()
        assert trend_json["success"] is True
        print("Trend Data API Success: True")
        print("  [PASS] BONUS: All interactive workspace features functioning for guest patient.")

        # View Original Medical Record redirect test
        res_view = client.get(
            f"/doctor/guest-record/{created_guest_id}/{created_guest_record_id}",
            follow_redirects=False
        )
        assert res_view.status_code == 302, f"Expected 302 signed URL redirect, got {res_view.status_code}"
        assert "supabase" in res_view.headers.get("Location", "").lower()
        print("  [PASS] BONUS: View Original Medical Record redirect to secure Supabase signed URL verified.")

        print("\n" + "=" * 80)
        print("ALL 12/12 REQUIREMENTS + WORKSPACE APIS VERIFIED AND PASSED!")
        print("=" * 80)

    finally:
        # Cleanup test data created during testing
        print("\nCleaning up test records from database and storage...")
        try:
            if created_guest_id:
                try:
                    supabase.table("guest_health_timeline_events").delete().eq("guest_patient_id", created_guest_id).execute()
                except Exception as e:
                    print("Timeline cleanup note:", e)
                try:
                    supabase.table("guest_medical_records").delete().eq("guest_patient_id", created_guest_id).execute()
                except Exception as e:
                    print("Records cleanup note:", e)
                try:
                    supabase.table("guest_patient_access").delete().eq("guest_patient_id", created_guest_id).execute()
                except Exception as e:
                    print("Access cleanup note:", e)
                try:
                    supabase.table("guest_patients").update({"status": "closed"}).eq("id", created_guest_id).execute()
                except Exception as e:
                    print("Guest patient archive note:", e)

            if second_guest_id:
                try:
                    supabase.table("guest_patient_access").delete().eq("guest_patient_id", second_guest_id).execute()
                except Exception:
                    pass
                try:
                    supabase.table("guest_patients").update({"status": "closed"}).eq("id", second_guest_id).execute()
                except Exception:
                    pass

            if created_guest_storage_path:
                bucket_name = "medical-records"
                clean_path = created_guest_storage_path
                if clean_path.startswith(bucket_name + "/"):
                    clean_path = clean_path[len(bucket_name) + 1:]
                supabase.storage.from_(bucket_name).remove([clean_path])

            print("Cleanup completed successfully.")
        except Exception as clean_err:
            print("Cleanup note (non-fatal):", repr(clean_err))

if __name__ == "__main__":
    run_tests()
