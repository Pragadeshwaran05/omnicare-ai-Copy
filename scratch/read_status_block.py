with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(2510, 2525):
    print(f"{i+1}: {repr(lines[i])}")
