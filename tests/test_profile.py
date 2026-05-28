"""Tests for PUT /auth/me — user profile edit endpoint."""
import io
from fastapi.testclient import TestClient


class TestUpdateProfile:
    """PUT /auth/me — text-field updates."""

    def test_update_full_name(self, client: TestClient, auth_headers, test_user):
        """Changing full_name is reflected in the response and persisted."""
        response = client.put(
            "/api/v1/auth/me",
            data={"full_name": "Updated Name"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["username"] == "testuser"

    def test_update_email(self, client: TestClient, auth_headers, test_user):
        """Changing to a free email address succeeds."""
        response = client.put(
            "/api/v1/auth/me",
            data={"email": "newemail@example.com"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["email"] == "newemail@example.com"

    def test_update_email_duplicate_rejected(self, client: TestClient, auth_headers, test_user, session):
        """Using another user's email returns 400."""
        from app.models.user import User
        from app.core.security import get_password_hash

        other = User(
            email="taken@example.com",
            username="otheruser",
            hashed_password=get_password_hash("x"),
            roles="user",
            is_active=True,
        )
        session.add(other)
        session.commit()

        response = client.put(
            "/api/v1/auth/me",
            data={"email": "taken@example.com"},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "already in use" in response.json()["detail"]

    def test_update_multiple_fields_at_once(self, client: TestClient, auth_headers, test_user):
        """full_name and email can be updated in a single request."""
        response = client.put(
            "/api/v1/auth/me",
            data={"full_name": "New Name", "email": "multi@example.com"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "New Name"
        assert data["email"] == "multi@example.com"

    def test_empty_request_is_no_op(self, client: TestClient, auth_headers, test_user):
        """Sending no fields leaves the profile unchanged."""
        before = client.get("/api/v1/auth/me", headers=auth_headers).json()
        response = client.put("/api/v1/auth/me", data={}, headers=auth_headers)
        assert response.status_code == 200
        after = response.json()
        assert after["full_name"] == before["full_name"]
        assert after["email"] == before["email"]

    def test_update_requires_auth(self, client: TestClient):
        """No token → 401."""
        response = client.put("/api/v1/auth/me", data={"full_name": "Ghost"})
        assert response.status_code == 401

    def test_response_contains_profile_image_url_field(self, client: TestClient, auth_headers, test_user):
        """Response always includes profile_image_url (null when not set)."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert "profile_image_url" in response.json()

    def test_update_phone(self, client: TestClient, auth_headers, test_user):
        """Phone number can be set via PUT /auth/me."""
        response = client.put(
            "/api/v1/auth/me",
            data={"phone": "+1234567890"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["phone"] == "+1234567890"

    def test_phone_persists_and_appears_in_get_me(self, client: TestClient, auth_headers, test_user):
        """After setting phone, GET /auth/me returns the same value."""
        client.put("/api/v1/auth/me", data={"phone": "+9876543210"}, headers=auth_headers)
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["phone"] == "+9876543210"

    def test_phone_field_in_response_is_null_by_default(self, client: TestClient, auth_headers, test_user):
        """phone is null in GET /auth/me when never set."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert "phone" in response.json()
        assert response.json()["phone"] is None

    def test_update_phone_and_name_together(self, client: TestClient, auth_headers, test_user):
        """phone and full_name can be updated in a single request."""
        response = client.put(
            "/api/v1/auth/me",
            data={"full_name": "Jane Doe", "phone": "+1112223333"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Jane Doe"
        assert data["phone"] == "+1112223333"


class TestUpdateProfileImage:
    """PUT /auth/me — image upload."""

    def _fake_image(self, content_type: str = "image/png", size: int = 100) -> tuple:
        """Return (filename, file-like, content_type) suitable for TestClient files=."""
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * size
        return ("avatar.png", io.BytesIO(data), content_type)

    def test_upload_valid_png(self, client: TestClient, auth_headers, test_user):
        """Valid PNG upload stores file and returns a /uploads/avatars/... URL."""
        response = client.put(
            "/api/v1/auth/me",
            files={"image": self._fake_image()},
            headers=auth_headers,
        )
        assert response.status_code == 200
        url = response.json()["profile_image_url"]
        assert url is not None
        assert url.startswith("/uploads/avatars/")
        assert url.endswith(".png")

    def test_upload_invalid_content_type_rejected(self, client: TestClient, auth_headers, test_user):
        """GIF upload is rejected with 400."""
        response = client.put(
            "/api/v1/auth/me",
            files={"image": ("avatar.gif", io.BytesIO(b"GIF89a"), "image/gif")},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "Unsupported image type" in response.json()["detail"]

    def test_upload_oversized_image_rejected(self, client: TestClient, auth_headers, test_user):
        """Images larger than 5 MB are rejected with 400."""
        big = b"\x00" * (5 * 1024 * 1024 + 1)
        response = client.put(
            "/api/v1/auth/me",
            files={"image": ("big.png", io.BytesIO(big), "image/png")},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "5 MB" in response.json()["detail"]

    def test_upload_jpeg_accepted(self, client: TestClient, auth_headers, test_user):
        """JPEG content type is accepted."""
        response = client.put(
            "/api/v1/auth/me",
            files={"image": ("photo.jpg", io.BytesIO(b"\xff\xd8\xff" + b"\x00" * 50), "image/jpeg")},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["profile_image_url"] is not None

    def test_image_and_text_fields_together(self, client: TestClient, auth_headers, test_user):
        """Image upload and full_name update can be combined in one request."""
        response = client.put(
            "/api/v1/auth/me",
            data={"full_name": "With Photo"},
            files={"image": self._fake_image()},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "With Photo"
        assert data["profile_image_url"] is not None
