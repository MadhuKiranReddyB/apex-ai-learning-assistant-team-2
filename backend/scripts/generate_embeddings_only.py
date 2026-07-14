"""Generate embeddings for cleaned courses and write a DB-ready JSON file.

This script reads `testdata/courses_cleaned.json`, generates embeddings using
the existing `app.core.gemini_client.embed_text`, attaches `embedding` arrays
to each course, and writes `testdata/courses_with_embeddings.json`.

It avoids importing Supabase so it can run in environments without the
`supabase` package.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import gemini_client

CLEANED = ROOT / "testdata" / "courses_cleaned.json"
OUTPUT = ROOT / "testdata" / "courses_with_embeddings.json"


def _embedding_text(data: Dict[str, Any]) -> str:
    parts = [
        data.get("course_name") or "",
        data.get("description") or "",
        "Category: " + (data.get("category") or ""),
        "Skills taught: " + ", ".join(data.get("skills_taught") or []),
    ]
    return ". ".join(p for p in parts if p)


async def _embed_with_semaphore(text: str, sem: asyncio.Semaphore) -> List[float]:
    async with sem:
        return await gemini_client.embed_text(text, task_type="retrieval_document")


async def process_batch(batch: List[Dict[str, Any]], concurrency: int) -> List[Dict[str, Any]]:
    sem = asyncio.Semaphore(concurrency)
    tasks = []
    for row in batch:
        txt = _embedding_text(row)
        tasks.append(asyncio.create_task(_embed_with_semaphore(txt, sem)))

    embeddings = []
    for t in asyncio.as_completed(tasks):
        try:
            emb = await t
        except Exception as exc:
            emb = None
            print("Embedding failed for one item:", exc)
        embeddings.append(emb)

    # attach embeddings in order
    out = []
    for i, row in enumerate(batch):
        row_copy = dict(row)
        row_copy["embedding"] = embeddings[i]
        out.append(row_copy)
    return out


async def main(batch_size: int, concurrency: int) -> None:
    if not CLEANED.exists():
        print(f"Cleaned file not found: {CLEANED}")
        return
    data = json.loads(CLEANED.read_text(encoding="utf-8"))
    courses = data.get("courses", [])
    total = len(courses)
    print(f"Loaded {total} cleaned courses")

    result: List[Dict[str, Any]] = []
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch = courses[start:end]
        print(f"Embedding batch {start}:{end} (size={len(batch)})")
        processed = await process_batch(batch, concurrency)
        result.extend(processed)
        print(f"Completed batch {start}:{end}")

    OUTPUT.write_text(json.dumps({"courses": result}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(result)} courses with embeddings to {OUTPUT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=200, help="Number of items per batch")
    parser.add_argument("--concurrency", type=int, default=8, help="Concurrent embedding calls")
    args = parser.parse_args()
    asyncio.run(main(args.batch_size, args.concurrency))
