#!/usr/bin/env python3
"""Refuse to publish a build that would fetch anything from another party.

Every page of this site is meant to load from this site alone. A picture, a
stylesheet, a font or a script served from somewhere else is requested by the
reader's browser the moment the page opens, without the reader choosing it and
before anything on the page could ask. That request carries their network
address, their browser, and the address of the page they are reading, and it
hands all of it to an operator the Association has no agreement with. The same
consideration retired the calendar embed.

A LINK IS NOT A RESOURCE and is not reported here. A link is followed only if
somebody decides to follow it, which is an ordinary thing to publish. Only
what the browser fetches on its own is in scope.

Run it by hand against a build directory:

    python3 tools/check-external-resources.py public

Exit status is 0 when the build may be published and 1 when it may not.
"""

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

# Attributes whose value the browser fetches without being asked. `href` is
# deliberately absent for `a`; it is handled per-tag below, because on `link`
# the same attribute name does fetch.
FETCHED = {
    "img": ("src", "srcset"),
    "script": ("src",),
    "link": ("href",),
    "iframe": ("src",),
    "frame": ("src",),
    "embed": ("src",),
    "object": ("data",),
    "source": ("src", "srcset"),
    "track": ("src",),
    "video": ("src", "poster"),
    "audio": ("src",),
    "input": ("src",),
    "use": ("href", "xlink:href"),
}

# Namespaces and vocabularies. These appear in attribute values as identifiers
# and are never fetched, so treating them as resources would report a defect
# that does not exist.
NEVER_FETCHED_VALUES = ("http://www.w3.org/", "https://schema.org", "http://schema.org")

# The editing tool is not part of the website. It is reached only by somebody
# who has come to edit, it carries a noindex tag, and it deliberately loads its
# code from a CDN — a decision recorded in static/admin/index.html together
# with the note to revisit it at hardening. The claim this check defends is
# about the pages a READER opens, so the editor is out of scope. Nothing else
# is exempt, and an exemption is a path, never a host: adding a host here would
# let the same third party appear on a page a visitor does see.
EXEMPT_PATHS = ("admin/",)


class ResourceCollector(HTMLParser):
    """Collects the addresses a page would fetch on its own."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.found = []

    def handle_starttag(self, tag, attrs):
        wanted = FETCHED.get(tag)
        if not wanted:
            return
        for name, value in attrs:
            if name not in wanted or not value:
                continue
            # srcset holds a comma-separated list of candidates, each of which
            # may carry a descriptor after a space.
            candidates = (
                [part.strip().split(" ")[0] for part in value.split(",")]
                if name == "srcset"
                else [value]
            )
            for candidate in candidates:
                if candidate:
                    self.found.append((tag, name, candidate))


def is_off_site(url, own_hosts):
    """True when a browser would fetch this from a host that is not ours."""
    if url.startswith(NEVER_FETCHED_VALUES):
        return False
    # A protocol-relative address inherits the page's scheme but not its host.
    if url.startswith("//"):
        host = urlparse("https:" + url).hostname
        return bool(host) and host.lower() not in own_hosts
    parsed = urlparse(url)
    if not parsed.scheme:
        return False  # relative, therefore ours
    if parsed.scheme in ("data", "mailto", "tel", "javascript", "about", "blob"):
        return False  # nothing is fetched from another party
    host = (parsed.hostname or "").lower()
    return bool(host) and host not in own_hosts


def main(argv):
    if len(argv) < 2:
        print("usage: check-external-resources.py <build-directory> [own-host ...]",
              file=sys.stderr)
        return 2

    root = Path(argv[1])
    own_hosts = {h.lower() for h in argv[2:]} or {
        "cctownship.org",
        "www.cctownship.org",
        "shelbybaird.github.io",
    }

    all_pages = sorted(root.rglob("*.html"))
    pages = [
        p for p in all_pages
        if not str(p.relative_to(root)).startswith(EXEMPT_PATHS)
    ]
    exempt_count = len(all_pages) - len(pages)
    offences = []
    resources_seen = 0

    for page in pages:
        collector = ResourceCollector()
        collector.feed(page.read_text(encoding="utf-8", errors="replace"))
        for tag, attr, url in collector.found:
            resources_seen += 1
            if is_off_site(url, own_hosts):
                offences.append((page.relative_to(root), tag, attr, url))

    # A check that examined nothing would otherwise report success, which is
    # the way this kind of guard usually fails.
    if not pages:
        print("::error::no pages were found, so nothing was checked", file=sys.stderr)
        return 1

    if offences:
        for page, tag, attr, url in offences:
            print(f"::error file=public/{page}::<{tag} {attr}> loads {url}", file=sys.stderr)
        print(
            f"::error::{len(offences)} off-site resource(s) across {len(pages)} pages. "
            "A reader opening these pages would be disclosed to another operator.",
            file=sys.stderr,
        )
        return 1

    print(f"{len(pages)} reader-facing pages carry {resources_seen} resources, all "
          f"served from {' or '.join(sorted(own_hosts))}. "
          f"{exempt_count} page(s) exempt: {', '.join(EXEMPT_PATHS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
