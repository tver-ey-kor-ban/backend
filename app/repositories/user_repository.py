from typing import Optional, List
from sqlmodel import Session, select, col

from app.models.user import User, RefreshToken


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.session.get(User, user_id)

    def get_by_username(self, username: str) -> Optional[User]:
        return self.session.exec(
            select(User).where(User.username == username)
        ).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.session.exec(
            select(User).where(User.email == email)
        ).first()

    def save(self, user: User) -> User:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def get_refresh_token(self, token: str) -> Optional[RefreshToken]:
        return self.session.exec(
            select(RefreshToken).where(RefreshToken.token == token)
        ).first()

    def save_refresh_token(self, token: RefreshToken) -> None:
        self.session.add(token)
        self.session.commit()

    def get_active_refresh_tokens(self, user_id: int) -> List[RefreshToken]:
        return self.session.exec(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                col(RefreshToken.revoked).is_(False),
            )
        ).all()

    def revoke_token(self, token: RefreshToken) -> None:
        token.revoked = True
        self.session.commit()

    def revoke_tokens(self, tokens: List[RefreshToken]) -> int:
        for token in tokens:
            token.revoked = True
        self.session.commit()
        return len(tokens)
