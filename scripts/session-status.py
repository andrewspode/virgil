#!/usr/bin/env python3
"""
Session status check for the Virgil journal.

Outputs current date/time, lists any missing summaries for completed periods,
and lists which files Claude should read at the start of a fresh session.

Called via the UserPromptSubmit hook on every message.
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

JOURNAL_DIR = Path(__file__).parent.parent.resolve()
ENTRIES_DIR = JOURNAL_DIR / 'entries'
SUMMARIES_DIR = JOURNAL_DIR / 'summaries'


def iso_week_bounds(d):
    """Return (monday, sunday) for the ISO week containing date d."""
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def week_label(d):
    """Return 'week-YYYY-WNN' label for the week containing date d."""
    iso = d.isocalendar()
    return f'week-{iso[0]}-W{iso[1]:02d}'


def all_log_dates():
    """Return sorted list of dates that have a .log.md file."""
    dates = []
    for log_path in ENTRIES_DIR.glob('*/*/*.log.md'):
        try:
            d = date.fromisoformat(log_path.stem.replace('.log', ''))
            dates.append(d)
        except ValueError:
            continue
    return sorted(dates)


def daily_summary_path(d):
    return SUMMARIES_DIR / d.strftime('%Y') / d.strftime('%m') / f'{d.strftime("%Y-%m-%d")}.summary.md'


def weekly_summary_path(d):
    iso = d.isocalendar()
    return SUMMARIES_DIR / str(iso[0]) / f'week-{iso[0]}-W{iso[1]:02d}.md'


def monthly_summary_path(d):
    return SUMMARIES_DIR / d.strftime('%Y') / f'{d.strftime("%Y-%m")}.md'


def quarterly_summary_path(d):
    q = (d.month - 1) // 3 + 1
    return SUMMARIES_DIR / d.strftime('%Y') / f'{d.strftime("%Y")}-Q{q}.md'


def yearly_summary_path(d):
    return SUMMARIES_DIR / d.strftime('%Y') / f'{d.strftime("%Y")}.md'



def journal_today():
    """Current journal date — days run 05:00 to 05:00."""
    now = datetime.now().astimezone()
    if now.hour < 5:
        return (now - timedelta(days=1)).date()
    return now.date()


def main():
    today = journal_today()
    monday, sunday = iso_week_bounds(today)


    log_dates = all_log_dates()
    if not log_dates:
        return

    missing = []

    # Check daily summaries for all log dates before today
    missing_daily = []
    for d in log_dates:
        if d >= today:
            continue
        if not daily_summary_path(d).exists():
            missing_daily.append(d.strftime('%Y-%m-%d'))

    # Check weekly summaries for complete weeks (weeks that ended before today)
    seen_weeks = set()
    missing_weekly = []
    for d in log_dates:
        _, sun = iso_week_bounds(d)
        if sun >= today:
            continue  # week not yet complete
        wlabel = week_label(d)
        if wlabel in seen_weeks:
            continue
        seen_weeks.add(wlabel)
        if not weekly_summary_path(d).exists():
            missing_weekly.append(wlabel)

    # Check monthly summaries for complete months
    seen_months = set()
    missing_monthly = []
    for d in log_dates:
        month_key = d.strftime('%Y-%m')
        if month_key in seen_months:
            continue
        # Month is complete if we're now in a later month
        month_end = date(d.year, d.month, 1)
        if d.month == 12:
            next_month = date(d.year + 1, 1, 1)
        else:
            next_month = date(d.year, d.month + 1, 1)
        if today < next_month:
            continue
        seen_months.add(month_key)
        if not monthly_summary_path(d).exists():
            missing_monthly.append(month_key)

    # Check quarterly summaries for complete quarters
    seen_quarters = set()
    missing_quarterly = []
    for d in log_dates:
        q = (d.month - 1) // 3 + 1
        qkey = f'{d.year}-Q{q}'
        if qkey in seen_quarters:
            continue
        quarter_end_month = q * 3
        if d.month == 12:
            next_quarter = date(d.year + 1, 1, 1)
        else:
            next_quarter = date(d.year, quarter_end_month + 1, 1)
        if today < next_quarter:
            continue
        seen_quarters.add(qkey)
        if not quarterly_summary_path(d).exists():
            missing_quarterly.append(qkey)

    missing = []
    if missing_daily:
        missing.append(f'daily: {", ".join(missing_daily)}')
    if missing_weekly:
        missing.append(f'weekly: {", ".join(missing_weekly)}')
    if missing_monthly:
        missing.append(f'monthly: {", ".join(missing_monthly)}')
    if missing_quarterly:
        missing.append(f'quarterly: {", ".join(missing_quarterly)}')

    if missing:
        print('Summaries needed: ' + '; '.join(missing))
        sys.exit(1)


if __name__ == '__main__':
    main()
