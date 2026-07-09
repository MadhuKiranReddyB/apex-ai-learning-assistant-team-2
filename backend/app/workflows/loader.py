"""Workflow registration loader.

Called once during application startup to populate the workflow registry. Any
new agent must be imported here and registered via ``workflow_registry.register``.
"""

from app.workflows.registry import workflow_registry
from app.workflows.agents.roadmap.workflow import RoadmapWorkflow


ROADMAP_WORKFLOW_ID = "roadmap"


def register_workflows() -> None:
    """Register all workflow agents with the registry."""
    workflow_registry.register(RoadmapWorkflow(ROADMAP_WORKFLOW_ID))
