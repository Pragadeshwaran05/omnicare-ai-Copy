import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('templates/doctor/patient_workspace.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for target_line in [1740, 1897, 2099, 2180, 2257, 2332]:
    print(f"=== Line {target_line} ===")
    start = max(0, target_line - 5)
    end = min(len(lines), target_line + 5)
    for j in range(start, end):
        print(f"{j+1}: {lines[j]}", end="")
