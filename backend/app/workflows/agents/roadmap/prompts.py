"""Prompts for the roadmap-generation agent.

The prompts are kept as plain Python strings so the LLM node can compose the
final ``SystemMessage`` + ``HumanMessage`` with the dynamic inputs (candidate
courses, skill gaps, roles, existing skills).
"""

ROADMAP_SYSTEM_PROMPT = (
    "You are an expert career-transition coach and curriculum designer. "
    "Your job is to build a structured, week-by-week learning roadmap that helps "
    "an employee transition from their current role to a target role. "
    "You must ONLY recommend courses from the catalogue provided below. "
    "Each course has a course_id; include only those ids in the output. "
    "Return the plan as the requested JSON structure with no extra commentary."
)

ROADMAP_USER_PROMPT_TEMPLATE = """Current role: {current_role}
Target role: {target_role}

Existing skill levels (0-10):
{skills_text}

Skill gaps to close (target levels shown):
{skill_gaps_text}

Available courses in the catalogue (choose from these ONLY):
{courses_text}

Create a {max_weeks}-week learning roadmap. For each week, include:
- "week_number"
- "focus" (one sentence describing the week)
- "skills_covered" (list of skills addressed)
- "course_ids" (list of course_ids from the catalogue above)
- "activities" (list of 2-3 practical exercises or milestones)

Return the plan as JSON with a "summary" and "total_weeks" field at the top."""

CANDIDATE_COURSE_FORMAT = (
    "course_id: {course_id}\n"
    "name: {course_name}\n"
    "provider: {provider}\n"
    "difficulty: {difficulty_level}\n"
    "duration_hours: {duration_hours}\n"
    "skills_taught: {skills_taught}\n"
    "description: {description}"
)
