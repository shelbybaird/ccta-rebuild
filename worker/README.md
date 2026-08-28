# The CMS sign-in broker

This directory holds a small Cloudflare Worker whose only job is to let an
officer sign in to the content management system from the published website.

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

`GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` are set as encrypted secrets
against the deployed worker, by hand, through the Cloudflare dashboard. They are
not in this repository and must never be added to it — this repository is
public. A secret committed here is a secret published, and rotating it means
registering a new application on GitHub.

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
