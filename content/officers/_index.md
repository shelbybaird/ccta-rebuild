---
title: "Officers"
weight: 0   # Out of the menu: the roster is reached through About, which
            # carries it. This page and its address still work, so nothing
            # that linked to /officers/ has broken.
# This page renders. Its ENTRIES do not — the cascade below applies to
# descendants, and the explicit block above it keeps this list page itself.
build:
  render: always
  list: always
cascade:
  build:
    render: never
    list: always
---
