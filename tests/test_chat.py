"""Tests for chat/support endpoints."""
from datetime import datetime
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.shop import Shop, UserShop, ShopRole
from app.models.chat import ChatRoom, ChatMessage, ChatRoomType, ChatMessageType


class TestChatRoomCreation:
    """Test chat room creation."""

    def test_create_chat_room(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test customer creating a chat room."""
        shop = Shop(name="Chat Shop", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        response = client.post(
            "/api/v1/chat/rooms",
            json={
                "shop_id": shop.id,
                "room_type": "general"
            },
            headers=customer_auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert "room_id" in data

    def test_duplicate_appointment_room_returns_existing(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test creating duplicate appointment-linked room returns existing."""
        shop = Shop(name="Chat Shop 2", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        from app.models.appointment import Appointment
        appointment = Appointment(
            shop_id=shop.id,
            customer_id=customer_user.id,
            appointment_date=datetime.utcnow(),
            status="pending",
            service_price=50
        )
        session.add(appointment)
        session.commit()
        session.refresh(appointment)

        room = ChatRoom(
            shop_id=shop.id,
            customer_id=customer_user.id,
            room_type=ChatRoomType.APPOINTMENT,
            appointment_id=appointment.id
        )
        session.add(room)
        session.commit()
        session.refresh(room)

        response = client.post(
            "/api/v1/chat/rooms",
            json={
                "shop_id": shop.id,
                "room_type": "appointment",
                "appointment_id": appointment.id
            },
            headers=customer_auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["room_id"] == room.id


class TestChatMessaging:
    """Test chat messaging."""

    def test_send_message(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test sending a message."""
        shop = Shop(name="Msg Shop", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        room = ChatRoom(
            shop_id=shop.id,
            customer_id=customer_user.id,
            room_type=ChatRoomType.GENERAL
        )
        session.add(room)
        session.commit()
        session.refresh(room)

        response = client.post(
            f"/api/v1/chat/rooms/{room.id}/messages",
            json={
                "content": "Hello, I have a question about my car"
            },
            headers=customer_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "message_id" in data

    def test_shop_member_can_send_message(self, client: TestClient, session: Session, shop_owner, customer_user, owner_auth_headers):
        """Test shop member sending a message."""
        shop = Shop(name="Shop Msg Shop", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()

        room = ChatRoom(
            shop_id=shop.id,
            customer_id=customer_user.id,
            room_type=ChatRoomType.GENERAL
        )
        session.add(room)
        session.commit()
        session.refresh(room)

        response = client.post(
            f"/api/v1/chat/rooms/{room.id}/messages",
            json={
                "content": "Hi, how can we help you?"
            },
            headers=owner_auth_headers
        )
        assert response.status_code == 200

    def test_unauthorized_user_cannot_send(self, client: TestClient, session: Session, shop_owner, customer_user, test_user, auth_headers):
        """Test unauthorized user cannot send messages."""
        shop = Shop(name="Unauthorized Shop", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        room = ChatRoom(
            shop_id=shop.id,
            customer_id=customer_user.id,
            room_type=ChatRoomType.GENERAL
        )
        session.add(room)
        session.commit()
        session.refresh(room)

        response = client.post(
            f"/api/v1/chat/rooms/{room.id}/messages",
            json={
                "content": "I shouldn't be able to send this"
            },
            headers=auth_headers
        )
        assert response.status_code == 403


class TestChatRoomView:
    """Test viewing chat rooms and messages."""

    def test_list_customer_rooms(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test customer listing their chat rooms."""
        shop = Shop(name="List Room Shop", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        room = ChatRoom(
            shop_id=shop.id,
            customer_id=customer_user.id,
            room_type=ChatRoomType.GENERAL
        )
        session.add(room)
        session.commit()

        response = client.get(
            "/api/v1/chat/rooms",
            headers=customer_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_view_room_messages(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test viewing room with messages."""
        shop = Shop(name="View Msg Shop", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        room = ChatRoom(
            shop_id=shop.id,
            customer_id=customer_user.id,
            room_type=ChatRoomType.GENERAL
        )
        session.add(room)
        session.commit()
        session.refresh(room)

        # Add messages
        msg1 = ChatMessage(
            room_id=room.id,
            sender_id=customer_user.id,
            message_type=ChatMessageType.TEXT,
            content="First message"
        )
        msg2 = ChatMessage(
            room_id=room.id,
            sender_id=customer_user.id,
            message_type=ChatMessageType.TEXT,
            content="Second message"
        )
        session.add(msg1)
        session.add(msg2)
        session.commit()

        response = client.get(
            f"/api/v1/chat/rooms/{room.id}",
            headers=customer_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) >= 2

    def test_mark_message_read(self, client: TestClient, session: Session, shop_owner, customer_user, owner_auth_headers):
        """Test marking a message as read."""
        shop = Shop(name="Read Shop", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        user_shop = UserShop(user_id=shop_owner.id, shop_id=shop.id, role=ShopRole.OWNER)
        session.add(user_shop)
        session.commit()

        room = ChatRoom(
            shop_id=shop.id,
            customer_id=customer_user.id,
            room_type=ChatRoomType.GENERAL
        )
        session.add(room)
        session.commit()
        session.refresh(room)

        # Customer sends message
        msg = ChatMessage(
            room_id=room.id,
            sender_id=customer_user.id,
            message_type=ChatMessageType.TEXT,
            content="Please read this"
        )
        session.add(msg)
        session.commit()
        session.refresh(msg)

        # Shop owner marks as read
        response = client.put(
            f"/api/v1/chat/rooms/{room.id}/messages/{msg.id}/read",
            headers=owner_auth_headers
        )
        assert response.status_code == 200

    def test_close_chat_room(self, client: TestClient, session: Session, shop_owner, customer_user, customer_auth_headers):
        """Test closing a chat room."""
        shop = Shop(name="Close Shop", address="123 St")
        session.add(shop)
        session.commit()
        session.refresh(shop)

        room = ChatRoom(
            shop_id=shop.id,
            customer_id=customer_user.id,
            room_type=ChatRoomType.GENERAL
        )
        session.add(room)
        session.commit()
        session.refresh(room)

        response = client.put(
            f"/api/v1/chat/rooms/{room.id}/close",
            headers=customer_auth_headers
        )
        assert response.status_code == 200

        # Verify room is closed - sending message should fail
        response = client.post(
            f"/api/v1/chat/rooms/{room.id}/messages",
            json={"content": "Should fail"},
            headers=customer_auth_headers
        )
        assert response.status_code == 400
