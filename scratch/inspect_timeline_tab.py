import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('id="health-timeline-tab"')
print("Timeline tab content:")
print(text[idx:idx+3000])
