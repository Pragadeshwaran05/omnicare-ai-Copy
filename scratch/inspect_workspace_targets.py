with open("templates/doctor/patient_workspace.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i in range(4230, 4245):
    print(f"{i+1}: {ascii(lines[i])}")
