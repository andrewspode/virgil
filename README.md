# Virgil

A journalling companion built on [Claude Code](https://claude.ai/code). Named after
the guide in Dante's Inferno — someone who knows you well enough to be honest with you.

Virgil is a conversational daily journal. You talk to it like a person. It's designed
for the long haul — conversations that span months and years, not just days. It
remembers what you've said across sessions by keeping full logs and building summaries
over time, so context accumulates rather than disappearing with each new conversation.

A key part of the design is that you can wipe the context window at any point and
start fresh — Virgil reads back through its summaries at the start of each session
and picks up exactly where you left off. This keeps conversations lightweight rather
than carrying months of history in every exchange.

It's intentionally non-prescriptive: use it however suits you, though it was designed
with daily journalling in mind.

---

## Why?

I started talking to Claude in the evenings to work through how my day had gone.
After a few days it began tying things together in ways I found genuinely useful —
noticing patterns, connecting threads, pushing back when I was being too hard on
myself or not hard enough.

I started weaving in philosophy too, and it began connecting ideas from Stoicism or
Kant directly to things happening in my life. A surprisingly good way to actually
learn something rather than just read about it.

The problem was context. Claude's web chat gets progressively slower as a conversation
grows, and it's just not built for something that runs for months. By the time I'd
been using it for a few weeks, each response was taking long enough to be genuinely
frustrating.

So I asked Claude to pick a name for itself (Virgil), and then built this.

---

## How It Works

Virgil runs as a Claude Code project in a git repository. Three things make it work:

**1. Logs**
Claude Code stores conversations in JSONL format in `~/.claude/`. A hook processes
this after every message and keeps `entries/YYYY/MM/YYYY-MM-DD.log.md` up to date —
one file per journal day, containing everything you said and everything Virgil said,
timestamped.

**2. Recursive summarisation**
Above the raw logs sits a hierarchy of summaries:

```
entries/YYYY/MM/YYYY-MM-DD.log.md     ← full verbatim logs
summaries/YYYY/MM/YYYY-MM-DD.summary.md  ← daily
summaries/YYYY/week-YYYY-WNN.md          ← weekly
summaries/YYYY/YYYY-MM.md               ← monthly
summaries/YYYY/YYYY-QN.md               ← quarterly
summaries/YYYY/YYYY.md                  ← yearly
```

Each tier is distilled from the tier below. When Virgil starts a new session, it reads
backwards from today at the finest resolution available — daily summaries for the last
week, then weekly, then monthly — so it's oriented without reading everything from
scratch. Summaries are generated automatically when they're missing.

**3. Stable profile**
`profile/stable.md` holds facts that don't change quickly: your name, pronouns, key
people in your life, significant ongoing threads. This is what Virgil reads first in
every session. It grows naturally over time as you talk.

**The journal day runs 05:00 to 05:00**, not midnight to midnight. A late-night session
and an early-morning one on the same calendar day are treated as a single journal day.

---

## Setup

### Prerequisites

- [Claude Code](https://claude.ai/code) installed and authenticated
- Python 3.11+
- Git

### Steps

1. **Clone this repository** somewhere on your machine — e.g. `~/journal`.

2. **Open the project in Claude Code.** Navigate to your journal directory and run
   `claude` (or open it from the Claude Code desktop app).

3. **Follow the first-run conversation.** Virgil will introduce itself, explain how
   the system works, ask for your name and pronouns, and offer to help with any
   initial setup — including importing an existing conversation and adjusting the
   journal day boundary if the default (05:00) doesn't suit you.

That's it. All paths are computed automatically. The timezone is read from your system.

---

## Importing an Existing Claude.ai Conversation

If you've been journalling in Claude.ai and don't want to lose that history, you can
import it before your first Claude Code session.

1. Open the conversation in Claude.ai and use the **Share** button to create a shared
   link.

2. Open that link in your browser, then open the browser's **developer tools**
   (F12 / Cmd+Option+I) and go to the **Network** tab.

3. Reload the page. Filter the requests for `.json` or look for a request that returns
   a large JSON payload — it will contain a `chat_messages` array. Download or copy
   this file and save it as `import/import.json` in your journal directory.

4. Run the import script — either ask Virgil to do it for you, or run it directly:
   ```bash
   python3 scripts/import-claude-ai.py
   ```
   This will create log files in `entries/` for each day in the conversation, in the
   same format as the live export. The imported logs will be picked up by the
   summarisation system automatically.

   You can also pass a path explicitly:
   ```bash
   python3 scripts/import-claude-ai.py path/to/export.json
   ```

> **Note:** The import script labels messages with your name (read from
> `profile/stable.md`) and "Claude". Run the first-run setup before importing so your
> name is already set correctly.

---

## Repository Structure

```
.claude/
  settings.json        ← Claude Code hooks configuration
entries/               ← Full verbatim conversation logs (gitignored or not — your call)
profile/
  stable.md            ← Persistent facts about you and your life
prompts/
  summarise.md         ← Sub-agent prompt for generating summaries
scripts/
  export-log.py        ← Exports Claude Code sessions to log files (runs at the end of every message)
  import-claude-ai.py  ← One-time import of Claude.ai conversation history
  session-status.py    ← Checks for missing summaries (runs at the start of every message)
  summarise-hook.sh    ← Shell wrapper for session-status.py
summaries/             ← Generated summary hierarchy
CLAUDE.md              ← Virgil's instructions (this is what shapes the companion)
```

---

## Making Changes

Virgil is released under the MIT licence — fork it, modify it, make it your own.

A few things worth knowing:

**Hook changes require a session restart.** If you edit `.claude/settings.json`,
the changes won't take effect until you close and reopen the Claude Code session.

**Deleting entries or summaries is safe.** If you're not happy with how summaries
are turning out, delete them and adjust `prompts/summarise.md`, then start a new
session — they'll be regenerated automatically. If you have a lot of history, Virgil
will process them in weekly batches so it doesn't try to do everything at once.

**`CLAUDE.md` is where the personality lives.** Tone, behaviour, how Virgil responds
to difficult conversations — all of that is just text you can edit. Changes take
effect immediately in the next session.

---

## Privacy

Your entries and summaries are local files in a git repository. They go where you put
them. If you push to a remote, make sure it's private — this is personal data.
