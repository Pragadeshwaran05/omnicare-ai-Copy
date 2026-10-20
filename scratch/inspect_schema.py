import os
import requests
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('SUPABASE_URL') + '/rest/v1/?apikey=' + os.getenv('SUPABASE_KEY')
r = requests.get(url)
defs = r.json().get('definitions', {})
for t in ['guest_patients', 'guest_patient_access', 'guest_medical_records', 'guest_health_timeline_events', 'patients', 'medical_records', 'health_timeline_events']:
    print('=== ' + t + ' ===')
    props = defs.get(t, {}).get('properties', {})
    reqs = defs.get(t, {}).get('required', [])
    for k, v in props.items():
        req = ' [REQUIRED]' if k in reqs else ''
        print(f'  {k}: {v.get("type", "")} / format={v.get("format", "")}{req}')
