# memorywire + LangChain

A drop-in `BaseChatMessageHistory` that persists to memorywire with **automatic provenance** — so
you get recoverable, poison-cleanable agent memory in LangChain with no manual tagging.

## Install

```bash
pip install "memorywire[langchain,sqlite-vec]"
```

## Use it

```python
from memorywire.integrations.langchain import MemorywireChatMessageHistory

history = MemorywireChatMessageHistory(session_id="user-42", store="sqlite-vec://./mem.db")
```

Drop it into `RunnableWithMessageHistory` exactly like any other chat history:

```python
from langchain_core.runnables.history import RunnableWithMessageHistory

chain_with_memory = RunnableWithMessageHistory(
    chain,
    lambda session_id: MemorywireChatMessageHistory(session_id, store="sqlite-vec://./mem.db"),
    input_messages_key="input",
    history_messages_key="history",
)
```

## The point: automatic provenance

Every message is written with a `source` derived from its role — no manual tagging:

| LangChain message | memorywire `source` | trust |
|---|---|---|
| `HumanMessage` | `user` | trusted |
| `SystemMessage` | `system` | trusted |
| `AIMessage` | `agent` | trusted |
| `ToolMessage` / `FunctionMessage` | `tool_result` | **untrusted** |

`tool_result` is where indirect prompt injection enters an agent (a poisoned document or API
response the model just read). Because those messages are automatically tagged untrusted, you can
clean them out later with one call.

## Recover a poisoned session

```python
print(history.recover(dry_run=True))   # preview — nothing changes
history.recover(dry_run=False)         # purge tool-origin poison; keep the conversation
```

In this conversational context the trusted participants are the user, the system prompt, and the
agent's own generations, so recovery **purges `tool_result`-origin poison without deleting the
conversation**. (Override with `recover(trusted_sources={...})` if you want a stricter policy.)

## Notes

- Async is first-class: `await history.aadd_messages([...])`, `await history.arecover()`.
- v0.1 keeps the session's message order in memory and persists every message to memorywire for
  durability + recovery; verbatim cross-session transcript replay is best-effort.
- Pass an existing `Memory` (`MemorywireChatMessageHistory(session_id, memory=my_memory)`) to share
  a store/router across sessions.
