from app import app

endpoints_to_test = [
    'home',
    'patient_register',
    'patient_login',
    'patient_dashboard',
    'patient_logout',
    'health_timeline',
    'patient_doctor_access',
    'patient_profile',
    'qr_health_id',
    'logout',
    'patient_upload_records',
    'patient_records',
    'patient_health_records',
    'doctor_register',
    'doctor_login',
    'doctor_dashboard',
    'doctor_access',
    'doctor_guest_patient',
    'doctor_medical_records',
    'doctor_ai_assistant',
    'doctor_consultations',
    'doctor_access_audit',
    'doctor_profile',
    'doctor_settings'
]

print("=== TESTING URL_FOR FOR ALL ENDPOINTS ===")
with app.test_request_context():
    from flask import url_for
    for ep in endpoints_to_test:
        try:
            url = url_for(ep)
            print(f"  [OK] Endpoint '{ep}' -> URL: {url}")
        except Exception as e:
            print(f"  [FAIL] Endpoint '{ep}': {e}")
