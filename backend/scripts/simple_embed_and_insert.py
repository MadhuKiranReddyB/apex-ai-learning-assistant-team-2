"""Simple: Read courses_cleaned.json, generate embeddings, insert into Supabase."""
import json
import time
import os
import sys
from pathlib import Path

# Add backend to path so imports work from anywhere
backend_path = Path(__file__).parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
from google import genai
from supabase import create_client

# Load environment variables
env_file = backend_path / ".env"
load_dotenv(env_file)

# Initialize clients
gemini_api_key = os.getenv("GEMINI_API_KEY")
supabase_url = os.getenv("SUPABASE_URL")
supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not all([gemini_api_key, supabase_url, supabase_service_key]):
    raise ValueError("Missing GEMINI_API_KEY or SUPABASE credentials in .env")

gemini_client = genai.Client(api_key=gemini_api_key)
supabase = create_client(supabase_url, supabase_service_key)

# Read cleaned courses
cleaned_file = Path(__file__).parent.parent / "testdata" / "courses_cleaned.json"
with open(cleaned_file, encoding='utf-8') as f:
    data = json.load(f)
    courses = data["courses"]

print(f"Found {len(courses)} courses. Starting embedding + insert...")

# Process each course
for i, course in enumerate(courses, 1):
    # Build text to embed
    text = f"{course['course_name']}. {course['description']}. Category: {course['category']}. Skills: {', '.join(course['skills_taught'])}"
    
    # Generate embedding
    result = gemini_client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config={
            "task_type": "RETRIEVAL_DOCUMENT",
            "output_dimensionality": 768
        }
    )
    embedding = result.embeddings[0].values
    
    # Insert into Supabase
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
        "embedding": embedding
    }
    
    supabase.table("courses").insert(row).execute()
    print(f"[{i}/{len(courses)}] Inserted: {course['course_name']}")
    time.sleep(0.3)  # Small delay to avoid rate limiting

print("✓ Done! All courses inserted with embeddings.")
