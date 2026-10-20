with open('app.py', 'rb') as f:
    content = f.read()

target = b'''            if latest.get("created_at"):
                created_dt = datetime.fromisoformat(latest["created_at"].replace("Z", "+00:00"))
                if (datetime.now(timezone.utc) - created_dt).total_seconds() < 5:
                    print("Duplicate guest patient creation prevented:", latest.get("id"))
                    return redirect(url_for("doctor_guest_workspace", guest_patient_id=latest["id"]))'''

replacement = b'''            if latest.get("created_at"):
                raw_created = latest["created_at"].replace("Z", "+00:00")
                try:
                    import dateutil.parser
                    created_dt = dateutil.parser.isoparse(raw_created)
                except Exception:
                    created_dt = datetime.fromisoformat(raw_created)
                if (datetime.now(timezone.utc) - created_dt).total_seconds() < 5:
                    print("Duplicate guest patient creation prevented:", latest.get("id"))
                    return redirect(url_for("doctor_guest_workspace", guest_patient_id=latest["id"]))'''

target_crlf = target.replace(b'\n', b'\r\n')
replacement_crlf = replacement.replace(b'\n', b'\r\n')

if target_crlf in content:
    content = content.replace(target_crlf, replacement_crlf, 1)
    with open('app.py', 'wb') as f:
        f.write(content)
    print("Successfully updated app.py with isoparse")
else:
    print("Target not found!")
