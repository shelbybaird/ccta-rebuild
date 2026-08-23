# Gates — things that must be settled before this repository is made public

This file exists because a public repository publishes its **history**, not just
its current state. Removing a detail in a later commit does not unpublish it.
Everything below must therefore be resolved **before the first push**, not
before cutover.

Delete this file once every item is closed.

## 1. Officer contact details — CLOSED 2026-08-23

**Decided: drop them.** Telephone numbers and street addresses are not carried
across. The reasoning was that a detail is far easier to add back later than to
remove from a repository's history, where a value committed once stays readable
for as long as the repository exists.

The removal was made before the first commit, so the values never entered any
history. Verified by scanning every file in the tree — source, built output and
the git object store — for each number in digit-normalised form, so that any
punctuation would still match, and for each street address. All zero. The check
was then proved able to fail by planting a control value written with different
punctuation, which it caught, and by finding the retired Gmail account still
sitting in the site configuration, which it also caught.

**What replaces them.** The roster carries **role addresses on the Association's
own domain** — `president@`, `vicepresident@`, `secretary@`, `treasurer@` and
`executive@` — forwarded by Cloudflare Email Routing to wherever each officer
already reads mail. These follow the office rather than the person, which is
what issue #2 asks for, and a change of officer becomes a forwarding rule rather
than an edit to a published page.

**Each officer's township is retained**, and it is doing real work: an officer
who publishes no direct line is still reachable through the number their own
township publishes.

**The withheld details are not lost.** They remain on the present site and in
the server mirror held in the private `ccta-website` repository.

**⚠ The dependency this creates.** None of the role addresses exist yet. They
begin working only when name service moves to Cloudflare and Email Routing is
configured, which the execution plan places after approval. Until then the
roster shows addresses that do not yet receive mail. **The exact strings are a
routing setting, not a code change, so any of them can be renamed later.**

## 2. `termStart` is required by the model and is not known for any officer

The content model marks *Term began* as required, because that field is what
makes the roster a dated record rather than a page that overwrites itself. **No
term start date is known for any of the four current officers.** The entries
have been written with the field absent rather than with an invented date, since
a wrong date in a history is worse than a missing one.

The minutes are the likely source. Article V sets elections on the third
Thursday in November.

## 3. The offices — CLOSED 2026-08-23

**Decided: build to the constitution's five offices, not to today's four.**
Article V: *"The officers to be elected are: President, Vice-President,
Secretary, Treasurer, and Executive Committee-person."*

The present site shows four because Secretary and Treasurer are held by one
person. Building to that compression would have made a future separation of the
two offices impossible to record, which is precisely the history the type
exists to keep.

Because the roster stores one entry per **term of office** rather than one per
person, the present arrangement expresses itself naturally as two entries
bearing the same name. A future split then requires no change to the site at
all: one term ends and another begins.

**"Executive Board" is not carried forward.** It appeared only in the previous
site's navigation. The constitution does not use it.

## 4. Three minutes documents are scans with no text layer

`2017-02-16`, `2017-03-16` and `2019-02-20` return zero extractable characters.
A screen reader gets nothing from them. Stage 3.5 measures against WCAG 2.1 AA,
and the execution plan notes the Department of Justice deadlines in 2027 and
2028. Three documents is a small OCR job, and it blocks nothing.

## 5. Five orphaned documents on the present server

`PDF/2019/` holds `2019SponsorLetter.pdf`, `2019SponsorForm.pdf`, `tu-cccs.pdf`,
`tu-4h.pdf` and `tu-chc.pdf`. Nothing on the site links to any of them. Somebody
should decide whether they carry across.

## 6. Content defects on the present site, not carried forward

Recorded so that they are fixed deliberately rather than reproduced:

- The minutes page misspells September as *"Sepember"* (2016).
- The minutes page links `092016.pdf` twice, the second time with no label.
- Three township tiles exist only at 160x105 (Goshen, Miami, Wayne), because
  their logos were refreshed in 2023 and only the small version was replaced.
  Asking those three for a current logo is a cheap fix.
