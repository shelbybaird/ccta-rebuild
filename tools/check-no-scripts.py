#!/usr/bin/env python3
"""Refuse to publish a reader-facing page that runs a script.

Every page a visitor opens on this site is markup and a stylesheet. Nothing on
one waits for a script to arrive, nothing breaks when a script fails to, and
nothing is slower because one is parsing while the reader waits. The calendar
grid, the collapsing menu, the townships row and the alert banner are all built
from what the browser already does.

That was true from the first commit and it stayed true because somebody was
paying attention each time. This makes it a property of the build instead:
adding a script to a reader-facing page now fails, and the failure is the
conversation about whether it is genuinely needed.

WHAT COUNTS. Any `script` element at all, whether it fetches a file or carries
the code between its tags. A `noscript` element is not a script and is fine.
A `link rel=modulepreload` is a fetch of a script and is caught here too.

WHY THIS IS SEPARATE FROM check-external-resources.py. That one asks WHOSE the
resource is, and passes anything served from this site. This one asks WHAT the
resource is, and does not care whose it is. A script hosted here would sail
through the other check untouched, which is exactly the gap this closes.

Run it by hand against a build directory:

    python3 tools/check-no-scripts.py public

Exit status is 0 when the build may be published and 1 when it may not.
"""

import sys
from html.parser import HTMLParser
from pathlib import Path

# The editing screens are not part of the website. They are reached only by
# somebody who has come to edit, they load their code by a decision recorded in
# their own file, and no visitor ever meets them. Exempted by PATH and never by
# what the page contains, so the exemption cannot spread.
EXEMPT_PATHS = ("admin/",)


class ScriptFinder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.found = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script":
            self.found.append(("script", a.get("src") or "written into the page"))
        elif tag == "link" and (a.get("rel") or "").lower() in ("modulepreload", "preload"):
            if (a.get("as") or "").lower() == "script" or (a.get("rel") or "").lower() == "modulepreload":
                self.found.append(("link", a.get("href") or "?"))


def main(argv):
    root = Path(argv[1] if len(argv) > 1 else "public")
    if not root.is_dir():
        print(f"::error::{root} is not a directory", file=sys.stderr)
        return 1

    pages, exempt_count, offences = [], 0, []
    for p in sorted(root.rglob("*.html")):
        rel = str(p.relative_to(root))
        if rel.startswith(EXEMPT_PATHS):
            exempt_count += 1
            continue
        pages.append(rel)
        f = ScriptFinder()
        f.feed(p.read_text(encoding="utf-8", errors="replace"))
        for tag, what in f.found:
            offences.append((rel, tag, what))

    # A check that examined nothing would otherwise pass, which is the way this
    # kind of guard usually fails.
    if not pages:
        print("::error::no pages were found, so nothing was checked", file=sys.stderr)
        return 1

    if offences:
        for page, tag, what in offences:
            print(f"::error file=public/{page}::<{tag}> {what}", file=sys.stderr)
        print(
            f"::error::{len(offences)} script(s) across {len(pages)} reader-facing pages. "
            "Every page here is markup and a stylesheet; if a script is genuinely "
            "needed, that is a decision to record rather than a line to add.",
            file=sys.stderr,
        )
        return 1

    print(f"{len(pages)} reader-facing pages carry no scripts. "
          f"{exempt_count} page(s) exempt: {', '.join(EXEMPT_PATHS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
