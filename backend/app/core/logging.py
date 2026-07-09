import sys
import logging
import warnings
import structlog


def _silence_known_false_positives() -> None:
    """Silences cosmetic third-party warnings that don't affect correctness.

    - FastAPI re-wraps a top-level request-body model in a union-like context when
      building its validator, which makes Pydantic emit ``UnsupportedFieldAttribute
      Warning`` for every ``alias`` on ``SkillAnalysis`` — even though the aliases
      work correctly.
    - LangGraph emits a pending-deprecation warning about ``allowed_objects`` from
      its checkpoint serializer during import.

    Both are confirmed false positives, so we suppress just those categories.
    """
    try:
        from pydantic.warnings import UnsupportedFieldAttributeWarning

        warnings.filterwarnings("ignore", category=UnsupportedFieldAttributeWarning)
    except Exception:  # pragma: no cover - defensive: never break startup on this
        pass

    try:
        from langchain_core.utils.interactive_env import LangChainPendingDeprecationWarning

        warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)
    except Exception:  # pragma: no cover - defensive: never break startup on this
        pass


def setup_logging() -> None:
    _silence_known_false_positives()
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
            structlog.processors.EventRenamer("message"),
            structlog.contextvars.merge_contextvars,
            structlog.processors.CallsiteParameterAdder(
                [
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
