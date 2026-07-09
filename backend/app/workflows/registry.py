"""In-memory registry of available workflows, keyed by workflow ``id``.

Populated once at startup by :func:`app.workflows.loader.register_workflows`.
Services resolve a workflow via :meth:`WorkflowRegistry.get` rather than
importing it directly, mirroring the ai-platform pattern.
"""

from typing import Optional

from app.workflows.base_workflow import BaseWorkflow
from app.core.logging import get_logger

logger = get_logger(__name__)


class WorkflowRegistry:
    def __init__(self) -> None:
        self._workflows: dict[str, BaseWorkflow] = {}

    def register(self, workflow: BaseWorkflow) -> None:
        self._workflows[workflow.id] = workflow
        logger.info("Workflow registered", id=workflow.id, name=workflow.name)

    def get(self, workflow_id: str) -> Optional[BaseWorkflow]:
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> list[BaseWorkflow]:
        return list(self._workflows.values())


workflow_registry = WorkflowRegistry()
