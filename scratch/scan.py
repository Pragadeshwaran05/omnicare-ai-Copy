import os, glob, re

print("=== ALL URL_FOR REFERENCES IN TEMPLATES ===")
for path in glob.glob("templates/**/*.html", recursive=True):
    content = open(path, "r", encoding="utf-8").read()
    matches = re.findall(r"url_for\(['\"]([^'\"]+)['\"]", content)
    static_matches = re.findall(r"url_for\('static',\s*filename=['\"]([^'\"]+)['\"]", content)
    if matches:
        print(f"\nFile: {path}")
        print("  Endpoints:", set(matches))
        if static_matches:
            print("  Static Files:", set(static_matches))
