"""Prepare and optionally seed courses from Online_Courses.csv

Usage:
  python -m backend.scripts.prepare_and_seed_courses [--seed-supabase]

This script reads `backend/testdata/Online_Courses.csv`, cleans and normalizes
rows into the `CourseCreate` shape used by the service, writes
`backend/testdata/courses_cleaned.json` and can optionally insert rows
directly into Supabase using `CourseRepository.create_many` (requires env config).
"""
import asyncio
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "testdata" / "Online_Courses.csv"
CLEANED_PATH = ROOT / "testdata" / "courses_cleaned.json"


def _safe_get(row: Dict[str, str], keys: List[str]) -> Optional[str]:
    for k in keys:
        v = row.get(k)
        if v and v.strip():
            return v.strip()
    return None


def parse_rating(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", value)
    return float(m.group(1)) if m else None


def parse_int(value: Optional[str]) -> int:
    if not value:
        return 0
    s = re.sub(r"[^0-9]", "", value)
    return int(s) if s else 0


def split_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    parts = [p.strip() for p in re.split(r",|;|\\|/", value) if p and p.strip()]
    # normalize and dedupe while preserving order
    seen = set()
    out = []
    for p in parts:
        key = p.lower()
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def parse_duration_hours(duration_text: Optional[str], weekly_text: Optional[str]) -> Optional[float]:
    # Try to infer duration in hours from 'Approximately X months' and weekly study hours
    months = None
    if duration_text:
        m = re.search(r"(\d+(?:\.\d+)?)\s*month", duration_text, re.I)
        if m:
            months = float(m.group(1))

    weekly_hours = None
    if weekly_text:
        m = re.search(r"(\d+(?:\.\d+)?)\s*hour", weekly_text, re.I)
        if m:
            weekly_hours = float(m.group(1))

    if months is not None and weekly_hours is not None:
        return round(months * 4 * weekly_hours, 2)
    return None


def row_to_course(row: Dict[str, str]) -> Optional[Dict[str, Any]]:
    title = _safe_get(row, ["Title", "Course Title"]) or None
    url = _safe_get(row, ["URL", "Course URL"]) or None
    if not title:
        return None

    description = _safe_get(row, ["Short Intro", "Course Short Intro", "What's include"]) or ""
    category = _safe_get(row, ["Category"]) or None
    difficulty = _safe_get(row, ["Level"]) or None
    provider = _safe_get(row, ["Site", "School"]) or None
    skills = split_list(_safe_get(row, ["Skills"]))
    prerequisites = split_list(_safe_get(row, ["Prequisites", "Prequisites", "Prequisites ", "Prequisites "]))
    rating = parse_rating(_safe_get(row, ["Rating"]))
    enrollment = parse_int(_safe_get(row, ["Number of viewers", "Number of viewers ", "Number of viewers"]))
    duration_hours = parse_duration_hours(_safe_get(row, ["Duration"]), _safe_get(row, ["Weekly study"]))

    course = {
        "course_id": str(uuid.uuid4()),
        "course_name": title,
        "provider": provider,
        "external_course_id": None,
        "description": description or None,
        "category": category,
        "difficulty_level": difficulty,
        "duration_hours": duration_hours,
        "url": url,
        "prerequisites": prerequisites,
        "skills_taught": skills,
        "rating": rating,
        "enrollment_count": enrollment,
    }
    return course


def clean_csv(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen = set()
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            course = row_to_course(r)
            if not course:
                continue
            key = (course.get("course_name"), course.get("url"))
            if key in seen:
                continue
            seen.add(key)
            rows.append(course)
    return rows


async def seed_to_supabase(rows: List[Dict[str, Any]]):
    # Import repository lazily to avoid requiring DB config when not seeding
    from app.repositories.course import CourseRepository

    repo = CourseRepository()
    # The repository expects DB column names that match our dicts; embedding is optional
    created = await repo.create_many(rows)
    print(f"Inserted {len(created)} rows into Supabase")


def write_cleaned(rows: List[Dict[str, Any]], path: Path):
    payload = {"courses": rows}
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    print(f"Wrote {len(rows)} cleaned courses to {path}")


def main(argv: List[str]):
    seed_flag = "--seed-supabase" in argv
    print(f"Using CSV_PATH={CSV_PATH}")
    if not CSV_PATH.exists():
        print(f"CSV not found: {CSV_PATH}")
        return
    rows = clean_csv(CSV_PATH)
    write_cleaned(rows, CLEANED_PATH)
    if seed_flag:
        print("Seeding to Supabase (requires env / config). This may fail if Supabase is not configured.")
        asyncio.run(seed_to_supabase(rows))


if __name__ == "__main__":
    main(sys.argv[1:])
