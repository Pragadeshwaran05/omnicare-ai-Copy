with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(2865, 2886):
    print(f"{i+1}: {repr(lines[i])}")
