# ccta-rebuild

Source for a rebuilt website for the **Clermont County Township Association**.

## This is not the live site

The Association's website is cctownship.org, which is served from elsewhere and
is unaffected by anything in this repository. What is here is a proposed
replacement that has not yet been presented to the membership. Nothing in it
should be treated as an Association publication, and content may be incomplete
while the work is under way.

## How it works

The site is built with Hugo from Markdown files in `content/`, and published as
static files. No page a visitor opens runs anything on a server.

`worker/` is the exception, and it is not part of the site. It is a small
service doing two things a set of static files cannot do for itself: it lets an
officer sign in to the editor, and it asks for a rebuild at the moments a page
would otherwise go stale — a notice due to start or stop showing, and a meeting
or event passing out of the calendar's list of what is coming up.
`worker/README.md` explains why each is necessary.

The calendar publishes twice from one set of content: as a page, and as
`calendar.ics`, which a calendar application can subscribe to. Both are built
from the meetings and the special events by `layouts/partials/occasions.html`,
which is the only place that knows about both types.
