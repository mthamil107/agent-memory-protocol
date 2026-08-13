"""LangChain drop-in: a memorywire-backed chat message history with auto-provenance.

Use it anywhere LangChain wants a ``BaseChatMessageHistory`` (e.g. with
``RunnableWithMessageHistory``). Every message is persisted to memorywire and — the point of
this integration — **tagged with a `source` derived from its role**:

    human   -> "user"          (trusted)
    system  -> "system"        (trusted)
    ai      -> "agent"         (trusted)
    tool    -> "tool_result"   (untrusted)   <- where injected poison usually enters
    function-> "tool_result"   (untrusted)

That auto-provenance is what lets ``recover`` clean the store later with no manual tagging: a
prompt-injection that arrives through a tool result is written as ``source="tool_result"`` and is
therefore purgeable by provenance. See :meth:`MemorywireChatMessageHistory.recover`.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from collections.abc import Sequence
from typing import Any, cast

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage

from memorywire import Memory, MemoryType
from memorywire.recovery import Recoverer

# message.type (langchain) -> memorywire source
_SOURCE = {
    "human": "user",
    "system": "system",
    "ai": "agent",
    "tool": "tool_result",
    "function": "tool_result",
}
_DEFAULT_STORE = "sqlite-vec://./memorywire-langchain.db"


def _run(coro: Any) -> Any:
    """Run a coroutine from sync code, whether or not a loop is already running."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(1) as ex:  # a loop is already running
        return ex.submit(lambda: asyncio.run(coro)).result()


class MemorywireChatMessageHistory(BaseChatMessageHistory):
    """A ``BaseChatMessageHistory`` backed by memorywire, with automatic provenance."""

    def __init__(
        self,
        session_id: str,
        *,
        memory: Memory | None = None,
        store: str | None = None,
        agent_id: str = "langchain",
    ) -> None:
        self.session_id = session_id
        self._mem = memory or Memory(agent_id=agent_id, stores=[store or _DEFAULT_STORE])
        self._cache: list[BaseMessage] = []
        self._ids: list[str] = []

    # --- required BaseChatMessageHistory surface --------------------------------------
    @property
    def messages(self) -> list[BaseMessage]:
        return list(self._cache)

    @messages.setter
    def messages(self, value: Sequence[BaseMessage]) -> None:
        self._cache = list(value)

    def add_message(self, message: BaseMessage) -> None:
        _run(self.aadd_messages([message]))

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        _run(self.aadd_messages(messages))

    async def aadd_messages(self, messages: Sequence[BaseMessage]) -> None:
        for m in messages:
            source = _SOURCE.get(m.type, "unknown")
            content = m.content if isinstance(m.content, str) else str(m.content)
            resp = await self._mem.remember(
                content,
                type=MemoryType.EPISODIC,
                source=source,
                user_id=self.session_id,
                metadata={"role": m.type, "seq": len(self._cache)},
            )
            self._cache.append(m)
            rid = getattr(resp, "id", None)
            if rid:
                self._ids.append(rid)

    async def aget_messages(self) -> list[BaseMessage]:
        return list(self._cache)

    def clear(self) -> None:
        _run(self.aclear())

    async def aclear(self) -> None:
        if self._ids:
            await self._mem.forget(ids=self._ids, hard_delete=True, reason="langchain:clear")
        self._cache.clear()
        self._ids.clear()

    # --- the payoff -------------------------------------------------------------------
    async def arecover(
        self, *, trusted_sources: set[str] | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """Detect and recover poisoned memory in this history's store.

        In a conversation the trusted participants are the user, the system prompt, and the
        agent's own generations; the untrusted vector is external input (`tool_result`), which is
        where indirect injection enters. So the default trusted set here is
        ``{"user", "system", "agent"}`` — recover purges tool-origin poison without deleting the
        conversation itself. `dry_run` defaults to True. See :class:`memorywire.recovery.Recoverer`.
        """
        trusted = trusted_sources or {"user", "system", "agent"}
        kwargs.setdefault("dry_run", True)
        report = await Recoverer(self._mem, trusted_sources=trusted).recover(**kwargs)
        return report.to_dict()

    def recover(self, **kwargs: Any) -> dict[str, Any]:
        return cast("dict[str, Any]", _run(self.arecover(**kwargs)))
