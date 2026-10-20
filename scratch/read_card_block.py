import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    text = f.read()

start = text.find('class="medical-record-card"')
end = text.find('{% endfor %}', start)
print(text[start:end])
