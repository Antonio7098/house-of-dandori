import pytest
from src.api.app import create_app


@pytest.fixture
def client(setup_test_db):
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"


def test_index(client):
    response = client.get("/")
    assert response.status_code in [200, 500]


def test_get_courses(client):
    response = client.get("/api/courses")
    assert response.status_code == 200
    data = response.get_json()
    assert "courses" in data
    assert "count" in data


def test_get_courses_with_pagination(client):
    response = client.get("/api/courses?page=1&limit=5")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["courses"]) <= 5
    assert data["page"] == 1
    assert data["limit"] == 5


def test_get_courses_with_search(client):
    response = client.get("/api/courses?search=baking")
    assert response.status_code == 200
    data = response.get_json()
    assert "courses" in data


def test_get_courses_with_filters(client):
    response = client.get("/api/courses?location=Harrogate&course_type=Culinary")
    assert response.status_code == 200
    data = response.get_json()
    assert "courses" in data


def test_get_course_by_id(client):
    response = client.get("/api/courses/1")
    if response.status_code == 200:
        data = response.get_json()
        assert "title" in data
    else:
        assert response.status_code == 404


def test_get_course_not_found(client):
    response = client.get("/api/courses/999999")
    assert response.status_code == 404


def test_create_course(client):
    new_course = {
        "title": "Test Course",
        "instructor": "Test Instructor",
        "location": "Test Location",
        "course_type": "Test Type",
        "cost": "£50",
        "description": "Test description",
    }
    response = client.post("/api/courses", json=new_course)
    assert response.status_code == 201
    data = response.get_json()
    assert "id" in data


def test_update_course(client):
    update_data = {"title": "Updated Title", "instructor": "Updated Instructor"}
    response = client.put("/api/courses/1", json=update_data)
    assert response.status_code in [200, 404]


def test_delete_course(client):
    response = client.delete("/api/courses/999999")
    assert response.status_code in [200, 404]


def test_bulk_courses(client):
    response = client.post("/api/courses/bulk", json={"ids": [1, 2, 3]})
    assert response.status_code == 200
    data = response.get_json()
    assert "courses" in data


def test_bulk_courses_invalid(client):
    response = client.post("/api/courses/bulk", json={})
    assert response.status_code == 400


def test_search(client):
    response = client.get("/api/search?q=baking")
    assert response.status_code == 200
    data = response.get_json()
    assert "results" in data


def test_search_missing_query(client):
    response = client.get("/api/search")
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data


def test_chat_non_stream_returns_artifacts(client):
    client.post(
        "/api/courses",
        json={
            "title": "Bread Basics",
            "instructor": "Ada Calm",
            "location": "Leeds",
            "course_type": "Culinary Arts",
            "cost": "£45",
            "description": "Learn sourdough and starter care",
            "filename": "bread-basics.pdf",
        },
    )
    response = client.post(
        "/api/chat",
        json={
            "message": "show me bread classes in Leeds",
            "filters": {"location": "Leeds", "title": "Bread"},
            "stream": False,
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "message" in data
    assert "artifacts" in data
    assert isinstance(data["artifacts"], list)


def test_chat_stream_sse(client):
    response = client.post(
        "/api/chat",
        json={"message": "any course suggestions?", "stream": True},
    )
    assert response.status_code == 200
    assert response.content_type.startswith("text/event-stream")


def test_cors_allows_origin_with_trailing_slash_env(monkeypatch, setup_test_db):
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS", "https://house-of-dandori.netlify.app/"
    )
    app = create_app()
    app.config["TESTING"] = True

    with app.test_client() as test_client:
        response = test_client.options(
            "/api/courses",
            headers={"Origin": "https://house-of-dandori.netlify.app"},
        )

    assert response.status_code == 204
    assert (
        response.headers.get("Access-Control-Allow-Origin")
        == "https://house-of-dandori.netlify.app"
    )
