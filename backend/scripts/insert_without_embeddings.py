"""Simple: Insert courses_cleaned.json into Supabase WITHOUT embeddings (add them later)."""
import json
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
env_file = backend_path / ".env"
load_dotenv(env_file)

supabase_url = os.getenv("SUPABASE_URL")
supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not all([supabase_url, supabase_service_key]):
    raise ValueError("Missing SUPABASE credentials in .env")

supabase = create_client(supabase_url, supabase_service_key)

# Read cleaned courses
cleaned_file = backend_path / "testdata" / "courses_cleaned.json"
with open(cleaned_file, encoding='utf-8') as f:
    data = json.load(f)
    courses = data["courses"]

print(f"Found {len(courses)} courses. Inserting without embeddings...")

# Insert each course (no embedding)
for i, course in enumerate(courses, 1):
    row = {
        "course_id": course["course_id"],
        "course_name": course["course_name"],
        "provider": course["provider"],
        "description": course["description"],
        "category": course["category"],
        "difficulty_level": course["difficulty_level"],
        "duration_hours": course["duration_hours"],
        "url": course["url"],
        "prerequisites": course["prerequisites"],
        "skills_taught": course["skills_taught"],
        "rating": course["rating"],
        "enrollment_count": course["enrollment_count"],
        # embedding = NULL (will add later)
    }
    
    try:
        supabase.table("courses").insert(row).execute()
        if i % 100 == 0:
            print(f"[{i}/{len(courses)}] Inserted {i} courses")
    except Exception as e:
        print(f"Error at course {i}: {e}")
        break

print(f"✓ Done! Inserted {i} courses. Embeddings can be added later when quota resets.")
