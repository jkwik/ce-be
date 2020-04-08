from backend import app
from backend.middleware.middleware import http_guard

@app.route("/middleware", methods=["GET"])
@http_guard(renew=True, nullable=False)
def middleware(token_claims):
    return {
        "token_claims": token_claims
    }

@app.route("/health", methods=['GET'])
def health():
    return {
        "success": True
    }
