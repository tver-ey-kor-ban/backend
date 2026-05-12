from datetime import datetime
from typing import Optional, List
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.notification import Notification, NotificationStatus


class NotificationRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, notification: Notification) -> Notification:
        self.session.add(notification)
        self.session.commit()
        self.session.refresh(notification)
        return notification

    def get_user_notifications(
        self,
        user_id: int,
        status: Optional[NotificationStatus] = None,
        limit: int = 50,
    ) -> List[Notification]:
        query = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
        )
        if status:
            query = query.where(Notification.status == status)
        return self.session.exec(query.limit(limit)).all()

    def get_by_id_and_user(
        self, notification_id: int, user_id: int
    ) -> Optional[Notification]:
        return self.session.exec(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        ).first()

    def get_unread_count(self, user_id: int) -> int:
        return self.session.exec(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.status == NotificationStatus.UNREAD,
            )
        ).one()

    def mark_as_read(self, notification: Notification) -> Notification:
        notification.status = NotificationStatus.READ
        notification.read_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(notification)
        return notification
