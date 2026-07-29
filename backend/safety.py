"""
Minimal safety layer. This is a floor, not a ceiling - it catches the
obvious cases so the demo doesn't ship with zero guardrails, but it is
NOT a substitute for a real moderation classifier before this touches
real children. See the README "Before this touches a real child" section.
"""

UNSAFE_TOPICS = [
    "kill", "suicide", "weapon", "gun", "knife", "sex", "drug", "blood",
    "die", "death", "hurt yourself", "abuse",
]

FALLBACK_REPLY_EN = (
    "That's a big question — let's ask a grown-up about that together. "
    "Want to hear a story instead?"
)
FALLBACK_REPLY_TA = (
    "அது ஒரு பெரிய கேள்வி — அதை பெரியவர்களிடம் சேர்ந்து கேட்போம். "
    "அதற்குள் ஒரு கதை கேட்கலாமா?"
)


def is_input_safe(text: str) -> bool:
    lowered = text.lower()
    return not any(topic in lowered for topic in UNSAFE_TOPICS)


def is_output_safe(text: str) -> bool:
    lowered = text.lower()
    return not any(topic in lowered for topic in UNSAFE_TOPICS)


def fallback_reply(language: str) -> str:
    return FALLBACK_REPLY_TA if language == "ta" else FALLBACK_REPLY_EN
