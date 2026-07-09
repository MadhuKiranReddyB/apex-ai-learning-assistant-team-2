import os
import warnings

warnings.simplefilter("always")

bad = [
    root
    for root, _, _ in os.walk("app")
    if "pycache" not in root and not os.path.exists(os.path.join(root, "__init__.py"))
]
print("missing __init__.py:", bad if bad else "none")

import app.main
from app.workflows.loader import register_workflows
from app.workflows.registry import workflow_registry

register_workflows()
w = workflow_registry.get("roadmap")
print("registered", w.name, w.id)
g = w._build_graph()
print("graph OK")

import app.services.recommendation
import app.api.v1.courses
import app.api.v1.recommendations
from app.workflows.agents.roadmap.workflow import RoadmapWorkflow
from app.workflows.agents.roadmap.nodes import node_retrieve_courses, node_generate_plan, node_enrich_plan
from app.workflows.agents.shared.llm import get_gemini_llm

print("all imports OK")
