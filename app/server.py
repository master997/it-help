"""The Slack door: /it-help slash command, tickets to #it-tickets, 👍/👎.

Slack's rules shape this file:
- Slash commands must get an HTTP response within 3 seconds. The LLM can take
  longer, so we acknowledge immediately and send the real answer to Slack's
  response_url from a background task.
- Every request from Slack is signed. We verify the signature so nobody can
  feed the bot fake requests just by finding the URL.
"""

import hashlib
import hmac
import json
import os
import time

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request

from app.brain import answer
from app.tickets import log_ticket, record_feedback

load_dotenv()

app = FastAPI()

TICKET_CHANNEL = "#it-tickets"

REFUSAL_REPLY = (
    "I don't have a guide for this yet — I've logged it as ticket #{tid} so "
    "IT sees it. For anything urgent, post in #it-help."
)


def _env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set — add it to .env")
    return value


def verify_slack_signature(body: bytes, timestamp: str, signature: str) -> None:
    """Reject anything not signed by our Slack app's signing secret."""
    if abs(time.time() - int(timestamp)) > 60 * 5:
        raise HTTPException(status_code=401, detail="Stale request")
    basestring = f"v0:{timestamp}:{body.decode()}".encode()
    expected = "v0=" + hmac.new(
        _env("SLACK_SIGNING_SECRET").encode(), basestring, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Bad signature")


def post_ticket_to_channel(tid: int, user: str, question: str, answered: bool) -> None:
    """Every ticket lands in #it-tickets so IT can see the queue live."""
    status = "answered" if answered else "NO GUIDE — needs one written"
    response = httpx.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {_env('SLACK_BOT_TOKEN')}"},
        json={
            "channel": TICKET_CHANNEL,
            "text": f"Ticket #{tid} from <@{user}>: “{question}” — {status}",
        },
        timeout=10,
    ).json()
    if not response.get("ok"):
        raise RuntimeError(f"Slack rejected ticket post: {response.get('error')}")


def answer_and_respond(question: str, user: str, response_url: str) -> None:
    """The slow part, run after the 3-second ack has already gone back."""
    result = answer(question)
    tid = log_ticket("slack", question, result)

    if result["answered"]:
        # Slack's mrkdwn uses *bold*, not markdown's **bold**.
        text = str(result["reply"]).replace("**", "*")
    else:
        text = REFUSAL_REPLY.format(tid=tid)

    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": text}},
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "👍 Helped"},
                    "action_id": "feedback_up",
                    "value": str(tid),
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "👎 Didn't help"},
                    "action_id": "feedback_down",
                    "value": str(tid),
                },
            ],
        },
    ]
    httpx.post(
        response_url,
        # replace_original=False is required: without it, Slack edits the
        # private "Looking that up…" message in place, and an edited
        # ephemeral message stays ephemeral no matter what response_type
        # says. This posts a genuinely new, genuinely public message.
        json={
            "response_type": "in_channel",
            "replace_original": False,
            "text": text,
            "blocks": blocks,
        },
        timeout=10,
    )
    post_ticket_to_channel(tid, user, question, bool(result["answered"]))


@app.post("/slack/commands")
async def slash_command(request: Request, background: BackgroundTasks):
    body = await request.body()
    verify_slack_signature(
        body,
        request.headers.get("X-Slack-Request-Timestamp", "0"),
        request.headers.get("X-Slack-Signature", ""),
    )
    form = dict(pair.split("=", 1) for pair in body.decode().split("&") if "=" in pair)
    question = httpx.QueryParams(body.decode()).get("text", "").strip()
    user = form.get("user_id", "unknown")
    response_url = httpx.QueryParams(body.decode()).get("response_url", "")

    if not question:
        return {"response_type": "ephemeral", "text": "Ask me something: `/it-help my wifi keeps dropping`"}

    background.add_task(answer_and_respond, question, user, response_url)
    # This ack is what beats Slack's 3-second timeout. It must be
    # in_channel: the ack's visibility anchors the whole exchange — an
    # ephemeral ack makes Slack hide the user's typed command AND keep
    # every follow-up on this response_url private, regardless of what
    # response_type the follow-up asks for.
    return {"response_type": "in_channel", "text": "Looking that up…"}


@app.post("/slack/interactions")
async def interactions(request: Request):
    """Slack sends button clicks here."""
    body = await request.body()
    verify_slack_signature(
        body,
        request.headers.get("X-Slack-Request-Timestamp", "0"),
        request.headers.get("X-Slack-Signature", ""),
    )
    payload = json.loads(httpx.QueryParams(body.decode()).get("payload", "{}"))
    action = payload["actions"][0]
    tid = int(action["value"])
    record_feedback(tid, "up" if action["action_id"] == "feedback_up" else "down")
    return {"text": "Thanks — noted."}


@app.post("/voice/ask")
async def voice_ask(request: Request):
    """The voice door: the ElevenLabs agent calls this as a webhook tool.

    Same brain, same ticket log as Slack — only the door differs.
    """
    if request.headers.get("X-Voice-Key", "") != _env("VOICE_API_KEY"):
        raise HTTPException(status_code=401, detail="Bad voice key")

    payload = await request.json()
    question = str(payload.get("question", "")).strip()
    if not question:
        raise HTTPException(status_code=400, detail="No question given")

    result = answer(question)
    tid = log_ticket("voice", question, result)

    if result["answered"]:
        # Spoken answers: no markdown symbols for the voice to read out.
        reply = str(result["reply"]).replace("**", "").replace("*", "")
    else:
        reply = (
            "I don't have a guide for that yet, so I've logged it as "
            f"ticket {tid} for the IT team. For anything urgent, post "
            "in the it-help channel."
        )
    return {"answer": reply}


@app.get("/health")
def health():
    return {"ok": True}
