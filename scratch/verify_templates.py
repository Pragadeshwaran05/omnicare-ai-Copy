import sys
sys.path.insert(0, '.')

from app import app
from flask import render_template

with app.test_request_context():
    print("Testing guest_patient.html rendering...")
    out1 = render_template("doctor/guest_patient.html", guests=[])
    assert "Guest Patient Record Access" in out1
    print("  [OK] guest_patient.html renders with empty guests list.")

    mock_guest = {
        "id": "11111111-2222-3333-4444-555555555555",
        "guest_code": "GUEST-TEST1234",
        "full_name": "Test Guest Patient",
        "date_of_birth": "2000-01-01",
        "gender": "Male",
        "status": "active",
        "created_at": "2026-10-20T12:00:00Z"
    }
    out1b = render_template("doctor/guest_patient.html", guests=[mock_guest])
    assert "Test Guest Patient" in out1b
    assert "GUEST-TEST1234" in out1b
    assert "/doctor/guest-workspace/11111111-2222-3333-4444-555555555555" in out1b
    print("  [OK] guest_patient.html renders with guest rows and valid workspace URLs!")

    print("\nTesting guest_upload_records.html rendering...")
    out2 = render_template("doctor/guest_upload_records.html", guest_patient=mock_guest, guest_patient_id=mock_guest["id"])
    assert "Upload Medical Document" in out2
    assert "/doctor/guest-workspace/11111111-2222-3333-4444-555555555555/upload" in out2
    print("  [OK] guest_upload_records.html renders with valid upload action!")

    print("\nTesting patient_workspace.html (is_guest=True) rendering...")
    out3_guest = render_template(
        "doctor/patient_workspace.html",
        patient=mock_guest,
        records=[],
        timeline_events=[],
        conflicts=[],
        conflict_summary={"total": 0, "high": 0, "medium": 0, "low": 0},
        access={"access_type": "guest", "status": "active", "approved_at": "2026-10-20", "expires_at": None},
        trend_data={},
        is_guest=True
    )
    assert "Guest Patient Record" in out3_guest
    assert "Back to Guest Patients" in out3_guest
    assert "guestUploadModal" in out3_guest
    print("  [OK] patient_workspace.html renders in guest mode with guest controls!")

    print("\nTesting patient_workspace.html (is_guest=False) rendering...")
    registered_patient = {
        "id": "a8360a17-d8a0-4524-bcc2-b1b4775e5c4f",
        "health_id": "HEALTH-9999",
        "full_name": "Registered Patient",
        "date_of_birth": "1990-05-15",
        "gender": "Female"
    }
    out3_reg = render_template(
        "doctor/patient_workspace.html",
        patient=registered_patient,
        records=[],
        timeline_events=[],
        conflicts=[],
        conflict_summary={"total": 0, "high": 0, "medium": 0, "low": 0},
        access={"access_type": "temporary", "status": "active", "approved_at": "2026-10-20", "expires_at": None},
        trend_data={},
        is_guest=False
    )
    assert "Back to My Patients" in out3_reg
    assert "guestUploadModal" not in out3_reg
    print("  [OK] patient_workspace.html renders in registered mode with registered controls!")

print("\n" + "=" * 70)
print("ALL TEMPLATE RENDERING TESTS PASSED!")
print("=" * 70)
