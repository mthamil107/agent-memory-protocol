# OWASP Agent Memory Guard — contribution/issue draft (POST THIS FIRST)

Per the roadmap validation: **file this before the public announcement.** It reframes the PurgeBench
result as a *contribution* to OWASP Agent Memory Guard (a benchmark to measure recovery), with the
conflict of interest disclosed up front, so the maintainers meet the finding as collaborators — not
as a public dunk.

Post as a GitHub issue on the OWASP Agent Memory Guard repo (owasp.org/www-project-agent-memory-guard →
their code repo), or raise it in the OWASP GenAI Slack / working group first.

---

**Title:** PurgeBench: a benchmark for measuring memory-poison *recovery* (contribution + results on the detector layer)

**Body:**

Hi Agent Memory Guard maintainers,

**Disclosure up front:** I'm the author of both PurgeBench and memorywire, so I have an interest here
— please treat the numbers below as something to reproduce and challenge, not as a verdict.

Agent Memory Guard focuses on *detecting and preventing* memory poisoning, and ships snapshot/rollback
for remediation. I've been working on the **recovery** side — once a store is poisoned, how completely
can you clean it and prove it — and built a small reproducible benchmark, **PurgeBench**
(github.com/mthamil107/purgebench), that scores recovery on three axes: eradication, utility
retention, and re-emergence resistance (combined so that "do nothing" and "wipe everything" both
score zero by construction).

**Why I'm opening this:** I think PurgeBench could be useful to you as a way to *measure* the
snapshot/rollback recovery you already ship — there's currently no standard metric for it. I'd be
glad to contribute it (or a subset) upstream, or adapt it to your interfaces.

**One result, stated carefully.** I ran Agent Memory Guard's **content detectors** as a recovery
procedure (flag → forget anything they catch). On *semantic* poison — a plausible-sounding malicious
"fact," not an injection signature — that path scored low (RC ≈ 0.036, near the do-nothing baseline),
while purging by **provenance/source** scored highest (RC ≈ 0.64).

**Important caveats so this is fair:**
- This exercised **only the content detectors**, applied as a post-hoc cleaner. It did **not** use
  Agent Memory Guard's `SourceClass` provenance, its policy layer, its integrity baselines, or its
  **snapshot/rollback** — which are arguably the right tools for this and which I'd expect to score
  much higher. The provenance procedure that *wins* in my benchmark is essentially what your policy
  layer already does.
- The takeaway I draw is **not** "the tool is weak." It's "content-anomaly detection alone doesn't
  catch semantic poison — provenance and rollback are the levers that do." That's an argument *for*
  the provenance/rollback parts of your design.

**Ask:** would a PR that (a) adds a recovery-scoring harness, and (b) evaluates Agent Memory Guard's
rollback (not just its content detectors) be welcome? Happy to run whatever configuration you
consider a fair test, and to co-author the writeup.

Thanks for building this — memory poisoning needs exactly this kind of runtime layer, and I'd rather
build the measurement *with* you than around you.

— Thamilvendhan Munirathinam (ORCID 0009-0005-5641-7424)
