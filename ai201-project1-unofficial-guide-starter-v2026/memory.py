"""
Conversational memory — the stretch feature.

Lets the next question build on the last one, with no second model call and
without loosening the relevance gate for any question that can stand on its own.

The rule, in one sentence: a question the gate has ALREADY refused, and that
reads like a follow-up rather than a new topic, gets one more try with the
previous question glued to the front — and that second try has to clear a
STRICTER cutoff than a fresh question does.

Three consequences worth being explicit about:

  • Nothing that works today changes. A question that passes the gate on its
    own never reaches this file. `run_eval.py` and `serve.py` never build a
    Memory at all, so the graded paths are exactly what they were.
  • No extra API calls. Expansion is string work; the retry is a local
    embedding and a Chroma query, both of which run on your laptop.
  • Memory changes what gets RETRIEVED. It never puts anything into the prompt
    that wasn't retrieved for this turn, so every answer is still grounded in
    chunks the gate approved on this turn.
"""

from dataclasses import dataclass, field


# How long a question can be and still count as a follow-up. A real follow-up
# is short because most of it is implied. "What is the recommended dosage of
# ibuprofen for a headache" is nine words of subject matter of its own.
MAX_FOLLOWUP_WORDS = 8

# A rescued question must clear THRESHOLD * this. With my cutoff of 0.74 that
# is 0.666. Memory is help, and help should have to score better than no help.
FOLLOWUP_TIGHTEN = 0.9

# Words that point back at something already said. A question containing one of
# these cannot be read on its own — which is what makes it a follow-up.
ANAPHORA = {
    "it", "its", "it's", "they", "them", "their", "theirs",
    "that", "this", "those", "these", "there", "then",
    "one", "ones", "he", "she", "him", "her", "his", "hers",
    "same", "both", "either",
}

# Elliptical openers: a follow-up with the subject dropped entirely.
OPENERS = (
    "what about", "how about", "and what", "and how", "and why",
    "what else", "anything else", "any others", "why not", "how so",
    "how come", "and is", "and does", "and can",
)

_PUNCT = ".,!?;:'\"()[]"


def _words(text: str) -> list[str]:
    stripped = (w.strip(_PUNCT).lower() for w in text.split())
    return [w for w in stripped if w]


def _introduces_a_new_topic(question: str) -> bool:
    """True if this question names a subject of its own.

    A capitalised word that isn't the first one, or a digit, is the cheapest
    signal there is that the asker has named something new — "Mongolia",
    "Rust", "1994". Follow-ups don't name things; not naming things is the
    entire point of a follow-up. This is the check that stops an out-of-scope
    question riding in on the previous one's topic.
    """
    for token in question.split()[1:]:
        bare = token.strip(_PUNCT)
        if not bare:
            continue
        if bare[0].isupper() or any(ch.isdigit() for ch in bare):
            return True
    return False


def looks_like_a_followup(question: str) -> bool:
    """Short, points at something already said, and names nothing new."""
    words = _words(question)
    if not words or len(words) > MAX_FOLLOWUP_WORDS:
        return False
    if _introduces_a_new_topic(question):
        return False
    if question.strip().lower().startswith(OPENERS):
        return True
    return any(w in ANAPHORA for w in words)


@dataclass
class Memory:
    """One conversation's worth of context. Built once per REPL session."""

    topic: str = ""
    sources: list[str] = field(default_factory=list)
    turns: int = 0

    def expand(self, question: str) -> str | None:
        """The follow-up rewritten as a standalone query, or None.

        None is the common case and the safe one: no topic yet, or a question
        that reads perfectly well by itself, gets no help at all.
        """
        if not self.topic:
            return None
        if not looks_like_a_followup(question):
            return None
        return f"{self.topic} {question}"

    def threshold(self, base: float) -> float:
        """The cutoff a rescued question has to clear. Stricter than `base`."""
        return base * FOLLOWUP_TIGHTEN

    def remember(self, question: str, sources: list[str], rescued: bool = False) -> None:
        """Record a turn that produced an answer.

        A `rescued` turn deliberately does NOT become the new topic. If it did,
        every follow-up would lengthen the string the next one gets glued to,
        and by turn five you'd be embedding a paragraph. The topic stays the
        last question that stood up on its own.
        """
        if not rescued:
            self.topic = question
        self.sources = list(sources)
        self.turns += 1

    def forget(self) -> None:
        """Drop the thread. Called on every refusal, and by 'new topic'."""
        self.topic = ""
        self.sources = []
