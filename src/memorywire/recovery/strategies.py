"""Classification strategies for memory-poison recovery.

Each memory is classified into one :class:`~memorywire.recovery.report.Verdict`. The default
lever is **provenance** (untrusted ``source`` → purge), which the PurgeBench benchmark found to
be the strongest recovery signal. A built-in **directive detector** flags content that reads like
an embedded instruction; trusted-origin content that trips it is *quarantined* (not deleted),
which is the honest handling of the entangled case. External detectors — including OWASP Agent
Memory Guard's — can be supplied and are treated the same way.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from .report import EntryVerdict, MemoryRecord, Verdict

DEFAULT_TRUSTED = frozenset({"user", "system"})

# Heuristic directive patterns: hyphenated imperative payloads and common bypass phrasings.
_DIRECTIVE = re.compile(
    r"\b("
    r"disable-\w+|mute-\w+|skip-\w+|grant-all|root-forever|allow-any|self-approve|"
    r"auto-approve\w*|force-push|drop-table|drop-index|chmod-777|open-shell|run-as-root|"
    r"leak-\w+|exfil-\w+|reroute-\w+|paste-public|bcc-\w+|log-plaintext|poison-\w+|"
    r"ignore-\w+|add-sleep|share-all-\w+|attacker-\w+"
    r")\b"
    r"|\b(always|just|simply)\s+\w+\s+(them|it|the)\b",
    re.IGNORECASE,
)

# A detector is either a callable content->bool, or an object exposing Agent Memory Guard's
# `.inspect(key, value, operation=...)` returning something with a truthy `.matched`.
Detector = Any


def _detector_hit(detector: Detector, key: str, content: str) -> bool:
    if callable(detector):
        try:
            return bool(detector(content))
        except TypeError:
            pass
    inspect = getattr(detector, "inspect", None)
    if inspect is not None:
        try:
            res = inspect(key, content, operation="write")
            return bool(getattr(res, "matched", False))
        except Exception:
            return False
    return False


def directive_detector(content: str) -> bool:
    """Built-in heuristic: does this content read like an embedded instruction?"""
    return bool(_DIRECTIVE.search(content or ""))


def classify(
    record: MemoryRecord,
    *,
    trusted_sources: frozenset[str] = DEFAULT_TRUSTED,
    detectors: list[Detector] | None = None,
    quarantine_suspicious: bool = True,
    purge_unsourced: bool = False,
) -> EntryVerdict:
    """Return the recovery verdict for one memory record.

    ``purge_unsourced`` controls what happens to a record carrying no ``source`` at all.
    It defaults to ``False``, because absence of a source is not evidence of untrusted
    origin: ``source`` is an optional field, and any store written before 0.2.0 (when
    ``--source`` landed on ``remember``) has none on any row. Treating absence as
    untrusted would purge such a store in full. Unsourced records are still passed to
    the content detectors, so a directive hiding in one is quarantined rather than kept.
    Set ``purge_unsourced=True`` only for a store where every legitimate write is known
    to be source-tagged.
    """
    raw = (record.source or "").strip()
    unsourced = not raw
    src = raw or "unknown"

    # 1) Provenance - the strongest lever. Untrusted origin => purge.
    #    An absent source is handled separately: see purge_unsourced above.
    if unsourced:
        if purge_unsourced:
            return EntryVerdict(
                record, Verdict.PURGE, "no source recorded (purge_unsourced enabled)"
            )
    elif src not in trusted_sources:
        return EntryVerdict(record, Verdict.PURGE, f"untrusted source '{src}'")

    # 2) Trusted or unsourced origin: run detectors (built-in + any supplied). A hit here
    #    is the entangled case - a directive hiding in a memory we are not deleting on
    #    provenance alone. Quarantine (soft-delete, restorable), do not purge.
    origin = "unsourced" if unsourced else "trusted-origin"
    dets: list[Callable[..., Any] | Detector] = [directive_detector]
    if detectors:
        dets = dets + list(detectors)
    for d in dets:
        if _detector_hit(d, record.id, record.content):
            if quarantine_suspicious:
                return EntryVerdict(
                    record, Verdict.QUARANTINE, f"{origin} content matched a directive pattern"
                )
            return EntryVerdict(record, Verdict.KEEP, "flagged but quarantine disabled")

    return EntryVerdict(
        record, Verdict.KEEP, "clean (no source recorded)" if unsourced else "clean"
    )
