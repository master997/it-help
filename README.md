# it-help

An internal IT helpdesk that answers colleagues' questions from written guides,
in Slack, and logs every question — including the ones it can't answer.

That last part is the point. The unanswered questions are a to-do list written
by your colleagues, telling you which guide to write next.

## What it looks like

Someone types this in any Slack channel:

```
/it-help my wifi keeps dropping
```

Two seconds later they get the actual steps from the Wi-Fi guide, with 👍 / 👎
buttons underneath. A ticket lands in `#it-tickets` at the same time, so IT can
see the queue without anyone filing anything.

If no guide covers the question, it says so plainly rather than inventing an
answer:

> I don't have a guide for this yet — I've logged it as ticket #7 so IT sees it.
> For anything urgent, post in #it-help.

## The guides come first

The five guides in [`guides/`](guides/) are the actual product — new joiner Mac
setup, passwords and logins, Wi-Fi and VPN, meeting room screens, lost laptop.
Everything else here is plumbing to get them to people faster.

They're written for someone stressed and non-technical, and two conventions in
them are load-bearing:

- **Headings are symptoms, in the words a person would use** — "My Wi-Fi keeps
  dropping", not "Wireless troubleshooting". People search with their own
  words, and it also makes retrieval more accurate (see below).
- **Every section stands alone.** Retrieval returns one section, not a whole
  document. A section that says "first do the thing above" produces an answer
  with a hole in it.

The [lost laptop guide](guides/lost-laptop.md) is the one worth reading — it
tells you to report before you search, explains why that instinct is backwards,
and says twice that nobody is in trouble. Someone who fears blame hides the
problem, so removing that fear is security work, not just tone.

Names, networks and URLs in the guides are placeholders — swap them for real
ones before use.

## The loop that makes it useful

Every question becomes a row: what was asked, what was retrieved, whether it
was answered, and any thumbs up/down.

```
python -m app.tickets report
```

```
Tickets: 12 total, 9 answered, 3 refused

Couldn't answer (write a guide for these):
  - 'printer wont print'  (closest match was: new-joiner-setup.md :: Something's gone wrong)

Answered but unhelpful (fix these guides):
  - 'wifi keeps cutting out'  (answered from: wifi-and-vpn.md :: My Wi-Fi keeps dropping)
```

Two failure modes, two different fixes. A refusal means a guide is missing. A
thumbs-down means a guide exists but isn't good enough. Recording *what was
retrieved* is what separates them — without it, a wrong answer and a missing
guide look identical.

## How it works

```
/it-help in Slack ─┐
                   ├─► FastAPI ─► retrieval ─► Gemini ─► answer
POST /voice/ask ───┘                                        │
                                                            ▼
                                              ticket logged + posted
                                                  to #it-tickets
```

The doors are deliberately thin. They take a question, hand it to the same
function, and deliver whatever comes back — so adding another one costs almost
nothing.

| File | Job |
|---|---|
| [`guides/`](guides/) | The knowledge. Plain markdown. |
| [`app/retrieval.py`](app/retrieval.py) | Splits guides into sections, finds the closest ones to a question. |
| [`app/brain.py`](app/brain.py) | Answers from those sections only, or returns `NO_GUIDE`. |
| [`app/server.py`](app/server.py) | Slack slash command, buttons, tickets, voice endpoint. |
| [`app/tickets.py`](app/tickets.py) | SQLite log and the write-this-next report. |
| [`tests/test_retrieval.py`](tests/test_retrieval.py) | Ten deliberately messy questions. |

## Engineering notes

**Why retrieval at all, when five guides fit in one prompt?** They do — the
first working version sent all 16KB of them with every question, and it worked
fine. Retrieval exists because a real IT team has 200 documents, not five, and
because sending only the relevant section costs ~70% fewer tokens per question.
At this size it's the pattern that matters, not the saving.

**ChromaDB came out.** The first version used it with a local embedding model.
On Render's free tier that meant every cold start booted a vector database,
downloaded a model, and re-embedded everything before serving a request — 90
seconds, on a container with 512MB of RAM. Embeddings are now computed once
(`python -m app.retrieval`) and committed as `index.json`; the server loads that
file and does the cosine similarity in plain Python. Cold start dropped to
0.2 seconds, and retrieval got *better* — the correct section is now the top hit
on all ten test questions, where the local model needed a wider net.

**`temperature=0`, set after a real bug.** The same question was answered
correctly on one run and refused on the next. A helpdesk that varies run to run
can't be tested or trusted. This buys consistent *behaviour*, not identical
wording — there's still nondeterminism below it.

**False refusals are the dangerous failure.** An invented answer is obviously
broken; "I don't have a guide for this" when a guide exists looks fine and
quietly sends someone to a human. That's why the log records what was
retrieved, and why the prompt says to answer from a section that only partly
covers the question.

## Running it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env`:

```
GEMINI_API_KEY=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
VOICE_API_KEY=...          # any random string; only needed for /voice/ask
```

Then:

```bash
python -m app.retrieval          # build index.json (only after editing guides)
python -m tests.test_retrieval   # ten messy questions, expects 10/10
python -m app.brain "my wifi keeps dropping"
uvicorn app.server:app --reload
```

For Slack, point a slash command at `POST /slack/commands` and interactivity at
`POST /slack/interactions`, with scopes `chat:write` and `commands`. Deploys to
Render from [`render.yaml`](render.yaml).

## Not built

- **Voice.** `POST /voice/ask` exists and works — it's the same brain with
  markdown stripped for speech, ready for a voice agent to call as a webhook
  tool. No agent is wired to it here.
- **Ticketing integration.** Tickets are SQLite plus a Slack channel. In
  production the same function would write to Jira, Linear, or ServiceNow.
- **Anything that changes state.** It reads guides and answers questions. It
  can't reset a password or unlock an account, deliberately.
