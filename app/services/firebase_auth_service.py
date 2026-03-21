"""Firebase Authentication Service."""
from typing import Optional
from sqlmodel import Session, select

from app.models.user import User
from app.core.firebase import (
    verify_firebase_token,
    get_firebase_user,
    set_custom_claims
)
from app.core.security import create_access_token


class FirebaseAuthService:
    """Service for Firebase authentication integration."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def verify_token(self, firebase_token: str) -> Optional[dict]:
        """Verify Firebase ID token.
        
        Args:
            firebase_token: Firebase ID token from client
            
        Returns:
            Decoded token data or None if invalid
        """
        return verify_firebase_token(firebase_token)
    
    def get_or_create_user(self, firebase_uid: str, email: str, **kwargs) -> User:
        """Get existing user or create new one from Firebase data.
        
        Args:
            firebase_uid: Firebase user ID
            email: User email
            **kwargs: Additional user data (full_name, photo_url, etc.)
            
        Returns:
            User model instance
        """
        # Try to find user by Firebase UID (stored in username for now)
        statement = select(User).where(User.username == firebase_uid)
        user = self.session.exec(statement).first()
        
        if user:
            return user
        
        # Create new user
        roles = kwargs.get("roles", ["user"])
        if isinstance(roles, list):
            roles = ",".join(roles)
        
        user = User(
            email=email,
            username=firebase_uid,  # Use Firebase UID as username
            full_name=kwargs.get("full_name") or kwargs.get("display_name"),
            hashed_password="FIREBASE_AUTH",  # Marker for Firebase auth
            roles=roles,
            is_active=True,
            is_superuser=kwargs.get("is_superuser", False)
        )
        
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
    
    def login_with_firebase(self, firebase_token: str) -> Optional[dict]:
        """Login user with Firebase token.
        
        Args:
            firebase_token: Firebase ID token from client
            
        Returns:
            Login result with access token or None if failed
        """
        # Verify Firebase token
        decoded_token = self.verify_token(firebase_token)
        if not decoded_token:
            return None
        
        firebase_uid = decoded_token.get("uid")
        email = decoded_token.get("email")
        
        if not firebase_uid or not email:
            return None
        
        # Get additional Firebase user data
        firebase_user = get_firebase_user(firebase_uid)
        
        # Get or create local user
        user = self.get_or_create_user(
            firebase_uid=firebase_uid,
            email=email,
            full_name=firebase_user.display_name if firebase_user else None,
            photo_url=firebase_user.photo_url if firebase_user else None
        )
        
        # Sync roles from Firebase custom claims
        if firebase_user and firebase_user.custom_claims:
            firebase_roles = firebase_user.custom_claims.get("roles", [])
            if isinstance(firebase_roles, list):
                firebase_roles_str = ",".join(firebase_roles)
            else:
                firebase_roles_str = firebase_roles
            if firebase_roles and firebase_roles_str != user.roles:
                user.roles = firebase_roles_str
                self.session.add(user)
                self.session.commit()
        
        # Create our own JWT token - convert string roles to list for JWT
        user_roles_list = user.roles.split(",") if user.roles else ["user"]
        access_token = create_access_token(
            user_id=user.id,
            username=user.username,
            email=user.email,
            roles=user_roles_list,
            is_superuser=user.is_superuser
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user,
            "firebase_uid": firebase_uid
        }
    
    def link_firebase_account(self, user_id: int, firebase_token: str) -> Optional[User]:
        """Link existing local account with Firebase.
        
        Args:
            user_id: Local user ID
            firebase_token: Firebase ID token
            
        Returns:
            Updated User or None if failed
        """
        # Verify Firebase token
        decoded_token = self.verify_token(firebase_token)
        if not decoded_token:
            return None
        
        firebase_uid = decoded_token.get("uid")
        
        # Get local user
        statement = select(User).where(User.id == user_id)
        user = self.session.exec(statement).first()
        
        if not user:
            return None
        
        # Update username to Firebase UID (for linking)
        user.username = firebase_uid
        user.hashed_password = "FIREBASE_AUTH"
        
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        
        return user
    
    def set_user_roles(self, firebase_uid: str, roles: list) -> bool:
        """Set roles for a Firebase user (updates both Firebase and local).
        
        Args:
            firebase_uid: Firebase user ID
            roles: List of roles
            
        Returns:
            True if successful
        """
        # Update Firebase custom claims
        claims = {"roles": roles}
        if not set_custom_claims(firebase_uid, claims):
            return False
        
        # Update local user
        statement = select(User).where(User.username == firebase_uid)
        user = self.session.exec(statement).first()
        
        if user:
            user.roles = ",".join(roles)
            self.session.add(user)
            self.session.commit()
        
        return True
