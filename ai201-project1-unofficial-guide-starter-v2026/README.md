# The Unofficial Guide

Kudzaishe Chikowore — corpus: `campus_life`

> **This file is your submission.** Fill it in as you go — most sections get
> written during the milestone that produces them, not at the end.
>
> How the starter works, and every command you'll need, is in `RUNNING.md`.
> Leave that file alone.
>
> **Paste everything as text.** No screenshots, no video. A typed table gets
> full credit; a picture of the same table gets none.
>
> Delete these instruction blocks as you replace them. The `<!-- -->` comments
> are notes to you and don't show up when the page renders — you can leave them
> or remove them.

---

# Unit 1

## What This Does

This is a question-answering system over `campus_life`, a corpus of 88 short
student posts about one university — dining halls, dorms, courses, and the
administrative rules nobody writes down plainly. You ask it something in
ordinary language ("Is the housing lottery actually random?") and it finds the
posts that bear on your question, answers from those posts only, and names the
file it used.

It handles the kinds of questions a student actually asks another student:
what a course's workload really is, how long the queue at a dining hall gets,
which dorm's laundry backs up and when, what a deadline means in practice
rather than on the registrar's site. It is deliberately bad at everything
else — ask it about Rust or ibuprofen and it will tell you it doesn't have
enough information rather than guess, because a relevance check runs before
the model is ever called.

Two of the three moving parts run entirely on this laptop: the embeddings and
the vector store. Only the sentence-writing step calls out to a hosted model.

## Chunking Strategy

**Chunk size:** 450 characters — but as a *ceiling*, not a target. See below;
nothing in this corpus is ever cut to that length.
**Overlap:** 0 characters. Replaced by carrying the document title into every
chunk, which is the only shared context that was doing any work.

**Baseline before I changed anything (Milestone 1).** `python app.py index` on
`campus_life` with the starter's `chunker.py::fallback_split` at 800/120:

```
loaded   88 documents, 27,908 characters, ~317 characters per document
chunked  88 chunks, 317 characters on average (shortest 178, longest 549),
         produced by chunker.py::fallback_split
```

88 documents in, 88 chunks out. The starter's chunker never fired once: it cuts
at 800 characters and the longest document in this corpus is 549. That is the
finding Milestone 3 starts from — the question here isn't "what chunk size?",
it's "should a post that holds two separate thoughts come apart at all?"

**What I changed it to.** `chunker.py::split_documents` now makes one chunk
per paragraph and prepends the document's title line to every one of them.
That takes the corpus from 88 chunks to 183, and the average chunk from 317
characters to 167:

```
loaded   88 documents, 27,908 characters, ~317 characters per document
chunked  183 chunks, 167 characters on average (shortest 63, longest 397),
         produced by chunker.py::split_documents
```

**Why paragraphs.** Every file in this corpus has the same shape: a title
line, a blank line, then one to four short paragraphs. I counted — 72 of the
88 hold more than one paragraph, and the split is almost always the same one:
a paragraph of somebody's experience, then a paragraph of hard facts. From
`dining_kestrel_commons.txt`:

> I'm a junior and I've done this twice now. Wait times: 20 to 25 minutes
> between 12:15 and 1:00 [...]
>
> Hours are 7:00am to 9:00pm weekdays, 9:00am to 8:00pm weekends. Costs one
> meal swipe, or $12.50 cash.

Those answer different questions. "How long is the queue?" and "when does it
close?" shouldn't have to retrieve the same blob and hope the model picks the
right half. The author already marked where one thought ends and the next
begins, by pressing Enter twice. Splitting on a character count throws that
information away; splitting on the blank line uses it.

**Why the title goes on every chunk, which is the part I got wrong first.**
My first version just split on blank lines. Look at what that does to the
second paragraph above: it gives opening hours and a price and never says
*Kestrel Commons* anywhere in it. As a standalone chunk it is unfindable by
anyone who asks about that dining hall by name — the words simply aren't
there to match. Seven dining halls and seven dorms all have this shape, so
this wasn't one bad chunk, it was about half the corpus.

Prepending the title fixes it for a mean of 27.7 characters per chunk. That is
a 9.6% increase in indexed text, and worth it.

**Why 450 and why 0.** Neither number is a knob I tuned; both are facts about
the corpus.

- **450 is a ceiling that never fires.** Chunk length here is decided by the
  author's paragraph breaks, not by me. The longest titled paragraph in the
  corpus is 397 characters (the 373-character explanation in
  `admin_housing_lottery.txt` plus its 24-character title), so 450 is that
  observed maximum plus headroom. I verified it splits 0 of 183 chunks. A cap
  low enough to actually bite — 300, say — would cut the housing lottery
  explanation between the rule and its consequence.
- **0 overlap, because there are no blind cuts left to repair.** Overlap
  exists to heal a thought that a fixed-width window severed mid-sentence.
  Every boundary this chunker makes is one a human wrote. What genuinely *is*
  lost across a paragraph break is not the previous sentence, it's the
  *subject* — and a 120-character trailing window would only sometimes happen
  to catch the building's name, where the title prefix catches it every time.
  So the honest framing is that I replaced positional overlap with semantic
  overlap.

**Two guard rails that do nothing here, and I'm not going to pretend
otherwise.** The code has a `MIN_BODY_CHARS = 30` rule that folds fragments
into the previous paragraph, and the 450 cap. Measured against `campus_life`,
**both fire exactly zero times** — the shortest body paragraph is 36
characters and the longest is 373. So I can't claim this strategy "handles
fragments and long documents" on the evidence of this corpus. They're there so
it degrades sanely elsewhere: run the same chunker over `city_guides` and the
merge rule fires 77 times and the cap once.

## Sample Chunks

Straight from `python app.py chunks -n 5`, which samples evenly across the
corpus rather than taking the first five. All five begin with their document's
title and end on a full stop — that is criterion 4, checked.

**Chunk 1** — source: `admin_add_drop_deadline.txt#0` — produced by: `chunker.py::split_documents`

```
On the add/drop deadline

You can add a course through the end of the second week. Dropping is a longer window — through the end of week six — but a drop after week two shows as a W on your transcript. Nothing anywhere on the registrar's site says this plainly, and students find out from each other.
```

**Chunk 2** — source: `course_cs_340_exams.txt#1` — produced by: `chunker.py::split_documents`

```
CS 340 Databases — assessment

Start the term project in week three, not week eight; everyone learns this the hard way.
```

**Chunk 3** — source: `course_phys_130_workload.txt#0` — produced by: `chunker.py::split_documents`

```
Workload for PHYS 130 Mechanics

People keep asking so: 7 hours a week, plus 3 on lab weeks. That's real time, not optimistic time.
```

**Chunk 4** — source: `dining_verrill_street_grill_followup.txt#1` — produced by: `chunker.py::split_documents`

```
Re: Verrill Street Grill

Also worth saying: one register, so the queue is a single line no matter how busy. Nobody tells you this at orientation.
```

**Chunk 5** — source: `housing_morrow_house.txt#1` — produced by: `chunker.py::split_documents`

```
Morrow House — what it's actually like

The good: cheapest housing tier by about $900 a year, and the singles are real singles.
```

Chunks 2, 4 and 5 are the ones that prove the point. Each is the *second*
paragraph of its document, and each would be anonymous without the title line
above it — "Also worth saying: one register, so the queue is a single line" is
unfindable on its own. Chunk 2 is 88 characters and still answers a real
question, which is why I set the fragment floor below it rather than above.

## Sample Answer

I've picked the hardest of my five questions rather than the flattering one.
This is the one at distance 0.700 — the question the starter's default cutoff
of 0.6 would have refused outright. It never says "library" anywhere.

**Question:** Where can I sit and still have somewhere to plug in a laptop?

**Answer:**

```
  (best distance 0.700, cutoff 0.74)

You can sit in the basement, as it has the only outlets at every seat.

Source: study_library_hours.txt

Sources retrieved: admin_wifi_and_accounts.txt, dining_north_kitchen.txt,
dining_the_ridgeway_cafe.txt, dining_the_ridgeway_cafe_followup.txt,
housing_tamsin_court.txt, study_library_hours.txt
```

Two things worth noticing in that output. The answer is correct and cites the
one document that contains it — `study_library_hours.txt` says "The basement
has the only outlets at every seat and is therefore full from about 10am."
But look at the other five sources retrieved: wifi, two dining halls, a dorm.
Six of the seven chunks that came back are irrelevant, and the question only
worked because the seventh was right and the grounding instruction kept the
model from inventing something out of the other six. At 0.700 this is a weak
retrieval that produced a strong answer, and I'd rather record that honestly
than pick a question that scored 0.161.

**My relevance cutoff: 0.74** (`config.py`, `THRESHOLD`). All ten measured
with `store.search`, which makes no model call.

| Question | In corpus? | Best distance |
|---|---|---|
| What are the wait times at Kestrel Commons during lunch? | yes | 0.161 |
| How many hours a week does CS 340 Databases take at its heaviest? | yes | 0.176 |
| Is the housing lottery actually random? | yes | 0.248 |
| Which evening should I avoid if I need to dry clothes? | yes | 0.464 |
| Where can I sit and still have somewhere to plug in a laptop? | yes | **0.700** |
| What is the capital of Mongolia? | no | **0.787** |
| Who won the 1994 World Cup? | no | 0.847 |
| What is the recommended dosage of ibuprofen for a headache? | no | 0.849 |
| How do I write a for loop in Rust? | no | 0.860 |
| How do I change the oil in a diesel engine? | no | 0.923 |

**What the two groups looked like.** Not two tidy clusters. The in-corpus group
is bimodal: the three questions that *name* their subject land at 0.161–0.248,
and the two that deliberately don't land at 0.464 and 0.700. The out-of-scope
group is tight, 0.787–0.923. So the entire decision lives in the **0.087
between 0.700 and 0.787**, and I put the cutoff at 0.74 — about 0.04 of margin
either side.

**The starter's 0.6 would have been wrong, and this is the finding I'm most
glad I have.** At 0.6, "Where can I sit and still have somewhere to plug in a
laptop?" is refused at 0.700 — a question `study_library_hours.txt` answers
outright ("The basement has the only outlets at every seat and is therefore
full from about 10am"). Had I written five questions that all named their
subject, every one would have come back under 0.25, the gap would have looked
enormous, and I'd have left 0.6 in place and shipped a system that refuses real
questions. The two awkward questions were worth more than the three good ones.

**What 0.04 of margin costs me.** It is thinner than I would like, and I should
be honest that my out-of-scope set is the easy case — Mongolia, diesel engines,
Rust, all from another world. "What is the recommended dosage of ibuprofen?"
only scores 0.849 because nothing here is medical; `health_center.txt` exists,
and a differently-phrased health question would land much closer to the line.
I biased the cutoff toward the lower half of the gap because a confident wrong
answer is worse than a refusal, but at this width a genuinely near-miss
question will get through.

Verified at 0.74: **5 of 5** in-corpus questions answered, **5 of 5**
out-of-scope questions refused.

## How I Used AI

**1. I asked Claude to design the chunker, and the part I had to push back on
was the evidence, not the code.** I described my corpus — title line, blank
line, a few short paragraphs — and asked for a chunking strategy that fitted
it. What came back was the paragraph-plus-title approach I ended up using, and
the code was essentially right. What also came back was a confident table of
cosine distances claiming to show the approach beating the baseline on five
probes, and a recommended relevance cutoff of 0.60–0.62 derived from them.

I hadn't run any of that. The numbers were predictions presented as
measurements. So I kept the design and threw away every number in it, and
measured my own — which is how I found that my cutoff needed to be **0.74**,
not 0.62. The predicted range would have refused one of my five real questions
outright. The lesson I'm taking is that the code an AI writes is checkable in
seconds and the numbers it quotes are not, so the numbers are the part that
needs the suspicion.

**2. I used Copilot to compare the saved before and after run logs.** It helped
aggregate the question-level results into the five criterion rows and check
that the gate result was deterministic. I verified the counts against the
actual answer text and saved files rather than treating the summary as a
measurement by itself.

**2. I asked it to verify the finished pipeline, and it caught a mistake it
had caused.** After building everything I asked Claude to re-run all ten
questions and confirm the cutoff still held. Every distance came back around
0.9 and every question was refused, including ones that had scored 0.161
twenty minutes earlier.

The cause was `tools/smoke_test.py`, which I'd been running as a free
regression check after changing the chunker. It's a staff tool, and line 23
sets `AI201_FAKE_EMBEDDINGS=1` while line 89 calls `build_index(chunks,
corpus=corpus)` with no `variant` — so it writes MD5 stand-in vectors straight
over the real `campus_life` collection. My index had been quietly replaced
with nonsense. Re-running `python app.py index` restored it and all ten
distances came back identical to the originals.

What I changed as a result: I stopped running `tools/smoke_test.py`, and if I
do run it I re-index immediately afterwards. It also made me re-verify the
distances in this README against a freshly built index rather than trusting
the ones I'd written down earlier — which is the only reason I know the table
above is right.

## Stretch Feature: Conversational Memory

*Declared before writing any of it — this section is committed ahead of the
code, and the commit history shows that.*

I'm adding conversational memory, so a follow-up question can build on the one
before it. `python app.py ask --memory` turns it on; it's interactive mode
only and off by default everywhere else.

The design rule I'm holding myself to: **memory is a second chance for a
question the gate has already refused, and the second chance has to clear a
stricter cutoff than a fresh question does.** A question that passes the gate
on its own never touches the memory code at all.

Why that shape and not the obvious one. The obvious version keeps the previous
turn's chunks around and adds them to the next prompt. That can't work here,
because the relevance gate sits *upstream* of prompt assembly — a bare
follow-up like "is it random?" is refused and the function returns before the
prompt is ever built, so carried chunks would never be seen. It would also put
documents in front of the model that this turn's gate never approved, which
breaks the grounding promise in criterion 2.

Three properties I want to be able to demonstrate:

- **No extra model calls.** Expanding the question is string concatenation, and
  the retry embedding runs locally in Chroma. The only new API calls are
  answers to turns that previously produced no answer at all.
- **The gate is never loosened, only tightened.** The retry must beat
  0.9 x my threshold.
- **The graded paths can't reach it.** `run_eval.py` doesn't call
  `ask_pipeline`, and `serve.py` never constructs a memory object, so my run
  logs and criterion 3 are unaffected.

### Evidence: the same three turns, run twice

**Run A — `python app.py ask`** (control, no flag)

```
> What are the wait times at Kestrel Commons during lunch?
  (best distance 0.161, cutoff 0.74)

According to `dining_kestrel_commons.txt`, the wait times at Kestrel Commons
are 20 to 25 minutes between 12:15 and 1:00, and under 5 minutes before 11:45.

> is it any good?
  (best distance 0.751, cutoff 0.74)

I don't have enough information about that.

> What is the capital of Mongolia?
  (best distance 0.787, cutoff 0.74)

I don't have enough information about that.
```

**Run B — `python app.py ask --memory`** (same three questions, same order)

```
> What are the wait times at Kestrel Commons during lunch?
  (best distance 0.161, cutoff 0.74)

According to `dining_kestrel_commons.txt`, the wait times at Kestrel Commons
are 20 to 25 minutes between 12:15 and 1:00, and under 5 minutes before 11:45.

> is it any good?
  (best distance 0.174, cutoff 0.666)
  (follow-up — actually searched for: "What are the wait times at Kestrel
   Commons during lunch? is it any good?")

Based on the provided documents, the wait times at Kestrel Commons are 20 to
25 minutes between 12:15 and 1:00, and under 5 minutes before 11:45
(`dining_kestrel_commons.txt`).

It is considered good, specifically for its stir-fry station which is made to
order (`dining_kestrel_commons.txt`).

> What is the capital of Mongolia?
  (best distance 0.787, cutoff 0.74)

I don't have enough information about that.
```

**Turn 2 is the feature.** 0.751 → 0.174, a refusal becomes a grounded answer
citing the same file. Note the printed cutoff changed too: 0.666, not 0.74.
The rescue had to clear a *stricter* bar than a fresh question.

**Turn 3 is the safety proof.** 0.787 and the same refusal in both runs, and
the distance is byte-identical because no expansion happened at all.
`memory.looks_like_a_followup` rejected it — "Mongolia" is a capitalised word
that isn't the first, which `_introduces_a_new_topic` reads as the asker
naming a new subject. The second search never ran.

**Turn 1 is the no-op proof.** Same distance, same answer, both runs. A
question that passes the gate on its own never enters the memory branch.

**Cost.** Memory itself adds no model calls — the expansion is string
concatenation and the retry is a local Chroma query. The one additional answer
in Run B is a turn that produced no answer at all before. (The raw
`generate.usage()` counters from this session are inflated by retries: Google
was returning 503 UNAVAILABLE for about half an hour while I was capturing
these, so the counter includes failed attempts.)

**Off by default, provably.** `grep -rn "Memory" *.py` returns only
`memory.py` and the interactive branch of `app.py::cmd_ask`. Neither
`run_eval.py` nor `serve.py` mentions it.

### What's wrong with it

- **At my threshold it rarely fires, and that's a real cost of Milestone 4.**
  I set the cutoff to 0.74, which is high. I tested nine follow-ups across
  three topics and only two of them were actually refused on their own —
  "is it any good?" at 0.751 and "and how many are there?" at 0.765. The rest
  ("what does it cost?" 0.586, "when do they come out?" 0.717) already pass
  unaided, so memory never gets a turn. At the starter's 0.6 the feature would
  earn its keep far more often. I'd rather have the correct threshold and a
  feature that fires rarely than the reverse.
- **A vague anaphoric shell can still carry an out-of-scope question through.**
  "is it three hundred milligrams?" is short, has no capitals and no digits, so
  it passes every trigger test and gets expanded. The gate does not catch it —
  what catches it is the grounding instruction, which is the less reliable of
  the two layers. Bounded to follow-ups the gate had already refused, but real.
- **The new-topic check is capitalisation-dependent.** Typed lowercase,
  "what about mongolia?" defeats it entirely.
- **Concatenation is not coreference resolution.** It doesn't work out what
  "it" refers to; it averages two embeddings. A follow-up that changes facet
  within a topic can retrieve the same chunks as the turn before.
- **REPL only.** `Memory` lives in one process's RAM, and `serve.py` has no
  session identity, so `POST /ask` gets nothing.
- **The trigger word lists are hand-written English and unmeasured.** Every
  miss and every false fire traces back to `ANAPHORA` and `OPENERS`.

---

# Unit 2

<!-- These sections get ADDED to what's already above. Don't delete or rewrite
     unit 1 — the point is that someone can see what you said before you knew
     how it went. -->

## Run Log — Before

<!-- Your five criteria, three runs each. `python run_eval.py --label before`
     runs the questions, puts the OUT_OF_SCOPE ones through the gate, and
     writes it all into results/ for you. Targets come from criteria.md; the
     verdict column is your call.

     Criterion 3 is measured in one deterministic pass rather than three, so
     the same number goes in all three run columns. That's correct, not lazy.

     Milestone 1. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. Every chunk names its own subject | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 5. The cited source is the right one | 3 of 5 | 5/5 | 5/5 | 5/5 | MET |

<!-- Underneath, paste the REAL output for each criterion from one of your
     runs — the actual text your system produced, not a description of it.
     Name the file and function that produced it. -->

### Criterion 1: Retrieved chunk contains the answer

From `results/run_2026-09-29_2210_before.md`, produced by `run_eval.py::main`:

```text
Based on the provided documents, the wait times at Kestrel Commons are 20 to 25 minutes between 12:15 and 1:00, and under 5 minutes before 11:45.

Source: dining_kestrel_commons.txt
```

The same evidence file records the retrieved chunks and answers for all five questions in all three runs; each answer is supported by a retrieved chunk.

### Criterion 2: Every answer names a source

From `results/run_2026-09-29_2210_before.md`, produced by `run_eval.py::main`:

```text
CS 340 Databases takes 15 hours a week in the last three weeks at its heaviest.
This information comes from `course_cs_340_workload.txt` and `course_cs_340.txt`.
```

All fifteen answers in the evidence file name at least one source document.

### Criterion 3: Gate stops out-of-corpus questions

From `results/run_2026-09-29_2210_before.md`, produced by `run_eval.py::check_out_of_scope`:

```text
Produced by `run_eval.py::check_out_of_scope`, cutoff 0.74. Refused 5 of 5.
```

### Criterion 4: Every chunk names its own subject

From `app.py chunks -n 5`, produced by `chunker.py::split_documents`:

```text
Chunk 1  |  source: admin_add_drop_deadline.txt#0  |  produced by: chunker.py::split_documents
On the add/drop deadline
```

The five sampled chunks each begin with a document title and end with a full stop.

### Criterion 5: The cited source is the right one

From `results/run_2026-09-29_2210_before.md`, produced by `run_eval.py::main`:

```text
CS 340 Databases takes 15 hours a week in the last three weeks at its heaviest.
This information comes from `course_cs_340_workload.txt` and `course_cs_340.txt`.
```

The cited documents contain the answers for all five test questions.

## Verdicts

<!-- MET or MISSED for each of the five, against the target you wrote last
     unit — not a new one. Plus a sentence on how you decided. That sentence
     matters most where it was close.

     If your target said 4 of 5 and your runs came out 4, 3, 4, that's a MISS.
     The target has to hold, not show up occasionally.

     Milestone 2. -->

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 | Retrieved chunks contain the answer | MET | Each of the three runs had an answer-containing retrieved chunk for all five questions, exceeding the target of 4 of 5. |
| 2 | Every answer names a source | MET | All fifteen generated answers named at least one source document, meeting the target of 5 of 5 in every run. |
| 3 | The relevance gate stops out-of-corpus questions | MET | The deterministic gate refused all 5 of 5 out-of-corpus questions, meeting the target of at least 4 of 5 in every run column. |
| 4 | Every chunk names its own subject | MET | The five sampled chunks each began with their document title and ended with a full stop, meeting the 5 of 5 target. |
| 5 | The cited source is the right one | MET | The cited documents contained the answers to all five test questions in each run, exceeding the target of 3 of 5. |

## Diagnoses

<!-- For each miss: which stage caused it, and how. The stage alone isn't
     enough — you need the mechanism.

     Not a diagnosis: "Question 3 didn't work."
     A diagnosis:     "Question 3 asks about laundry costs. The answer is in
                       one sentence that got split across two chunks, so
                       neither chunk on its own contains it."

     The five stages: loading → chunking → embedding → retrieval → generation.

     Look for a pattern. If three misses all ask about numbers, that's one
     problem, not three.

     Missed nothing? Say so, then say honestly whether your targets were set
     low, and which one you'd tighten and to what.

     Milestone 3. -->

  No criteria were missed, so no pipeline stage caused a measured failure in
  this baseline. The five in-corpus questions all retrieved chunks containing
  their answers, all generated answers named sources, and the gate refused all
  five out-of-corpus questions. The chunk sample also passed, and each cited
  document contained the answer it was used to support.

  The targets were conservative in two places. I would tighten criterion 1 from
  4 of 5 to 5 of 5 because all five deliberately selected questions succeeded,
  including the two ambiguous questions about outlets and laundry. I would also
  tighten criterion 5 from 3 of 5 to 4 of 5 because all five citations were
  correct in these runs. These are revised future targets, not explanations for
  changing a missed result.

## The Improvement

**What I changed:**

I changed `config.py::THRESHOLD` from `0.74` to `0.72`, tightening the
relevance gate by `0.02`.

**Why I picked it:**

There was no missed criterion to repair, so I chose the weakest measured
boundary: the hardest in-corpus question had distance `0.700`, while the
closest out-of-corpus question had distance `0.787`. The tighter cutoff tests
whether a smaller margin improves refusal behavior without rejecting that
hardest valid question.

<!-- Connect it to a specific diagnosis above in one sentence. If you can't,
     you picked a fix because it sounded impressive. -->

### Run Log — After

<!-- Same format, same five criteria, three runs each.
     `python run_eval.py --label after` -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. Every chunk names its own subject | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 5. The cited source is the right one | 3 of 5 | 5/5 | 5/5 | 5/5 | MET |

**Did it help?**

<!-- Say plainly whether it did, and how you know. If it made things worse,
     say that — a change that backfired, honestly reported, earns full credit
     and is more interesting than one that worked. What matters is that you can
     tell.

     Milestone 4. -->

  No, it did not improve the measured results. Before and after both scored
  5/5 on every criterion, and the five best distances were unchanged because
  the threshold changes the gate decision, not retrieval. The change also did
  not hurt the hardest valid question at `0.700`, and the gate still refused
  all five out-of-corpus questions.

## What's Still Broken

<!-- For each criterion still missed after your fix: what you'd do about it,
     and why you stopped where you did.

     "I ran out of time" is fine if it's true. Pretending nothing is left is
     not.

     Milestone 5. -->

  No acceptance criterion is still missed after the change. The remaining risk
  is not visible in this easy out-of-corpus test set: the closest valid question
  is only `0.087` away from the closest invalid one, so a near-topic question
  could still pass or be refused unpredictably. I stopped after one threshold
  change because changing retrieval or generation as well would make the result
  impossible to attribute to one improvement. The next focused improvement
  would be hybrid keyword-plus-semantic search, especially for names and exact
  numbers.

## What I'd Do Differently

<!-- Knowing what you know now — which of your five criteria would you write
     differently, and why?

     Milestone 5. -->

  I would write criterion 1 as **5 of 5** rather than 4 of 5, and criterion 5
  as **4 of 5** rather than 3 of 5, for the next unit. The original targets were
  reasonable before measurement, but this deliberately chosen test set passed
  all five questions and all five citations in both evaluations. I would keep
  criterion 3 at 4 of 5 because the current out-of-scope questions are broad,
  easy cases and do not test the narrow boundary well.
