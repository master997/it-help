"""Ten messy questions, phrased the way a stressed person would type them.

Run: python -m tests.test_retrieval

Each case asserts the right guide appears in what retrieval hands the model.
Slang ("nicked"), typos, and missing punctuation are deliberate — those are
the questions that break naive keyword search.
"""

from app.retrieval import search

CASES = [
    ("my wifi keeps cutting out", "wifi-and-vpn.md"),
    ("the meeting room screen wont connect", "meeting-room-screens.md"),
    ("someone nicked my laptop", "lost-laptop.md"),
    ("i cant get into 1password", "passwords-and-logins.md"),
    ("just started today what do i do with my mac", "new-joiner-setup.md"),
    ("no sound coming through the tv in the boardroom", "meeting-room-screens.md"),
    ("i think someone got my password", "passwords-and-logins.md"),
    ("left my laptop in an uber", "lost-laptop.md"),
    ("cant reach the internal dashboard from home", "wifi-and-vpn.md"),
    ("how do i install slack on my new machine", "new-joiner-setup.md"),
]


def run() -> int:
    failures = 0
    for question, expected in CASES:
        hits = search(question, n=6)
        guides = [h["guide"] for h in hits]
        ok = expected in guides
        if not ok:
            failures += 1
        mark = "PASS" if ok else "FAIL"
        print(f"{mark}  {question!r}")
        print(f"      top: {hits[0]['guide']} :: {hits[0]['heading']}")
        if not ok:
            print(f"      expected {expected}, got {guides}")
    print(f"\n{len(CASES) - failures}/{len(CASES)} passed")
    return failures


if __name__ == "__main__":
    raise SystemExit(1 if run() else 0)
