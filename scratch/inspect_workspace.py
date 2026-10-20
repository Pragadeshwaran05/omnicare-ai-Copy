import re

with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    content = f.read()

endpoints = set(re.findall(r"url_for\(['\"]([^'\"]+)['\"]", content))
print("Endpoints in patient_workspace.html:", endpoints)

# Find form actions and fetch/ajax endpoints
forms = re.findall(r'<form[^>]*action=["\']([^"\']*)["\']', content)
print("Forms in patient_workspace.html:", forms)

fetches = re.findall(r'fetch\(["\']([^"\']+)["\']', content)
print("Fetches in patient_workspace.html:", fetches)

# Check tabs or sections
sections = re.findall(r'id=["\']([^"\']*(?:tab|section|pane)[^"\']*)["\']', content, re.IGNORECASE)
print("Sections/Tabs in patient_workspace.html:", sections)

print("\n=== MAJOR SECTIONS IN PATIENT WORKSPACE ===")
for i, line in enumerate(content.splitlines()):
    if '<!-- =====' in line:
        # print next line
        lines = content.splitlines()
        next_line = lines[i+1] if i+1 < len(lines) else ""
        print(f"Line {i+1}: {next_line.strip()}")

print("\n=== PATIENT AND ACCESS KEYS IN WORKSPACE ===")
patient_gets = set(re.findall(r"patient\.get\(['\"]([^'\"]+)['\"]", content))
access_gets = set(re.findall(r"access\.get\(['\"]([^'\"]+)['\"]", content))
print("patient.get keys:", patient_gets)
print("access.get keys:", access_gets)

patient_dots = set(re.findall(r"patient\.([a-zA-Z0-9_]+)", content))
print("patient.dot keys:", patient_dots)

record_gets = set(re.findall(r"record\.get\(['\"]([^'\"]+)['\"]", content))
print("record.get keys:", record_gets)

timeline_gets = set(re.findall(r"event\.get\(['\"]([^'\"]+)['\"]", content))
print("event.get keys:", timeline_gets)

print("\n=== RECORD LINKS IN PATIENT WORKSPACE ===")
for i, line in enumerate(content.splitlines()):
    if 'view-record' in line or 'doctor_view_medical_record' in line or 'record_id' in line or 'medical_record_id' in line or 'Original' in line:
        print(f"Line {i+1}: {line.strip()[:100]}")
