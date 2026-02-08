import json
import os

INPUT_FILE = "bleet_gen_checkpoint.json"
OUTPUT_FILE = "bleet_clean.json"

def clean_dataset():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ File {INPUT_FILE} not found!")
        return

    print(f"🧹 Reading {INPUT_FILE}...")
    try:
        with open(INPUT_FILE, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("❌ Error: Your JSON file format is broken. Try checking the file manually.")
        return

    print(f"   Original Raw Count: {len(data)}")

    unique_rows = []
    seen_questions = set()
    
    for row in data:
        # 1. Check for Nulls (Must have Question AND Ideal Answer)
        q = row.get("question")
        a = row.get("ideal_answer")
        
        if q and a: # This checks if they are not None AND not empty strings
            
            # 2. Check for Duplicates (based on the question text)
            # We use the question string as a unique "fingerprint"
            if q not in seen_questions:
                unique_rows.append(row)
                seen_questions.add(q)

    print(f"   ✅ Cleaned Count: {len(unique_rows)} (Removed {len(data) - len(unique_rows)} duplicates/blanks)")
    
    # Save the new file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(unique_rows, f, indent=2)
    
    print(f"💾 Saved to {OUTPUT_FILE}")
    print("👉 You can now use this file for uploading.")

if __name__ == "__main__":
    clean_dataset()