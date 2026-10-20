import re
from collections import Counter

with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Duplicate IDs
ids = re.findall(r'\bid=["\']([^"\']+)["\']', content)
counts = Counter(ids)
duplicates = {k: v for k, v in counts.items() if v > 1}
print("Duplicate IDs:", duplicates)

# 2. Check tab IDs present
expected_tabs = ['medical-records-tab', 'health-timeline-tab', 'medical-conflicts-tab', 'ai-assistant-tab']
for tab in expected_tabs:
    print(f"Tab '{tab}' in content:", tab in ids, f"(count: {counts.get(tab, 0)})")

# 3. Check data-tab attributes
data_tabs = re.findall(r'data-tab=["\']([^"\']+)["\']', content)
print("data-tab values in nav:", data_tabs)
