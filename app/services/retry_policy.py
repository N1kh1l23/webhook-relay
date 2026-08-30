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
