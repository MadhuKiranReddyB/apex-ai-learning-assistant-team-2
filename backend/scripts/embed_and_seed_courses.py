"""Generate embeddings for cleaned courses and insert them into Supabase.

Reads `testdata/courses_cleaned.json`, calls `CourseService.create_courses_bulk`
which generates embeddings via Gemini and inserts rows into Supabase. The
created records (with `embedding`) are written to
`testdata/courses_with_embeddings.json` for auditing.

Usage:
  python -m backend.scripts.embed_and_seed_courses
"""
import asyncio
import json
import os
import sys
from pathlib import Path
import argparse
from typing import List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.course import course_service
from app.schemas.course import CourseBulkCreate, CourseCreate
from app.core.config import get_settings
from app.core.exceptions import ConfigurationException

CLEANED = ROOT / "testdata" / "courses_cleaned.json"
OUTPUT = ROOT / "testdata" / "courses_with_embeddings.json"


def load_cleaned() -> List[dict]:
    with CLEANED.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("courses", [])


def to_course_create(row: dict) -> CourseCreate:
    # Map cleaned row keys to CourseCreate model; omit course_id (service generates it)
    return CourseCreate(
        course_name=row.get("course_name"),
        provider=row.get("provider"),
        external_course_id=row.get("external_course_id"),
        description=row.get("description"),
        category=row.get("category"),
        difficulty_level=row.get("difficulty_level"),
        duration_hours=row.get("duration_hours"),
        url=row.get("url"),
        prerequisites=row.get("prerequisites") or [],
        skills_taught=row.get("skills_taught") or [],
        rating=row.get("rating"),
        enrollment_count=row.get("enrollment_count") or 0,
    )


async def _create_with_retries(payload: CourseBulkCreate, retries: int = 3):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return await course_service.create_courses_bulk(payload)
        except Exception as exc:
            last_error = exc
            print(f"Batch insert failed on attempt {attempt}/{retries}: {exc}")
            if attempt < retries:
                await asyncio.sleep(2)
    raise last_error


async def main(batch_size: int) -> None:
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        raise ConfigurationException("GEMINI_API_KEY not set in environment; cannot generate embeddings.")

    cleaned = load_cleaned()
    total = len(cleaned)
    print(f"Loaded {total} cleaned courses")

    created_all = []
    # process in small batches to avoid flooding the embedding API
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch = cleaned[start:end]
        print(f"Processing batch {start}-{end} ({len(batch)} rows)")
        courses = [to_course_create(r) for r in batch]
        payload = CourseBulkCreate(courses=courses)
        created = await _create_with_retries(payload)
        created_all.extend(created)
        print(f"Inserted {len(created)} courses for batch {start}-{end}")

    # Write created rows (should include embedding field)
    with OUTPUT.open("w", encoding="utf-8") as fh:
        json.dump({"courses": created_all}, fh, indent=2, ensure_ascii=False)
    print(f"Wrote output to {OUTPUT} (total {len(created_all)} records)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=5, help="Number of courses to process per batch (default: 5)")
    args = parser.parse_args()
    try:
        asyncio.run(main(args.batch_size))
    except Exception as exc:
        print("Error:", exc)
        raise
