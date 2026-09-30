"""
Settings for The Unofficial Guide.

Everything you're likely to change lives here, at the top, on purpose.
You'll edit THRESHOLD in Milestone 4 and the chunking numbers in Milestone 3.

Anything you set in your .env file wins over the defaults here.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")


# ─── The corpus you're working with ──────────────────────────────────────────
# Change this to switch corpora, or pass --corpus on the command line.
# Options are the folder names inside corpora/. See corpora/README.md.

CORPUS = os.getenv("AI201_CORPUS", "campus_life")


# ─── Chunking (Milestone 3) ──────────────────────────────────────────────────
# Measured against campus_life, not picked for being round.
#
# CHUNK_SIZE is a CEILING, not a target. chunker.py::split_documents cuts on
# paragraph breaks, so chunk length is decided by the author, not by this
# number. The longest titled paragraph in the corpus is 397 characters (a
# 373-character paragraph in admin_housing_lottery.txt plus its 24-character
# title), so 450 is that observed maximum plus headroom. It splits nothing
# here. A cap low enough to actually bite — 300, say — would cut the housing
# lottery explanation between the rule and its consequence.
#
# CHUNK_OVERLAP is 0 because there are no blind cuts left to repair. Overlap
# exists to heal a thought severed mid-sentence by a fixed-width window; every
# boundary this chunker makes is one the author wrote. What IS lost across a
# paragraph break is the subject ("Kestrel Commons"), and the title prefix
# fixes that deterministically for 27.7 characters, where a 120-character
# trailing window would only sometimes happen to catch the name.

CHUNK_SIZE = 450        # ceiling per chunk; nothing in campus_life reaches it
CHUNK_OVERLAP = 0       # no positional overlap — the title prefix replaces it


# ─── Retrieval (Milestone 4) ─────────────────────────────────────────────────

# Raised from the starter's 5. Paragraph chunking halved the mean chunk length
# (317 -> 167 characters), so k=5 now hands the model about half the material
# it used to. It also tends to spend several slots on one document, because
# every chunk of a document shares its title. 7 restores roughly the old
# context budget and gets more distinct sources in front of the model.
TOP_K = 7               # how many chunks to pull back per question

# The relevance gate. If the best chunk is further away than this, the system
# refuses to answer instead of handing the model thin material.
#
# LOWER IS BETTER: 0.3 is a close match, 0.9 is unrelated.
#
# Measured, not inherited. My five questions came back at 0.161, 0.176, 0.248,
# 0.464 and 0.700; the five OUT_OF_SCOPE ones at 0.787, 0.847, 0.849, 0.860 and
# 0.923. So the gap is 0.700 -> 0.787 and 0.74 sits in it, roughly 0.04 from
# each side.
#
# The starter's 0.6 would have been wrong here, and not by a little: it would
# refuse "Where can I sit and still have somewhere to plug in a laptop?" at
# 0.700, a question study_library_hours.txt answers outright. The three
# questions that name their subject all land under 0.25, and a cutoff chosen
# from those alone looks safe and silently breaks the other two.
#
# 0.087 is a narrower gap than I would like — see the README. It is narrow
# because a question phrased without the subject's name is genuinely closer to
# an unrelated question than to a keyword match.
THRESHOLD = 0.72


# ─── Models ──────────────────────────────────────────────────────────────────
# Embeddings run on your own machine and cost no API quota.
# Only generation calls out to a service.

# This is the model Chroma bundles, and leaving it alone is the fast path: it
# downloads about 80 MB from Chroma's own CDN and needs nothing else installed.
#
# Setting it to any other name — unit 2's "try a second embedding model"
# stretch option — switches to loading that model from Hugging Face instead,
# which needs `pip install 'sentence-transformers>=3.4,<3.5'` first. store.py
# says so with a real error message rather than a stack trace if you forget.
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
MODEL = os.getenv("AI201_MODEL", "gemini-3.5-flash-lite")


# ─── Rate limiting and quota guards ──────────────────────────────────────────
# You should not need to touch these. They exist so that a runaway loop costs
# you a warning instead of your whole day's allowance.

REQUESTS_PER_MINUTE = 30       # outgoing calls the limiter will allow per minute
SESSION_REQUEST_BUDGET = 300   # stop and warn rather than draining the daily quota
MAX_RETRIES = 4                # on 429 / resource-exhausted, with backoff

CACHE_ENABLED = os.getenv("AI201_CACHE", "1") != "0"
CACHE_DIR = ROOT / ".cache"


# ─── Paths ───────────────────────────────────────────────────────────────────

CORPORA_DIR = ROOT / "corpora"
CHROMA_DIR = ROOT / "chroma_db"
RESULTS_DIR = ROOT / "results"


def corpus_path(name: str | None = None) -> Path:
    """Folder holding the documents for a corpus."""
    return CORPORA_DIR / (name or CORPUS) / "documents"


def collection_name(name: str | None = None, variant: str = "default") -> str:
    """
    Name of the vector-store collection for a corpus.

    `variant` lets you index the same corpus two different ways and query both
    without deleting anything — you'll want that in unit 2 when you compare
    chunking strategies.

    Chroma is fussy about collection names: 3 to 63 characters, starting and
    ending with a letter or digit, and nothing but letters, digits, underscores
    and hyphens in between. If you bring your own corpus and name the folder
    something Chroma won't accept, this cleans it up rather than failing.
    """
    import re

    raw = f"{name or CORPUS}__{variant}"
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "-", raw)
    cleaned = cleaned.strip("_-")          # must start and end alphanumeric
    if not cleaned or not cleaned[0].isalnum():
        cleaned = f"c{cleaned}"
    if not cleaned[-1].isalnum():
        cleaned = f"{cleaned}0"
    return cleaned[:63].rstrip("_-") or "collection"
