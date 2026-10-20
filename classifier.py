"""
classifier.py
=============
Keyword-based complaint classifier (version 1).

IMPORTANT: This file does NOT use machine learning. It uses simple,
transparent keyword rules that anyone can read and change. Because of this,
the results are helpful suggestions, NOT guaranteed to be correct.

The three main jobs are kept in separate functions so that
`classify_category()` can later be replaced by a trained ML model without
touching the rest of the project:

    1. classify_category()  -> Billing / Technical / Delivery / Service
    2. assign_priority()    -> High / Medium / Low (with a reason)
    3. get_support_team()   -> the team that should handle the complaint

`analyze_complaint()` runs all three and returns one result dictionary.
"""

import re

# ---------------------------------------------------------------------------
# 1. SETTINGS YOU CAN EDIT
# ---------------------------------------------------------------------------

CATEGORIES = ["Billing", "Technical", "Delivery", "Service"]

# Used when no keyword matches (unclear complaints).
DEFAULT_CATEGORY = "Service"

SUPPORT_TEAMS = {
    "Billing": "Billing Support Team",
    "Technical": "Technical Support Team",
    "Delivery": "Delivery Support Team",
    "Service": "Customer Service Team",
}

DISCLAIMER = (
    "This result is a suggestion made by simple keyword rules. "
    "It is not guaranteed to be correct, so a person should review it."
)

# Keywords are written in lowercase WITHOUT apostrophes ("cant", not "can't"),
# because clean_text() removes apostrophes before matching.
# A keyword with more words (a phrase) counts more, because it is more specific.
CATEGORY_KEYWORDS = {
    "Billing": [
        "bill", "billing", "invoice", "charge", "charged twice", "double charge",
        "overcharge", "payment", "pay", "paid", "refund", "money back", "price",
        "fee", "subscription", "transaction", "receipt", "credit card",
        "debit card", "credit", "deduct", "deduction", "wrong amount", "extra amount",
        "amount", "discount", "coupon", "promo code", "balance",
    ],
    "Technical": [
        "app", "application", "website", "web site", "site", "portal", "software",
        "crash", "bug", "error", "glitch", "freeze", "freezing", "frozen", "hang",
        "login", "log in", "sign in", "password", "otp", "verification code",
        "locked out", "account locked", "cannot log in", "cant log in",
        "cannot access", "cant access", "unable to access", "not working",
        "doesnt work", "dont work", "wont open", "wont load", "wont start",
        "slow", "slowly", "load", "page", "server", "outage", "is down",
        "completely down", "been down", "went down", "internet", "wifi",
        "network", "connection", "install", "laptop", "device", "technical",
    ],
    "Delivery": [
        "delivery", "deliver", "courier", "parcel", "package", "shipment",
        "shipping", "shipped", "ship", "tracking", "tracking number",
        "not arrived", "hasnt arrived", "didnt arrive", "never arrived",
        "arrive", "delay", "late", "dispatch", "damage", "missing item",
        "missing", "lost", "wrong item", "wrong address", "address",
        "not received", "never received", "rider", "driver", "postal",
        "post office", "logistics",
    ],
    "Service": [
        "service", "customer service", "customer support", "customer care",
        "support team", "support", "staff", "agent", "representative",
        "employee", "manager", "rude", "unhelpful", "impolite", "unprofessional",
        "behavior", "behaviour", "attitude", "ignore", "no response", "no reply",
        "no answer", "didnt respond", "didnt reply", "never replied",
        "never responded", "not replied", "poor service", "bad service",
        "bad experience", "feedback", "friendly",
    ],
}

# Priority rules. Each HIGH rule has a plain-English label that is shown to the
# user as the reason for the priority.
HIGH_PRIORITY_RULES = {
    "an urgent request": [
        "urgent", "urgently", "urgency", "asap", "as soon as possible",
        "immediately", "emergency", "right now", "critical",
    ],
    "an account access problem": [
        "cannot log in", "cant log in", "unable to log in", "cannot login",
        "cant login", "cannot access", "cant access", "unable to access",
        "locked out", "account locked", "account blocked", "account suspended",
    ],
    "a repeated failure": [
        "again and again", "repeatedly", "multiple times", "several times",
        "third time", "fourth time", "keeps", "keep happening", "every time",
    ],
    "a serious service interruption": [
        "completely down", "outage", "no service", "cannot use", "cant use",
        "unable to use", "cannot work", "cant work",
    ],
    "a possible security or fraud issue": [
        "hacked", "fraud", "unauthorized", "unauthorised", "scam", "stolen",
    ],
}

# Words that clearly say "this is small" -> Low priority.
LOW_PRIORITY_STRONG = [
    "minor", "small issue", "small problem", "slight", "slightly", "no rush",
    "no hurry", "cosmetic", "suggestion", "feedback", "just a question",
    "general question", "just curious", "not urgent",
]

# Question-style words -> Low priority, but ONLY if no problem word is present.
LOW_PRIORITY_QUESTION = [
    "how do i", "how can i", "how to", "question", "inquiry", "enquiry",
    "wondering", "would like to know", "want to know", "could you tell me",
    "information", "please let me know",
]

# Words that show a real problem exists (blocks the "question" rule above).
PROBLEM_WORDS = [
    "not working", "doesnt work", "dont work", "wrong", "damage", "broken",
    "fail", "error", "crash", "refund", "charge", "overcharge", "missing",
    "rude", "unhelpful", "never", "cant", "cannot", "wont", "didnt",
    "hasnt", "not arrived", "not received", "unable",
]


# ---------------------------------------------------------------------------
# 2. SMALL HELPER FUNCTIONS
# ---------------------------------------------------------------------------

def clean_text(text):
    """Make text easy to match: lowercase, no apostrophes, no punctuation."""
    if text is None:
        return ""
    text = str(text).lower()
    text = text.replace("\u2019", "'").replace("\u2018", "'")  # curly quotes
    text = text.replace("'", "")                               # can't -> cant
    text = re.sub(r"[^a-z0-9\s]", " ", text)                   # remove punctuation
    return " ".join(text.split())                              # single spaces


def _build_pattern(keyword):
    """
    Turn a keyword into a regular expression.
    - \\b means "whole word only", so 'app' does not match 'apple'.
    - The optional ending lets 'crash' also match 'crashes', 'crashed', 'crashing'.
    """
    words = clean_text(keyword).split()
    phrase = r"\s+".join(re.escape(word) for word in words)
    return re.compile(r"\b" + phrase + r"(?:s|es|ed|d|ing)?\b"), len(words)


def _compile(keywords):
    """Pre-build the patterns once, so matching is fast."""
    return [(kw, *_build_pattern(kw)) for kw in keywords]


def _find_matches(cleaned_text, compiled_keywords):
    """Return a list of (keyword, weight) for every keyword found in the text."""
    found = []
    for keyword, pattern, weight in compiled_keywords:
        if pattern.search(cleaned_text):
            found.append((keyword, weight))
    return found


def _quote_list(words):
    return ", ".join("'" + w + "'" for w in words)


# Patterns are built once when the file is loaded.
_CATEGORY_PATTERNS = {cat: _compile(kws) for cat, kws in CATEGORY_KEYWORDS.items()}
_HIGH_PATTERNS = {label: _compile(kws) for label, kws in HIGH_PRIORITY_RULES.items()}
_LOW_STRONG_PATTERNS = _compile(LOW_PRIORITY_STRONG)
_LOW_QUESTION_PATTERNS = _compile(LOW_PRIORITY_QUESTION)
_PROBLEM_PATTERNS = _compile(PROBLEM_WORDS)

# "not urgent" / "no urgency" must NOT count as an urgent request.
_NEGATED_URGENT = re.compile(r"\b(?:not|isnt|is not|no|never)\s+urgen(?:t|tly|cy)\b")


# ---------------------------------------------------------------------------
# 3. THE THREE MAIN FUNCTIONS
# ---------------------------------------------------------------------------

def classify_category(text):
    """
    Decide the category of a complaint.

    Returns a dictionary:
        category        - one of CATEGORIES
        matched         - keywords that were found for that category
        scores          - score of every category
        used_default    - True when nothing matched (unclear complaint)

    How it works: every matching keyword adds points (phrases add more).
    The category with the most points wins. If there is a tie, the category
    that comes first in CATEGORIES wins. If nothing matches, DEFAULT_CATEGORY
    is used.

    TO UPGRADE LATER: replace the inside of this function with an ML model
    but keep the same return format.
    """
    cleaned = clean_text(text)
    scores = {}
    matched = {}
    for category in CATEGORIES:
        hits = _find_matches(cleaned, _CATEGORY_PATTERNS[category])
        matched[category] = [keyword for keyword, _ in hits]
        scores[category] = sum(weight for _, weight in hits)

    best_score = max(scores.values())
    if best_score == 0:
        return {"category": DEFAULT_CATEGORY, "matched": [],
                "scores": scores, "used_default": True}

    for category in CATEGORIES:          # first category with the best score
        if scores[category] == best_score:
            return {"category": category, "matched": matched[category],
                    "scores": scores, "used_default": False}


def assign_priority(text):
    """
    Decide the priority (High / Medium / Low) and explain why.
    Returns (priority, reason).

    Order of the rules:
        1. HIGH   - urgent request, account access problem, repeated failure,
                    serious interruption, or possible fraud.
        2. LOW    - clearly minor, feedback, or a simple question.
        3. MEDIUM - everything else (a problem that needs attention).
    """
    cleaned = clean_text(text)

    # Remove phrases like "not urgent" so they are not seen as urgent.
    cleaned_for_high = _NEGATED_URGENT.sub(" ", cleaned)

    # Rule 1: High
    reasons = []
    for label, patterns in _HIGH_PATTERNS.items():
        hits = _find_matches(cleaned_for_high, patterns)
        if hits:
            reasons.append(label + " (" + _quote_list([k for k, _ in hits]) + ")")
    if reasons:
        return "High", "Marked High because the complaint mentions " + " and ".join(reasons) + "."

    # Rule 2: Low
    strong = _find_matches(cleaned, _LOW_STRONG_PATTERNS)
    if strong:
        return "Low", ("Marked Low because the complaint sounds minor or like feedback ("
                       + _quote_list([k for k, _ in strong]) + ").")
    question = _find_matches(cleaned, _LOW_QUESTION_PATTERNS)
    problems = _find_matches(cleaned, _PROBLEM_PATTERNS)
    if question and not problems:
        return "Low", ("Marked Low because it looks like a general question or routine request ("
                       + _quote_list([k for k, _ in question]) + ").")

    # Rule 3: Medium (default)
    return "Medium", ("Marked Medium because it describes a problem that needs attention, "
                      "but no urgent signs were found.")


def get_support_team(category):
    """Return the support team for a category (unknown -> Customer Service Team)."""
    return SUPPORT_TEAMS.get(category, SUPPORT_TEAMS[DEFAULT_CATEGORY])


def analyze_complaint(title, description):
    """Run category, priority and team selection and return one result."""
    combined_text = f"{title or ''} {description or ''}"

    category_result = classify_category(combined_text)
    category = category_result["category"]
    priority, priority_reason = assign_priority(combined_text)

    if category_result["used_default"]:
        category_reason = ("No category keywords were found, so this complaint was placed in the "
                           f"default '{DEFAULT_CATEGORY}' category for a person to check.")
    else:
        category_reason = (f"Classified as {category} because these keywords were found: "
                           + _quote_list(category_result["matched"]) + ".")

    return {
        "category": category,
        "priority": priority,
        "team": get_support_team(category),
        "matched_keywords": category_result["matched"],
        "used_default_category": category_result["used_default"],
        "category_reason": category_reason,
        "priority_reason": priority_reason,
        "disclaimer": DISCLAIMER,
    }
