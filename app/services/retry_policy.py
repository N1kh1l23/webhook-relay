import random
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from enum import Enum

import httpx


class Outcome(Enum):
    SUCCESS = "success"
    RETRY = "retry"
    TERMINAL = "terminal"


def classify(result: httpx.Response | Exception) -> Outcome:
    if isinstance(result, httpx.Response):
        if result.status_code == 429:
            return Outcome.RETRY
        elif 200 <= result.status_code < 300:
            return Outcome.SUCCESS
        elif 400 <= result.status_code < 500:
            return Outcome.TERMINAL
        elif 500 <= result.status_code < 600:
            return Outcome.RETRY
        elif result.status_code < 200:
            return Outcome.RETRY
        return Outcome.TERMINAL
    elif isinstance(result, (httpx.UnsupportedProtocol,
                             httpx.LocalProtocolError,
                             httpx.InvalidURL)):
        return Outcome.TERMINAL
    elif isinstance(result, httpx.TimeoutException):
        return Outcome.RETRY
    elif isinstance(result, httpx.NetworkError):
        return Outcome.RETRY
    elif isinstance(result, httpx.RemoteProtocolError):
        return Outcome.RETRY
    return Outcome.RETRY

def next_delay(previous_delay_ms: int, base_ms: int = 15_000, cap_ms: int = 300_000) -> int:
    randnum = random.randint(base_ms, max(previous_delay_ms * 3, base_ms))
    return min(randnum, cap_ms)

def parse_retry_after(response: httpx.Response, max_honored_ms: int = 600_000) -> int | None:
    header_value = response.headers.get("Retry-After")
    if header_value is None:
        return None
    try:
        seconds = int(header_value)
    except ValueError:
        try:
            target = parsedate_to_datetime(header_value)
        except (ValueError, TypeError):
            return None
        seconds = int((target - datetime.now(timezone.utc)).total_seconds())
    if seconds < 0:
        return None
    return min(seconds * 1000, max_honored_ms)

