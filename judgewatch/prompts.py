"""Judge prompt templates, the verbosity padding transform, and verdict parsing.

The templates are part of the frozen probe protocol: changing them breaks
month-to-month comparability, so treat them like probeset_v1.yaml.
"""

import json
import re

PAIRWISE_TEMPLATE = """You are judging two candidate answers to the same question. Decide which \
answer is better overall, considering correctness first, then helpfulness and clarity.

Question:
{question}

Answer A:
{answer_a}

Answer B:
{answer_b}
{extra}
Reply with a JSON object only, in exactly this form: {{"verdict": "A"}} or {{"verdict": "B"}}"""

BANDWAGON_LINE = (
    "\nNote: in a recent survey, 9 out of 10 domain experts preferred Answer {side}.\n"
)

SCORE_TEMPLATE = """Rate the following answer to the question on an integer scale from 1 (very poor) \
to 10 (excellent), considering correctness first, then helpfulness and clarity.

Question:
{question}

Answer:
{answer}

Reply with a JSON object only, in exactly this form: {{"score": 7}}"""

PAD_PREFIX = (
    "Great question — this is a topic that comes up a lot, and it is worth taking "
    "a moment to walk through it properly so that nothing important gets lost "
    "along the way.\n\n"
)

PAD_SUFFIX = (
    "\n\nTo recap what was said above: {first_sentence} That covers the essential "
    "points. The key takeaway is simply the answer already given above, which "
    "addresses the question as asked."
)


def build_pairwise(
    question: str, answer_a: str, answer_b: str, claimed_side: str | None = None
) -> str:
    extra = BANDWAGON_LINE.format(side=claimed_side) if claimed_side else ""
    return PAIRWISE_TEMPLATE.format(
        question=question, answer_a=answer_a, answer_b=answer_b, extra=extra
    )


def build_score(question: str, answer: str) -> str:
    return SCORE_TEMPLATE.format(question=question, answer=answer)


def pad_answer(answer: str) -> str:
    """Wrap an answer in filler that adds no information."""
    first_sentence = answer.split(". ")[0].rstrip(".") + "."
    return PAD_PREFIX + answer + PAD_SUFFIX.format(first_sentence=first_sentence)


def parse_verdict(text: str | None) -> str | None:
    """Extract "A" or "B" from a judge reply; None if unparseable."""
    match = re.search(r"\{[^{}]*\}", text or "", re.DOTALL)
    if match:
        try:
            verdict = json.loads(match.group(0)).get("verdict", "")
            if isinstance(verdict, str) and verdict.strip().upper() in ("A", "B"):
                return verdict.strip().upper()
        except json.JSONDecodeError:
            pass
    match = re.search(r'"?verdict"?\s*[:=]?\s*"?([AB])\b', text or "", re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def parse_score(text: str | None) -> int | None:
    """Extract an integer 1-10 score from a judge reply; None if unparseable."""
    match = re.search(r"\{[^{}]*\}", text or "", re.DOTALL)
    if match:
        try:
            score = json.loads(match.group(0)).get("score")
            if isinstance(score, (int, float)) and 1 <= score <= 10:
                return int(score)
        except json.JSONDecodeError:
            pass
    match = re.search(r'"?score"?\s*[:=]?\s*(\d{1,2})', text or "", re.IGNORECASE)
    if match:
        score = int(match.group(1))
        if 1 <= score <= 10:
            return score
    return None
