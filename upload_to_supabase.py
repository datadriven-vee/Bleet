import json
import os
from supabase import create_client, Client

# --- CONFIGURATION ---
INPUT_FILE = "bleet_clean.json"
# ⚠️ PASTE YOUR SECRETS HERE (Or load from .env)
SUPABASE_URL = "https://hcpujywdhobacukhoukd.supabase.co"        
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhjcHVqeXdkaG9iYWN1a2hvdWtkIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzNzUwNTYsImV4cCI6MjA4NDk1MTA1Nn0.4PUKc_k0lGWK5Uo0zMdqIGiO9DkZGmZuZC5qtAoYaYA"   

# Connect to Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_data():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ File {INPUT_FILE} not found!")
        return

    print(f"📂 Loading data from {INPUT_FILE}...")
    with open(INPUT_FILE, "r") as f:
        data = json.load(f)

    # FILTER: Only keep rows where question AND ideal_answer are NOT null
    valid_data = [
        row for row in data 
        if row.get("question") is not None and row.get("ideal_answer") is not None
    ]
    
    print(f"🚀 Found {len(valid_data)} complete rows. Uploading to Supabase...")

    # Upload in batches of 100
    BATCH_SIZE = 100
    for i in range(0, len(valid_data), BATCH_SIZE):
        batch = valid_data[i : i + BATCH_SIZE]
        
        clean_batch = []
        for item in batch:
            clean_batch.append({
                "question": item.get("question"),
                "ideal_answer": item.get("ideal_answer"),
                "company": item.get("company"),
                "role": item.get("role"),
                "experience": item.get("experience"),
                "category": item.get("category"),
                "difficulty": item.get("difficulty"),
                "source_type": item.get("source_type")
            })

        try:
            supabase.table("questions").insert(clean_batch).execute()
            print(f"   ✅ Batch {i//BATCH_SIZE + 1} uploaded.")
        except Exception as e:
            print(f"   ❌ Error uploading batch: {e}")

    print("\n🎉 Upload Complete! Your app is live with real data.")

if __name__ == "__main__":
    upload_data()