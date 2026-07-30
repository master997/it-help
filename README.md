# it-help

An internal IT helpdesk that answers colleagues' questions from written guides —
by text or out loud — and logs every question, including the ones it can't answer.

That last part is the point. The unanswered questions are a to-do list written
by your colleagues, telling you which guide to write next.

**Try it: https://it-help-f8gb.onrender.com** — type a question, or press the
button in the corner and ask out loud. Try to catch it out; anything the guides
don't cover, it refuses rather than guessing.

## What it looks like

Three ways in, one brain behind all of them.

**In Slack**, someone types this in any channel:

```
/it-help my wifi keeps dropping
```

Two seconds later they get the actual steps from the Wi-Fi guide, with 👍 / 👎
buttons underneath. A ticket lands in `#it-tickets` at the same time, so IT can
see the queue without anyone filing anything.

**On the web page**, the same question typed into a box gets the same answer.

**Out loud**, an ElevenLabs voice agent takes the question, calls the same
lookup, and talks the person through it a step at a time. Voice matters more
than it looks: three of the five guides cover situations where the person has no
working computer — forgotten Mac password, lost laptop, lost phone so 2FA is
gone. Slack is unreachable in all three, because they're locked out of the
device it runs on. That's the out-of-band channel problem real IT teams keep a
phone line for.

If no guide covers the question, every door says so plainly rather than
inventing an answer:

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
/it-help in Slack ────────┐
web page (GET /)  ────────┼─► FastAPI ─► retrieval ─► Gemini ─► answer
voice agent (/voice/ask) ─┘                                       │
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
| [`app/server.py`](app/server.py) | Slack slash command, buttons, tickets, web page, voice endpoint. |
| [`app/demo.html`](app/demo.html) | The public try-it page. One file; loads the ElevenLabs widget for the voice door. |
| [`app/tickets.py`](app/tickets.py) | SQLite log and the write-this-next report. |
| [`tests/test_retrieval.py`](tests/test_retrieval.py) | Ten deliberately messy questions. |
| [`tests/preflight.py`](tests/preflight.py) | Smoke test against a running deployment. |

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

**The free tier sleeps, so it gets pinged.** Render spins a free service down
after ~15 minutes idle and takes 40–90 seconds to wake. Slack kills a slash
command after 3 seconds, and ElevenLabs webhook tools time out at 20 by
default — so a sleeping service breaks two of the three doors, and looks like a
configuration bug rather than a hosting one. An UptimeRobot monitor hits
`/health` every 5 minutes; a [GitHub Action](.github/workflows/keep-warm.yml)
does the same every 10 as a backup, though scheduled Actions drift by 15–30
minutes so it can't be the primary.

**A health check has to answer HEAD.** UptimeRobot reported the service down for
20 minutes while it was serving every real request fine. Uptime monitors default
to `HEAD` because it's cheaper, and the route only declared `GET`, so every check
got a 405. The pings were keeping it warm the whole time — only the reporting
was broken. Worth knowing because the failure is invisible from the inside:
every `GET` I tested by hand returned 200. `tests/preflight.py` now checks
`/health` with the same method the monitor uses.

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
python -m app.retrieval          # rebuild index.json — required after editing a guide
python -m tests.test_retrieval   # ten messy questions, expects 10/10
python -m tests.preflight        # smoke test — checks the deployed URL, or pass your own
python -m app.brain "my wifi keeps dropping"
python -m app.tickets report     # the write-this-next queue
uvicorn app.server:app --reload
```

**`python -m app.retrieval` is not optional after editing a guide.** The
embeddings live in `index.json`, so an edited guide with a stale index answers
from superseded text and nothing looks wrong. `tests/preflight.py` compares the
two and fails if they've drifted.

For Slack, point a slash command at `POST /slack/commands` and interactivity at
`POST /slack/interactions`, with scopes `chat:write` and `commands`. For voice,
an ElevenLabs agent calls `POST /voice/ask` as a webhook tool with an
`X-Voice-Key` header, and the widget on the page is scoped to this domain via
the agent's allowlist. Deploys to Render from [`render.yaml`](render.yaml).

## Not built

- **Ticketing integration.** Tickets are SQLite plus a Slack channel. In
  production the same function would write to Jira, Linear, or ServiceNow —
  ElevenLabs already ship ServiceNow and Zendesk connectors for agents, so the
  production path is one connector away.
- **A phone number.** The voice agent answers in the browser. Attaching a real
  number needs a paid tier plus Twilio, and it's the version that would matter
  most in practice — someone locked out of their laptop can't open a web page
  either.
- **Anything that changes state.** It reads guides and answers questions. It
  can't reset a password or unlock an account, deliberately.
