#!/usr/bin/env python3
"""Write the moment at which this site next needs rebuilding.

Hugo decides what to publish from the dates on a piece of content, but it
decides during a build. Nothing becomes visible at two o'clock; it becomes
visible in the first build after two o'clock. Something outside the site has
to notice the moment has arrived and ask for a build, and to do that cheaply
it needs one fact: when is the next such moment.

WHY THIS READS THE FILES RATHER THAN ASKING HUGO. Hugo cannot see the content
whose dates matter most. With `buildFuture` off, a page whose `publishDate` is
in the future is not built at all and appears in no collection, so a template
could never report the moment it is waiting for. The alert banner is likewise
absent from every collection: its section sets `build: {render: never}`. Both
were confirmed against this repository. Reading the front matter directly
avoids both blind spots and keeps the reading of a date in one place.

A DATE WITHOUT AN OFFSET IS EASTERN, because the site declares
`timeZone = "America/New_York"` and the editor writes dates without one. This
program resolves every date to an absolute moment and writes it out with its
offset, so that whatever reads the result cannot repeat the interpretation and
cannot get it wrong. A naked timestamp handed to JavaScript is read as UTC,
which in summer is four hours adrift.

    python3 tools/next-boundary.py content public/status.json
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SITE_ZONE = ZoneInfo("America/New_York")

# These two dates move content in or out of the site, on any page.
BOUNDARY_KEYS = ("publishDate", "expiryDate")

# ⭐ AND the days of a meeting or a special event, since the calendar was built.
# The calendar page and the home page divide what is happening now, what is
# coming up and what has already happened, and they divide on when each day
# begins and when the whole occasion is over. The moment either passes, a page
# that was correct becomes wrong, and stays wrong until something asks for a
# build. Those are exactly the boundaries this program exists to report.
#
# Only these two sections. An announcement's `date` is the day it was posted
# and still moves nothing; a minutes entry's is the day of the meeting it
# records, which is in the past by the time it is filed.
OCCASION_SECTIONS = ("meetings", "events")
OCCASION_KEY = "date"

# The most days any event is given, as in `layouts/partials/event-sessions.html`
# and the editor's preview, so that the three agree on its last day.
MAX_DAYS = 63

def front_matter(text):
    """Return the top-level scalars of a YAML front matter block.

    Deliberately shallow: only keys at column zero are read, so that a nested
    `src:` beneath `image:` cannot be mistaken for a field of the page. The
    three keys this program needs are all top-level scalars, and a real YAML
    parser is not available on every machine that may run this by hand.
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fields = {}
    for line in text[3:end].splitlines():
        if not line or line[0] in " \t#-":
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        value = value.strip().strip('"').strip("'")
        fields[key.strip()] = value
    return fields


def multi_day(text):
    """Return an event's `multiDay` group: its pattern, day count and further days.

    The one nested block this program reads. The editor writes it as

        multiDay:
          pattern: sameTime            or  pattern: eachDay
          day_count: 4                     more_days:
                                             - after: 1
                                               start: "08:00"
                                               end: "14:00"

    and nothing else in a page's front matter is nested under that key.
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    group, item = None, None
    for line in text[3:end].splitlines():
        if line and line[0] not in " \t":
            if group is not None:
                break
            if line.partition(":")[0].strip() == "multiDay":
                group = {"more_days": []}
            continue
        if group is None:
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            item = {}
            group["more_days"].append(item)
            stripped = stripped[2:].strip()
        key, sep, value = stripped.partition(":")
        if not sep:
            continue
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if item is not None and key in ("after", "start", "end"):
            item[key] = value
        elif key in ("pattern", "day_count"):
            group[key] = value
    return group or {}


def default_minutes(content):
    """The default length of a meeting or event, from the calendar settings."""
    path = content.parent / "data" / "calendar.yml"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return 90
    for line in lines:
        if line.startswith("defaultMinutes:"):
            try:
                return int(line.partition(":")[2].strip().strip('"').strip("'"))
            except ValueError:
                return 90
    return 90


def clock(value, day):
    """A time of day, "08:00" or "08:00:00", on the given date, or None."""
    parts = value.strip().split(":")
    try:
        hour, minute = int(parts[0]), int(parts[1])
        return datetime(day.year, day.month, day.day, hour, minute, tzinfo=SITE_ZONE)
    except (ValueError, IndexError):
        return None


def occasion_days(fields, text):
    """Each day of a meeting or event as (start, end-or-None), earliest first.

    Mirrors `layouts/partials/event-sessions.html`. Once an event is multi-day,
    its end describes the first day alone: only the time counts, on the start's
    own day. An end not after its start is no set end. Further days are counted
    from the first by calendar date, not by 24 hours, so that a clock time holds
    across a change to or from daylight saving time. Raises ValueError naming
    the first value that cannot be read.
    """
    first = as_moment(fields.get("date"))
    if first is None:
        raise ValueError(f"date: {fields.get('date')}")
    first_end = None
    if fields.get("end"):
        first_end = as_moment(fields["end"])
        if first_end is None:
            raise ValueError(f"end: {fields['end']}")
    group = multi_day(text)
    pattern = group.get("pattern")
    if first_end is not None:
        if pattern in ("sameTime", "eachDay"):
            closing = first.replace(hour=first_end.hour, minute=first_end.minute,
                                    second=first_end.second, microsecond=0)
            first_end = closing if closing > first else None
        elif first_end <= first:
            first_end = None
    days = [(first, first_end)]

    if pattern == "sameTime":
        try:
            count = int(group.get("day_count") or 1)
        except ValueError:
            raise ValueError(f"multiDay day_count: {group.get('day_count')}")
        for n in range(1, min(count, MAX_DAYS)):
            day = first.date() + timedelta(days=n)
            start = first.replace(year=day.year, month=day.month, day=day.day)
            end = None
            if first_end is not None:
                end = first_end.replace(year=day.year, month=day.month, day=day.day)
            days.append((start, end))

    elif pattern == "eachDay":
        previous = first.date()
        for item in group["more_days"]:
            try:
                after = max(1, int(item.get("after") or 1))
            except ValueError:
                raise ValueError(f"multiDay after: {item.get('after')}")
            day = previous + timedelta(days=after)
            previous = day
            if not item.get("start") or len(days) >= MAX_DAYS:
                continue
            start = clock(item["start"], day)
            if start is None:
                raise ValueError(f"multiDay day start: {item['start']}")
            end = None
            if item.get("end"):
                end = clock(item["end"], day)
                if end is None:
                    raise ValueError(f"multiDay day end: {item['end']}")
                if end <= start:
                    end = None
            days.append((start, end))

    return sorted(days, key=lambda day: day[0])


def as_moment(value):
    """Resolve a front-matter date to an absolute moment, or None."""
    if not value:
        return None
    text = value.strip().replace(" ", "T", 1) if " " in value else value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.fromisoformat(text + "T00:00:00")
        except ValueError:
            return None
    # A date Hugo would read in the site's zone must be read the same way here.
    return parsed.replace(tzinfo=SITE_ZONE) if parsed.tzinfo is None else parsed


def main(argv):
    if len(argv) < 3:
        print("usage: next-boundary.py <content-dir> <output-file>", file=sys.stderr)
        return 2

    content, out = Path(argv[1]), Path(argv[2])
    now = datetime.now(SITE_ZONE)
    length = timedelta(minutes=default_minutes(content))

    scanned = 0
    skipped_drafts = 0
    unreadable = []
    future = []

    for page in sorted(content.rglob("*.md")):
        scanned += 1
        text = page.read_text(encoding="utf-8", errors="replace")
        fields = front_matter(text)
        # A draft is never published, so its dates move nothing and must not
        # cause a build. The alert banner sat as a draft carrying a live expiry
        # while this was written, which is exactly the case that matters.
        if fields.get("draft", "").lower() == "true":
            skipped_drafts += 1
            continue
        keys = list(BOUNDARY_KEYS)
        # `page` is under the content directory given on the command line, so
        # the section is the first part of the path relative to it.
        parts = page.relative_to(content).parts
        if parts and parts[0] in OCCASION_SECTIONS and fields.get(OCCASION_KEY):
            # Every day's start, and the moment the whole occasion is over: the
            # last day's end, or its start plus the default length. The section
            # index files carry no date and are passed over by the test above.
            try:
                days = occasion_days(fields, text)
            except ValueError as err:
                unreadable.append(f"{page}: {err}")
                continue
            last_start, last_end = days[-1]
            moments = [start for start, _ in days] + [last_end or last_start + length]
            future.extend(moment for moment in moments if moment > now)

        for key in keys:
            raw = fields.get(key)
            if not raw:
                continue
            moment = as_moment(raw)
            if moment is None:
                unreadable.append(f"{page}: {key}: {raw}")
                continue
            if moment > now:
                future.append(moment)

    # A date nobody can read is worse than no date: the content would move
    # without anything expecting it to. Refuse rather than report a boundary
    # that silently omits it.
    if unreadable:
        for item in unreadable:
            print(f"::error::unreadable date - {item}", file=sys.stderr)
        return 1

    if scanned == 0:
        print("::error::no content files were found, so nothing was scanned",
              file=sys.stderr)
        return 1

    nxt = min(future) if future else None
    status = {
        "builtAt": now.isoformat(timespec="seconds"),
        "nextBoundary": nxt.isoformat(timespec="seconds") if nxt else None,
        "boundaryCount": len(future),
        "filesScanned": scanned,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")

    print(f"scanned {scanned} files ({skipped_drafts} drafts skipped); "
          f"{len(future)} future boundary(ies); next: {status['nextBoundary']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
