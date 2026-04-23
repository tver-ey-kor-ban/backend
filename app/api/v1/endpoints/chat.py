"""Chat/Support endpoints for customer-shop communication."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, func

from app.db import get_session
from app.models.chat import (
    ChatRoom, ChatMessage, ChatRoomCreate,
    ChatMessageCreate,
    ChatMessageType
)
from app.models.shop import Shop, UserShop
from app.models.user import User
from app.core.security import get_current_user, TokenData

router = APIRouter(prefix="/chat", tags=["chat"])


# ==================== CHAT ROOMS ====================

@router.post("/rooms", status_code=status.HTTP_201_CREATED)
def create_chat_room(
    room_data: ChatRoomCreate,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new chat room for customer-shop communication."""
    # Verify shop exists
    shop = session.get(Shop, room_data.shop_id)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shop not found"
        )
    
    # Check if room already exists for this appointment/order
    if room_data.appointment_id:
        existing = session.exec(
            select(ChatRoom).where(
                ChatRoom.appointment_id == room_data.appointment_id,
                ChatRoom.customer_id == current_user.user_id
            )
        ).first()
        if existing:
            return {
                "message": "Chat room already exists",
                "room_id": existing.id
            }
    
    if room_data.product_order_id:
        existing = session.exec(
            select(ChatRoom).where(
                ChatRoom.product_order_id == room_data.product_order_id,
                ChatRoom.customer_id == current_user.user_id
            )
        ).first()
        if existing:
            return {
                "message": "Chat room already exists",
                "room_id": existing.id
            }
    
    # Create room
    room = ChatRoom(
        shop_id=room_data.shop_id,
        customer_id=current_user.user_id,
        room_type=room_data.room_type,
        appointment_id=room_data.appointment_id,
        product_order_id=room_data.product_order_id
    )
    session.add(room)
    session.flush()
    
    # Add system message
    system_msg = ChatMessage(
        room_id=room.id,
        sender_id=current_user.user_id,
        message_type=ChatMessageType.SYSTEM,
        content="Chat room created"
    )
    session.add(system_msg)
    session.commit()
    session.refresh(room)
    
    return {
        "message": "Chat room created",
        "room_id": room.id
    }


@router.get("/rooms")
def get_my_chat_rooms(
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all chat rooms for current user (customer or shop member)."""
    # Check if user is a shop member for any shop
    user_shops = session.exec(
        select(UserShop).where(
            UserShop.user_id == current_user.user_id,
            UserShop.is_active
        )
    ).all()
    
    shop_ids = [us.shop_id for us in user_shops]
    
    if shop_ids:
        # User is a shop member - get rooms for their shops
        query = select(ChatRoom).where(ChatRoom.shop_id.in_(shop_ids))
    else:
        # User is a customer - get their rooms
        query = select(ChatRoom).where(ChatRoom.customer_id == current_user.user_id)
    
    query = query.where(ChatRoom.is_active).order_by(ChatRoom.updated_at.desc())
    rooms = session.exec(query).all()
    
    result = []
    for room in rooms:
        # Get last message
        last_message = session.exec(
            select(ChatMessage).where(
                ChatMessage.room_id == room.id,
                ChatMessage.message_type != ChatMessageType.SYSTEM
            ).order_by(ChatMessage.created_at.desc())
        ).first()
        
        # Count unread messages
        if shop_ids:
            # Shop member - count unread customer messages
            unread_count = session.exec(
                select(func.count(ChatMessage.id)).where(
                    ChatMessage.room_id == room.id,
                    ChatMessage.sender_id == room.customer_id,
                    not ChatMessage.is_read
                )
            ).one()
        else:
            # Customer - count unread shop messages
            unread_count = session.exec(
                select(func.count(ChatMessage.id)).where(
                    ChatMessage.room_id == room.id,
                    ChatMessage.sender_id != current_user.user_id,
                    not ChatMessage.is_read
                )
            ).one()
        
        # Get shop/customer info
        shop = session.get(Shop, room.shop_id)
        customer = session.get(User, room.customer_id)
        
        result.append({
            "id": room.id,
            "shop": {
                "id": room.shop_id,
                "name": shop.name if shop else "Unknown"
            },
            "customer": {
                "id": room.customer_id,
                "name": customer.full_name if customer else "Unknown"
            },
            "room_type": room.room_type,
            "appointment_id": room.appointment_id,
            "product_order_id": room.product_order_id,
            "is_active": room.is_active,
            "last_message": {
                "id": last_message.id,
                "sender_id": last_message.sender_id,
                "content": last_message.content,
                "created_at": last_message.created_at
            } if last_message else None,
            "unread_count": unread_count,
            "created_at": room.created_at,
            "updated_at": room.updated_at
        })
    
    return result


@router.get("/rooms/{room_id}")
def get_chat_room(
    room_id: int,
    limit: int = 50,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get chat room with messages."""
    room = session.get(ChatRoom, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found"
        )
    
    # Verify access
    user_shops = session.exec(
        select(UserShop).where(
            UserShop.user_id == current_user.user_id,
            UserShop.is_active
        )
    ).all()
    shop_ids = [us.shop_id for us in user_shops]
    
    if room.customer_id != current_user.user_id and room.shop_id not in shop_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get messages
    messages = session.exec(
        select(ChatMessage).where(
            ChatMessage.room_id == room.id
        ).order_by(ChatMessage.created_at.asc()).limit(limit)
    ).all()
    
    # Mark messages as read
    for msg in messages:
        if msg.sender_id != current_user.user_id and not msg.is_read:
            msg.is_read = True
            msg.read_at = datetime.utcnow()
    session.commit()
    
    # Get shop/customer info
    shop = session.get(Shop, room.shop_id)
    customer = session.get(User, room.customer_id)
    
    return {
        "id": room.id,
        "shop": {
            "id": room.shop_id,
            "name": shop.name if shop else "Unknown"
        },
        "customer": {
            "id": room.customer_id,
            "name": customer.full_name if customer else "Unknown"
        },
        "room_type": room.room_type,
        "appointment_id": room.appointment_id,
        "product_order_id": room.product_order_id,
        "is_active": room.is_active,
        "messages": [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "message_type": m.message_type,
                "content": m.content,
                "attachment_url": m.attachment_url,
                "is_read": m.is_read,
                "read_at": m.read_at,
                "created_at": m.created_at
            }
            for m in messages
        ],
        "created_at": room.created_at,
        "updated_at": room.updated_at
    }


# ==================== MESSAGES ====================

@router.post("/rooms/{room_id}/messages")
def send_message(
    room_id: int,
    message_data: ChatMessageCreate,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Send a message in a chat room."""
    room = session.get(ChatRoom, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found"
        )
    
    if not room.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chat room is closed"
        )
    
    # Verify access
    user_shops = session.exec(
        select(UserShop).where(
            UserShop.user_id == current_user.user_id,
            UserShop.is_active
        )
    ).all()
    shop_ids = [us.shop_id for us in user_shops]
    
    if room.customer_id != current_user.user_id and room.shop_id not in shop_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Create message
    message = ChatMessage(
        room_id=room.id,
        sender_id=current_user.user_id,
        message_type=message_data.message_type,
        content=message_data.content,
        attachment_url=message_data.attachment_url
    )
    session.add(message)
    
    # Update room timestamp
    room.updated_at = datetime.utcnow()
    session.commit()
    session.refresh(message)
    
    # Notify recipient
    from app.services.notification_service import NotificationService
    from app.models.notification import NotificationType
    
    notification_service = NotificationService(session)
    sender = session.get(User, current_user.user_id)
    sender_name = sender.full_name if sender else "Someone"
    
    # Determine recipient
    if current_user.user_id == room.customer_id:
        # Customer sent message - notify shop members
        members = session.exec(
            select(UserShop).where(
                UserShop.shop_id == room.shop_id,
                UserShop.is_active
            )
        ).all()
        for member in members:
            notification_service.create_notification(
                user_id=member.user_id,
                type=NotificationType.STATUS_UPDATE,
                title="New Chat Message",
                message=f"{sender_name}: {message_data.content[:50]}...",
                data={
                    "room_id": room.id,
                    "message_id": message.id,
                    "sender_id": current_user.user_id
                }
            )
    else:
        # Shop member sent message - notify customer
        notification_service.create_notification(
            user_id=room.customer_id,
            type=NotificationType.STATUS_UPDATE,
            title="New Message from Shop",
            message=f"{sender_name}: {message_data.content[:50]}...",
            data={
                "room_id": room.id,
                "message_id": message.id,
                "sender_id": current_user.user_id
            }
        )
    
    return {
        "message": "Message sent",
        "message_id": message.id,
        "created_at": message.created_at
    }


@router.put("/rooms/{room_id}/messages/{message_id}/read")
def mark_message_read(
    room_id: int,
    message_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Mark a message as read."""
    message = session.exec(
        select(ChatMessage).where(
            ChatMessage.id == message_id,
            ChatMessage.room_id == room_id
        )
    ).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    if message.sender_id == current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot mark your own message as read"
        )
    
    message.is_read = True
    message.read_at = datetime.utcnow()
    session.commit()
    
    return {"message": "Message marked as read"}


@router.get("/rooms/{room_id}/unread-count")
def get_unread_count(
    room_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get unread message count for a chat room."""
    room = session.get(ChatRoom, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found"
        )
    
    # Verify access
    user_shops = session.exec(
        select(UserShop).where(
            UserShop.user_id == current_user.user_id,
            UserShop.is_active
        )
    ).all()
    shop_ids = [us.shop_id for us in user_shops]
    
    if room.customer_id != current_user.user_id and room.shop_id not in shop_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    unread_count = session.exec(
        select(func.count(ChatMessage.id)).where(
            ChatMessage.room_id == room_id,
            ChatMessage.sender_id != current_user.user_id,
            not ChatMessage.is_read
        )
    ).one()
    
    return {"unread_count": unread_count}


@router.put("/rooms/{room_id}/close")
def close_chat_room(
    room_id: int,
    current_user: TokenData = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Close a chat room (customer or shop member)."""
    room = session.get(ChatRoom, room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found"
        )
    
    # Verify access
    user_shops = session.exec(
        select(UserShop).where(
            UserShop.user_id == current_user.user_id,
            UserShop.is_active
        )
    ).all()
    shop_ids = [us.shop_id for us in user_shops]
    
    if room.customer_id != current_user.user_id and room.shop_id not in shop_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    room.is_active = False
    room.updated_at = datetime.utcnow()
    
    # Add system message
    system_msg = ChatMessage(
        room_id=room.id,
        sender_id=current_user.user_id,
        message_type=ChatMessageType.SYSTEM,
        content="Chat room closed"
    )
    session.add(system_msg)
    session.commit()
    
    return {"message": "Chat room closed"}
