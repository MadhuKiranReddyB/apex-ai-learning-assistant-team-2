"""Base class every workflow (agent) must implement.

Mirrors the ai-platform convention: a workflow is an addressable unit with an
``id``/``name``/``description`` and an async ``run`` entrypoint. ``validate_input``
runs before any work/persistence so bad requests fail fast.
"""

from abc import ABC, abstractmethod


class BaseWorkflow(ABC):
    id: str = ""
    name: str = ""
    description: str = ""

    def validate_input(self, input_data: dict) -> None:
        """Override to validate workflow-specific inputs.

        Raise :class:`app.core.exceptions.WorkflowInputException` on invalid
        input. Called before the workflow runs, so nothing is persisted on a
        bad request.
        """
        pass

    @abstractmethod
    async def run(self, input_data: dict) -> dict:
        """Execute the workflow and return its result as a plain dict."""
        raise NotImplementedError
