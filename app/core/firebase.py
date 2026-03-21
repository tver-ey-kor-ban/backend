"""Firebase Admin SDK configuration."""
import os
import json
from typing import Optional

import firebase_admin
from firebase_admin import credentials, auth
from firebase_admin.auth import UserRecord

# Global Firebase app instance
_firebase_app: Optional[firebase_admin.App] = None


def initialize_firebase() -> firebase_admin.App:
    """Initialize Firebase Admin SDK.
    
    Looks for Firebase credentials in the following order:
    1. FIREBASE_CREDENTIALS_JSON environment variable (JSON string)
    2. FIREBASE_CREDENTIALS_PATH environment variable (file path)
    3. firebase-credentials.json file in project root
    """
    global _firebase_app
    
    if _firebase_app is not None:
        return _firebase_app
    
    # Try to get credentials from environment variable (JSON string)
    firebase_creds_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
    if firebase_creds_json:
        creds_dict = json.loads(firebase_creds_json)
        cred = credentials.Certificate(creds_dict)
        _firebase_app = firebase_admin.initialize_app(cred)
        return _firebase_app
    
    # Try to get credentials from file path
    firebase_creds_path = os.getenv(
        "FIREBASE_CREDENTIALS_PATH",
        "firebase-credentials.json"
    )
    
    if os.path.exists(firebase_creds_path):
        cred = credentials.Certificate(firebase_creds_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        return _firebase_app
    
    # Initialize without credentials (for emulator or public access)
    _firebase_app = firebase_admin.initialize_app()
    return _firebase_app


def get_firebase_auth():
    """Get Firebase Auth client."""
    if _firebase_app is None:
        initialize_firebase()
    return auth


def verify_firebase_token(token: str) -> Optional[dict]:
    """Verify Firebase ID token.
    
    Args:
        token: Firebase ID token from client
        
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        firebase_auth = get_firebase_auth()
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token
    except Exception:
        return None


def get_firebase_user(uid: str) -> Optional[UserRecord]:
    """Get Firebase user by UID.
    
    Args:
        uid: Firebase user ID
        
    Returns:
        UserRecord or None if not found
    """
    try:
        firebase_auth = get_firebase_auth()
        return firebase_auth.get_user(uid)
    except Exception:
        return None


def create_firebase_user(
    email: str,
    password: str,
    display_name: Optional[str] = None,
    phone_number: Optional[str] = None,
    photo_url: Optional[str] = None
) -> Optional[UserRecord]:
    """Create a new Firebase user.
    
    Args:
        email: User email
        password: User password
        display_name: Optional display name
        phone_number: Optional phone number
        photo_url: Optional photo URL
        
    Returns:
        Created UserRecord or None if failed
    """
    try:
        firebase_auth = get_firebase_auth()
        user = firebase_auth.create_user(
            email=email,
            password=password,
            display_name=display_name,
            phone_number=phone_number,
            photo_url=photo_url
        )
        return user
    except Exception:
        return None


def delete_firebase_user(uid: str) -> bool:
    """Delete a Firebase user.
    
    Args:
        uid: Firebase user ID
        
    Returns:
        True if deleted successfully
    """
    try:
        firebase_auth = get_firebase_auth()
        firebase_auth.delete_user(uid)
        return True
    except Exception:
        return False


def set_custom_claims(uid: str, claims: dict) -> bool:
    """Set custom claims for a Firebase user.
    
    Args:
        uid: Firebase user ID
        claims: Dictionary of custom claims (roles, permissions, etc.)
        
    Returns:
        True if successful
    """
    try:
        firebase_auth = get_firebase_auth()
        firebase_auth.set_custom_user_claims(uid, claims)
        return True
    except Exception:
        return False
