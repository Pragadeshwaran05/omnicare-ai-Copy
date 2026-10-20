with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

target = '''        # Fetch all guest patients created by this doctor, latest first
        response = (
            supabase_admin
            .table("guest_patients")
            .select("*")
            .eq("created_by_doctor_id", doctor_id)
            .order("created_at", desc=True)
            .execute()
        )'''

replacement = '''        # Fetch all guest patients created by this doctor, latest first
        response = (
            supabase_admin
            .table("guest_patients")
            .select("*")
            .eq("created_by_doctor_id", doctor_id)
            .eq("status", "active")
            .order("created_at", desc=True)
            .execute()
        )'''

assert target in content, "target not found"
content = content.replace(target, replacement, 1)

target2 = '''                shared_guests_res = (
                    supabase_admin
                    .table("guest_patients")
                    .select("*")
                    .in_("id", missing_ids)
                    .order("created_at", desc=True)
                    .execute()
                )'''

replacement2 = '''                shared_guests_res = (
                    supabase_admin
                    .table("guest_patients")
                    .select("*")
                    .in_("id", missing_ids)
                    .eq("status", "active")
                    .order("created_at", desc=True)
                    .execute()
                )'''

assert target2 in content, "target2 not found"
content = content.replace(target2, replacement2, 1)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated status='active' filtering in doctor_guest_patient successfully!")
