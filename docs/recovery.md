# memorywire recover — un-poison your agent's memory

Most agent-memory security tooling *detects* or *prevents* poisoning. Almost nothing **recovers**
from it: once a malicious "fact" or "experience" is in the store, how do you clean it out — and
know you kept the legitimate memories? `memorywire recover` does that.

It uses the lever the [PurgeBench](https://github.com/mthamil107/purgebench) benchmark found to be
strongest — **provenance** — and is honest about the case nobody has solved.

## What it does

For every memory of an agent it assigns one verdict:

| Verdict | When | Action |
|---|---|---|
| **purge** | `source` is set to a value that is not trusted (e.g. `web_page`, `tool_result`) | `forget` (soft by default, `--hard` to hard-delete) |
| **keep** | `source` is **absent** — see [Memories with no source](#memories-with-no-source) | untouched unless `--purge-unsourced` |
| **quarantine** | trusted `source`, but the content reads like an embedded directive (the *entangled* case) | soft-`forget`, flagged for **human review** — never silently deleted |
| **expire** | low confidence (with `--expire-low-conf`) | `expire` policy |
| **keep** | clean | untouched |

The mutations run through memorywire's real `forget` / `expire`, so the audit trail and
soft-delete (restorable) semantics are the genuine ones.

## CLI

```bash
# see what would happen — safe, changes nothing
memorywire recover --agent my-agent --store sqlite-vec://./mem.db --dry-run

# apply: purge untrusted-origin poison, quarantine suspicious trusted memories
memorywire recover --agent my-agent --store sqlite-vec://./mem.db

# also run the built-in content detectors, and hard-delete purged poison
memorywire recover --agent my-agent --store sqlite-vec://./mem.db --detectors --hard
```

Flags: `--trusted user,system` · `--expire-low-conf` / `--confidence-below 0.75` ·
`--detectors` · `--no-quarantine` · `--purge-unsourced` · `--hard` · `--dry-run` · `--json`.

> **Note:** on the CLI, `--dry-run` is opt-in — `memorywire recover` **applies** by default.
> The MCP `recover` tool is the other way round (`dry_run` defaults to `true`).

## Memories with no source

`source` is optional, and `--source` only landed on `remember` in 0.2.0, so a store written
before that has no source on **any** row.

Absence of a source is **not** treated as untrusted origin. Unsourced memories are kept, and
the reason on the verdict says `clean (no source recorded)` so they are visible in the report
rather than silently ignored. They are still run through the content detectors, so a directive
hiding in an unsourced memory is quarantined (soft-delete, restorable) like any other.

Pass `--purge-unsourced` to opt in to the stricter behaviour — only do this on a store where
every legitimate write is known to be source-tagged, because on a legacy store it will purge
every row.

Set provenance when you write (agents should tag where a memory came from):

```bash
memorywire remember "the vendor iban is ..." --source tool_result --agent my-agent
```

## Library

```python
from memorywire import Memory
from memorywire.recovery import Recoverer

rec = Recoverer(memory, trusted_sources={"user", "system"})
print((await rec.recover(dry_run=True)).to_text())   # preview
report = await rec.recover(expire_low_conf=True)      # apply
```

### Pluggable detectors

Any callable `content -> bool`, or an object exposing OWASP Agent Memory Guard's
`.inspect(key, value, operation=...)`, can be supplied and is applied to trusted-origin content
(a hit → quarantine):

```python
from agent_memory_guard.detectors import PromptInjectionDetector
rec = Recoverer(memory, detectors=[PromptInjectionDetector()])
```

## Honest limits

- **The entangled case is not auto-solved.** A directive hidden inside a trusted, legitimate
  memory is *quarantined for review*, not deleted — because deleting it would also destroy the
  benign fact it rides with. PurgeBench measures exactly this gap; recover handles it the honest
  way (surface it, let a human decide).
- **Enumeration** in v0.1 reads the reference `SqliteVecStore`. Other adapters can pass records
  explicitly (`Recoverer(memory, records=[...])`) until a per-adapter enumerator lands.
- Content detection alone does **not** catch semantic poison (see the PurgeBench results);
  provenance is the lever that works. Detectors here are advisory, layered on top.
