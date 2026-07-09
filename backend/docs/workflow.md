# Backend Workflow: Learning Roadmap Generation

This document describes the end-to-end flow of the recommendation engine after
the refactor to match the `ai-platform/backend` workflow architecture.

## High-level flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│  POST /api/v1/employees/{employee_id}/recommendations                    │
│  Body: Team 1 SkillAnalysis JSON                                        │
└──────────────────────────────────────────────────┬──────────────────────┘
                                                   │
                                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  app/api/v1/recommendations.py                                            │
│  create_recommendation(employee_id, analysis: SkillAnalysis)              │
│  - Validates request body via Pydantic                                   │
│  - Calls recommendation_service.generate(employee_id, analysis)        │
└──────────────────────────────────────────────────┬──────────────────────┘
                                                   │
                                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  app/services/recommendation.py                                           │
│  RecommendationService.generate()                                       │
│  - Resolves the roadmap workflow from the registry:                       │
│    workflow_registry.get("roadmap")                                        │
│  - Converts SkillAnalysis → workflow input dict                            │
│  - Runs the workflow and receives final_plan                               │
│  - Persists final_plan as JSONB in the roadmaps table                    │
│  - Returns the persisted roadmaps row                                      │
└──────────────────────────────────────────────────┬──────────────────────┘
                                                   │
                                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  app/workflows/agents/roadmap/workflow.py                                 │
│  RoadmapWorkflow.run()                                                    │
│  - Validates employee_id and skill_gaps                                   │
│  - Builds the LangGraph StateGraph                                        │
│  - Invokes: retrieve_courses → generate_plan → enrich_plan             │
└──────────────────────────────────────────────────┬──────────────────────┘
                                                   │
         ┌─────────────────────────────────────────┐
         │                                         │
         ▼                                         │
┌────────────────────┐                             │
│  retrieve_courses  │  node 1                     │
│  - embeds skill gaps│                             │
│  - vector search    │                             │
│  - candidate courses│                             │
└────────┬───────────┘                             │
         │                                          │
         ▼                                          │
┌────────────────────┐                             │
│  generate_plan     │  node 2 (Gemini LLM)        │
│  - reads candidate │                             │
│    catalogue       │                             │
│  - returns         │                             │
│    structured plan │                             │
│    with course_ids │                             │
└────────┬───────────┘                             │
         │                                          │
         ▼                                          │
┌────────────────────┐                             │
│  enrich_plan       │  node 3                     │
│  - maps course_ids  │                             │
│    to full rows   │                             │
│  - builds final   │                             │
│    RoadmapPlan    │                             │
└────────┬───────────┘                             │
         │                                          │
         └──────────────────────────────────────────┘
                            │
                            ▼
                  returns { "final_plan": {...} }
```

## Flow details

### 1. API layer

File: `app/api/v1/recommendations.py`

```python
@router.post("/{employee_id}/recommendations", response_model=RoadmapResponse)
async def create_recommendation(employee_id: UUID, analysis: SkillAnalysis) -> RoadmapResponse:
    roadmap = await recommendation_service.generate(employee_id, analysis)
    return _to_roadmap_response(roadmap)
```

The endpoint accepts the same `SkillAnalysis` payload Team 1 already sends.
It does **not** store the skill analysis itself; it only uses it to build the
roadmap.

### 2. Service layer

File: `app/services/recommendation.py`

The service is now a thin orchestrator. It does not contain prompt engineering
or vector-search logic directly. Instead:

1. Resolves the workflow from the registry.
2. Builds a workflow input dict.
3. Runs the workflow.
4. Stores the resulting `final_plan` JSONB document.

```python
workflow = workflow_registry.get(ROADMAP_WORKFLOW_ID)
result = await workflow.run(workflow_input)
final_plan = result["final_plan"]
roadmap = await roadmap_repo.create({... "plan": final_plan})
```

### 3. Workflow registry

File: `app/workflows/registry.py`

The registry is populated once at startup by `app/workflows/loader.py`:

```python
def register_workflows() -> None:
    workflow_registry.register(RoadmapWorkflow(ROADMAP_WORKFLOW_ID))
```

This decouples the service from the concrete workflow class. Adding a new
agent later only requires importing it in `loader.py` and registering it.

### 4. Roadmap LangGraph workflow

File: `app/workflows/agents/roadmap/workflow.py`

Graph definition:

```python
graph.add_node(NODE_RETRIEVE, node_retrieve_courses)
graph.add_node(NODE_GENERATE, node_generate_plan)
graph.add_node(NODE_ENRICH, node_enrich_plan)
graph.set_entry_point(NODE_RETRIEVE)
graph.add_edge(NODE_RETRIEVE, NODE_GENERATE)
graph.add_edge(NODE_GENERATE, NODE_ENRICH)
graph.add_edge(NODE_ENRICH, END)
```

State shape: `RoadmapState` (`app/workflows/agents/roadmap/state.py`)
- Inputs: `employee_id`, `current_role`, `target_role`, `skills`, `skill_gaps`
- Working fields: `candidate_courses`, `llm_plan`, `final_plan`
- Error field: `error`

### 5. Nodes

#### Node 1: `retrieve_courses`

File: `app/workflows/agents/roadmap/nodes.py`

1. Joins skill gaps into a query string.
2. Calls `gemini_client.embed_text(..., task_type="retrieval_query")` to create a
   768-dimensional vector.
3. Runs `CourseRepository.list_by_embedding()` which calls the Supabase
   `match_courses` RPC (pgvector cosine similarity).
4. Stores the top `CANDIDATE_COURSE_LIMIT` (10) courses in the state.

#### Node 2: `generate_plan`

File: `app/workflows/agents/roadmap/nodes.py`

1. Loads the candidate catalogue from the state.
2. Formats the prompt using `prompts.py` templates.
3. Calls `get_gemini_llm()` (Gemini 2.5 Flash) via LangChain with structured
   output (`with_structured_output(RoadmapPlanSchema)`).
4. Returns a plan whose weeks reference courses by `course_id` strings only.

Structured output schema: `app/workflows/agents/roadmap/schema.py`

#### Node 3: `enrich_plan`

File: `app/workflows/agents/roadmap/nodes.py`

1. Takes the LLM's `course_ids` and looks them up in the retrieved candidate
   courses.
2. Builds the final `final_plan` dict that matches the API `RoadmapPlan`
   schema, including full course references (`course_id`, `course_name`,
   `provider`, `url`).
3. Drops any course IDs the LLM invented that are not in the candidate set.

### 6. Persistence

File: `app/repositories/roadmap.py`

The service inserts a single row into the `roadmaps` table:

```json
{
  "roadmap_id": "<uuid>",
  "user_id": "<employee_id>",
  "target_role": "AI Engineer",
  "status": "active",
  "plan": { /* final_plan JSONB */ }
}
```

The `plan` column is JSONB. There are no separate `skill_profiles` or
`roadmap_courses` tables.

## Supporting flows

### Course seeding

`POST /api/v1/courses` (file: `app/api/v1/courses.py`):

1. Accepts `CourseBulkCreate` payload.
2. `CourseService.create_courses_bulk()` assigns a `course_id` per row.
3. Calls `gemini_client.embed_text(..., task_type="retrieval_document")` for each
   course description to produce the vector stored in `courses.embedding`.
4. Inserts the batch via `CourseRepository.create_many()`.

**Important:** This step uses the **embedding model** (`gemini-embedding-001`),
not the chat LLM. Embeddings are mandatory because the roadmap workflow depends
on vector similarity search over `courses.embedding`.

### Fetching a saved roadmap

`GET /api/v1/employees/{employee_id}/recommendations`:

1. Calls `recommendation_service.get_roadmap()`.
2. `RoadmapRepository.get_latest_by_user_id()` returns the most recent
   `roadmaps` row for that user.
3. The API maps it to `RoadmapResponse`.

## File map

| Path | Purpose |
|------|---------|
| `app/api/v1/recommendations.py` | HTTP routes for generate + fetch |
| `app/services/recommendation.py` | Service orchestrator |
| `app/workflows/registry.py` | Workflow lookup table |
| `app/workflows/loader.py` | Startup registration of all workflows |
| `app/workflows/agents/roadmap/workflow.py` | LangGraph StateGraph definition |
| `app/workflows/agents/roadmap/nodes.py` | `retrieve_courses`, `generate_plan`, `enrich_plan` |
| `app/workflows/agents/roadmap/prompts.py` | Prompt templates |
| `app/workflows/agents/roadmap/schema.py` | LLM structured-output schema |
| `app/workflows/agents/roadmap/state.py` | LangGraph state type |
| `app/workflows/agents/shared/llm.py` | LangChain Gemini chat client |
| `app/core/gemini_client.py` | Gemini embedding client only |
| `app/repositories/course.py` | Vector search + course insert |
| `app/repositories/roadmap.py` | Roadmap insert + latest lookup |
| `app/db/schema.sql` | Supabase schema (courses, roadmaps) |

## Why LangGraph / this structure

- **Clear pipeline:** Each step (retrieve, generate, enrich) is explicit.
- **Testable:** Nodes can be unit-tested in isolation with a mocked state.
- **Extensible:** New agents can be added by creating a new folder under
  `app/workflows/agents/` and registering them in `loader.py`.
- **Matches reference:** The layout mirrors `ai-platform/backend/app/workflows`,
  making it easy for the team to move between projects.
