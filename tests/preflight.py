"""Pre-demo checklist. Run this before recording or sending anything.

    python -m tests.preflight

Checks the things that fail silently: a search index that no longer matches
the guides, a sleeping server, and the two answers the demo depends on.
"""

import json
import sys
import time
import urllib.error
import urllib.request

from app.retrieval import INDEX_FILE, all_chunks

LIVE = "https://it-help-f8gb.onrender.com"
TIMEOUT = 90

# The demo script: one question that must answer, one that must refuse.
DEMO_ANSWER = "my wifi keeps dropping"
DEMO_REFUSAL = "how do i expense a taxi"


def _request(path: str, body: dict | None = None, method: str | None = None):
    data = json.dumps(body).encode() if body else None
    request = urllib.request.Request(
        f"{LIVE}{path}",
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method=method or ("POST" if data else "GET"),
    )
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        payload = response.read()
        return response.status, payload, time.monotonic() - started


def check_index_fresh() -> tuple[bool, str]:
    """Guides edited without rebuilding the index is the silent failure —
    everything looks fine and answers come from superseded text."""
    if not INDEX_FILE.exists():
        return False, "index.json missing — run `python -m app.retrieval`"
    indexed = {entry["id"]: entry["text"] for entry in json.loads(INDEX_FILE.read_text())}
    current = {chunk["id"]: chunk["text"] for chunk in all_chunks()}
    if indexed == current:
        return True, f"{len(current)} sections, matches the guides"
    added = set(current) - set(indexed)
    removed = set(indexed) - set(current)
    changed = {k for k in set(current) & set(indexed) if current[k] != indexed[k]}
    detail = ", ".join(
        part
        for part in (
            f"{len(added)} new" if added else "",
            f"{len(removed)} deleted" if removed else "",
            f"{len(changed)} edited" if changed else "",
        )
        if part
    )
    return False, f"STALE ({detail}) — run `python -m app.retrieval` and commit"


def check_head() -> tuple[bool, str]:
    """Uptime monitors use HEAD; a 405 here reads as an outage."""
    status, _, _ = _request("/health", method="HEAD")
    return status == 200, f"HEAD /health -> {status}"


def check_warm() -> tuple[bool, str]:
    """Over ~5s means it was asleep — wait and re-run before recording."""
    status, _, elapsed = _request("/health")
    return status == 200 and elapsed < 5, f"GET /health -> {status} in {elapsed:.2f}s"


def check_page() -> tuple[bool, str]:
    status, payload, _ = _request("/")
    ok = status == 200 and b"IT Help" in payload
    return ok, f"GET / -> {status}, {len(payload)} bytes"


def check_demo_answer() -> tuple[bool, str]:
    _, payload, elapsed = _request("/ask", {"question": DEMO_ANSWER})
    data = json.loads(payload)
    ok = data.get("answered") is True
    return ok, f"{DEMO_ANSWER!r} -> answered={data.get('answered')} in {elapsed:.1f}s"


def check_demo_refusal() -> tuple[bool, str]:
    _, payload, _ = _request("/ask", {"question": DEMO_REFUSAL})
    data = json.loads(payload)
    ok = data.get("answered") is False
    return ok, f"{DEMO_REFUSAL!r} -> answered={data.get('answered')} (want False)"


CHECKS = [
    ("Search index matches guides", check_index_fresh),
    ("Health answers HEAD", check_head),
    ("Server is warm", check_warm),
    ("Demo page loads", check_page),
    ("Demo question answers", check_demo_answer),
    ("Demo question refuses", check_demo_refusal),
]


def main() -> int:
    failures = 0
    for name, check in CHECKS:
        try:
            ok, detail = check()
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            ok, detail = False, f"request failed: {error}"
        if not ok:
            failures += 1
        print(f"{'PASS' if ok else 'FAIL'}  {name}\n      {detail}")

    print()
    if failures:
        print(f"{failures} check(s) failed — fix before recording.")
    else:
        print("All clear. Safe to record and send.")
    return failures


if __name__ == "__main__":
    raise SystemExit(1 if main() else 0)
