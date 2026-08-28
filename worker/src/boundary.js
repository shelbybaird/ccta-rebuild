/**
 * Ask for a build when a display window has opened or closed.
 *
 * Hugo applies `publishDate` and `expiryDate` while it builds. Nothing becomes
 * visible at two o'clock; it becomes visible in the first build after two
 * o'clock. So a notice written for Thursday, or one due to come down after the
 * meeting, does neither unless something asks for a build at the right time.
 *
 * GitHub's own scheduled trigger was that something, and it delivered one run
 * in seventeen on 27 August 2026 while reporting itself healthy. It was removed
 * rather than left believed. This replaces it from a different system, which is
 * the only honest way to replace it.
 *
 * ⛔ THE THING THIS DESIGN REFUSES TO DO IS TRUST ITS OWN REQUEST. A dispatch
 * answers 204, which means the request was accepted — NOT that a run was
 * created. Believing 204 would rebuild the same silent failure at a new
 * address. So nothing is remembered here and nothing is assumed: every fifteen
 * minutes the question is asked again from scratch, against what the site
 * actually published. If a dispatch quietly did nothing, the site's own
 * status file still says a boundary is overdue, and the next tick asks again.
 * Correctness is re-derived, not accumulated.
 *
 * Every branch that cannot establish that a build is due does nothing. An
 * unreachable site, an unreadable file, a date that will not parse: none of
 * them dispatch. The cost of wrongly doing nothing is that a notice is late
 * and the next tick tries again fifteen minutes later. The cost of wrongly
 * dispatching is an unbounded loop against somebody else's service.
 */

const API = 'https://api.github.com';

/** Requests to GitHub's API must identify themselves or are refused. */
const UA = 'ccta-rebuild-boundary-check';

/**
 * Read what the site last published about itself.
 * @param {string} url - Address of the status file.
 * @returns {Promise<object|null>} Parsed status, or null if it cannot be had.
 */
const readStatus = async (url) => {
  try {
    // Pages serves this with ten minutes of cache. Ticks are fifteen minutes
    // apart, so a cached copy is usually harmless — but immediately after a
    // build it would still describe the boundary that build just satisfied,
    // and this would ask for a second, pointless build. Read past the cache.
    const response = await fetch(url, { cf: { cacheTtl: 0, cacheEverything: false } });

    if (!response.ok) {
      console.warn(`status file answered ${response.status}; doing nothing`);

      return null;
    }

    return await response.json();
  } catch (error) {
    console.warn(`status file could not be read (${error}); doing nothing`);

    return null;
  }
};

/**
 * Whether a build is already queued or running.
 *
 * The workflow serializes on a concurrency group, so a second request while one
 * is in flight does not produce a second build — it displaces the one waiting.
 * Asking first is one request on the rare tick where a boundary has passed.
 * @param {object} env - Environment.
 * @returns {Promise<boolean|null>} True/false, or null if it cannot be told.
 */
const buildAlreadyUnderway = async (env) => {
  const { REPO, WORKFLOW_FILE, GITHUB_DISPATCH_TOKEN } = env;
  const url = `${API}/repos/${REPO}/actions/workflows/${WORKFLOW_FILE}/runs?per_page=10`;

  try {
    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${GITHUB_DISPATCH_TOKEN}`,
        Accept: 'application/vnd.github+json',
        'User-Agent': UA,
      },
    });

    if (!response.ok) {
      console.warn(`could not list runs: ${response.status}`);

      return null;
    }

    const { workflow_runs: runs = [] } = await response.json();

    return runs.some(({ status }) => status === 'queued' || status === 'in_progress');
  } catch (error) {
    console.warn(`could not list runs (${error})`);

    return null;
  }
};

/**
 * Ask for a build.
 * @param {object} env - Environment.
 * @returns {Promise<boolean>} Whether the request was accepted — which is not
 * the same as a run having been created, and is deliberately not relied upon.
 */
const requestBuild = async (env) => {
  const { REPO, WORKFLOW_FILE, REF, GITHUB_DISPATCH_TOKEN } = env;
  const url = `${API}/repos/${REPO}/actions/workflows/${WORKFLOW_FILE}/dispatches`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${GITHUB_DISPATCH_TOKEN}`,
        Accept: 'application/vnd.github+json',
        'Content-Type': 'application/json',
        'User-Agent': UA,
      },
      body: JSON.stringify({ ref: REF }),
    });

    if (!response.ok) {
      console.warn(`dispatch refused: ${response.status} ${await response.text()}`);

      return false;
    }

    return true;
  } catch (error) {
    console.warn(`dispatch failed (${error})`);

    return false;
  }
};

/**
 * The scheduled handler.
 * @param {object} event - Scheduled event.
 * @param {object} env - Environment variables and secrets.
 * @returns {Promise<void>} Nothing; every outcome is logged rather than thrown,
 * because a thrown scheduled handler is retried in ways that are harder to
 * reason about than simply waiting for the next tick.
 */
export const checkBoundary = async (event, env) => {
  const status = await readStatus(env.STATUS_URL);

  if (!status) {
    return;
  }

  const { nextBoundary: next, builtAt } = status;

  if (!next) {
    // Nothing on the site is waiting for a moment. Said out loud for the same
    // reason as below: silence must not be the sound of working correctly.
    console.log(`no boundary scheduled; site built ${builtAt}`);

    return;
  }

  const boundary = Date.parse(next);

  if (Number.isNaN(boundary)) {
    console.warn(`nextBoundary "${next}" could not be read; doing nothing`);

    return;
  }

  if (Date.now() < boundary) {
    // Said out loud on purpose. This is the answer on almost every tick, and
    // if it were silent then a timer that had stopped would look exactly like
    // a timer with nothing to do — which is the failure being corrected here.
    console.log(`nothing due; next boundary ${next}, site built ${builtAt}`);

    return;
  }

  // A moment has passed that the published site has not yet accounted for.
  const underway = await buildAlreadyUnderway(env);

  if (underway === null) {
    // Could not tell. Doing nothing costs fifteen minutes; dispatching blind
    // risks displacing a build that is already waiting to run.
    return;
  }

  if (underway) {
    console.log(`boundary ${next} passed; a build is already under way`);

    return;
  }

  const accepted = await requestBuild(env);

  console.log(
    `boundary ${next} passed (site last built ${builtAt}); ` +
      `build requested, accepted=${accepted}. Not treated as proof: if no run ` +
      `appears, status.json stays stale and the next tick asks again.`,
  );
};
