"""
Stage 2 of the pipeline: splitting documents into chunks.

⚠️ THIS IS THE FILE YOU CHANGE IN MILESTONE 3.

`split_documents` below is deliberately plain. It cuts every document into
fixed-size pieces with a fixed overlap and pays no attention to where sentences
or paragraphs end. It works, and it is not good.

On a corpus of short posts it may not cut anything at all: `campus_life` comes
out as 88 documents and 88 chunks, because almost nothing in it reaches 800
characters. That is the baseline, not a bug — Milestone 3 is where you decide
whether one post should stay one chunk.

Your job in Milestone 3 is to replace the *body* of `split_documents` with a
strategy that fits the documents you actually read in Milestone 1. Keep the
name and the shape of what it returns — the rest of the pipeline calls it, and
your README has to name the function that produced your chunks.

If you get stuck for 30 minutes, `fallback_split` is the original. Switch back
to it, write down what you saw, and move on. That's a real observation about
your pipeline, not giving up.
"""

import re
from dataclasses import dataclass

import config
from ingest import Document


@dataclass
class Chunk:
    """One piece of one document."""

    text: str
    source: str        # which file it came from
    index: int         # which chunk within that file, starting at 0
    produced_by: str   # the function that made it — cite this in your README

    @property
    def label(self) -> str:
        return f"{self.source}#{self.index}"


def fallback_split(
    documents: list[Document],
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    """
    The starter's original chunker. Fixed-size character windows with overlap.

    Keep this function. Milestone 3's stop rule points back at it, and having
    something to compare your own strategy against is useful in unit 2.
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP

    if overlap >= chunk_size:
        raise ValueError("overlap has to be smaller than chunk_size")

    chunks: list[Chunk] = []
    for doc in documents:
        start = 0
        index = 0
        while start < len(doc.text):
            piece = doc.text[start : start + chunk_size].strip()
            if piece:
                chunks.append(
                    Chunk(
                        text=piece,
                        source=doc.source,
                        index=index,
                        produced_by="chunker.py::fallback_split",
                    )
                )
                index += 1
            start += chunk_size - overlap

    return chunks


# ── Milestone 3: structure-aware chunking for campus_life ───────────────────
# Every document in this corpus is a title line, a blank line, then one to four
# short paragraphs. The author already put the blank lines where the thoughts
# end, so the paragraph is the chunk. The title is carried into every chunk
# because a bare paragraph loses its subject: paragraph two of
# dining_kestrel_commons.txt reads "Hours are 7:00am to 9:00pm weekdays..." and
# never says Kestrel Commons, so nothing that names the hall can match it.

_PARA_BREAK = re.compile(r"\n\s*\n")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")

# Body text below this is a fragment rather than a thought, and gets folded into
# the paragraph before it. Measured on campus_life: the shortest body paragraph
# is 36 characters ("Expect 4 hours a week outside class.") and it is a
# complete, answerable fact — so this floor sits deliberately below it and fires
# zero times here. It earns its place on the other corpora, where it does fire.
MIN_BODY_CHARS = 30


def _blocks(text: str) -> list[str]:
    """Split on blank lines. ingest.clean_text has already normalised them."""
    return [b.strip() for b in _PARA_BREAK.split(text) if b.strip()]


def _respect_cap(body: str, prefix: str, limit: int) -> list[str]:
    """Last resort: a paragraph is over the ceiling, so cut it on sentences."""
    if len(prefix) + len(body) <= limit:
        return [prefix + body]

    pieces: list[str] = []
    buffer = ""
    for sentence in _SENTENCE_END.split(body):
        if buffer and len(prefix) + len(buffer) + 1 + len(sentence) > limit:
            pieces.append(prefix + buffer)
            buffer = sentence
        else:
            buffer = f"{buffer} {sentence}".strip()
    if buffer:
        pieces.append(prefix + buffer)
    return pieces


def split_documents(documents: list[Document]) -> list[Chunk]:
    """
    One chunk per paragraph, with the document's title prepended to each.

    Why this, for campus_life specifically:
      - All 88 files are TITLE / blank line / 1-4 paragraphs, and 72 of them
        hold more than one paragraph — usually one of lived experience and one
        of hard facts (hours, prices, hours-per-week). Those answer different
        questions and should be retrievable separately.
      - But a bare paragraph loses its subject, so every chunk carries its
        document's title. That costs a mean of 27.7 characters per chunk.

    config.CHUNK_SIZE is a ceiling here, not a target: nothing in this corpus
    is cut to length, because no paragraph reaches it.
    """
    limit = config.CHUNK_SIZE
    chunks: list[Chunk] = []

    for doc in documents:
        blocks = _blocks(doc.text)
        if not blocks:
            continue

        title, body = blocks[0], blocks[1:]

        # A file with nothing but a title line: keep it whole rather than
        # emitting the title twice. (campus_life has none; other corpora do.)
        if not body:
            chunks.append(
                Chunk(
                    text=title,
                    source=doc.source,
                    index=0,
                    produced_by="chunker.py::split_documents",
                )
            )
            continue

        prefix = f"{title}\n\n"

        # Fold fragments into the paragraph before them, but never past the cap.
        merged: list[str] = []
        for block in body:
            fits = merged and len(prefix) + len(merged[-1]) + 1 + len(block) <= limit
            if len(block) < MIN_BODY_CHARS and fits:
                merged[-1] = f"{merged[-1]} {block}"
            else:
                merged.append(block)

        index = 0
        for block in merged:
            for text in _respect_cap(block, prefix, limit):
                chunks.append(
                    Chunk(
                        text=text,
                        source=doc.source,
                        index=index,
                        produced_by="chunker.py::split_documents",
                    )
                )
                index += 1

    return chunks


def describe(chunks: list[Chunk]) -> str:
    """A one-line summary, printed after indexing."""
    if not chunks:
        return "0 chunks"
    lengths = [len(c.text) for c in chunks]
    return (
        f"{len(chunks)} chunks, "
        f"{sum(lengths) // len(lengths)} characters on average "
        f"(shortest {min(lengths)}, longest {max(lengths)}), "
        f"produced by {chunks[0].produced_by}"
    )


if __name__ == "__main__":
    from ingest import load_documents

    chunks = split_documents(load_documents())
    print(describe(chunks))
