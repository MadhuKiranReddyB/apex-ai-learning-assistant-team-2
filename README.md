# Learning Recommendation Engine - Backend (Team 2)

FastAPI backend for the personalized learning recommendation engine. Consumes skill-analysis JSON produced by Team 1 and generates course roadmaps.

## Tech Stack

- **FastAPI** — REST API
- **Supabase (PostgreSQL)** — data storage, accessed via the `supabase-py` client over the REST API
- **pgvector** — course similarity search over Gemini embeddings
- **Gemini API** — generates course embeddings and (optionally) natural-language recommendation text

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your Supabase project's API credentials (Dashboard → Project Settings → API):
   ```
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_ANON_KEY=your-supabase-anon-key
   SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
   SUPABASE_JWT_SECRET=your-supabase-jwt-secret
   GEMINI_API_KEY=your-gemini-api-key
   ```
   Get a Gemini key from https://aistudio.google.com/app/apikey. If left blank, course matching falls back to naive keyword overlap instead of vector search.

3. Create the tables (including the `vector` extension, `courses.embedding` column, and `match_courses` RPC): run `app/db/schema.sql` once in the Supabase SQL editor.

4. Run the server:
   ```bash
   python -m uvicorn app.main:app --reload --port 8001
   ```

   The async Supabase client is initialised on startup (see `app/core/supabase_client.py`). API docs available at `http://localhost:8001/docs`.

## Data Flow

1. Courses are pre-seeded into the `courses` table (each row embedded with Gemini and stored in `courses.embedding`).
2. **Team 1's** skill-analysis JSON is posted to `POST /api/v1/employees/{employee_id}/recommendations` — it is used only to build the roadmap and is never persisted.
3. Backend embeds the `skillGaps` with Gemini, runs a pgvector similarity search over `courses.embedding` (via the `match_courses` RPC) to find the closest-matching courses, then prompts Gemini to arrange them into a **week-by-week** roadmap, and stores it as a JSONB `plan` document in `roadmaps`. The saved roadmap is returned in the same response.
4. The frontend fetches the saved roadmap via `GET /api/v1/employees/{employee_id}/recommendations`.

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/courses` | Seed course(s) into the vector DB (each is embedded with Gemini) |
| POST | `/api/v1/employees/{employee_id}/recommendations` | Generate, store and return a week-by-week roadmap from Team 1's skill-analysis JSON |
| GET | `/api/v1/employees/{employee_id}/recommendations` | Fetch the saved roadmap |
| GET | `/health` | Health check |

## Notes

- No auth layer yet — add JWT verification before this goes beyond MVP/demo.
- `GEMINI_API_KEY` is required: course embedding, skill-gap vector search, and roadmap generation all depend on it. The embedding step (`gemini-embedding-001`) is mandatory — vector similarity search needs vectors, which can only be produced by an embedding model.
- Seed courses via `POST /api/v1/courses` (or a script) before generating a roadmap, otherwise there are no courses to plan around.
- The generated roadmap is stored as a single JSONB `plan` column in `roadmaps`; there are no `skill_profiles` or `roadmap_courses` tables.
