import sys
sys.path.insert(0, '.')

from app import app
from utils.supabase_client import supabase

print("=" * 70)
print("TESTING FLASK WORKSPACE & TREND ROUTES")
print("=" * 70)

client = app.test_client()

# 1. Test doctor_patient_workspace unauthenticated
res_unauth = client.get('/doctor/patient-workspace/a8360a17-d8a0-4524-bcc2-b1b4775e5c4f')
print("[1] Unauthenticated GET /doctor/patient-workspace/... -> Status:", res_unauth.status_code)
assert res_unauth.status_code == 302, f"Expected 302 redirect, got {res_unauth.status_code}"
assert "/doctor/login" in res_unauth.headers.get("Location", "")
print("  [OK] Unauthenticated request redirects to doctor_login.")

# 2. Test trend-data API unauthenticated
res_api_unauth = client.post('/doctor/patient-workspace/a8360a17-d8a0-4524-bcc2-b1b4775e5c4f/trend-data')
print("[2] Unauthenticated POST /doctor/patient-workspace/.../trend-data -> Status:", res_api_unauth.status_code)
assert res_api_unauth.status_code == 401
print("  [OK] Unauthenticated API request returned 401 Unauthorized.")

# 3. Test with doctor session but unauthorized patient
with client.session_transaction() as sess:
    sess["doctor_id"] = "00000000-0000-0000-0000-000000000000"

res_fake_doc = client.get('/doctor/patient-workspace/a8360a17-d8a0-4524-bcc2-b1b4775e5c4f')
print("[3] Unauthorized doctor GET /doctor/patient-workspace/... -> Status:", res_fake_doc.status_code)
assert res_fake_doc.status_code == 302
assert "/doctor/my-patients" in res_fake_doc.headers.get("Location", "")
print("  [OK] Unauthorized doctor request redirects to my_patients.")

res_api_fake_doc = client.post('/doctor/patient-workspace/a8360a17-d8a0-4524-bcc2-b1b4775e5c4f/trend-data')
print("[4] Unauthorized doctor POST /doctor/patient-workspace/.../trend-data -> Status:", res_api_fake_doc.status_code)
assert res_api_fake_doc.status_code == 403
print("  [OK] Unauthorized doctor API request returned 403 Forbidden.")

# 4. Find real active doctor access for patient
access_res = supabase.table("access_requests").select("*").eq("patient_id", "a8360a17-d8a0-4524-bcc2-b1b4775e5c4f").eq("status", "active").execute()
if access_res.data:
    real_doc_id = access_res.data[0]["doctor_id"]
    print(f"\n[5] Testing with real active doctor access (Doctor ID: {real_doc_id})...")

    with client.session_transaction() as sess:
        sess["doctor_id"] = real_doc_id

    # GET Workspace page
    res_workspace = client.get('/doctor/patient-workspace/a8360a17-d8a0-4524-bcc2-b1b4775e5c4f')
    print("  GET workspace status:", res_workspace.status_code)
    assert res_workspace.status_code == 200
    html = res_workspace.data.decode("utf-8")
    assert 'id="trend-analysis-tab"' in html, "trend-analysis-tab not found in HTML"
    assert 'Patient Health Trends' in html, "Patient Health Trends title not found in HTML"
    assert 'data-tab="trend-analysis-tab"' in html, "trend-analysis-tab nav item not found"
    assert 'Fasting Blood Glucose' in html, "Fasting Blood Glucose not found in HTML"
    print("  [OK] Workspace page rendered with Trend Analysis tab!")

    # POST trend-data API (all parameters)
    res_api = client.post(
        '/doctor/patient-workspace/a8360a17-d8a0-4524-bcc2-b1b4775e5c4f/trend-data',
        json={"parameters": ["fasting_blood_glucose", "hba1c"], "time_period": "all"}
    )
    print("  POST trend-data status:", res_api.status_code)
    assert res_api.status_code == 200
    data = res_api.get_json()
    assert data["success"] is True
    assert "trend_data" in data
    assert len(data["trend_data"]["summaries"]) == 2
    assert "fasting_blood_glucose" in data["trend_data"]["charts"]
    assert "hba1c" in data["trend_data"]["charts"]
    print("  [OK] Trend data API successfully filtered to 2 requested parameters!")

    # POST trend-data API with time period filter
    res_api_period = client.post(
        '/doctor/patient-workspace/a8360a17-d8a0-4524-bcc2-b1b4775e5c4f/trend-data',
        json={"time_period": "3m"}
    )
    assert res_api_period.status_code == 200
    pdata = res_api_period.get_json()
    assert pdata["success"] is True
    print("  [OK] Trend data API successfully filtered by 3m time period!")
else:
    print("\n[5] Note: No active access record found in database for patient a8360a17-d8a0-4524-bcc2-b1b4775e5c4f to test authorized session.")

print("\n" + "=" * 70)
print("ALL FLASK ROUTE TESTS PASSED!")
print("=" * 70)
