from utils.supabase_client import supabase

try:
    response = supabase.table("patients").select("id").limit(1).execute()

    print("Supabase connection successful!")
    print(response.data)

except Exception as e:
    print("Supabase connection failed!")
    print(e)