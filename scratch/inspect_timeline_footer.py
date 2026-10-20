import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('class="event-footer"')
if idx == -1: idx = text.find('source-record')
if idx == -1: idx = text.find('view-source')
print(text[idx-200:idx+1500])
