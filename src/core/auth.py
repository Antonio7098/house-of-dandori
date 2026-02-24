import os
from functools import wraps
from typing import Optional, Dict, Any

import jwt
from flask import request, jsonify, g

from src.core.config import (
    SUPABASE_URL,
    SUPABASE_ANON_KEY,
    SUPABASE_SERVICE_KEY,
    DEV_BYPASS_AUTH,
    ENVIRONMENT,
)
from src.core.errors import AuthenticationError, handle_exception
from src.core.logging import get_logger

logger = get_logger("auth")


class AuthService:
    def __init__(self):
        self.supabase_url = SUPABASE_URL
        self.anon_key = SUPABASE_ANON_KEY
        self.service_key = SUPABASE_SERVICE_KEY
        self.dev_bypass = DEV_BYPASS_AUTH
        self.environment = ENVIRONMENT

    def verify_token(self, token: str) -> Dict[str, Any]:
        if not token:
            raise AuthenticationError("No token provided")

        if self.dev_bypass:
            logger.info("Dev bypass enabled, skipping token verification")
            return {
                "sub": "dev_user",
                "email": "dev@localhost",
                "role": "authenticated",
            }

        if not self.supabase_url or not self.anon_key:
            logger.warning("Supabase not configured, rejecting request")
            raise AuthenticationError("Authentication not configured")

        try:
            payload = jwt.decode(
                token,
                self.anon_key,
                algorithms=["HS256"],
                audience="authenticated",
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")

    def get_token_from_header(self) -> Optional[str]:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        return parts[1]

    def get_current_user(self) -> Optional[Dict[str, Any]]:
        if hasattr(g, "user"):
            return g.user
        return None


auth_service = AuthService()


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if auth_service.dev_bypass:
            g.user = {
                "sub": "dev_user",
                "email": "dev@localhost",
                "role": "authenticated",
            }
            return f(*args, **kwargs)

        token = auth_service.get_token_from_header()
        if not token:
            error_dict, status_code = handle_exception(
                AuthenticationError("Authorization token required")
            )
            return jsonify(error_dict), status_code

        try:
            user = auth_service.verify_token(token)
            g.user = user
        except AuthenticationError as e:
            error_dict, status_code = handle_exception(e)
            return jsonify(error_dict), status_code

        return f(*args, **kwargs)

    return decorated


def optional_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = auth_service.get_token_from_header()
        if token:
            try:
                user = auth_service.verify_token(token)
                g.user = user
            except AuthenticationError:
                g.user = None
        else:
            g.user = None

        return f(*args, **kwargs)

    return decorated
