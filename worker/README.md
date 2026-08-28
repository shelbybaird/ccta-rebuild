# The sign-in broker, and the timer

This directory holds a small Cloudflare Worker doing two unrelated jobs. It
answers web requests, which is how an officer signs in to the content
management system from the published website. It also answers a timer, which is
how a notice written for Thursday appears on Thursday.

They share a worker because one is cheaper to operate and to explain than two,
and they are kept in separate files so that sharing an address never becomes
sharing a design. `src/worker.js` is the seam.

## Why it has to exist

Sveltia CMS reads and writes the site's content through GitHub. To do that on
someone's behalf it needs a GitHub access token, and GitHub will only hand one
over in exchange for an authorization code sent together with a client secret.
A secret cannot live in a web page, and GitHub does not support the browser-only
sign-in method (PKCE) that would remove the need for one. So the exchange has to
happen on a server. This worker is that server, and it is small on purpose: it
holds the secret, performs the exchange, and hands the resulting token back to
the page that asked for it.

The only alternative Sveltia offers is for every officer to generate a personal
access token by hand and paste it in. That is a reasonable thing to ask of a
developer and an unreasonable thing to ask of a volunteer secretary.

## Where the code came from

`src/index.js` is `sveltia-cms-auth`, published by the author of Sveltia CMS
under the MIT license, vendored here unmodified at upstream commit `25f56e1`
(2026-08-21). `LICENSE.txt` is upstream's and stays with it.

It is copied in rather than depended on because the same worker is expected to
grow a second, unrelated job later: waking the site's build when a notice is due
to start or stop showing. Keeping the source here means that change is an
ordinary edit in this repository rather than a fork of somebody else's.

## What is configured where

`wrangler.toml` carries `ALLOWED_DOMAINS`, which is the setting that decides who
may obtain a token through this worker. It is committed because it is not a
secret and because its value should be visible to anyone reading the site's
source.

`GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` and `GITHUB_DISPATCH_TOKEN` are set
as encrypted secrets
against the deployed worker, by hand, through the Cloudflare dashboard. They are
not in this repository and must never be added to it — this repository is
public. A secret committed here is a secret published, and rotating it means
registering a new application on GitHub.

## The second job: asking for a build when a moment arrives

Hugo applies a display window while it builds. Nothing becomes visible at two
o'clock; it becomes visible in the first build after two o'clock. GitHub's own
scheduled trigger was what asked for those builds, and on 27 August 2026 it
delivered one run in seventeen while reporting itself healthy. It was removed
rather than left believed, and this replaces it from a different system, which
is the only honest way to replace something that failed silently.

Every fifteen minutes the worker reads `status.json`, which the site publishes
about itself, and which names the next moment at which the site will need
rebuilding. On almost every tick the answer is "not yet" and nothing further
happens. When a moment has passed, the worker checks whether a build is already
running and, if not, asks for one.

**It does not trust its own request.** A dispatch answers 204, meaning the
request was accepted — not that a run was created. Believing that would rebuild
the same silent failure at a new address. So the worker remembers nothing:
every tick asks the question again against what the site actually published. If
a request quietly did nothing, `status.json` still shows the boundary overdue,
and the next tick asks again. Correctness is re-derived rather than
accumulated, which also means the worker recovers by itself from a tick that
never ran.

Every branch that cannot establish that a build is due does nothing at all — an
unreachable site, an unreadable file, a date that will not parse. Wrongly doing
nothing costs fifteen minutes. Wrongly asking risks an unbounded loop against
somebody else's service.

One consequence worth stating plainly: a build that fails for a reason that
will not go away is asked for again every fifteen minutes until somebody fixes
it. That is deliberate. The alternative is to give up quietly, which is the
behavior this whole arrangement exists to eliminate.

## Deploying

    npx wrangler deploy

from inside this directory. The worker answers at

    https://sveltia-cms-auth.cctownship.workers.dev

and the content management system is pointed at it by `backend.base_url` in the
site's CMS configuration.

## Checking that it works

Two routes matter. `/auth` starts the flow and should redirect to GitHub.
`/callback` finishes it. Anything else returns 404, which is the correct answer
and not a sign of a broken deployment.

A request to `/auth` carrying a `site_id` that is not one of `ALLOWED_DOMAINS`
must be refused. That refusal is the whole point of the setting, so it is worth
provoking once deliberately rather than assuming it works.
