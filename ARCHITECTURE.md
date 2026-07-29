# How it works

```
                 ┌─────────────────────┐
   Slack         │                     │        guides/ (5 markdown files)
  /it-help ────► │   FastAPI server    │              │
                 │   (app/)            │              ▼
   Voice         │                     │ ────► the brain: find the right
  ElevenLabs ──► │   one endpoint      │       guide section, write an
   agent         │   per door          │       answer using ONLY that text
                 │                     │              │
                 └─────────┬───────────┘              │
                           │                          │
                           ▼                          ▼
                  tickets.db (SQLite)          answer goes back
                  + #it-tickets channel        to whoever asked
```

## The four pieces

1. **The guides** (`guides/`) — five markdown how-to docs. The knowledge.
   Everything else is plumbing to deliver these.
2. **The brain** (`app/`) — takes a messy human question, finds the right
   guide section, writes an answer from only that text. Refuses and logs
   when no guide covers it.
3. **The Slack door** — Slack pings our server when someone types
   `/it-help`. Server answers, posts a ticket to `#it-tickets`.
4. **The voice door** — an ElevenLabs agent that calls the same brain,
   so voice and Slack share one knowledge base and one ticket log.

## The loop that makes it real

Every question → a ticket row: what was asked, what was retrieved,
answered or refused, 👍/👎. The refused + 👎 list = which guide to
write next. The system improves on evidence, not guesses.
