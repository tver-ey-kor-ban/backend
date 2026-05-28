"""Cloudinary-backed image storage service.

Set CLOUDINARY_URL in your environment:
  cloudinary://API_KEY:API_SECRET@CLOUD_NAME

Get these values from: Cloudinary Console → Dashboard.
"""
import os

import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, status

cloudinary.config(cloudinary_url=os.getenv("CLOUDINARY_URL"))

# Cloudinary transformation applied to produce the thumbnail URL.
# w_400,h_400,c_fill  → square-crop to 400 px
# q_auto              → automatic quality compression
# f_auto              → serve WebP/AVIF to browsers that support it
_THUMB_TRANSFORM = "w_400,h_400,c_fill,q_auto,f_auto"


class ImageStorageService:
    """Upload images to Cloudinary and return CDN URLs."""

    def upload(self, file_bytes: bytes, folder: str = "products") -> dict:
        """Upload *file_bytes* to Cloudinary under *folder*.

        Returns a dict with:
          image_url     – full-resolution HTTPS URL
          thumbnail_url – 400×400 square-crop URL (no extra upload needed)
          public_id     – Cloudinary public_id (useful for future deletions)
        """
        if not os.getenv("CLOUDINARY_URL"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Image storage is not configured (CLOUDINARY_URL missing).",
            )
        try:
            result = cloudinary.uploader.upload(
                file_bytes,
                folder=folder,
                resource_type="image",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Image upload to Cloudinary failed: {exc}",
            )

        image_url: str = result["secure_url"]
        # Insert the transformation string right after /upload/ in the CDN URL.
        # e.g. https://res.cloudinary.com/demo/image/upload/v123/products/abc.jpg
        #   →  https://res.cloudinary.com/demo/image/upload/w_400,.../v123/products/abc.jpg
        thumbnail_url: str = image_url.replace(
            "/upload/", f"/upload/{_THUMB_TRANSFORM}/"
        )
        return {
            "image_url": image_url,
            "thumbnail_url": thumbnail_url,
            "public_id": result["public_id"],
        }
