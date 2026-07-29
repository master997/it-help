"""Answer an IT question from the written guides, via retrieval.

Flow: embed the question -> pull the 3 closest guide sections -> ask the
model to answer from only those sections, or refuse with NO_GUIDE.
"""

import os
import sys

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.retrieval import search

load_dotenv()

MODEL = "gemini-3.5-flash-lite"
REFUSAL = "NO_GUIDE"

PROMPT = """You are the IT helpdesk for a company. Answer the question using \
ONLY the guide sections below.

Rules:
- Use only what the sections say. Never add steps from your own knowledge, \
and never invent a URL, tool name, or channel name.
- If any section is relevant, answer from it, even if it only partly covers \
the question.
- Reply with exactly NO_GUIDE only when no section is relevant at all.
- Write to someone stressed and non-technical. Short numbered steps, plain \
words, no jargon.
- Keep it to the steps that answer this specific question.
- Start with the first step. No preamble, no sign-off, no reassurance the \
sections do not themselves give.

GUIDE SECTIONS:
{sections}

QUESTION: {question}
"""


def answer(question: str) -> dict[str, object]:
    """Returns the reply plus what was retrieved, for the ticket log."""
    hits = search(question, n=4)
    sections = "\n\n".join(f"--- {h['guide']} :: {h['heading']} ---\n{h['text']}" for h in hits)

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=MODEL,
        contents=PROMPT.format(sections=sections, question=question),
        # Same question must give the same behaviour — a helpdesk that varies
        # run to run is impossible to test or trust.
        config=types.GenerateContentConfig(temperature=0),
    )
    text = response.text.strip()
    return {
        "answered": text != REFUSAL,
        "reply": text,
        "retrieved": [f"{h['guide']} :: {h['heading']}" for h in hits],
        "best_distance": hits[0]["distance"],
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit('Usage: python -m app.brain "your question here"')
    result = answer(" ".join(sys.argv[1:]))
    print(result["reply"])
    print(f"\n[retrieved: {result['retrieved'][0]} | distance {result['best_distance']:.2f}]")
