# Ungated distribution — MCP directories + LangChain listing (no flag can kill these)

Per the roadmap validation: run these FIRST, as the primary channels. They're neutral registries —
listing a real, installable integration isn't self-promotion, so the HN/domain flag doesn't apply.
Each is copy-paste ready.

Positioning rule (from the reframe): lead with **recovery/security**, not "wire format."

---

## 1. MCP server directories

memorywire ships `memorywire-mcp` (stdio). Submit to each registry below. Same one-liner + config.

**One-line description (reuse everywhere):**
> memorywire — recoverable, governable agent memory. remember / recall / forget / merge / expire, plus **recover**: purge poisoned memory by provenance and quarantine hidden directives for human review. Addresses OWASP ASI06.

**Install / run:**
```
pip install "memorywire[mcp,sqlite-vec]"
```
**Client config block (what registries want):**
```json
{ "mcpServers": { "memorywire": { "command": "memorywire-mcp",
    "env": { "MEMORYWIRE_STORE": "sqlite-vec://./mem.db", "MEMORYWIRE_AGENT": "assistant" } } } }
```
**Tools exposed:** `remember`, `recall`, `forget`, `merge`, `expire`, `recover`
**Repo:** https://github.com/mthamil107/memorywire

Where to submit:
- **awesome-mcp-servers** (github.com/punkpeye/awesome-mcp-servers) — open a PR adding the line under the memory/knowledge or security section.
- **PulseMCP** (pulsemcp.com) — submit via their "add a server" form.
- **Smithery** (smithery.ai) — add via their registry (needs the config above).
- **Glama** (glama.ai/mcp/servers) — submit listing.
- **modelcontextprotocol/servers** community list — PR if there's a community section.

---

## 2. LangChain integration listing

memorywire ships a drop-in `BaseChatMessageHistory` with auto-provenance.

**Listing blurb:**
> **memorywire** — a chat message history with automatic provenance. Messages persist to memorywire tagged by origin (tool output → untrusted), so a poisoned tool result can be purged later with one call. Adds `recover()` to clean a poisoned session while keeping the conversation.

**Snippet:**
```python
from memorywire.integrations.langchain import MemorywireChatMessageHistory
history = MemorywireChatMessageHistory(session_id="user-42", store="sqlite-vec://./mem.db")
# use with RunnableWithMessageHistory ...
history.recover(dry_run=True)   # preview cleaning tool-origin poison
```
`pip install "memorywire[langchain,sqlite-vec]"` · docs: docs/langchain.md

Where to submit:
- **LangChain integrations docs** (github.com/langchain-ai/langchain → docs/docs/integrations/memory or /providers) — PR adding a short page/entry.
- **LangChain providers page** — add memorywire as a provider with the snippet above.
- Mention in the **LangChain Discord/forum** #integrations if there's a share channel.

---

## 3. Security lists (also ungated)

- **awesome-llm-security** (corca-ai) — you already have PR #255 for signalbench; add a memorywire line (recovery/ASI06) in the same or a follow-up PR.
- **awesome-agent-security** / **awesome-agentic-ai** lists — add memorywire under memory/defense.
- **OWASP GenAI Slack / Agentic working group** — share the PurgeBench contribution (see `owasp-submission.md`) — this doubles as channel #1 of the launch.

---

## Order (per validation)
1. OWASP contribution (`owasp-submission.md`) — first.
2. These registry listings (MCP dirs + LangChain) — the ungated primary channels.
3. The finding-first announcement (`recover-announce.md`).
4. Show HN — only after emailing HN mods about the old flag; post repo-linked, GIF-led.
