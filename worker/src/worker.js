/**
 * The worker's entry point, and the seam between two unrelated jobs.
 *
 * `index.js` is `sveltia-cms-auth`, somebody else's code, vendored unmodified
 * so that taking a newer version is a copy rather than a merge. It answers web
 * requests: it is what lets an officer sign in to the editor.
 *
 * `boundary.js` is ours. It answers a timer, and has nothing to do with signing
 * in. The two share a worker only because one worker is cheaper to operate and
 * to explain than two, and they are kept in separate files so that sharing an
 * address never becomes sharing a design.
 */

import broker from './index.js';
import { checkBoundary } from './boundary.js';

export default {
  fetch: broker.fetch,
  scheduled: checkBoundary,
};
