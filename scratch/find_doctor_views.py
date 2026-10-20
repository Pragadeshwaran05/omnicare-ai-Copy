with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'doctor_view_', text)]
for m in matches:
    print(text[m-50:m+200])
    print("="*40)
