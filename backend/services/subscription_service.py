from typing import Optional

from sqlalchemy.orm import Session

from backend.models.message import MessagePriority, MessageType
from backend.models.subscription import EventType, Subscription
from backend.services.message_service import send_message


def subscribe(
    db: Session,
    coordinate_id: str,
    subscriber_role: str,
    corps_id: str,
    event_type: EventType,
    subscriber_session_id: Optional[str] = None,
) -> Subscription:
    # Check for existing active subscription to avoid duplicates
    existing = (
        db.query(Subscription)
        .filter(
            Subscription.coordinate_id == coordinate_id,
            Subscription.subscriber_role == subscriber_role,
            Subscription.corps_id == corps_id,
            Subscription.event_type == event_type,
            Subscription.active.is_(True),
        )
        .first()
    )
    if existing:
        return existing

    sub = Subscription(
        coordinate_id=coordinate_id,
        subscriber_role=subscriber_role,
        subscriber_session_id=subscriber_session_id,
        corps_id=corps_id,
        event_type=event_type,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def unsubscribe(db: Session, subscription_id: str) -> Subscription:
    sub = db.get(Subscription, subscription_id)
    if sub is None:
        raise ValueError(f"Subscription {subscription_id} not found")
    sub.active = False
    db.commit()
    db.refresh(sub)
    return sub


def get_subscribers(
    db: Session,
    coordinate_id: str,
    event_type: EventType,
) -> list[Subscription]:
    return (
        db.query(Subscription)
        .filter(
            Subscription.coordinate_id == coordinate_id,
            Subscription.event_type == event_type,
            Subscription.active.is_(True),
        )
        .all()
    )


def notify_subscribers(
    db: Session,
    coordinate_id: str,
    corps_id: str,
    event_type: EventType,
    subject: str,
    body: Optional[str] = None,
    source_role: str = "system",
) -> list:
    """Fire notifications for all active subscribers to an event on a coordinate."""
    subscribers = get_subscribers(db, coordinate_id, event_type)
    messages = []
    for sub in subscribers:
        msg = send_message(
            db=db,
            corps_id=corps_id,
            from_role=source_role,
            type=MessageType.STATUS,
            subject=subject,
            body=body,
            to_role=sub.subscriber_role,
            to_session_id=sub.subscriber_session_id,
            priority=MessagePriority.NORMAL,
            coordinate_id=coordinate_id,
        )
        messages.append(msg)
    return messages
