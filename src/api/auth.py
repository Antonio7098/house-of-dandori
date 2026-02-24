import os
from flask import Blueprint, jsonify, request
import requests

from src.core.config import (
    SUPABASE_URL,
    SUPABASE_ANON_KEY,
    SUPABASE_SERVICE_KEY,
    DEV_BYPASS_AUTH,
)
from src.core.errors import AuthenticationError, BadRequestError, handle_exception
from src.core.logging import api_logger

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    if DEV_BYPASS_AUTH:
        return jsonify(
            {"token": "dev_token", "user": {"email": "dev@localhost", "id": "dev_user"}}
        )

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return jsonify(
            {
                "error": "Supabase not configured. Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables."
            }
        ), 500

    data = request.get_json()
    if not data:
        error_dict, status_code = handle_exception(
            BadRequestError("Request body required")
        )
        return jsonify(error_dict), status_code

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        error_dict, status_code = handle_exception(
            BadRequestError("Email and password required")
        )
        return jsonify(error_dict), status_code

    try:
        response = requests.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            json={"email": email, "password": password},
            headers={
                "Content-Type": "application/json",
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            },
        )

        if response.status_code != 200:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get(
                "msg", error_data.get("error_description", "Authentication failed")
            )

            # Check if email needs confirmation
            if "email" in error_msg.lower() or "confirm" in error_msg.lower():
                error_dict, status_code = handle_exception(
                    AuthenticationError(
                        "Email not confirmed. Please check your email to verify your account."
                    )
                )
                return jsonify(error_dict), 401

            api_logger.log_error(
                Exception(f"Supabase auth failed: {response.text}"), {"email": email}
            )
            error_dict, status_code = handle_exception(
                AuthenticationError("Invalid email or password")
            )
            return jsonify(error_dict), 401

        token_data = response.json()
        access_token = token_data.get("access_token")

        return jsonify({"token": access_token, "user": token_data.get("user")})

    except Exception as e:
        api_logger.log_error(e, {"email": email})
        return jsonify({"error": "Authentication failed"}), 500


@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    return jsonify({"message": "Logged out successfully"})


@auth_bp.route("/api/auth/profile", methods=["GET"])
def get_profile():
    from src.core.auth import auth_service

    if auth_service.dev_bypass:
        return jsonify({"user": {"email": "dev@localhost", "id": "dev_user"}})

    token = auth_service.get_token_from_header()
    if not token:
        return jsonify({"error": "No token provided"}), 401

    try:
        user = auth_service.verify_token(token)
        return jsonify({"user": user})
    except Exception as e:
        return jsonify({"error": str(e)}), 401


@auth_bp.route("/api/auth/signup", methods=["POST"])
def signup():
    if DEV_BYPASS_AUTH:
        return jsonify(
            {
                "message": "Account created successfully (dev mode)",
                "user": {"email": "dev@localhost", "id": "dev_user"},
            }
        )

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return jsonify(
            {
                "error": "Supabase not configured. Please set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY environment variables."
            }
        ), 500

    data = request.get_json()
    if not data:
        error_dict, status_code = handle_exception(
            BadRequestError("Request body required")
        )
        return jsonify(error_dict), status_code

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        error_dict, status_code = handle_exception(
            BadRequestError("Email and password required")
        )
        return jsonify(error_dict), status_code

    if len(password) < 6:
        error_dict, status_code = handle_exception(
            BadRequestError("Password must be at least 6 characters")
        )
        return jsonify(error_dict), status_code

    try:
        response = requests.post(
            f"{SUPABASE_URL}/auth/v1/signup",
            json={"email": email, "password": password},
            headers={
                "Content-Type": "application/json",
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            },
        )

        if response.status_code != 200:
            api_logger.log_error(
                Exception(f"Supabase signup failed: {response.text}"), {"email": email}
            )
            error_dict, status_code = handle_exception(
                AuthenticationError("Could not create account")
            )
            return jsonify(error_dict), 400

        user_data = response.json()

        return jsonify(
            {
                "message": "Account created successfully. Please check your email to verify.",
                "user": user_data.get("user"),
            }
        )

    except Exception as e:
        api_logger.log_error(e, {"email": email})
        return jsonify({"error": "Signup failed"}), 500
