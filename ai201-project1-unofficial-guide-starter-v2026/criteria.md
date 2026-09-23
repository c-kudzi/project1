# Acceptance criteria — The Unofficial Guide

Five criteria that say what "working" means for this system, written in unit 1
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"Retrieval works"* is an opinion. *"For at
least 4 of my 5 test questions, the top results include a chunk containing the
answer"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter or looser one. A reason that says something about your corpus or your
pipeline earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

---

## 1. Retrieved chunks contain the answer

For at least 4 of my 5 test questions, the retrieved chunks include one that
contains the answer.

**Why this target:** 4 of 5 rather than 5 of 5 because two of my five questions
deliberately don't name the thing they're asking about — "Where can I sit and
still have somewhere to plug in a laptop?" never says library, and "Which
evening should I avoid if I need to dry clothes?" never says laundry. Retrieval
here is similarity between the words in my question and the words in the chunk,
so those two are the ones with real room to fail. The laundry one is harder
still: seven buildings each have a laundry document and they all say much the
same thing, so the right *answer* can come back attached to the wrong building.
I'd rather set the target where I think one genuinely difficult question can
miss than claim all five and quietly be describing the three easy ones.

---

## 2. Every answer names a source

Every answer the system produces names at least one source document.

**Why this target:** All five and not four, because naming a source is the one
thing in this pipeline that doesn't depend on the answer being any good. Two
separate mechanisms have to fail for it to miss: `generate.py::build_prompt`
stamps every chunk with `[from FILENAME]` before the model ever sees it, and
`GROUNDING_INSTRUCTION` tells the model to name the file it used. The filename
is in the prompt whether or not retrieval found the right material, so even a
wrong answer should still cite something. A miss here wouldn't mean retrieval
was weak — it would mean the model ignored a direct instruction, and I'd want
to know that. This is the criterion I'd be most embarrassed to miss.

---

## 3. The relevance gate stops out-of-corpus questions

When I ask a question my documents clearly don't cover, the relevance gate
stops it and the system returns "I don't have enough information about that" —
in at least 4 of 5 tries.

<!-- The five questions are the ones in `OUT_OF_SCOPE` at the bottom of
     `questions.py`, and `run_eval.py` puts them through the gate and writes
     what happened into your run log. Swap them for your own if you'd rather —
     just keep five of them, or the "4 of 5" above has nothing to be 4 of. -->

**Why this target:** My two groups didn't overlap, but the gap is narrow and
that's why I'm not claiming 5 of 5. My in-corpus questions came back at 0.161,
0.176, 0.248, 0.464 and 0.700; the five out-of-scope ones at 0.787, 0.847,
0.849, 0.860 and 0.923. So the whole decision lives in the 0.087 between 0.700
and 0.787, and I put the cutoff at 0.74 — about 0.04 of margin on each side.

0.04 is not much. The out-of-scope questions I'm measured against are from
another world entirely (Mongolia, diesel engines, Rust), and they're the easy
case. A question that is *nearly* in scope — "what's the ibuprofen dosage?"
scores 0.849 only because nothing here is medical, and `health_center.txt`
exists — would land far closer to the line. 4 of 5 leaves room for one
out-of-scope question to be more topical than I expected.

---

## 4. Every chunk names its own subject

Every chunk my chunker produces begins with the title line of the document it
came from, and no chunk is cut mid-sentence. Checked by sampling 5 chunks with
`python app.py chunks -n 5`: 5 of 5 should start with a title and end on a
full stop.

**Why this target:** 5 of 5 and not 4 of 5, because this one isn't a
probability — it's a property of the code, so anything less than all of them
means the chunker has a bug rather than a bad day.

It's the criterion I care most about because I watched it fail. My documents
are a title line, a blank line, then one to four paragraphs, and my first
instinct was simply to split on the blank lines. That breaks badly here:
paragraph two of `dining_kestrel_commons.txt` reads "Hours are 7:00am to 9:00pm
weekdays, 9:00am to 8:00pm weekends" and never says Kestrel Commons anywhere in
it. As a standalone chunk it can't be found by anyone asking about that dining
hall. Carrying the title into every chunk is what fixes it, and this criterion
is how I check the fix is actually applied everywhere rather than just in the
examples I happened to look at.


---

## 5. The cited source is the right one, not just any one

For at least 3 of my 5 test questions, the document the answer names is the
document that actually contains the answer — not merely a document that
mentions the topic.

**Why this target:** Criterion 2 only asks that an answer names *a* source.
That's a low bar, and I think it can be met while still being wrong in a way a
reader would never catch. This is the stricter version of it.

3 of 5 and not 4 or 5, because I know the corpus is built to make this hard and
I'd rather be honest about that than set a number I've quietly stacked in my
favour. Seven buildings each have three documents — an overview, a laundry
post, and a noise post — and the overview repeats one-line summaries of the
other two. So a laundry question can legitimately match the overview, which
mentions laundry in passing, above the dedicated laundry document that actually
has the prices in it. The same shape shows up in the dining hall documents,
where each hall has an original post and a "Re:" follow-up that re-quotes its
numbers. In both cases the shorter, denser summary can out-rank the detailed
source.

A wrong citation that sits under a right answer is the failure I'd least like
to ship, because it looks completely fine.


---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 2 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 1. Retrieved chunks contain the answer

         For at least 4 of my 5 test questions, the retrieved chunks include
         one that contains the answer.

         **Why this target:** ...

         > **Revised in unit 2:** For at least 4 of 5 questions, the top three
         > results contain the answer.
         >
         > **Why revised:** I couldn't judge "the chunks include one that
         > contains the answer" the same way twice — I scored two questions
         > differently on Monday than on Wednesday. The new version is
         > something I can actually check.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said 4 of 5 but got 2 of 5, so 2 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.

     The whole reason the originals stay visible is so someone can see what you
     said before you knew the answer.
     ───────────────────────────────────────────────────────────────────────── -->
