with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    if 'doctor_view_medical_record' in line:
        print(f"Line {i}: {line.strip()[:120]}")
