import sys
sys.path.insert(0, '.')
import jinja2
from services.medical_conflict_detector import detect_medical_conflicts

class MockRequest:
    endpoint = 'doctor_patient_workspace'

env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))
def mock_url_for(endpoint, **kwargs):
    return f"/{endpoint}?" + "&".join(f"{k}={v}" for k, v in kwargs.items())

env.globals['url_for'] = mock_url_for
env.globals['request'] = MockRequest()
env.globals['session'] = {'doctor_id': 'doc-1', 'doctor_name': 'Dr. Test'}

template = env.get_template('doctor/patient_workspace.html')

patient = {'id': 'pat-123', 'name': 'John Doe', 'age': 45, 'gender': 'Male'}
records = [{'id': 'rec-1', 'title': 'Prescription', 'uploaded_at': '2026-05-10'}]
timeline_events = [{'event_date': '2026-05-10', 'event_type': 'consultation', 'doctor_name': 'Dr. Test'}]

# Test 1: Empty conflicts
out1 = template.render(
    patient=patient,
    records=records,
    timeline_events=timeline_events,
    conflicts=[],
    conflict_summary={'total': 0, 'high': 0, 'medium': 0, 'low': 0},
    access={'access_type': 'temporary'}
)
print("Test 1 (empty conflicts) rendered! Size:", len(out1))
assert 'No Conflicts Detected' in out1, "Empty state missing"
assert 'id="medical-conflicts-tab"' in out1, "medical-conflicts-tab ID missing"
assert 'id="conflict-nav-count">0<' in out1 or 'id="conflict-nav-count">0</span>' in out1, "Nav count 0 missing"

# Test 2: Real conflicts (with medication_change)
sample_events = [
    {
        'event_date': '2026-01-10',
        'event_type': 'consultation',
        'provider_name': 'Dr. Smith',
        'hospital_name': 'City Hospital',
        'medical_record_id': 'rec-1',
        'medications': [
            {'name': 'Metformin', 'dose': '500mg', 'frequency': 'Twice daily', 'duration': '30 days', 'instructions': 'Take after food'}
        ]
    },
    {
        'event_date': '2026-05-10',
        'event_type': 'consultation',
        'provider_name': 'Dr. Jones',
        'hospital_name': 'General Hospital',
        'medical_record_id': 'rec-2',
        'medications': [
            {'name': 'Metformin', 'dose': '850mg', 'frequency': 'Once daily', 'duration': '60 days', 'instructions': 'Take with water'}
        ]
    }
]
conflicts_detected = detect_medical_conflicts(sample_events)
summary = {'total': len(conflicts_detected), 'high': 0, 'medium': len(conflicts_detected), 'low': 0}

out2 = template.render(
    patient=patient,
    records=records,
    timeline_events=sample_events,
    conflicts=conflicts_detected,
    conflict_summary=summary,
    access={'access_type': 'temporary'}
)
print("Test 2 (real conflicts) rendered! Size:", len(out2))
assert 'Possible Medication Change' in out2, "Possible Medication Change missing"
assert 'Medication History Comparison' in out2, "Medication History Comparison missing"
assert 'View Original' in out2, "View Original missing"
assert 'rec-1' in out2 and 'rec-2' in out2, "Record IDs missing in links"
assert 'id="conflict-nav-count">1<' in out2 or 'id="conflict-nav-count">1</span>' in out2, "Nav count 1 missing"

# Test 3: Same day conflict
sample_events_same_day = [
    {
        'event_date': '2026-05-10',
        'event_type': 'consultation',
        'provider_name': 'Dr. Smith',
        'hospital_name': 'City Hospital',
        'medical_record_id': 'rec-1',
        'medications': [
            {'name': 'Amlodipine', 'dose': '5mg', 'frequency': 'Once daily', 'duration': '30 days', 'instructions': 'Morning'}
        ]
    },
    {
        'event_date': '2026-05-10',
        'event_type': 'consultation',
        'provider_name': 'Dr. Jones',
        'hospital_name': 'General Hospital',
        'medical_record_id': 'rec-2',
        'medications': [
            {'name': 'Amlodipine', 'dose': '10mg', 'frequency': 'Twice daily', 'duration': '30 days', 'instructions': 'Night'}
        ]
    }
]
conflicts_same_day = detect_medical_conflicts(sample_events_same_day)
out3 = template.render(
    patient=patient,
    records=records,
    timeline_events=sample_events_same_day,
    conflicts=conflicts_same_day,
    conflict_summary={'total': len(conflicts_same_day), 'high': len(conflicts_same_day), 'medium': 0, 'low': 0},
    access={'access_type': 'temporary'}
)
print("Test 3 (same day conflict) rendered! Size:", len(out3))
assert 'Possible Same-Day Medication Conflict' in out3
assert 'Documented Information' in out3
assert 'View Original' in out3

print("ALL RENDERING ASSERTIONS PASSED SUCCESSFULLY!")
