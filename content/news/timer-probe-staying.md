---
title: "TEST — this notice must survive the same rebuild that removes the other"
date: 2026-08-27
expiryDate: 2026-08-28T23:59:59-04:00
summary: "The control. Proves a scheduled rebuild removes what has expired rather than whatever it happens to touch."
---

This entry is the control for the notice that expires at 12:55 am.

Both are published together. The rebuild timed for 1:10 am must remove that one
and keep this one. If both vanish, the rebuild is losing content rather than
applying a display window, and a single expiring notice would not have told
those two outcomes apart.
