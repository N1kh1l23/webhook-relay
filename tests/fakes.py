"""
HTTP client doubles shared across test modules.

These replace httpx.AsyncClient inside app.services.delivery via monkeypatch.
Each returns a real httpx.Response rather than a look-alike object, because
classify() branches on isinstance(result, httpx.Response) — a duck-typed
stand-in silently falls through to the RETRY default.
"""

import httpx


class ClientReplacement:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def post(self, url, *args, **kwargs):
        return httpx.Response(200, text="ok")

    async def __aexit__(self, exc_type, exc, tb):
        pass


class ClientReplacementFail:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def post(self, url, *args, **kwargs):
        return httpx.Response(500, text="yes")

    async def __aexit__(self, exc_type, exc, tb):
        pass


class ClientTimeout:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def post(self, url, *args, **kwargs):
        raise httpx.TimeoutException("No response exists")

    async def __aexit__(self, exc_type, exc, tb):
        pass


class ClientInvalidURL:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def post(self, url, *args, **kwargs):
        raise httpx.InvalidURL("Not a url")

    async def __aexit__(self, exc_type, exc, tb):
        pass
