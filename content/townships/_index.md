---
title: "Member Townships"
menuLabel: "Townships"   # shorter word for the pinned menu; the page heading keeps its full title
weight: 50
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
