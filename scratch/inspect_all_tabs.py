with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
tabs = re.findall(r'id="([^"]+-tab)"', text)
print("Tab IDs found:", tabs)

buttons = re.findall(r'data-tab="([^"]+)"', text)
print("Data tabs in nav:", buttons)
