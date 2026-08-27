# Changelog

All notable changes to memorywire are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). Until v1.0, breaking
changes may land between minor versions per the spec evolution policy in
[`docs/spec/v0.md`](docs/spec/v0.md).

## [Unreleased]

### Fixed
- **`recover` no longer purges memories that have no `source`.** An absent `source` was
  normalised to `"unknown"`, failed the trusted-set membership test, and was classified
  `PURGE` — so running `memorywire recover` (which applies by default on the CLI) against a
  store written before 0.2.0, when `--source` landed on `remember`, soft-deleted every row
  while reporting `untrusted source 'unknown'`. Absence of provenance is not evidence of
  untrusted origin. Unsourced records are now kept, with the verdict reason
  `clean (no source recorded)` so they stay visible in the report, and are still passed to the
  content detectors — a directive hiding in an unsourced memory is quarantined as before.
  Records with an explicitly untrusted `source` are unaffected.

### Added
- `purge_unsourced` (default `False`) on `classify()`, `Recoverer`, and the MCP `recover` tool,
  plus `--purge-unsourced` on `memorywire recover`, to opt in to the previous stricter
  behaviour on stores where every legitimate write is known to be source-tagged.
- [`docs/recovery.md`](docs/recovery.md): a "Memories with no source" section, and a note that
  `--dry-run` is opt-in on the CLI while the MCP tool defaults to `dry_run=true`.

## [0.5.0] - 2026-08-10

### Added
- **Trust-graph report** (`memorywire graph`, `memorywire.graph`): renders the memory store as a
  self-contained HTML graph (inline SVG, no server/CDN/external calls). Memories are colored by
  recovery verdict (clean / quarantined / purged); sources are squares ringed by trust
  (green = trusted origin, red = untrusted); edges are provenance. Click an untrusted source to see
  its **blast radius** and **purge by provenance** with a live animation.
  - Colorblind-safe palette with redundant shape encoding; hardened against attacker-controlled
    memory content (no script break-out; content escaped everywhere).
  - CLI: `memorywire graph --report out.html [--trusted user,system] [--title ...]`.
- Docs: [`docs/graph.md`](docs/graph.md).

## [0.4.0] - 2026-07-27

### Added
- **LangChain integration** (`memorywire.integrations.langchain`): a drop-in
  `MemorywireChatMessageHistory` (`BaseChatMessageHistory`) that persists messages to memorywire
  with **automatic provenance** — the `source` is derived from the message role
  (`HumanMessage`→`user`, `SystemMessage`→`system`, `AIMessage`→`agent`,
  `ToolMessage`/`FunctionMessage`→`tool_result`). Because tool output (the usual injection vector)
  is auto-tagged untrusted, `recover` works with no manual tagging.
  - `.recover()` / `.arecover()` clean a session scoped to conversation trust
    (`{user, system, agent}`): purge tool-origin poison without deleting the conversation.
  - Sync and async (`aadd_messages`, `aget_messages`, `arecover`).
- `[langchain]` optional dependency group (`langchain-core>=0.3`).
- Docs: [`docs/langchain.md`](docs/langchain.md).

## [0.3.0] - 2026-07-17

### Added
- **MCP server** (`memorywire-mcp`, `memorywire.mcp`): exposes memorywire's operations —
  `remember`, `recall`, `forget`, `merge`, `expire`, and **`recover`** — as MCP tools over stdio.
  Any MCP-aware agent (Claude Desktop, IDE assistants, other clients) gains persistent,
  governable, recoverable memory by adding the server to its client config; no code changes.
  - `remember` exposes `source` (the provenance `recover` relies on).
  - `recover` defaults to `dry_run=true` (safe preview).
  - Configured via `MEMORYWIRE_STORE` / `MEMORYWIRE_AGENT` env vars.
- `[mcp]` optional dependency group and the `memorywire-mcp` console entry point.
- Docs: [`docs/mcp-server.md`](docs/mcp-server.md).

## [0.2.0] - 2026-07-16

### Added
- **Memory-poison recovery** (`memorywire.recovery`, `memorywire recover`): a
  detect → recover → verify capability for compromised agent memory.
  - Provenance is the primary lever — memories from untrusted sources are purged
    (soft-delete by default, `--hard` to hard-delete).
  - A directive hidden inside a **trusted** memory (the *entangled* case) is
    **quarantined** for human review, never silently deleted.
  - Pluggable content detectors: a built-in directive heuristic, any callable
    `content -> bool`, or an OWASP Agent Memory Guard detector.
  - `--dry-run` previews without mutating; `--expire-low-conf` adds a confidence sweep.
  - Library API: `memorywire.recovery.Recoverer`.
- `--source` flag on `memorywire remember` so provenance is set from the CLI.
- Docs: [`docs/recovery.md`](docs/recovery.md); concept + CLI demo GIFs.

### Notes
- Recovery is validated by the external
  [PurgeBench](https://github.com/mthamil107/purgebench) benchmark (provenance-based
  forget is the strongest recovery lever measured).

## [0.1.0] - 2026-06-10

### Added
- Initial public release of the memorywire.
- JSON Schema 2020-12 specification covering 5 operations
  (`remember`, `recall`, `forget`, `merge`, `expire`) over 4 memory types
  (semantic, episodic, procedural, emotional).
- Five backend adapters implementing the `MemoryStore` protocol:
  `sqlite-vec`, `mem0`, `Letta`, `Cognee`, and `pgvector`.
- Memory router with Reciprocal Rank Fusion (RRF, k=60) and an optional
  1-hop graph boost for cross-store recall fusion.
- FSM-based procedural-memory backend powered by `pytransitions`.
- Asynchronous STM &harr; LTM transformer for short-term to long-term
  memory consolidation.
- `amp` CLI exposing `remember`, `recall`, and `forget` subcommands.
- Apache-2.0 licensed protocol and reference implementation.
- Microbenchmark harness, adversarial-fusion sub-experiment, and a
  16-scenario cross-adapter conformance suite.
- 290+ tests passing by default; `ruff` and `mypy --strict` clean.

[Unreleased]: https://github.com/mthamil107/memorywire/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mthamil107/memorywire/releases/tag/v0.1.0
