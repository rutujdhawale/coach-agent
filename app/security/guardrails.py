import re
import time
from collections import defaultdict, deque
from typing import Deque, Dict, Optional, Tuple

from fastapi import HTTPException, Request

MAX_MESSAGE_LENGTH = 2000
STUDENT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above|system)\s+instructions", re.IGNORECASE),
    re.compile(r"(reveal|print|show|dump|repeat|output)\s+(your\s+)?(system\s+prompt|initial\s+prompt|instructions|rules|api\s*key|\.env)", re.IGNORECASE),
    re.compile(r"\b(jailbreak|dan\s+mode|developer\s+mode|bypass\s+safety|unrestricted\s+mode)\b", re.IGNORECASE),
    re.compile(r"(you\s+are\s+now|pretend\s+to\s+be|act\s+as\s+(?!a\s+(?:tutor|coach|teacher)))\b", re.IGNORECASE),
    re.compile(r"(<\|im_start\|>\s*system|\[system\]|###\s*system\s*:)", re.IGNORECASE),
    re.compile(r"(\$gt|\$ne|\$where|\$regex|\{\s*['\"]?\$)", re.IGNORECASE),
]

_UNSAFE_PATTERNS = [
    re.compile(r"\b(hack\s+exam|leak\s+exam|steal\s+paper|cheat\s+on\s+exam|fake\s+certificate)\b", re.IGNORECASE),
    re.compile(r"\b(malware|ransomware|phishing|ddos|sql\s+injection|exploit\s+code|bypass\s+login)\b", re.IGNORECASE),
    re.compile(r"\b(self[- ]?harm|suicide|build\s+a\s+bomb)\b", re.IGNORECASE),
]

_SECRET_REDACTION_PATTERNS = [
    (re.compile(r"gsk_[A-Za-z0-9]{16,}"), "[REDACTED_GROQ_KEY]"),
    (re.compile(r"AIza[0-9A-Za-z\-_]{20,}"), "[REDACTED_GEMINI_KEY]"),
    (re.compile(r"mongodb(\+srv)?://[^\s\"']+"), "[REDACTED_MONGODB_URI]"),
]


def is_valid_student_id(student_id: str) -> bool:
    return bool(student_id and STUDENT_ID_PATTERN.match(student_id))


def validate_student_id(student_id: str) -> str:
    """Ensure student_id is safe against NoSQL injection and path traversal."""
    if not is_valid_student_id(student_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid student_id. Use 1-64 alphanumeric characters, '-' or '_'.",
        )
    return student_id


def check_user_message(message: str) -> Tuple[bool, Optional[str]]:
    """Validate incoming chat text against length, prompt-injection, and safety rules."""
    if not message or not message.strip():
        return False, "Message cannot be empty."
    if len(message) > MAX_MESSAGE_LENGTH:
        return False, f"Message exceeds maximum length of {MAX_MESSAGE_LENGTH} characters."
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(message):
            return (
                False,
                "I cannot process requests that attempt to override system instructions or access internal data.",
            )
    for pattern in _UNSAFE_PATTERNS:
        if pattern.search(message):
            return (
                False,
                "I can only help with legitimate exam preparation, study plans, and academic coaching.",
            )
    return True, None


def sanitize_output(text: str) -> str:
    """Redact any accidentally leaked secrets or connection strings from responses."""
    sanitized = text
    for pattern, replacement in _SECRET_REDACTION_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


class InMemoryRateLimiter:
    """Simple sliding-window rate limiter per client key."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        bucket = self._hits[key]
        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please wait a moment before sending more requests.",
            )
        bucket.append(now)


rate_limiter = InMemoryRateLimiter()


async def enforce_rate_limit(request: Request) -> None:
    client_host = request.client.host if request.client else "unknown"
    rate_limiter.check(client_host)
