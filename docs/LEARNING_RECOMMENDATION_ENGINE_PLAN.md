# Personalized Learning Recommendation Engine - Technical Plan

## 1. Executive Summary

This project builds a personalized learning recommendation engine that analyzes employee skills, matches courses, and generates a dynamic learning roadmap. The system uses FastAPI for REST APIs, LangGraph for workflow orchestration, Supabase (PostgreSQL + pgvector) for data storage and vector search, and React for the frontend.

## 2. System Architecture

### 2.1 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend API | FastAPI | REST endpoints, request validation, async support |
| Workflow Engine | LangGraph | Stateful recommendation orchestration |
| Database | Supabase (PostgreSQL + pgvector) | Employee profiles, learning history, roadmap state, vector search |
| LLM | Groq (Gemma) / OpenAI-compatible | Skill gap reasoning and roadmap planning |
| Vector Database | pgvector (built into Supabase) | Course similarity search using embeddings |
| Frontend | React + TypeScript | Employee and manager dashboard |
| Course Source | Udemy API / Custom Catalog | Course metadata and content |

### 2.2 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Employee     │  │ Manager      │  │ Admin        │          │
│  │ Dashboard    │  │ Dashboard    │  │ Portal       │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              REST API Layer (FastAPI)                     │  │
│  │  /employee/{id}/skills  /learning/recommend               │  │
│  │  /learning/roadmap/{id}  /courses  /analytics/progress   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           LangGraph Workflow Engine                       │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │  │
│  │  │ Skill    │  │ Course   │  │ Roadmap  │  │ Validation│ │  │
│  │  │ Profile  │  │ Retrieval│  │ Planning │  │ Node     │ │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Supabase (PostgreSQL + pgvector)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Employees    │  │ Courses      │  │ Roadmaps     │          │
│  │ (pgvector)   │  │ (pgvector)   │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Skills       │  │ Progress     │  │ Embeddings   │          │
│  │              │  │              │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Udemy API    │  │ Groq LLM     │  │ Embedding     │          │
│  │ (Course Data)│  │ (Gemma)      │  │ Service       │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

## 3. User Flow Diagram

```
┌─────────────┐
│   User      │
│  Login      │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Input Collection Phase                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ • User provides:                                       │  │
│  │   - Current role                                       │  │
│  │   - Target role                                        │  │
│  │   - Current skills (JSON)                              │  │
│  │   - Learning history                                   │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Course Retrieval Phase                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ • System fetches courses from Udemy API              │  │
│  │ • Vector similarity search based on skill gaps        │  │
│  │ • Returns ranked course list                          │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  3. User Preference Input                                    │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ • User provides:                                       │  │
│  │   - Hours available per week                           │  │
│  │   - Learning rate (beginner/intermediate/advanced)    │  │
│  │   - Preferred learning format                          │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Roadmap Generation Phase                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ • LangGraph orchestrates:                              │  │
│  │   - Skill gap analysis (LLM)                           │  │
│  │   - Course sequencing (prerequisites)                 │  │
│  │   - Timeline planning (based on hours/rate)           │  │
│  │   - Month-by-month learning path                      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Review & Iteration                                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ • User reviews generated roadmap                       │  │
│  │ • Can request changes:                                 │  │
│  │   - Swap courses                                       │  │
│  │   - Adjust timeline                                    │  │
│  │   - Change priorities                                  │  │
│  │ • System regenerates roadmap                           │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  6. Storage Phase                                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ • User accepts roadmap                                 │  │
│  │ • Store in PostgreSQL:                                 │  │
│  │   - Roadmap structure                                  │  │
│  │   - Course assignments                                 │  │
│  │   - Timeline milestones                                │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  7. Progress Tracking Phase                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ • User manually enters completion progress             │  │
│  │ • System validates:                                    │  │
│  │   - Course completion status                           │  │
│  │   - Quiz scores                                        │  │
│  │   - Time spent                                         │  │
│  │ • Progress data passed to analytics team               │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 4. Database Schema (Supabase / PostgreSQL + pgvector)

### 4.1 Supabase Setup

1. Create a free project at **[supabase.com](https://supabase.com)**.
2. Go to **Database → Extensions** and enable the **`vector`** extension (pgvector is pre-packaged with Supabase, no manual install needed). `uuid-ossp` is enabled by default.
3. Copy the connection string from **Project Settings → Database → Connection string** (use the "Transaction" pooler URI for serverless/async apps).
4. Use the async driver format for FastAPI/SQLAlchemy:
   ```
   DATABASE_URL=postgresql+asyncpg://postgres.<project-ref>:<password>@<pooler-host>:6543/postgres
   ```
5. Run the schema SQL below via the **Supabase SQL Editor** (or `psql` against the connection string).

### 4.2 Required Extensions

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
```

### 4.3 Core Tables

#### 4.3.1 Employees Table
```sql
CREATE TABLE employees (
    employee_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    current_role VARCHAR(100),
    target_role VARCHAR(100),
    department VARCHAR(100),
    manager_id UUID REFERENCES employees(employee_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_employees_email ON employees(email);
CREATE INDEX idx_employees_manager ON employees(manager_id);
```

#### 4.3.2 Skills Table
```sql
CREATE TABLE skills (
    skill_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50), -- technical, soft, domain
    description TEXT,
    embedding vector(1536) -- OpenAI embedding dimension
);

CREATE INDEX idx_skills_name ON skills(skill_name);
CREATE INDEX idx_skills_embedding ON skills USING ivfflat (embedding vector_cosine_ops);
```

#### 4.3.3 Employee Skills (Junction Table)
```sql
CREATE TABLE employee_skills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id UUID NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,
    proficiency_level INTEGER CHECK (proficiency_level BETWEEN 1 AND 5),
    last_assessed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(employee_id, skill_id)
);

CREATE INDEX idx_employee_skills_employee ON employee_skills(employee_id);
CREATE INDEX idx_employee_skills_skill ON employee_skills(skill_id);
```

#### 4.3.4 Courses Table
```sql
CREATE TABLE courses (
    course_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    course_name VARCHAR(255) NOT NULL,
    provider VARCHAR(100), -- udemy, coursera, internal
    external_course_id VARCHAR(100), -- Udemy course ID
    description TEXT,
    category VARCHAR(100),
    difficulty_level VARCHAR(20) CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced')),
    duration_hours DECIMAL(5,2),
    url VARCHAR(500),
    prerequisites TEXT[], -- Array of prerequisite skill names
    skills_taught TEXT[], -- Array of skill names taught
    embedding vector(1536), -- Course description embedding
    rating DECIMAL(3,2),
    enrollment_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_courses_provider ON courses(provider);
CREATE INDEX idx_courses_category ON courses(category);
CREATE INDEX idx_courses_embedding ON courses USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_courses_external_id ON courses(external_course_id);
```

#### 4.3.5 Roadmaps Table
```sql
CREATE TABLE roadmaps (
    roadmap_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id UUID NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    roadmap_name VARCHAR(255),
    target_role VARCHAR(100),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'completed', 'paused', 'cancelled')),
    start_date DATE,
    target_completion_date DATE,
    hours_per_week INTEGER,
    learning_rate VARCHAR(20),
    total_courses INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_roadmaps_employee ON roadmaps(employee_id);
CREATE INDEX idx_roadmaps_status ON roadmaps(status);
```

#### 4.3.6 Roadmap Courses (Junction Table)
```sql
CREATE TABLE roadmap_courses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    roadmap_id UUID NOT NULL REFERENCES roadmaps(roadmap_id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
    sequence_order INTEGER NOT NULL,
    month INTEGER, -- Which month in the roadmap
    status VARCHAR(20) DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'completed', 'skipped')),
    completion_percentage INTEGER DEFAULT 0 CHECK (completion_percentage BETWEEN 0 AND 100),
    quiz_score INTEGER, -- Quiz score if applicable
    hours_spent DECIMAL(5,2) DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    notes TEXT,
    UNIQUE(roadmap_id, course_id)
);

CREATE INDEX idx_roadmap_courses_roadmap ON roadmap_courses(roadmap_id);
CREATE INDEX idx_roadmap_courses_sequence ON roadmap_courses(sequence_order);
```

#### 4.3.7 Learning History Table
```sql
CREATE TABLE learning_history (
    history_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id UUID NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    course_id UUID REFERENCES courses(course_id),
    action VARCHAR(50), -- started, completed, quiz_passed, etc.
    details JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_learning_history_employee ON learning_history(employee_id);
CREATE INDEX idx_learning_history_timestamp ON learning_history(timestamp);
```

#### 4.3.8 Skill Gaps Table (Computed/Cache)
```sql
CREATE TABLE skill_gaps (
    gap_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    employee_id UUID NOT NULL REFERENCES employees(employee_id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(skill_id),
    current_level INTEGER,
    required_level INTEGER,
    gap_score INTEGER, -- Difference between required and current
    priority VARCHAR(20) CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(employee_id, skill_id)
);

CREATE INDEX idx_skill_gaps_employee ON skill_gaps(employee_id);
CREATE INDEX idx_skill_gaps_priority ON skill_gaps(priority);
```

## 5. LangGraph Workflow Design

### 5.1 Workflow State Schema

```python
from typing import TypedDict, List, Optional, Annotated
from langgraph.graph import add_messages

class RecommendationState(TypedDict):
    # Input data
    employee_id: str
    current_role: str
    target_role: str
    current_skills: List[dict]  # [{"skill_name": "Python", "level": 3}]
    learning_history: List[dict]
    
    # User preferences
    hours_per_week: Optional[int]
    learning_rate: Optional[str]  # "beginner", "intermediate", "advanced"
    
    # Intermediate data
    skill_gaps: List[dict]
    candidate_courses: List[dict]
    
    # Output data
    roadmap: Optional[dict]
    validation_errors: List[str]
    
    # Control flow
    iteration_count: int
    user_feedback: Optional[str]
    
    # Messages for LLM
    messages: Annotated[list, add_messages]
```

### 5.2 LangGraph Nodes

#### Node 1: Skill Profile Analysis
```python
async def skill_profile_node(state: RecommendationState) -> RecommendationState:
    """
    Analyzes current skills vs target role requirements
    Identifies skill gaps and prioritizes them
    """
    # 1. Fetch target role skill requirements from database
    # 2. Compare with current skills
    # 3. Calculate gap scores
    # 4. Prioritize gaps (critical, high, medium, low)
    # 5. Use LLM to explain gaps and suggest focus areas
    
    state["skill_gaps"] = identified_gaps
    return state
```

#### Node 2: Course Retrieval
```python
async def course_retrieval_node(state: RecommendationState) -> RecommendationState:
    """
    Retrieves relevant courses using vector similarity search
    Filters based on skill gaps and user preferences
    """
    # 1. Generate embedding for skill gaps
    # 2. Query pgvector for similar courses
    # 3. Filter by difficulty level (based on learning_rate)
    # 4. Filter by duration (based on hours_per_week)
    # 5. Rank courses by relevance and rating
    
    state["candidate_courses"] = ranked_courses
    return state
```

#### Node 3: Roadmap Planning
```python
async def roadmap_planning_node(state: RecommendationState) -> RecommendationState:
    """
    Creates month-by-month learning path
    Sequences courses based on prerequisites
    Uses LLM for intelligent planning
    """
    # 1. Analyze course prerequisites
    # 2. Build dependency graph
    # 3. Sequence courses (topological sort)
    # 4. Distribute across months based on hours_per_week
    # 5. Use LLM to explain the learning path
    # 6. Generate timeline with milestones
    
    state["roadmap"] = generated_roadmap
    return state
```

#### Node 4: Validation
```python
async def validation_node(state: RecommendationState) -> RecommendationState:
    """
    Validates the generated roadmap
    Checks for circular dependencies, duplicates, etc.
    """
    # 1. Verify all course IDs exist
    # 2. Remove duplicate courses
    # 3. Filter out already completed courses
    # 4. Detect circular prerequisites
    # 5. Validate timeline feasibility
    
    state["validation_errors"] = errors
    return state
```

#### Node 5: User Feedback Handler
```python
async def feedback_node(state: RecommendationState) -> RecommendationState:
    """
    Handles user feedback and modifies roadmap
    Allows course swaps, timeline adjustments
    """
    # 1. Parse user feedback
    # 2. Apply requested changes
    # 3. Re-run planning if needed
    # 4. Limit iterations to prevent loops
    
    state["iteration_count"] += 1
    return state
```

### 5.3 LangGraph Workflow Graph

```
                    ┌──────────────────┐
                    │   Start (Input)   │
                    └────────┬─────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │  Skill Profile Analysis  │
              └──────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────────────┐
              │   Course Retrieval      │
              └──────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────────────┐
              │   Roadmap Planning      │
              └──────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────────────┐
              │      Validation         │
              └──────────┬───────────────┘
                         │
                ┌────────┴────────┐
                │                 │
          Has Errors?        No Errors
                │                 │
                ▼                 ▼
      ┌──────────────────┐  ┌──────────────────┐
      │ Return Errors    │  │ User Review      │
      └──────────────────┘  └────────┬─────────┘
                                      │
                             ┌────────┴────────┐
                             │                 │
                       Accept?           Request Changes
                             │                 │
                             ▼                 ▼
                   ┌──────────────────┐  ┌──────────────────┐
                   │  Store to DB      │  │ Feedback Handler │
                   │  (End)           │  └────────┬─────────┘
                   └──────────────────┘           │
                                                 ▼
                                      ┌──────────────────┐
                                      │ Roadmap Planning │
                                      │  (Re-run)        │
                                      └──────────────────┘
```

### 5.4 Conditional Routing Logic

```python
def should_validate(state: RecommendationState) -> str:
    """Route to validation or return errors"""
    if state.get("validation_errors"):
        return "return_errors"
    return "user_review"

def should_store_or_iterate(state: RecommendationState) -> str:
    """Route to storage or feedback handler"""
    if state.get("user_feedback") and state["iteration_count"] < 3:
        return "feedback_handler"
    return "store_to_db"
```

## 6. API Design

### 6.1 API Endpoints

| Method | Path | Purpose | Request Body | Response |
|--------|------|---------|--------------|----------|
| POST | `/api/v1/auth/register` | Register new employee | `{username, email, password}` | `{employee_id, token}` |
| POST | `/api/v1/auth/login` | Login employee | `{username, password}` | `{token, employee_id}` |
| GET | `/api/v1/employee/{id}/skills` | Fetch current skills and gaps | - | `{current_skills, skill_gaps}` |
| POST | `/api/v1/learning/recommend` | Generate personalized learning path | `{employee_id, target_role, hours_per_week, learning_rate}` | `{roadmap_id, roadmap}` |
| GET | `/api/v1/learning/roadmap/{employee_id}` | Get active roadmap | - | `{roadmap, courses, progress}` |
| POST | `/api/v1/learning/roadmap/{employee_id}/rerank` | Update roadmap after progress | `{employee_id, progress_data}` | `{updated_roadmap}` |
| GET | `/api/v1/courses` | List available courses | Query params: `category, difficulty` | `{courses}` |
| POST | `/api/v1/courses/sync` | Sync courses from Udemy | `{provider, credentials}` | `{synced_count}` |
| POST | `/api/v1/learning/roadmap/{roadmap_id}/accept` | Accept and store roadmap | - | `{success}` |
| POST | `/api/v1/learning/progress/{course_id}` | Update course progress | `{completion_percentage, quiz_score, hours_spent}` | `{success}` |
| GET | `/api/v1/analytics/progress/{employee_id}` | Show learning progress summary | - | `{summary, charts_data}` |
| GET | `/api/v1/analytics/team/{manager_id}` | Team progress for manager | - | `{team_progress}` |

### 6.2 Request/Response Schemas

#### 6.2.1 Recommendation Request
```json
{
  "employee_id": "uuid",
  "target_role": "Senior Data Scientist",
  "hours_per_week": 10,
  "learning_rate": "intermediate",
  "preferences": {
    "format": ["video", "hands-on"],
    "providers": ["udemy", "coursera"]
  }
}
```

#### 6.2.2 Roadmap Response
```json
{
  "roadmap_id": "uuid",
  "employee_id": "uuid",
  "target_role": "Senior Data Scientist",
  "status": "active",
  "timeline": {
    "total_months": 6,
    "start_date": "2026-07-01",
    "target_completion_date": "2026-12-31"
  },
  "courses": [
    {
      "course_id": "uuid",
      "course_name": "Advanced Machine Learning",
      "provider": "udemy",
      "month": 1,
      "sequence_order": 1,
      "duration_hours": 20,
      "prerequisites": ["Python", "Statistics"],
      "status": "not_started"
    }
  ],
  "skill_gaps": [
    {
      "skill_name": "Deep Learning",
      "current_level": 2,
      "required_level": 4,
      "priority": "high"
    }
  ]
}
```

#### 6.2.3 Progress Update Request
```json
{
  "roadmap_course_id": "uuid",
  "completion_percentage": 75,
  "quiz_score": 85,
  "hours_spent": 15.5,
  "notes": "Completed modules 1-5"
}
```

## 7. Vector Database Configuration (Supabase pgvector)

### 7.1 pgvector Setup

Supabase ships pgvector as a managed extension — no manual installation required. Enable it once via the SQL Editor or Dashboard:

```sql
-- Enable pgvector extension (managed by Supabase)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create indexes for efficient similarity search
CREATE INDEX ON skills USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX ON courses USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

**MVP note:** For an MVP with a small course catalog (a few hundred to low-thousands of rows), you can skip the `ivfflat` index entirely and rely on a plain sequential scan with the `<=>` operator — simpler to set up and avoids retraining the index as the table grows. Add the index later once the catalog scales.

### 7.2 Embedding Generation

```python
from langchain_openai import OpenAIEmbeddings

# Initialize embedding model
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    dimensions=1536
)

# Generate embedding for skill description
skill_embedding = embeddings.embed_query("Python programming and data analysis")

# Generate embedding for course description
course_embedding = embeddings.embed_query("Learn Python from scratch with hands-on projects")
```

### 7.3 Vector Similarity Search

```python
# Find similar courses based on skill gaps
async def find_similar_courses(skill_gaps: List[str], limit: int = 10):
    # Combine skill gaps into search query
    query = " ".join(skill_gaps)
    query_embedding = embeddings.embed_query(query)
    
    # PostgreSQL vector similarity search
    query = """
        SELECT course_id, course_name, description, 
               1 - (embedding <=> $1) as similarity
        FROM courses
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> $1
        LIMIT $2
    """
    
    results = await db.fetch_all(query, query_embedding, limit)
    return results
```

## 8. External Integrations

### 8.1 Udemy API Integration

```python
import httpx

class UdemyClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.udemy.com/api-2.0"
    
    async def search_courses(self, query: str, category: str = None):
        """Search for courses on Udemy"""
        params = {
            "search": query,
            "page_size": 50,
            "fields": [
                "id", "title", "description", "category", 
                "subcategory", "estimated_content_length",
                "avg_rating", "num_reviews", "image_240x135"
            ]
        }
        if category:
            params["category"] = category
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/courses/",
                params=params,
                headers=headers
            )
            return response.json()
    
    async def sync_courses_to_db(self, courses: List[dict]):
        """Sync Udemy courses to local database"""
        for course in courses["results"]:
            # Generate embedding
            embedding = embeddings.embed_query(
                f"{course['title']} {course['description']}"
            )
            
            # Store in database
            await db.execute("""
                INSERT INTO courses 
                (course_name, provider, external_course_id, description, 
                 category, embedding, rating)
                VALUES ($1, 'udemy', $2, $3, $4, $5, $6)
                ON CONFLICT (external_course_id) 
                DO UPDATE SET 
                    course_name = EXCLUDED.course_name,
                    embedding = EXCLUDED.embedding
            """, course["title"], course["id"], 
                course["description"], course["category"], 
                embedding, course["avg_rating"])
```

### 8.2 Groq LLM Integration

```python
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

# Initialize Groq client
llm = ChatGroq(
    model="gemma2-9b-it",
    temperature=0.7,
    api_key=settings.GROQ_API_KEY
)

async def analyze_skill_gaps(current_skills: List[str], target_role: str):
    """Use LLM to analyze skill gaps"""
    prompt = f"""
    Current skills: {', '.join(current_skills)}
    Target role: {target_role}
    
    Analyze the skill gaps and provide:
    1. Missing skills
    2. Priority level (critical/high/medium/low)
    3. Recommended learning path
    """
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    return response.content
```

## 9. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- Set up PostgreSQL with pgvector extension
- Create database schema
- Set up FastAPI project structure
- Implement authentication (register/login)
- Create basic API endpoints

### Phase 2: Data Ingestion (Week 3)
- Implement Udemy API integration
- Create course sync mechanism
- Generate embeddings for courses
- Populate courses table
- Create skills catalog

### Phase 3: LangGraph Workflow (Week 4-5)
- Implement LangGraph nodes
- Create workflow state schema
- Build skill profile analysis node
- Implement course retrieval with vector search
- Create roadmap planning node
- Add validation node

### Phase 4: API Integration (Week 6)
- Connect LangGraph to FastAPI endpoints
- Implement recommendation API
- Create roadmap CRUD operations
- Add progress tracking endpoints
- Implement analytics endpoints

### Phase 5: Frontend Integration (Week 7-8)
- Build React dashboard
- Implement user profile management
- Create roadmap visualization
- Add progress tracking UI
- Implement manager dashboard

### Phase 6: Testing & Deployment (Week 9-10)
- Write unit tests
- Integration testing
- Performance optimization
- Deploy to production
- Monitor and iterate

## 10. Key Considerations

### 10.1 Performance
- Use pgvector IVFFlat indexes for fast similarity search
- Implement caching for frequent queries
- Use async/await throughout the stack
- Batch embedding generation

### 10.2 Security
- JWT-based authentication
- Role-based access control (employee, manager, admin)
- Input validation on all endpoints
- Secure API key management
- CORS configuration

### 10.3 Scalability
- Database connection pooling
- Horizontal scaling of FastAPI workers
- Vector index tuning for large datasets
- Async processing for long-running workflows

### 10.4 Data Quality
- Regular course data sync from Udemy
- Embedding regeneration for updated content
- Skill gap validation
- Progress data integrity checks

## 11. Success Metrics

- **User Engagement**: % of employees with active roadmaps
- **Completion Rate**: % of courses completed in roadmaps
- **Time to Proficiency**: Average time to reach target role
- **Satisfaction Score**: User feedback on roadmap quality
- **Skill Gap Reduction**: Average reduction in skill gaps over time

## 12. Next Steps

1. Set up PostgreSQL with pgvector extension
2. Create database schema and tables
3. Implement FastAPI authentication
4. Integrate Udemy API for course data
5. Build LangGraph workflow nodes
6. Create API endpoints
7. Develop React frontend
8. Test end-to-end flow
9. Deploy and monitor

---

**Document Version**: 1.0  
**Last Updated**: July 3, 2026  
**Author**: AI Platform Team
