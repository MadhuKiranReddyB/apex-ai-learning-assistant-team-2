"""Continue embedding from course 558 onwards."""
import json
import time
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv
from google import genai
from supabase import create_client

# Load environment variables
env_file = backend_path / ".env"
load_dotenv(env_file)

gemini_api_key = os.getenv("GEMINI_API_KEY")
supabase_url = os.getenv("SUPABASE_URL")
supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not all([gemini_api_key, supabase_url, supabase_service_key]):
    raise ValueError("Missing GEMINI_API_KEY or SUPABASE credentials in .env")

gemini_client = genai.Client(api_key=gemini_api_key)
supabase = create_client(supabase_url, supabase_service_key)

total = len(courses)
# Read cleaned courses
cleaned_file = backend_path / "testdata" / "courses_cleaned.json"
with open(cleaned_file, encoding='utf-8') as f:
    data = json.load(f)
    courses = data["courses"]


def _embed_text(course: dict) -> str:
    return f"{course.get('course_name','')}. {course.get('description','')}. Category: {course.get('category','')}. Skills: {', '.join(course.get('skills_taught') or [])}"


def _insert_row(course: dict, embedding: list):
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
        "embedding": embedding,
    }
    return supabase.table("courses").insert(row).execute()


def run(start_index: int = 558, sleep_on_quota: int = 60):
    # start_index: 1-based index (course number). Convert to 0-based.
    START_FROM = max(0, start_index - 1)
    total = len(courses)
    print(f"Found {total} total courses. Starting from course {START_FROM + 1}...")

    for i in range(START_FROM, total):
        course = courses[i]
        course_num = i + 1
        text = _embed_text(course)

        # retry loop for embedding (handles quota errors)
        embedding = None
        for attempt in range(1, 6):
            try:
                result = gemini_client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=text,
                    config={
                        "task_type": "RETRIEVAL_DOCUMENT",
                        "output_dimensionality": 768,
                    },
                )
                embedding = result.embeddings[0].values
                break
            except Exception as e:
                msg = str(e)
                if "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
                    print(f"[{course_num}/{total}] Quota hit (attempt {attempt}). Sleeping {sleep_on_quota}s then retrying...")
                    time.sleep(sleep_on_quota)
                    continue
                else:
                    print(f"[{course_num}/{total}] Embedding failed: {e}")
                    raise

        if embedding is None:
            print(f"[{course_num}/{total}] Failed to get embedding after retries; stopping.")
            break

        try:
            _ = _insert_row(course, embedding)
            if course_num % 100 == 0:
                print(f"[{course_num}/{total}] Inserted: {course['course_name']}")
        except Exception as e:
            print(f"[{course_num}/{total}] Insert failed: {e}")
            raise

        time.sleep(0.3)

    print(f"✓ Done! Inserted courses from {START_FROM + 1} to {i + 1}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--start-index", type=int, default=558, help="1-based course number to start from (default: 558)")
    parser.add_argument("--sleep-on-quota", type=int, default=60, help="Seconds to sleep when quota is hit before retrying")
    args = parser.parse_args()
    run(start_index=args.start_index, sleep_on_quota=args.sleep_on_quota)
