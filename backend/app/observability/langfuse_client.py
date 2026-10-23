"""Privacy-aware, optional Langfuse instrumentation.

The application must continue to work when Langfuse is disabled or the SDK is
not installed.  This adapter keeps the rest of the Agent code independent of
SDK version details and never sends raw prompts/resumes unless explicitly
enabled through ``LANGFUSE_CAPTURE_CONTENT=true``.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import time
from contextlib import contextmanager
from typing import Any, Awaitable, Callable, Dict, Iterator, Optional

logger = logging.getLogger(__name__)


class LangfuseObservability:
    """Small no-op-safe adapter used by the Agent and LangGraph nodes."""

    def __init__(self, settings: Any):
        self.enabled = bool(
            getattr(settings, "langfuse_enabled", False)
            and getattr(settings, "langfuse_public_key", None)
            and getattr(settings, "langfuse_secret_key", None)
        )
        self.capture_content = bool(getattr(settings, "langfuse_capture_content", False))
        self.sample_rate = float(getattr(settings, "langfuse_sample_rate", 1.0))
        self.client = None
        self._callback_handler = None

        if not self.enabled:
            return

        public_key = settings.langfuse_public_key
        secret_key = settings.langfuse_secret_key
        host = settings.langfuse_host
        # Set standard variables so the LangChain callback integration can
        # initialize consistently across Langfuse SDK versions.
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", public_key)
        os.environ.setdefault("LANGFUSE_SECRET_KEY", secret_key)
        os.environ.setdefault("LANGFUSE_HOST", host)
        os.environ.setdefault("LANGFUSE_SAMPLE_RATE", str(self.sample_rate))

        try:
            from langfuse import Langfuse

            kwargs = {
                "public_key": public_key,
                "secret_key": secret_key,
                "host": host,
                "sample_rate": self.sample_rate,
            }
            # Langfuse v2/v3 support masking hooks, but keep a compatibility
            # fallback for versions that do not expose this constructor option.
            try:
                self.client = Langfuse(mask=self._mask_event, **kwargs)
            except TypeError:
                self.client = Langfuse(**kwargs)
            logger.info("Langfuse observability enabled")
        except Exception as exc:
            self.enabled = False
            logger.warning("Langfuse disabled: SDK initialization failed: %s", exc)

    def _mask_event(
        self,
        event: Any = None,
        *,
        data: Any = None,
        **_: Any,
    ) -> Any:
        """Mask sensitive Langfuse event fields.

        Langfuse v2 calls a mask callback with one positional argument while
        newer SDK releases call it as ``mask(data=...)``.  Accept both forms;
        otherwise the SDK catches the ``TypeError`` and replaces the complete
        event with ``<fully masked due to failed mask function>``.  The
        redacted path returns a copy so the SDK's event object is not mutated
        by the privacy adapter.
        """
        if data is not None:
            event = data

        # Content capture is an explicit opt-in.  Metadata and the manual
        # spans are still emitted when this is disabled, but their payloads
        # are redacted below by ``update``/this callback.
        if self.capture_content:
            return event

        return self._redact_event(event)

    @classmethod
    def _redact_event(cls, value: Any) -> Any:
        """Recursively redact content fields while preserving event shape."""
        if isinstance(value, dict):
            sensitive = {
                "input",
                "output",
                "prompt",
                "completion",
                "messages",
                "arguments",
                "args",
                "tool_input",
                "tool_output",
            }
            return {
                key: "[REDACTED]"
                if str(key).lower() in sensitive
                else cls._redact_event(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [cls._redact_event(item) for item in value]
        if isinstance(value, tuple):
            return tuple(cls._redact_event(item) for item in value)
        return value

    def _safe_metadata(self, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not metadata:
            return {}
        safe: Dict[str, Any] = {}
        for key, value in metadata.items():
            # Callers should pass IDs/counts only.  Truncate strings to avoid
            # accidentally sending a full prompt or resume as metadata.
            if isinstance(value, str):
                safe[key] = value if self.capture_content else value[:160]
            elif isinstance(value, (int, float, bool)) or value is None:
                safe[key] = value
            else:
                safe[key] = str(value)[:160]
        return safe

    def _start_current_observation(self, kwargs: Dict[str, Any]) -> Any:
        """Start an observation while tolerating SDK signature differences."""
        starter = self.client.start_as_current_observation
        try:
            signature = inspect.signature(starter)
        except (TypeError, ValueError):
            # Some extension/mocked callables do not expose a signature.
            return starter(**kwargs)

        if any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        ):
            return starter(**kwargs)

        accepted = signature.parameters
        filtered = {key: value for key, value in kwargs.items() if key in accepted}
        return starter(**filtered)

    def _update_current_trace(self, *, session_id: Optional[str], user_id: Optional[str]) -> None:
        """Set trace-level identity fields when the SDK exposes that API."""
        if not session_id and not user_id:
            return
        updater = getattr(self.client, "update_current_trace", None)
        if not callable(updater):
            return
        kwargs: Dict[str, Any] = {}
        if session_id:
            kwargs["session_id"] = session_id
        if user_id:
            kwargs["user_id"] = user_id
        try:
            updater(**kwargs)
        except Exception as exc:
            logger.debug("Langfuse trace identity update failed: %s", exc)

    @contextmanager
    def observation(
        self,
        name: str,
        *,
        as_type: str = "span",
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Iterator[Any]:
        """Create a span/generation context, or a no-op context when disabled."""
        if not self.enabled or self.client is None:
            yield None
            return

        safe_metadata = self._safe_metadata(metadata)
        if hasattr(self.client, "start_as_current_observation"):
            kwargs: Dict[str, Any] = {
                "as_type": as_type,
                "name": name,
                "metadata": safe_metadata,
            }
            if session_id:
                kwargs["session_id"] = session_id
            if user_id:
                kwargs["user_id"] = user_id
            try:
                observation_context = self._start_current_observation(kwargs)
            except Exception as exc:
                # ``tool`` was added as a named observation type after the
                # original span API.  Retry as a span for older SDKs rather
                # than dropping the tool observation completely.
                if as_type == "tool":
                    try:
                        kwargs["as_type"] = "span"
                        observation_context = self._start_current_observation(kwargs)
                    except Exception as fallback_exc:
                        logger.debug(
                            "Langfuse observation setup failed for %s: %s (span fallback: %s)",
                            name,
                            exc,
                            fallback_exc,
                        )
                        yield None
                        return
                else:
                    logger.debug("Langfuse observation setup failed for %s: %s", name, exc)
                    yield None
                    return
            # Do not catch exceptions raised by the application body here;
            # the context manager must preserve normal Agent error handling.
            with observation_context as observation:
                self._update_current_trace(session_id=session_id, user_id=user_id)
                yield observation
            return

        # Legacy SDK fallback.
        if hasattr(self.client, "trace"):
            try:
                observation = self.client.trace(
                    name=name,
                    session_id=session_id,
                    user_id=user_id,
                    metadata=safe_metadata,
                )
            except Exception as exc:
                logger.debug("Langfuse trace setup failed for %s: %s", name, exc)
                yield None
                return
            yield observation
            return

        logger.debug("Langfuse SDK has no supported observation API")
        yield None

    def update(self, observation: Any, **fields: Any) -> None:
        if observation is None:
            return
        try:
            safe_fields = dict(fields)
            if "metadata" in safe_fields:
                safe_fields["metadata"] = self._safe_metadata(safe_fields["metadata"])
            if not self.capture_content:
                for key in (
                    "input",
                    "output",
                    "prompt",
                    "completion",
                    "messages",
                    "arguments",
                    "args",
                ):
                    if key in safe_fields:
                        safe_fields[key] = "[REDACTED]"
            if hasattr(observation, "update"):
                observation.update(**safe_fields)
        except Exception as exc:
            logger.debug("Langfuse observation update failed: %s", exc)

    def callback_handler(self) -> Any:
        """Return the LangChain callback handler when available."""
        # LangChain callbacks may include full message payloads.  Keep them
        # disabled in the default privacy-safe mode; the manual spans above
        # still expose latency, errors, counts, and tool names.
        if not self.enabled or not self.capture_content:
            return None
        if self._callback_handler is not None:
            return self._callback_handler
        try:
            from langfuse.langchain import CallbackHandler

            try:
                self._callback_handler = CallbackHandler()
            except TypeError:
                self._callback_handler = CallbackHandler(
                    public_key=os.getenv("LANGFUSE_PUBLIC_KEY")
                )
            return self._callback_handler
        except Exception as exc:
            logger.warning("Langfuse LangChain callback unavailable: %s", exc)
            return None

    def runnable_config(
        self,
        *,
        session_id: Optional[str],
        user_id: Optional[str],
        tags: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        config: Dict[str, Any] = {
            "metadata": {
                "observability_session_id": session_id,
                "observability_user_id": user_id,
            },
            "tags": tags or ["recruitment-agent"],
        }
        handler = self.callback_handler()
        if handler is not None:
            config["callbacks"] = [handler]
        return config

    async def ainvoke(
        self,
        runnable: Any,
        messages: Any,
        *,
        name: str,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Invoke an LLM and record a generation without exposing content."""
        started = time.perf_counter()
        with self.observation(name, as_type="generation", metadata=metadata) as span:
            try:
                response = await runnable.ainvoke(messages)
                usage = getattr(response, "usage_metadata", None)
                self.update(
                    span,
                    model=model,
                    latency_ms=round((time.perf_counter() - started) * 1000, 2),
                    usage_details=usage if isinstance(usage, dict) else None,
                    metadata={"output_chars": len(str(getattr(response, "content", "") or ""))},
                )
                return response
            except Exception as exc:
                self.update(
                    span,
                    level="ERROR",
                    status_message=str(exc)[:240],
                    metadata={"latency_ms": round((time.perf_counter() - started) * 1000, 2)},
                )
                raise

    async def tool_call(
        self,
        name: str,
        operation: Callable[[], Awaitable[Any]],
        *,
        metadata: Optional[Dict[str, Any]] = None,
        input_data: Any = None,
    ) -> Any:
        started = time.perf_counter()
        # ``tool`` is a first-class observation type in current Langfuse
        # releases and is rendered as a tool call in the trace tree.  The
        # observation adapter still has the legacy span fallback for older
        # SDKs, so callers do not need version-specific code.
        with self.observation(name, as_type="tool", metadata=metadata) as span:
            try:
                result = await operation()
                self.update(
                    span,
                    input=input_data,
                    output=result,
                    metadata={
                        **(metadata or {}),
                        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                        "result_chars": len(str(result or "")),
                    },
                )
                return result
            except Exception as exc:
                self.update(span, level="ERROR", status_message=str(exc)[:240])
                raise

    def flush(self) -> None:
        if self.client is None:
            return
        try:
            self.client.flush()
        except Exception as exc:
            logger.debug("Langfuse flush failed: %s", exc)
