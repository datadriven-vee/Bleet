import pandas as pd
import json
import time
import os
from google import genai
from google.genai import types

# --- CONFIGURATION ---
OUTPUT_FILE = "bleet_premium_dataset.json"
CHECKPOINT_FILE = "bleet_gen_checkpoint.json"
GEMINI_API_KEY = "AIzaSyDpXyU6Ge7rGeRnAFmulAiLdGesRoxIRWw"  # <--- PASTE YOUR AIza KEY HERE

# Initialize the NEW Client
client = genai.Client(api_key=GEMINI_API_KEY)

BATCH_SIZE = 10 

def generate_content_for_batch(batch_df):
    # Prepare the input data
    rows_to_process = batch_df[['role', 'experience', 'category', 'company', 'source_type']].to_dict(orient='records')
    
    prompt = f"""
    You are an expert Bar Raiser interviewer.
    Act as a data generator. I will provide a list of profiles.
    
    INPUT:
    {json.dumps(rows_to_process)}
    
    TASK:
    For EACH profile in the input list, generate:
    1. "question": A scenario-based behavioral interview question (NOT a one-liner).
    2. "ideal_answer": A detailed STAR method response (Situation, Task, Action, Result). 
       - Length: approx 150-200 words.
       - Tone: Professional, specific, and sounding like a spoken answer.
    
    OUTPUT FORMAT:
    Return a JSON object with a SINGLE key "results" which is a list of objects.
    The order must match the input exactly.
    """

    try:
        # NEW SYNTAX for google-genai library
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt,
            config={
                'response_mime_type': 'application/json'
            }
        )
        
        # Parse the JSON response
        parsed = json.loads(response.text)
        return parsed.get("results", [])
        
    except Exception as e:
        print(f"❌ API Error: {e}")
        return None

# --- MAIN EXECUTION ---
def main():
    # 1. Load Checkpoint
    if os.path.exists(CHECKPOINT_FILE):
        print(f"🔄 Checkpoint found. Resuming from {CHECKPOINT_FILE}...")
        try:
            df = pd.read_json(CHECKPOINT_FILE)
        except ValueError:
            print("⚠️ Checkpoint file corrupted. Please check manually.")
            return
    else:
        print("❌ No checkpoint found! Please ensure 'bleet_gen_checkpoint.json' is in this folder.")
        return

    # 2. Find rows to process
    todo_indices = df[df['question'].isnull()].index
    print(f"🎯 Total rows remaining: {len(todo_indices)}")
    
    # 3. Loop through batches
    for i in range(0, len(todo_indices), BATCH_SIZE):
        batch_idx = todo_indices[i : i + BATCH_SIZE]
        batch_df = df.loc[batch_idx]
        
        print(f"Processing Batch {i//BATCH_SIZE + 1} ({len(batch_idx)} items)... ", end="")
        
        results = generate_content_for_batch(batch_df)
        
        if results and len(results) == len(batch_idx):
            for idx, res in zip(batch_idx, results):
                df.at[idx, 'question'] = res.get('question')
                df.at[idx, 'ideal_answer'] = res.get('ideal_answer')
            print("✅ Done")
            
            # Save Progress
            df.to_json(CHECKPOINT_FILE, orient='records', indent=2)
            
            # Sleep 4s to respect Free Tier limits (15 RPM)
            time.sleep(4) 
            
        else:
            print("⚠️ Batch failed. Waiting 10s...")
            time.sleep(10)

    print(f"\n🎉 Generation Complete! Saving to {OUTPUT_FILE}")
    df.to_json(OUTPUT_FILE, orient='records', indent=2)

if __name__ == "__main__":
    main()