import os
from typing import Any, Dict

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
from src.models.database import get_db_connection

auth_bp = Blueprint("auth", __name__)


def _get_profile_from_db(user_id: str) -> Dict[str, Any]:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        use_postgres = bool(os.environ.get("DATABASE_URL"))
        placeholder = "%s" if use_postgres else "?"
        cursor.execute(
            f"SELECT name, email, location, bio FROM user_profiles WHERE user_id = {placeholder}",
            (user_id,),
        )
        row = cursor.fetchone()
        if row:
            if isinstance(row, dict):
                return {k: v for k, v in row.items() if v is not None}
            return {
                k: v
                for k, v in zip(["name", "email", "location", "bio"], row)
                if v is not None
            }
        return {}
    finally:
        conn.close()


def _upsert_profile_in_db(user_id: str, profile: Dict[str, Any]) -> None:
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        use_postgres = bool(os.environ.get("DATABASE_URL"))
        if use_postgres:
            cursor.execute(
                """INSERT INTO user_profiles (user_id, name, email, location, bio, updated_at)
                   VALUES (%s, %s, %s, %s, %s, NOW())
                   ON CONFLICT (user_id) DO UPDATE SET
                       name = EXCLUDED.name,
                       email = EXCLUDED.email,
                       location = EXCLUDED.location,
                       bio = EXCLUDED.bio,
                       updated_at = NOW()""",
                (
                    user_id,
                    profile.get("name"),
                    profile.get("email"),
                    profile.get("location"),
                    profile.get("bio"),
                ),
            )
        else:
            cursor.execute(
                """INSERT INTO user_profiles (user_id, name, email, location, bio, updated_at)
                   VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT (user_id) DO UPDATE SET
                       name = excluded.name,
                       email = excluded.email,
                       location = excluded.location,
                       bio = excluded.bio,
                       updated_at = CURRENT_TIMESTAMP""",
                (
                    user_id,
                    profile.get("name"),
                    profile.get("email"),
                    profile.get("location"),
                    profile.get("bio"),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def _resolve_user_identifier(user: Dict[str, Any]) -> str | None:
    return user.get("sub") or user.get("id") or user.get("email")


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


@auth_bp.route("/api/auth/profile", methods=["GET"])
def get_profile():
    from src.core.auth import auth_service

    if auth_service.dev_bypass:
        base_user = {"email": "dev@localhost", "id": "dev_user"}
        profile = _get_profile_from_db("dev_user")
        return jsonify({"user": {**base_user, **profile}})

    token = auth_service.get_token_from_header()
    if not token:
        return jsonify({"error": "No token provided"}), 401

    try:
        user = auth_service.verify_token(token)
        user_id = _resolve_user_identifier(user)
        profile = _get_profile_from_db(user_id or "")
        return jsonify({"user": {**user, **profile}})
    except Exception as e:
        return jsonify({"error": str(e)}), 401


@auth_bp.route("/api/auth/profile", methods=["PUT"])
def update_profile():
    from src.core.auth import auth_service

    data = request.get_json(silent=True) or {}

    if auth_service.dev_bypass:
        base_user = {"email": "dev@localhost", "id": "dev_user"}
        user_id = "dev_user"
    else:
        token = auth_service.get_token_from_header()
        if not token:
            return jsonify({"error": "No token provided"}), 401

        try:
            base_user = auth_service.verify_token(token)
            user_id = _resolve_user_identifier(base_user)
        except Exception as e:
            return jsonify({"error": str(e)}), 401

    if not user_id:
        return jsonify({"error": "Unable to determine user"}), 400

    allowed_fields = {"name", "location", "bio", "email"}
    profile_updates = {k: v for k, v in data.items() if k in allowed_fields}

    current_profile = _get_profile_from_db(user_id)
    updated_profile = {**current_profile, **profile_updates}
    _upsert_profile_in_db(user_id, updated_profile)

    return jsonify({**base_user, **updated_profile})


@auth_bp.route("/api/auth/review-count", methods=["GET"])
def get_user_review_count():
    from src.core.auth import auth_service

    if auth_service.dev_bypass:
        user_id = "dev_user"
    else:
        token = auth_service.get_token_from_header()
        if not token:
            return jsonify({"error": "No token provided"}), 401
        try:
            user = auth_service.verify_token(token)
            user_id = _resolve_user_identifier(user)
        except Exception as e:
            return jsonify({"error": str(e)}), 401

    if not user_id:
        return jsonify({"count": 0})

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        use_postgres = bool(os.environ.get("DATABASE_URL"))
        placeholder = "%s" if use_postgres else "?"
        cursor.execute(
            f"SELECT COUNT(*) FROM reviews WHERE user_id = {placeholder}",
            (user_id,),
        )
        row = cursor.fetchone()
        if isinstance(row, dict):
            count = row.get("count", 0)
        else:
            count = row[0] if row else 0
        return jsonify({"count": count})
    except Exception:
        return jsonify({"count": 0})
    finally:
        conn.close()


@auth_bp.route("/api/auth/reviews", methods=["GET"])
def get_user_reviews():
    from src.core.auth import auth_service

    if auth_service.dev_bypass:
        user_id = "dev_user"
    else:
        token = auth_service.get_token_from_header()
        if not token:
            return jsonify({"error": "No token provided"}), 401
        try:
            user = auth_service.verify_token(token)
            user_id = _resolve_user_identifier(user)
        except Exception as e:
            return jsonify({"error": str(e)}), 401

    if not user_id:
        return jsonify({"reviews": []})

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        use_postgres = bool(os.environ.get("DATABASE_URL"))
        placeholder = "%s" if use_postgres else "?"
        cursor.execute(
            f"""SELECT r.id, r.course_id, r.rating, r.review, r.author_name, r.author_email, r.created_at, c.title
                FROM reviews r
                LEFT JOIN courses c ON r.course_id = c.id
                WHERE r.user_id = {placeholder}
                ORDER BY r.created_at DESC""",
            (user_id,),
        )
        rows = cursor.fetchall()
        reviews = []
        for row in rows:
            if isinstance(row, dict):
                r = dict(row)
                if r.get("created_at") and hasattr(r["created_at"], "isoformat"):
                    r["created_at"] = r["created_at"].isoformat()
                reviews.append(r)
            else:
                reviews.append(
                    {
                        "id": row[0],
                        "course_id": row[1],
                        "rating": row[2],
                        "review": row[3],
                        "author_name": row[4],
                        "author_email": row[5],
                        "created_at": str(row[6]) if row[6] else None,
                        "course_title": row[7],
                    }
                )
        return jsonify({"reviews": reviews})
    finally:
        conn.close()


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
