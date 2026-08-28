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
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SITE_ZONE = ZoneInfo("America/New_York")

# Only these two dates move content in or out of the site. `date` is what a
# reader sees and what orders a list; it publishes nothing on its own.
BOUNDARY_KEYS = ("publishDate", "expiryDate")


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

    scanned = 0
    skipped_drafts = 0
    unreadable = []
    future = []

    for page in sorted(content.rglob("*.md")):
        scanned += 1
        fields = front_matter(page.read_text(encoding="utf-8", errors="replace"))
        # A draft is never published, so its dates move nothing and must not
        # cause a build. The alert banner sat as a draft carrying a live expiry
        # while this was written, which is exactly the case that matters.
        if fields.get("draft", "").lower() == "true":
            skipped_drafts += 1
            continue
        for key in BOUNDARY_KEYS:
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
