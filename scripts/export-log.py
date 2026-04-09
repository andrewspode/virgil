#!/usr/bin/env python3
"""
Export journal conversations from Claude Code JSONL session files
to clean, readable markdown logs — one file per date.

Reads the full JSONL history (capped at 30 days by Claude Code), groups
entries by date, and writes entries/YYYY/MM/YYYY-MM-DD.log.md for each.
Historical log files are skipped if their entry count already matches
the JSONL — so only today's file is typically rewritten on each run.

Filters out tool calls, thinking blocks, and subagent sidechains — leaving
only the real conversation between user and Claude.

Usage:
    python3 scripts/export-log.py        # normal (hook) usage
    python3 scripts/export-log.py --all  # force rewrite all dates
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, date, timedelta
from pathlib import Path


JOURNAL_DIR = Path(__file__).parent.parent.resolve()
_project_hash = str(JOURNAL_DIR).replace('/', '-')
PROJECT_DIR = Path.home() / '.claude' / 'projects' / _project_hash


def user_name():
    """Read the user's name from profile/stable.md, fallback to 'User'."""
    stable = JOURNAL_DIR / 'profile' / 'stable.md'
    if stable.exists():
        for line in stable.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if line.startswith('# '):
                name = line[2:].strip()
                if name:
                    return name
    return 'User'


def journal_date(dt):
    """Return the journal date for a datetime — days run 05:00 to 05:00."""
    if dt.hour < 5:
        return (dt - timedelta(days=1)).date()
    return dt.date()


def parse_timestamp(ts_str):
    """Parse ISO 8601 timestamp and convert to local time."""
    dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    return dt.astimezone()


def format_time(dt):
    """Format datetime as HH:MM."""
    return dt.strftime('%H:%M')


def extract_all_entries(project_dir):
    """
    Scan all JSONL files and return entries grouped by date.

    Returns dict[date, list[{dt, role, text}]]
    """
    by_date = defaultdict(list)

    for jsonl_path in sorted(project_dir.glob('*.jsonl')):
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if entry.get('isSidechain'):
                    continue

                ts_str = entry.get('timestamp', '')
                if not ts_str:
                    continue

                try:
                    dt = parse_timestamp(ts_str)
                except (ValueError, KeyError):
                    continue

                entry_type = entry.get('type')
                message = entry.get('message', {})
                content = message.get('content')

                if entry_type == 'user':
                    if isinstance(content, str) and content.strip():
                        text = content.strip()
                        if (text.startswith('<local-command-caveat>') or
                                text.startswith('<command-name>') or
                                text.startswith('<local-command-stdout>') or
                                text.startswith('<system-reminder>') or
                                text.startswith('<function_calls>')):
                            continue
                        by_date[journal_date(dt)].append({
                            'dt': dt,
                            'role': user_name(),
                            'text': text,
                        })

                elif entry_type == 'assistant':
                    if isinstance(content, list):
                        text_parts = [
                            block.get('text', '')
                            for block in content
                            if block.get('type') == 'text'
                        ]
                        combined = '\n\n'.join(p for p in text_parts if p.strip())
                        if combined.strip():
                            by_date[journal_date(dt)].append({
                                'dt': dt,
                                'role': 'Claude',
                                'text': combined.strip(),
                            })

    return by_date


def count_existing_entries(log_path):
    """Count the number of entries in an existing log file."""
    try:
        content = log_path.read_text(encoding='utf-8')
        return len(re.findall(r'^## \d{2}:\d{2} —', content, re.MULTILINE))
    except FileNotFoundError:
        return -1


def write_log(entries, target_date, journal_dir):
    """Write sorted entries to entries/YYYY/MM/YYYY-MM-DD.log.md."""
    entries.sort(key=lambda x: x['dt'])

    date_str = target_date.strftime('%Y-%m-%d')
    year = target_date.strftime('%Y')
    month = target_date.strftime('%m')

    output_dir = journal_dir / 'entries' / year / month
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f'{date_str}.log.md'

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f'# {date_str}\n\n')
        for entry in entries:
            time_str = format_time(entry['dt'])
            f.write(f"## {time_str} — {entry['role']}\n")
            f.write(entry['text'])
            f.write('\n\n')

    return output_path, len(entries)


def read_hook_payload():
    """Read Stop hook JSON payload from stdin if available."""
    import select
    try:
        if select.select([sys.stdin], [], [], 0)[0]:
            raw = sys.stdin.read()
            if raw.strip():
                return json.loads(raw)
    except Exception:
        pass
    return {}


def main():
    force_all = '--all' in sys.argv

    if not PROJECT_DIR.exists():
        print(f"Error: project directory not found: {PROJECT_DIR}", file=sys.stderr)
        sys.exit(1)

    hook_payload = read_hook_payload()
    last_assistant_message = hook_payload.get('last_assistant_message', '').strip()

    by_date = extract_all_entries(PROJECT_DIR)

    if not by_date:
        sys.exit(0)

    today = journal_date(datetime.now().astimezone())

    # Inject current assistant response into today's entries if not yet in JSONL
    if last_assistant_message:
        today_entries = by_date[today]
        already_present = any(
            e['role'] == 'Claude' and e['text'].strip() == last_assistant_message
            for e in today_entries
        )
        if not already_present:
            today_entries.append({
                'dt': datetime.now().astimezone(),
                'role': 'Claude',
                'text': last_assistant_message,
            })

    written = 0
    skipped = 0

    for entry_date, entries in sorted(by_date.items()):
        date_str = entry_date.strftime('%Y-%m-%d')
        year = entry_date.strftime('%Y')
        month = entry_date.strftime('%m')
        log_path = JOURNAL_DIR / 'entries' / year / month / f'{date_str}.log.md'

        # For historical dates, skip if the log already has the right entry count
        if not force_all and entry_date != today:
            existing = count_existing_entries(log_path)
            if existing == len(entries):
                skipped += 1
                continue

        write_log(entries, entry_date, JOURNAL_DIR)
        written += 1

    if written:
        print(f"Wrote {written} log file(s), skipped {skipped} unchanged.")
    elif skipped:
        print(f"All {skipped} log file(s) up to date.")


if __name__ == '__main__':
    main()
