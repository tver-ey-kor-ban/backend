"""Tests for local authentication endpoints."""
from fastapi.testclient import TestClient


class TestAuthEndpoints:
    """Test authentication endpoints."""
    
    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["message"] == "Backend is running"
    
    def test_docs_endpoint(self, client: TestClient):
        """Test Swagger docs endpoint."""
        response = client.get("/docs")
        assert response.status_code == 200
    
    def test_register_user(self, client: TestClient):
        """Test user registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "testpassword123",
                "full_name": "New User"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert "password" not in data
    
    def test_register_duplicate_email(self, client: TestClient, test_user):
        """Test registration with duplicate email."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",  # Same as test_user
                "username": "differentuser",
                "password": "testpassword123"
            }
        )
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    def test_login_without_credentials(self, client: TestClient):
        """Test login without credentials."""
        response = client.post("/api/v1/auth/login")
        assert response.status_code == 422  # Missing required fields
    
    def test_login_with_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "nonexistent", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_with_valid_credentials(self, client: TestClient, test_user):
        """Test login with valid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "testpassword"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_refresh_token(self, client: TestClient, test_user):
        """Test refreshing access token with refresh token."""
        # First login to get refresh token
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "testpassword"}
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]
        
        # Use refresh token to get new access token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_refresh_token_invalid(self, client: TestClient):
        """Test refreshing with invalid refresh token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )
        assert response.status_code == 401
        assert "Invalid or expired refresh token" in response.json()["detail"]
    
    def test_logout(self, client: TestClient, test_user, auth_headers):
        """Test logout by revoking refresh token."""
        # First login to get refresh token
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "testpassword"}
        )
        refresh_token = login_response.json()["refresh_token"]
        
        # Logout
        response = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["message"]
        
        # Try to use the revoked refresh token
        refresh_response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert refresh_response.status_code == 401
    
    def test_logout_all(self, client: TestClient, test_user, auth_headers):
        """Test logout from all devices."""
        # Login multiple times to create multiple refresh tokens
        for _ in range(3):
            client.post(
                "/api/v1/auth/login",
                data={"username": "testuser", "password": "testpassword"}
            )
        
        # Logout from all devices
        response = client.post(
            "/api/v1/auth/logout-all",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["revoked_tokens"] >= 3
    
    def test_me_without_auth(self, client: TestClient):
        """Test /me endpoint without authentication."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
    
    def test_me_with_auth(self, client: TestClient, auth_headers, test_user):
        """Test /me endpoint with authentication."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
    
    def test_me_roles_with_auth(self, client: TestClient, auth_headers, test_user):
        """Test /me/roles endpoint with authentication."""
        response = client.get("/api/v1/auth/me/roles", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert "roles" in data
        assert data["roles"] == ["user"]
    
    def test_admin_only_without_auth(self, client: TestClient):
        """Test admin-only endpoint without authentication."""
        response = client.get("/api/v1/auth/admin-only")
        assert response.status_code == 401
    
    def test_admin_only_with_user_role(self, client: TestClient, auth_headers):
        """Test admin-only endpoint with regular user."""
        response = client.get("/api/v1/auth/admin-only", headers=auth_headers)
        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]
    
    def test_admin_only_with_admin_role(self, client: TestClient, admin_auth_headers):
        """Test admin-only endpoint with admin user."""
        response = client.get("/api/v1/auth/admin-only", headers=admin_auth_headers)
        assert response.status_code == 200
        assert "Hello Admin!" in response.json()["message"]
