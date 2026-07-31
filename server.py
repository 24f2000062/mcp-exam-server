import hashlib
from contextvars import ContextVar
from mcp.server.transport_security import TransportSecuritySettings
from mcp.server.fastmcp import FastMCP


EMAIL = "24f2000062@ds.study.iitm.ac.in".strip().lower()

exam_challenge = ContextVar("exam_challenge", default=None)

mcp = FastMCP(
    "IITM Exam Challenge Server",
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "127.0.0.1:*",
            "localhost:*",
            "[::1]:*",
            "mcp-exam-server-nzw4.onrender.com",
        ],
        allowed_origins=[
            "http://127.0.0.1:*",
            "http://localhost:*",
            "http://[::1]:*",
            "https://mcp-exam-server-nzw4.onrender.com",
        ],
    ),
)

@mcp.tool()
async def solve_challenge() -> str:
    """Solve the challenge supplied in the current HTTP request header."""

    challenge = exam_challenge.get()

    if not challenge:
        raise ValueError("Missing X-Exam-Challenge header")

    raw = f"{challenge}:{EMAIL}"

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()[:16]


mcp_app = mcp.streamable_http_app()


class ChallengeHeaderMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        challenge = None

        for key, value in scope.get("headers", []):
            if key.lower() == b"x-exam-challenge":
                challenge = value.decode("latin-1")
                break

        token = exam_challenge.set(challenge)

        try:
            await self.app(scope, receive, send)
        finally:
            exam_challenge.reset(token)


app = ChallengeHeaderMiddleware(mcp_app)