import sys
sys.path.insert(0, '.')
from utils.supabase_client import supabase

for t in ['doctors', 'guest_patients', 'guest_patient_access', 'guest_medical_records', 'guest_health_timeline_events']:
    res = supabase.table(t).select('*').execute()
    print(f"=== {t} ({len(res.data)}) ===")
    for row in res.data[:3]:
        print(" ", row)
