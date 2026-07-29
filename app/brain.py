"""Answer an IT question using the written guides as the only source."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GUIDES_DIR = Path(__file__).parent.parent / "guides"
MODEL = "gemini-3.5-flash-lite"

PROMPT = """You are the IT helpdesk for a company. Answer the question using \
ONLY the guides below.

Rules:
- Use only what the guides say. Never add steps from your own knowledge, and \
never invent a URL, tool name, or channel name.
- If any guide section is relevant, answer from it, even if it only partly \
covers the question.
- Reply with exactly NO_GUIDE only when no section is relevant at all.
- Write to someone stressed and non-technical. Short numbered steps, plain \
words, no jargon.
- Keep it to the steps that answer this specific question.
- Start with the first step. No preamble, no sign-off, no reassurance the \
guide does not itself give.

GUIDES:
{guides}

QUESTION: {question}
"""


def load_guides() -> str:
    """Read every guide into one string, each labelled with its filename."""
    paths = sorted(GUIDES_DIR.glob("*.md"))
    if not paths:
        raise FileNotFoundError(f"No guides found in {GUIDES_DIR}")
    return "\n\n".join(f"--- {p.name} ---\n{p.read_text()}" for p in paths)


def answer(question: str) -> str:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=MODEL,
        contents=PROMPT.format(guides=load_guides(), question=question),
        # Same question must give the same answer — a helpdesk that varies
        # run to run is impossible to test or trust.
        config=types.GenerateContentConfig(temperature=0),
    )
    return response.text.strip()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit('Usage: python app/brain.py "your question here"')
    print(answer(" ".join(sys.argv[1:])))
