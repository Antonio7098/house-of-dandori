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
        # Generate a fake token for dev mode
        return jsonify(
            {"token": "dev_token", "user": {"email": request.json.get("email", "dev@localhost"), "id": "dev_user"}}
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

        if not access_token:
            return jsonify({"error": "Login failed - no token received"}), 401

        # Get user info from the response
        user = token_data.get("user", {})
        if not user and "email" in token_data:
            user = {"email": token_data.get("email"), "id": token_data.get("id")}

        return jsonify({"token": access_token, "user": user})

    except Exception as e:
        api_logger.log_error(e, {"email": email})
        return jsonify({"error": "Authentication failed"}), 500


@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    return jsonify({"message": "Logged out successfully"})


@auth_bp.route("/api/auth/profile", methods=["GET", "PUT"])
def profile():
    from src.core.auth import auth_service
    from src.models.database import get_db_connection

    if auth_service.dev_bypass:
        user_id = "dev_user"
        email = "dev@localhost"
    else:
        token = auth_service.get_token_from_header()
        if not token:
            return jsonify({"error": "No token provided"}), 401
        try:
            user = auth_service.verify_token(token)
            user_id = user["id"]
            email = user.get("email")
        except Exception as e:
            return jsonify({"error": str(e)}), 401

    if request.method == "GET":
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
            profile_row = cursor.fetchone()
            conn.close()

            profile_data = dict(profile_row) if profile_row else {}
            return jsonify({
                "user": {
                    "id": user_id,
                    "email": email,
                    "name": profile_data.get("name", ""),
                    "location": profile_data.get("location", ""),
                    "avatar": profile_data.get("avatar", "")
                }
            })
        except Exception as e:
            api_logger.log_error(e, {"user_id": user_id})
            return jsonify({"error": "Failed to fetch profile"}), 500

    elif request.method == "PUT":
        data = request.get_json()
        name = data.get("name", "")
        location = data.get("location", "")
        avatar = data.get("avatar", "")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO profiles (user_id, name, location, avatar)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    name = excluded.name,
                    location = excluded.location,
                    avatar = excluded.avatar
                """,
                (user_id, name, location, avatar)
            )
            conn.commit()
            conn.close()

            return jsonify({
                "id": user_id,
                "email": email,
                "name": name,
                "location": location,
                "avatar": avatar
            })
        except Exception as e:
            api_logger.log_error(e, {"user_id": user_id})
            return jsonify({"error": "Failed to update profile"}), 500


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
