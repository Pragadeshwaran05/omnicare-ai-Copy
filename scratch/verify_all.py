import re
import sys
from collections import Counter

with open("templates/doctor/patient_workspace.html", "r", encoding="utf-8") as f:
    template_content = f.read()

# 1. Check duplicate IDs
ids = re.findall(r'\bid=["\']([^"\']+)["\']', template_content)
counts = Counter(ids)
duplicates = {k: v for k, v in counts.items() if v > 1}
print("Duplicate IDs:", duplicates)
assert len(duplicates) == 0, f"Found duplicate IDs: {duplicates}"

# 2. Check tab IDs
expected_tabs = [
    "medical-records-tab",
    "health-timeline-tab",
    "trend-analysis-tab",
    "medical-conflicts-tab",
    "ai-assistant-tab"
]
for tab in expected_tabs:
    assert tab in ids, f"Missing tab ID: {tab}"
    assert counts[tab] == 1, f"Tab ID {tab} appears {counts[tab]} times!"
print("All 5 expected tabs exist exactly once as element IDs!")

# 3. Check navigation buttons
data_tabs = re.findall(r'data-tab=["\']([^"\']+)["\']', template_content)
print("Navigation data-tab attributes:", data_tabs)
assert data_tabs == expected_tabs, f"data-tab attributes mismatch: {data_tabs} vs {expected_tabs}"

# 4. Check each tab panel has .workspace-tab-content class
for tab in expected_tabs:
    match = re.search(r'<div[^>]*id=["\']' + tab + r'["\'][^>]*class=["\']([^"\']+)["\']', template_content)
    if not match:
        match = re.search(r'<div[^>]*class=["\']([^"\']+)["\'][^>]*id=["\']' + tab + r'["\']', template_content)
    assert match is not None, f"Could not find div for tab {tab}"
    classes = match.group(1).split()
    assert "workspace-tab-content" in classes, f"Tab {tab} missing .workspace-tab-content class (has: {classes})"
print("All 4 tab panels have .workspace-tab-content class!")

# 5. Check sibling hierarchy - ensure none of the tabs are nested inside each other
# A simple check: in the HTML, each tab div opens and closes before the next tab div opens
tab_indices = {}
for tab in expected_tabs:
    pos = template_content.find(f'id="{tab}"')
    assert pos != -1
    tab_indices[tab] = pos

sorted_tabs = sorted(tab_indices.keys(), key=lambda t: tab_indices[t])
assert sorted_tabs == expected_tabs, f"Tabs order mismatch: {sorted_tabs}"
print("Tabs are in proper sequential order in template!")

# 6. Check JS syntax
# Extract javascript between <script> and </script>
scripts = re.findall(r'<script>(.*?)</script>', template_content, re.DOTALL)
print(f"Found {len(scripts)} <script> blocks.")
# Check JS for basic balance of braces, brackets, parentheses
for idx, script in enumerate(scripts):
    stack = []
    pairs = {')': '(', '}': '{', ']': '['}
    # ignore string literals
    cleaned = re.sub(r'(\"\"\"|\'\'\'|\".*?\"|\'.*?\')', '', script)
    # ignore comments
    cleaned = re.sub(r'//.*', '', cleaned)
    cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
    for char in cleaned:
        if char in '({[':
            stack.append(char)
        elif char in ')}]':
            if not stack:
                print(f"Error: unmatched closing {char} in script {idx}")
                sys.exit(1)
            top = stack.pop()
            if top != pairs[char]:
                print(f"Error: mismatched {top} and {char} in script {idx}")
                sys.exit(1)
    assert len(stack) == 0, f"Unclosed brackets in script {idx}: {stack}"
print("JavaScript brackets and syntax balance verified!")

# 7. Check CSS file syntax
with open("static/css/doctor_patient_workspace.css", "r", encoding="utf-8") as f:
    css_content = f.read()

# Check CSS bracket balance
css_cleaned = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
css_stack = []
for char in css_cleaned:
    if char == '{':
        css_stack.append('{')
    elif char == '}':
        if not css_stack:
            print("Error: unmatched closing brace in CSS")
            sys.exit(1)
        css_stack.pop()
assert len(css_stack) == 0, f"Unclosed braces in CSS: {len(css_stack)}"
print("CSS syntax balance verified!")

print("\nALL VERIFICATION CHECKS PASSED!")
