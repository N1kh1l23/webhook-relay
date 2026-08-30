import httpx
import pytest

from app.services.retry_policy import Outcome, classify, next_delay


@pytest.mark.parametrize("status_code, expected", [(200, Outcome.SUCCESS),
                                                   (299, Outcome.SUCCESS),
                                                   (199, Outcome.RETRY),
                                                   (300, Outcome.TERMINAL),
                                                   (500, Outcome.RETRY),
                                                   (502, Outcome.RETRY),
                                                   (503, Outcome.RETRY),
                                                   (504, Outcome.RETRY),
                                                   (429, Outcome.RETRY),
                                                   (400, Outcome.TERMINAL),
                                                   (401, Outcome.TERMINAL),
                                                   (404, Outcome.TERMINAL),
                                                   (422, Outcome.TERMINAL)])
def test_classify_status(status_code, expected):
    response = httpx.Response(status_code)
    assert classify(response) is expected

@pytest.mark.parametrize("exception_class, expected",
                         [(httpx.ConnectTimeout, Outcome.RETRY),
                          (httpx.ReadTimeout, Outcome.RETRY),
                          (httpx.ConnectError, Outcome.RETRY),
                          (httpx.RemoteProtocolError, Outcome.RETRY),
                          (httpx.UnsupportedProtocol, Outcome.TERMINAL),
                          (httpx.LocalProtocolError, Outcome.TERMINAL),
                          (httpx.InvalidURL, Outcome.TERMINAL)])
def test_classify_exception(exception_class, expected):
    exception = exception_class("boom")
    assert classify(exception) is expected


def test_next_delay_within_bounds():
    previous = 10000
    for x in range(500):
        result = next_delay(previous, base_ms=1000, cap_ms=300000)
        assert 1000 <= result <= 30000

def test_next_delay_varies():
    previous = 10000
    results = set()
    for x in range(500):
        result = next_delay(previous, base_ms=1000, cap_ms=300000)
        results.add(result)
    assert len(results) > 1

def test_next_delay_respects_cap():
    previous = 200000
    for x in range(500):
        result = next_delay(previous, base_ms=1000, cap_ms=300000)
        assert result <= 300000

def test_next_delay_floors_below_base():
    result = next_delay(0, base_ms=1000, cap_ms=300000)
    assert result == 1000