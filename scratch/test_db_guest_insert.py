import sys
sys.path.insert(0, '.')
from utils.supabase_client import supabase

# Let's get the first guest patient
guest = supabase.table('guest_patients').select('*').limit(1).execute().data[0]
guest_id = guest['id']
doctor_id = guest['created_by_doctor_id']

print(f"Testing with guest_id: {guest_id}, doctor_id: {doctor_id}")

# Insert a test record
rec_res = supabase.table('guest_medical_records').insert({
    'guest_patient_id': guest_id,
    'uploaded_by_doctor_id': doctor_id,
    'record_type': 'Lab Report',
    'title': 'Test CBC Report',
    'description': 'Automated schema validation test',
    'file_name': 'test.pdf',
    'file_path': f'guests/{guest_id}/test.pdf',
    'file_url': None
}).execute()

print("Record inserted:", rec_res.data)
rec_id = rec_res.data[0]['id']

# Insert a test timeline event
tl_res = supabase.table('guest_health_timeline_events').insert({
    'guest_patient_id': guest_id,
    'guest_medical_record_id': rec_id,
    'event_date': '2026-10-15',
    'event_type': 'investigation',
    'provider_name': 'Dr. Test',
    'hospital_name': 'Apollo Hospital',
    'diagnosis': 'Routine checkup',
    'clinical_findings': 'Normal',
    'investigations': [{'test_name': 'Hemoglobin', 'result': '14.2', 'unit': 'g/dL'}],
    'medications': [],
    'follow_up': None,
    'clinical_summary': 'Normal report',
    'ai_processed': True
}).execute()

print("Timeline event inserted:", tl_res.data)

# Now delete the test rows to keep DB clean
supabase.table('guest_health_timeline_events').delete().eq('id', tl_res.data[0]['id']).execute()
supabase.table('guest_medical_records').delete().eq('id', rec_id).execute()
print("Cleaned up test rows successfully!")
