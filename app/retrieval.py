"""Find the guide section that answers a question.

Guides are split on their `##` headings, so one chunk is one problem. The
headings are phrased the way a person describes the symptom, which is what
makes them land close to a real question in embedding space.
"""

import re
from pathlib import Path

import chromadb

GUIDES_DIR = Path(__file__).parent.parent / "guides"
INDEX_DIR = Path(__file__).parent.parent / "chroma_db"
COLLECTION = "guides"


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


def build_index() -> int:
    """Embed every guide section. Returns the number of chunks indexed."""
    client = chromadb.PersistentClient(path=str(INDEX_DIR))
    client.get_or_create_collection(COLLECTION)
    client.delete_collection(COLLECTION)
    collection = client.create_collection(COLLECTION)

    chunks = all_chunks()
    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[{"guide": c["guide"], "heading": c["heading"]} for c in chunks],
    )
    return len(chunks)


def search(question: str, n: int = 3) -> list[dict[str, object]]:
    """Return the n closest guide sections, nearest first."""
    client = chromadb.PersistentClient(path=str(INDEX_DIR))
    collection = client.get_collection(COLLECTION)
    result = collection.query(query_texts=[question], n_results=n)
    return [
        {
            "text": text,
            "guide": meta["guide"],
            "heading": meta["heading"],
            "distance": distance,
        }
        for text, meta, distance in zip(
            result["documents"][0], result["metadatas"][0], result["distances"][0]
        )
    ]


if __name__ == "__main__":
    print(f"Indexed {build_index()} guide sections")
