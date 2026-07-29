"""Find the guide section that answers a question.

Guides are split on their `##` headings, so one chunk is one problem. The
headings are phrased the way a person describes the symptom, which is what
makes them land close to a real question in embedding space.

Embeddings are computed once by running `python -m app.retrieval` and
committed as index.json. The server only loads that file and does the
similarity maths itself, so a cold start costs milliseconds rather than
booting a vector database and downloading a model.
"""

import json
import math
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GUIDES_DIR = Path(__file__).parent.parent / "guides"
INDEX_FILE = Path(__file__).parent.parent / "index.json"
EMBED_MODEL = "gemini-embedding-001"
# 768 instead of the full 3072: a quarter of the file size for no measurable
# loss on a corpus this small.
DIMENSIONS = 768


def chunk(markdown: str, filename: str) -> list[dict[str, str]]:
    """Split one guide into a chunk per `##` section."""
    title_match = re.search(r"^# (.+)$", markdown, re.MULTILINE)
    if not title_match:
        raise ValueError(f"{filename} has no `# ` title line")
    title = title_match.group(1)

    parts = re.split(r"^## ", markdown, flags=re.MULTILINE)
    chunks = []

    # Text between the title and the first `##` — often the most important
    # instruction in the guide. Dropping it would silently unindex it.
    intro = re.sub(r"^# .+$", "", parts[0], flags=re.MULTILINE).strip()
    intro = re.sub(r"^> .*$", "", intro, flags=re.MULTILINE).strip()
    if intro:
        chunks.append(
            {
                "id": f"{filename}::intro",
                "text": f"{title} — read this first\n{intro}",
                "guide": filename,
                "heading": "read this first",
            }
        )

    for section in parts[1:]:
        heading, _, body = section.partition("\n")
        chunks.append(
            {
                "id": f"{filename}::{heading.strip()}",
                # The embedded text carries the guide title and the symptom
                # heading, so a question matches on both topic and problem.
                "text": f"{title} — {heading.strip()}\n{body.strip()}",
                "guide": filename,
                "heading": heading.strip(),
            }
        )
    return chunks


def all_chunks() -> list[dict[str, str]]:
    paths = sorted(GUIDES_DIR.glob("*.md"))
    if not paths:
        raise FileNotFoundError(f"No guides found in {GUIDES_DIR}")
    return [c for p in paths for c in chunk(p.read_text(), p.name)]


def _unit(vector: list[float]) -> list[float]:
    """Scale to length 1 so a dot product is the cosine similarity."""
    length = math.sqrt(sum(v * v for v in vector))
    if length == 0:
        raise ValueError("Embedding has zero length")
    return [v / length for v in vector]


def _embed(texts: list[str], task_type: str) -> list[list[float]]:
    """Turn text into vectors. Guides and questions use different task
    types — the model places a question near the passage that answers it,
    not near other questions."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.embed_content(
        model=EMBED_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type=task_type, output_dimensionality=DIMENSIONS
        ),
    )
    return [_unit(e.values) for e in response.embeddings]


def build_index() -> int:
    """Embed every guide section and write index.json. Run after editing
    a guide; the result is committed so the server never rebuilds it."""
    chunks = all_chunks()
    vectors = _embed([c["text"] for c in chunks], "RETRIEVAL_DOCUMENT")
    INDEX_FILE.write_text(
        json.dumps([{**c, "vector": v} for c, v in zip(chunks, vectors)])
    )
    return len(chunks)


def search(question: str, n: int = 6) -> list[dict[str, object]]:
    """Return the n closest guide sections, nearest first."""
    if not INDEX_FILE.exists():
        raise FileNotFoundError(
            f"{INDEX_FILE} missing — run `python -m app.retrieval` to build it"
        )
    index = json.loads(INDEX_FILE.read_text())
    query = _embed([question], "RETRIEVAL_QUERY")[0]

    scored = [
        (sum(a * b for a, b in zip(query, entry["vector"])), entry)
        for entry in index
    ]
    scored.sort(key=lambda pair: pair[0], reverse=True)

    return [
        {
            "text": entry["text"],
            "guide": entry["guide"],
            "heading": entry["heading"],
            # Kept as a distance (lower is closer) so callers read the same
            # way they did when this was a vector database.
            "distance": 1 - similarity,
        }
        for similarity, entry in scored[:n]
    ]


if __name__ == "__main__":
    print(f"Indexed {build_index()} guide sections into {INDEX_FILE.name}")
