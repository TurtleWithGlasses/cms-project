"""
ETag Middleware

Adds ETag headers to GET JSON responses and supports conditional
requests with ``If-None-Match`` for 304 Not Modified responses.
"""

import hashlib

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

EXCLUDED_PATHS = frozenset({"/metrics", "/health", "/ready"})


class ETagMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds ETag headers to GET JSON responses and handles
    ``If-None-Match`` for 304 Not Modified.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Only process GET requests
        if request.method != "GET":
            return await call_next(request)

        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        response = await call_next(request)

        # Only add ETags to successful JSON responses
        content_type = response.headers.get("content-type", "")
        if response.status_code != 200 or "application/json" not in content_type:
            return response

        # Skip file downloads
        if "content-disposition" in response.headers:
            return response

        # Read the response body to compute ETag
        body = b""
        async for chunk in response.body_iterator:
            body += chunk if isinstance(chunk, bytes) else chunk.encode()

        etag = '"' + hashlib.md5(body).hexdigest() + '"'  # nosec S324

        # Check If-None-Match
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and if_none_match == etag:
            return Response(status_code=304, headers={"ETag": etag})

        # Return response with ETag header
        headers = dict(response.headers)
        headers["ETag"] = etag
        return Response(
            content=body,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )
