import pandas as pd
import json
import time
import random
import os
from groq import Groq

# --- CONFIGURATION ---
OUTPUT_FILE = "bleet_premium_dataset.json"
CHECKPOINT_FILE = "bleet_gen_checkpoint.json"
GROQ_API_KEY = "st.secrets["GROQ_API_KEY"]" # <--- PASTE KEY HERE

# User requested Qwen model.
# Note: If this specific ID is unavailable, swap to 'llama-3.3-70b-versatile'
MODEL_ID = "llama-3.1-8b-instant" 
BATCH_SIZE = 5 # Small batch size because we are generating LONG text (2 min answers)

# --- DEFINING THE DISTRIBUTION ---
# We define our classes here to ensure perfect distribution
ROLES = [
    "Data Scientist", "Data Engineer", "Machine Learning Engineer",
    "Backend Engineer", "Frontend Engineer", "Full Stack Developer",
    "DevOps Engineer", "Product Manager", "Engineering Manager",
    "QA/Automation Engineer", "Solutions Architect"
]

EXPERIENCE_LEVELS = [
    "Intern (0 years)", "Junior (1-2 years)", 
    "Senior (3-5 years)", "Staff/Principal (6+ years)", 
    "Managerial"
]

CATEGORIES = [
    "Conflict Resolution", "Leadership & Mentorship", "Failure & Learning",
    "Delivering Results", "Bias for Action", "Technical Trade-offs",
    "Ethics & Integrity", "Navigating Ambiguity", "Cross-functional Collaboration"
]

DIFFICULTIES = ["Medium", "Hard", "Expert"] # Skipping "Easy" for premium feel

SOURCE_TYPES = ["Hiring Manager Round", "Bar Raiser Round", "Team Fit Round", "Executive Round"]

TARGET_COMPANIES = [
    "Amazon", "Google", "Meta", "Microsoft", "Netflix", "Tesla", "Uber", 
    "Airbnb", "Stripe", "Databricks", "Snowflake", "Goldman Sachs", 
    "JPMorgan Chase", "McKinsey", "Walmart Labs", "ByteDance"
]

# --- PART 1: GENERATE THE BLUEPRINT ---
def generate_blueprint(n=5000):
    """
    Creates a DataFrame with pre-assigned metadata to guarantee distribution.
    """
    print(f"🏗️ Constructing blueprint for {n} questions...")
    data = []
    for _ in range(n):
        data.append({
            "role": random.choice(ROLES),
            "experience": random.choice(EXPERIENCE_LEVELS),
            "category": random.choice(CATEGORIES),
            "difficulty": random.choice(DIFFICULTIES),
            "source_type": random.choice(SOURCE_TYPES),
            "company": random.choice(TARGET_COMPANIES),
            "question": None,     # To be filled by AI
            "ideal_answer": None  # To be filled by AI
        })
    return pd.DataFrame(data)

# --- PART 2: THE AI GENERATOR ---
client = Groq(api_key=GROQ_API_KEY)

def generate_content_for_batch(batch_df):
    """
    Takes a dataframe batch (metadata only) and asks AI to fill the text.
    """
    # Convert batch to a lightweight JSON string for the prompt
    rows_to_process = batch_df[['role', 'experience', 'category', 'company', 'source_type']].to_dict(orient='records')
    prompt_json = json.dumps(rows_to_process)

    system_prompt = f"""
    You are an expert Bar Raiser interviewer at a top tech company.
    I will give you a list of candidate profiles (Role, Level, Company, Category).
    
    For EACH item in the list, generate:
    1. "question": A complex, behavioral interview question specific to that Company's culture and the Role's challenges. It should NOT be a one-liner. It should be scenario-based.
    2. "ideal_answer": A high-quality response using the STAR method (Situation, Task, Action, Result). It must be detailed (approx 200-250 words), sounding like a real human speaking for 2 minutes. Include specific technical details relevant to the role.

    OUTPUT FORMAT:
    Return ONLY a JSON object with a key "results" containing a list of objects.
    Each object must have "question" and "ideal_answer".
    The order must match the input list exactly.
    """

    try:
        completion = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_json}
            ],
            temperature=0.7, # Slightly creative for better writing
            response_format={"type": "json_object"}
        )
        
        response_content = completion.choices[0].message.content
        parsed = json.loads(response_content)
        return parsed.get("results", [])

    except Exception as e:
        print(f"❌ API Error: {e}")
        return None

# --- MAIN EXECUTION ---
def main():
    # 1. Check for Checkpoint
    if os.path.exists(CHECKPOINT_FILE):
        print(f"🔄 Checkpoint found. Resuming...")
        try:
            df = pd.read_json(CHECKPOINT_FILE)
        except ValueError:
            print("⚠️ Checkpoint file is empty or corrupted. Starting fresh.")
            df = generate_blueprint(5000)
    else:
        # Start fresh
        df = generate_blueprint(5000)
        # Save immediately
        df.to_json(CHECKPOINT_FILE, orient='records', indent=2)

    # 2. Identify rows that need generation
    # We look for rows where 'question' is still None
    todo_indices = df[df['question'].isnull()].index
    print(f"🎯 Total rows to generate: {len(todo_indices)}")

    # 3. Process in batches
    for i in range(0, len(todo_indices), BATCH_SIZE):
        batch_idx = todo_indices[i : i + BATCH_SIZE]
        batch_df = df.loc[batch_idx]
        
        print(f"Processing Batch {i//BATCH_SIZE + 1} ({len(batch_idx)} items)... ", end="")
        
        results = generate_content_for_batch(batch_df)
        
        if results and len(results) == len(batch_idx):
            # Map results back to the dataframe
            for idx, res in zip(batch_idx, results):
                df.at[idx, 'question'] = res.get('question')
                df.at[idx, 'ideal_answer'] = res.get('ideal_answer')
            print("✅ Done")
        else:
            print("⚠️ Batch failed or mismatch. Skipping (will retry next run).")
            time.sleep(2) # Penalty wait
        
        # Save Progress
        df.to_json(CHECKPOINT_FILE, orient='records', indent=2)
        
        # Rate Limit Protection
        # We are generating A LOT of text, so we need a healthy sleep
        time.sleep(2) 

    print(f"\n🎉 Generation Complete! Saving to {OUTPUT_FILE}")
    df.to_json(OUTPUT_FILE, orient='records', indent=2)

if __name__ == "__main__":
    main()