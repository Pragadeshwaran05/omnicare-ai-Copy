import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('class="timeline-list"')
if idx == -1: idx = text.find('timeline-event')
print(text[idx:idx+3000])
