"""Tests for product image upload — ImageStorageService unit tests + endpoint integration tests.

Cloudinary is mocked throughout so these run locally with no real credentials.
"""
import io
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.product import Product
from app.models.shop import Shop, ShopRole, UserShop
from app.services.image_storage_service import ImageStorageService

# ---------------------------------------------------------------------------
# Fake Cloudinary response used across multiple tests
# ---------------------------------------------------------------------------
FAKE_CLOUDINARY_RESULT = {
    "secure_url": "https://res.cloudinary.com/demo/image/upload/v123/products/abc.jpg",
    "public_id": "products/abc",
}

EXPECTED_IMAGE_URL = "https://res.cloudinary.com/demo/image/upload/v123/products/abc.jpg"
EXPECTED_THUMB_URL = (
    "https://res.cloudinary.com/demo/image/upload"
    "/w_400,h_400,c_fill,q_auto,f_auto/v123/products/abc.jpg"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_shop_with_owner(session: Session, owner) -> Shop:
    shop = Shop(name="Test Shop", address="1 Main St", owner_id=owner.id)
    session.add(shop)
    session.commit()
    session.refresh(shop)
    session.add(UserShop(user_id=owner.id, shop_id=shop.id, role=ShopRole.OWNER))
    session.commit()
    return shop


def _make_product(session: Session, shop: Shop) -> Product:
    product = Product(name="Oil Filter", price=25.99, stock_quantity=10, shop_id=shop.id)
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


def _fake_image(content: bytes = b"FAKEJPEG", content_type: str = "image/jpeg", filename: str = "test.jpg"):
    return ("image", (filename, io.BytesIO(content), content_type))


# ===========================================================================
# 1. Unit tests for ImageStorageService
# ===========================================================================
class TestImageStorageService:
    """Pure unit tests — cloudinary.uploader is mocked, no network calls."""

    def test_upload_returns_correct_urls(self):
        """upload() must return image_url, thumbnail_url, and public_id."""
        with patch.dict(os.environ, {"CLOUDINARY_URL": "cloudinary://key:secret@demo"}):
            with patch("cloudinary.uploader.upload", return_value=FAKE_CLOUDINARY_RESULT):
                result = ImageStorageService().upload(b"bytes", folder="products")

        assert result["image_url"] == EXPECTED_IMAGE_URL
        assert result["thumbnail_url"] == EXPECTED_THUMB_URL
        assert result["public_id"] == "products/abc"

    def test_thumbnail_url_contains_transform(self):
        """Thumbnail URL must embed the Cloudinary transformation string."""
        with patch.dict(os.environ, {"CLOUDINARY_URL": "cloudinary://key:secret@demo"}):
            with patch("cloudinary.uploader.upload", return_value=FAKE_CLOUDINARY_RESULT):
                result = ImageStorageService().upload(b"bytes")

        assert "w_400,h_400,c_fill,q_auto,f_auto" in result["thumbnail_url"]

    def test_upload_raises_503_when_env_var_missing(self):
        """Without CLOUDINARY_URL the service must raise 503, not a raw SDK error."""
        from fastapi import HTTPException

        env = {k: v for k, v in os.environ.items() if k != "CLOUDINARY_URL"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(HTTPException) as exc_info:
                ImageStorageService().upload(b"bytes")

        assert exc_info.value.status_code == 503

    def test_upload_raises_502_on_cloudinary_sdk_error(self):
        """A Cloudinary SDK exception must be wrapped in a 502 HTTPException."""
        from fastapi import HTTPException

        with patch.dict(os.environ, {"CLOUDINARY_URL": "cloudinary://key:secret@demo"}):
            with patch("cloudinary.uploader.upload", side_effect=Exception("network timeout")):
                with pytest.raises(HTTPException) as exc_info:
                    ImageStorageService().upload(b"bytes")

        assert exc_info.value.status_code == 502
        assert "Cloudinary" in exc_info.value.detail

    def test_upload_passes_folder_to_cloudinary(self):
        """The folder argument must be forwarded to cloudinary.uploader.upload."""
        with patch.dict(os.environ, {"CLOUDINARY_URL": "cloudinary://key:secret@demo"}):
            with patch("cloudinary.uploader.upload", return_value=FAKE_CLOUDINARY_RESULT) as mock_upload:
                ImageStorageService().upload(b"bytes", folder="products")

        mock_upload.assert_called_once()
        _, kwargs = mock_upload.call_args
        assert kwargs.get("folder") == "products"


# ===========================================================================
# 2. Endpoint integration tests  (Cloudinary mocked via patch)
# ===========================================================================
class TestProductImageUploadEndpoint:
    """Integration tests for POST /api/v1/shops/{shop_id}/products/{product_id}/image."""

    # Patch target: ImageStorageService where it is imported in products.py
    _PATCH = "app.api.v1.endpoints.products.ImageStorageService"

    def _mock_service(self):
        mock = MagicMock()
        mock.return_value.upload.return_value = {
            "image_url": EXPECTED_IMAGE_URL,
            "thumbnail_url": EXPECTED_THUMB_URL,
            "public_id": "products/abc",
        }
        return mock

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------
    def test_upload_jpeg_sets_image_and_thumbnail_url(
        self, client: TestClient, session: Session, shop_owner, owner_auth_headers
    ):
        """Successful upload must persist image_url + thumbnail_url and return them."""
        shop = _make_shop_with_owner(session, shop_owner)
        product = _make_product(session, shop)

        with patch(self._PATCH, self._mock_service()):
            response = client.post(
                f"/api/v1/shops/{shop.id}/products/{product.id}/image",
                files=[_fake_image()],
                headers=owner_auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["image_url"] == EXPECTED_IMAGE_URL
        assert data["thumbnail_url"] == EXPECTED_THUMB_URL
        assert data["id"] == product.id

    def test_upload_png_accepted(
        self, client: TestClient, session: Session, shop_owner, owner_auth_headers
    ):
        """PNG files must be accepted."""
        shop = _make_shop_with_owner(session, shop_owner)
        product = _make_product(session, shop)

        with patch(self._PATCH, self._mock_service()):
            response = client.post(
                f"/api/v1/shops/{shop.id}/products/{product.id}/image",
                files=[_fake_image(content_type="image/png", filename="photo.png")],
                headers=owner_auth_headers,
            )

        assert response.status_code == 200

    def test_upload_webp_accepted(
        self, client: TestClient, session: Session, shop_owner, owner_auth_headers
    ):
        """WebP files must be accepted."""
        shop = _make_shop_with_owner(session, shop_owner)
        product = _make_product(session, shop)

        with patch(self._PATCH, self._mock_service()):
            response = client.post(
                f"/api/v1/shops/{shop.id}/products/{product.id}/image",
                files=[_fake_image(content_type="image/webp", filename="photo.webp")],
                headers=owner_auth_headers,
            )

        assert response.status_code == 200

    def test_image_url_persisted_in_db(
        self, client: TestClient, session: Session, shop_owner, owner_auth_headers
    ):
        """After upload the product row in DB must have image_url set."""
        shop = _make_shop_with_owner(session, shop_owner)
        product = _make_product(session, shop)

        with patch(self._PATCH, self._mock_service()):
            client.post(
                f"/api/v1/shops/{shop.id}/products/{product.id}/image",
                files=[_fake_image()],
                headers=owner_auth_headers,
            )

        session.refresh(product)
        assert product.image_url == EXPECTED_IMAGE_URL
        assert product.thumbnail_url == EXPECTED_THUMB_URL

    # ------------------------------------------------------------------
    # Validation errors
    # ------------------------------------------------------------------
    def test_unsupported_content_type_returns_400(
        self, client: TestClient, session: Session, shop_owner, owner_auth_headers
    ):
        """Uploading a non-image file must return 400 before hitting Cloudinary."""
        shop = _make_shop_with_owner(session, shop_owner)
        product = _make_product(session, shop)

        with patch(self._PATCH, self._mock_service()) as mock_cls:
            response = client.post(
                f"/api/v1/shops/{shop.id}/products/{product.id}/image",
                files=[_fake_image(content_type="text/plain", filename="hack.txt")],
                headers=owner_auth_headers,
            )
            # Cloudinary must never be called
            mock_cls.return_value.upload.assert_not_called()

        assert response.status_code == 400
        assert "Unsupported image type" in response.json()["detail"]

    def test_file_over_5mb_returns_400(
        self, client: TestClient, session: Session, shop_owner, owner_auth_headers
    ):
        """Files larger than 5 MB must be rejected before hitting Cloudinary."""
        shop = _make_shop_with_owner(session, shop_owner)
        product = _make_product(session, shop)

        oversized = b"x" * (5 * 1024 * 1024 + 1)
        with patch(self._PATCH, self._mock_service()) as mock_cls:
            response = client.post(
                f"/api/v1/shops/{shop.id}/products/{product.id}/image",
                files=[_fake_image(content=oversized)],
                headers=owner_auth_headers,
            )
            mock_cls.return_value.upload.assert_not_called()

        assert response.status_code == 400
        assert "5 MB" in response.json()["detail"]

    # ------------------------------------------------------------------
    # Auth / ownership checks
    # ------------------------------------------------------------------
    def test_mechanic_cannot_upload_image(
        self, client: TestClient, session: Session, shop_owner, mechanic_user, mechanic_auth_headers
    ):
        """Mechanic role must receive 403."""
        shop = _make_shop_with_owner(session, shop_owner)
        session.add(UserShop(user_id=mechanic_user.id, shop_id=shop.id, role=ShopRole.MECHANIC))
        session.commit()
        product = _make_product(session, shop)

        response = client.post(
            f"/api/v1/shops/{shop.id}/products/{product.id}/image",
            files=[_fake_image()],
            headers=mechanic_auth_headers,
        )
        assert response.status_code == 403

    def test_unauthenticated_request_returns_401(
        self, client: TestClient, session: Session, shop_owner
    ):
        """Requests without a token must be rejected."""
        shop = _make_shop_with_owner(session, shop_owner)
        product = _make_product(session, shop)

        response = client.post(
            f"/api/v1/shops/{shop.id}/products/{product.id}/image",
            files=[_fake_image()],
        )
        assert response.status_code == 401

    # ------------------------------------------------------------------
    # Not-found cases
    # ------------------------------------------------------------------
    def test_nonexistent_product_returns_404(
        self, client: TestClient, session: Session, shop_owner, owner_auth_headers
    ):
        """Uploading to a product that does not exist must return 404."""
        shop = _make_shop_with_owner(session, shop_owner)

        with patch(self._PATCH, self._mock_service()):
            response = client.post(
                f"/api/v1/shops/{shop.id}/products/99999/image",
                files=[_fake_image()],
                headers=owner_auth_headers,
            )

        assert response.status_code == 404

    def test_product_in_different_shop_returns_404(
        self, client: TestClient, session: Session, shop_owner, owner_auth_headers
    ):
        """Product belonging to another shop must not be accessible."""
        shop_a = _make_shop_with_owner(session, shop_owner)
        shop_b = Shop(name="Other Shop", address="2 Other St", owner_id=shop_owner.id)
        session.add(shop_b)
        session.commit()
        session.refresh(shop_b)

        # Product lives in shop_b, but we upload to shop_a
        product = Product(name="Wrong Shop Part", price=10.0, stock_quantity=1, shop_id=shop_b.id)
        session.add(product)
        session.commit()
        session.refresh(product)

        with patch(self._PATCH, self._mock_service()):
            response = client.post(
                f"/api/v1/shops/{shop_a.id}/products/{product.id}/image",
                files=[_fake_image()],
                headers=owner_auth_headers,
            )

        assert response.status_code == 404

    # ------------------------------------------------------------------
    # Cloudinary failure propagation
    # ------------------------------------------------------------------
    def test_cloudinary_502_propagates_to_client(
        self, client: TestClient, session: Session, shop_owner, owner_auth_headers
    ):
        """When Cloudinary fails the endpoint must return 502."""
        from fastapi import HTTPException

        shop = _make_shop_with_owner(session, shop_owner)
        product = _make_product(session, shop)

        mock_cls = MagicMock()
        mock_cls.return_value.upload.side_effect = HTTPException(
            status_code=502, detail="Image upload to Cloudinary failed: network timeout"
        )

        with patch(self._PATCH, mock_cls):
            response = client.post(
                f"/api/v1/shops/{shop.id}/products/{product.id}/image",
                files=[_fake_image()],
                headers=owner_auth_headers,
            )

        assert response.status_code == 502

    def test_cloudinary_503_propagates_when_url_missing(
        self, client: TestClient, session: Session, shop_owner, owner_auth_headers
    ):
        """When CLOUDINARY_URL is absent the endpoint must return 503."""
        from fastapi import HTTPException

        shop = _make_shop_with_owner(session, shop_owner)
        product = _make_product(session, shop)

        mock_cls = MagicMock()
        mock_cls.return_value.upload.side_effect = HTTPException(
            status_code=503, detail="Image storage is not configured (CLOUDINARY_URL missing)."
        )

        with patch(self._PATCH, mock_cls):
            response = client.post(
                f"/api/v1/shops/{shop.id}/products/{product.id}/image",
                files=[_fake_image()],
                headers=owner_auth_headers,
            )

        assert response.status_code == 503
