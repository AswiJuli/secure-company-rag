import re


MAX_QUESTION_LENGTH = 1000


# -------------------------------------------------
# Prompt-injection patterns
# -------------------------------------------------

INJECTION_PATTERNS = [
    re.compile(
        r"\b(ignore|disregard|forget)\b"
        r".{0,60}"
        r"\b(instructions?|rules?|prompts?)\b",
        re.IGNORECASE | re.DOTALL
    ),

    re.compile(
        r"\b(reveal|show|print|repeat)\b"
        r".{0,60}"
        r"\b(system prompt|hidden instructions?|"
        r"developer message)\b",
        re.IGNORECASE | re.DOTALL
    ),

    re.compile(
        r"\b(bypass|disable|override|circumvent)\b"
        r".{0,60}"
        r"\b(security|rules?|guardrails?|"
        r"permissions?|access controls?)\b",
        re.IGNORECASE | re.DOTALL
    ),

    re.compile(
        r"\b(pretend|act|behave)\b"
        r".{0,30}"
        r"\b(admin|administrator|executive|root)\b",
        re.IGNORECASE | re.DOTALL
    ),

    re.compile(
        r"\b(jailbreak|developer mode|dan mode)\b",
        re.IGNORECASE
    )
]


# -------------------------------------------------
# Clearly out-of-scope patterns
# -------------------------------------------------

OUT_OF_SCOPE_PATTERNS = [
    re.compile(
        r"\b(favou?rite|recommend|suggest|best)\b"
        r".{0,40}"
        r"\b(movie|film|song|music|book|tv show)s?\b",
        re.IGNORECASE | re.DOTALL
    ),

    re.compile(
        r"\b(movie|film)s?\b"
        r".{0,30}"
        r"\b(watch|recommend|suggest)\b",
        re.IGNORECASE | re.DOTALL
    ),

    re.compile(
        r"\b(cricket|football|soccer|basketball)\b"
        r".{0,40}"
        r"\b(score|match|result|standings?)\b",
        re.IGNORECASE | re.DOTALL
    ),

    re.compile(
        r"\b(weather|temperature|forecast)\b"
        r".{0,30}"
        r"\b(today|tomorrow|outside|currently|now)\b",
        re.IGNORECASE | re.DOTALL
    ),

    re.compile(
        r"\b(recipe|cooking instructions?|"
        r"how to cook)\b",
        re.IGNORECASE
    ),

    re.compile(
        r"\b(election results?|celebrity news)\b",
        re.IGNORECASE
    ),

    re.compile(
        r"\btell me\b"
        r".{0,20}"
        r"\b(joke|riddle)\b",
        re.IGNORECASE | re.DOTALL
    )
]


def matches_any_pattern(text, patterns):
    """
    Returns True when the text matches at least one
    regular-expression pattern.
    """

    return any(
        pattern.search(text)
        for pattern in patterns
    )


def check_input(question):
    """
    Checks a user question before retrieval.

    Returns:
        (True, None) when the question is allowed.

        (False, reason) when the question is blocked.
    """

    if not isinstance(question, str):
        return (
            False,
            "The question must be text."
        )

    normalized_question = question.strip()

    if not normalized_question:
        return (
            False,
            "The question cannot be empty."
        )

    if len(normalized_question) > MAX_QUESTION_LENGTH:
        return (
            False,
            "The question is too long."
        )

    if matches_any_pattern(
        normalized_question,
        INJECTION_PATTERNS
    ):
        return (
            False,
            "Possible prompt-injection attempt detected."
        )

    if matches_any_pattern(
        normalized_question,
        OUT_OF_SCOPE_PATTERNS
    ):
        return (
            False,
            "This question is outside the scope "
            "of company documents."
        )

    return True, None