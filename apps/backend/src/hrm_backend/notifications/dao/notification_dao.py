"""Data-access helpers for in-app notification persistence."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy.orm import Session

from hrm_backend.notifications.models.notification import Notification
from hrm_backend.notifications.schemas.notification import NotificationCreate


class NotificationDAO:
    """Persist and query recipient-scoped in-app notifications."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with an active SQLAlchemy session.

        Args:
            session: Active request or job session.
        """
        self._session = session

    def get_by_id_for_recipient(
        self,
        *,
        notification_id: str,
        recipient_staff_id: str,
    ) -> Notification | None:
        """Load one notification only when it belongs to the requested recipient."""
        return (
            self._session.query(Notification)
            .filter(
                Notification.notification_id == notification_id,
                Notification.recipient_staff_id == recipient_staff_id,
            )
            .first()
        )

    def list_for_recipient(
        self,
        *,
        recipient_staff_id: str,
        unread_only: bool,
        limit: int,
        offset: int,
    ) -> list[Notification]:
        """List notifications for one recipient with optional unread-only filtering."""
        query = self._session.query(Notification).filter(
            Notification.recipient_staff_id == recipient_staff_id,
        )
        if unread_only:
            query = query.filter(Notification.read_at.is_(None))
        return list(
            query.order_by(
                Notification.created_at.desc(),
                Notification.notification_id.desc(),
            )
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_all_for_recipient(self, *, recipient_staff_id: str) -> int:
        """Count all notifications stored for one recipient."""
        return (
            self._session.query(Notification)
            .filter(Notification.recipient_staff_id == recipient_staff_id)
            .count()
        )

    def count_unread_for_recipient(self, *, recipient_staff_id: str) -> int:
        """Count unread notifications stored for one recipient."""
        return (
            self._session.query(Notification)
            .filter(
                Notification.recipient_staff_id == recipient_staff_id,
                Notification.read_at.is_(None),
            )
            .count()
        )

    def create_notifications(
        self,
        *,
        payloads: Sequence[NotificationCreate],
        commit: bool = True,
    ) -> list[Notification]:
        """Insert one or more notification rows while skipping existing dedupe pairs."""
        if not payloads:
            return []

        dedupe_keys_by_recipient: dict[str, set[str]] = defaultdict(set)
        for payload in payloads:
            dedupe_keys_by_recipient[str(payload.recipient_staff_id)].add(payload.dedupe_key)

        existing_pairs: set[tuple[str, str]] = set()
        for recipient_staff_id, dedupe_keys in dedupe_keys_by_recipient.items():
            rows = (
                self._session.query(Notification.dedupe_key)
                .filter(
                    Notification.recipient_staff_id == recipient_staff_id,
                    Notification.dedupe_key.in_(sorted(dedupe_keys)),
                )
                .all()
            )
            existing_pairs.update((recipient_staff_id, dedupe_key) for (dedupe_key,) in rows)

        entities = []
        for payload in payloads:
            recipient_staff_id = str(payload.recipient_staff_id)
            dedupe_pair = (recipient_staff_id, payload.dedupe_key)
            if dedupe_pair in existing_pairs:
                continue
            entity = Notification(
                recipient_staff_id=recipient_staff_id,
                recipient_role=payload.recipient_role,
                kind=payload.kind,
                source_type=payload.source_type,
                source_id=str(payload.source_id),
                dedupe_key=payload.dedupe_key,
                title=payload.title,
                body=payload.body,
                payload_json=payload.payload.model_dump(mode="json"),
            )
            self._session.add(entity)
            entities.append(entity)
            existing_pairs.add(dedupe_pair)

        if commit:
            self._session.commit()
            for entity in entities:
                self._session.refresh(entity)
            return entities

        self._session.flush()
        return entities

    def mark_as_read(
        self,
        *,
        entity: Notification,
        commit: bool = True,
    ) -> Notification:
        """Persist read-state changes for one notification row."""
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity

        self._session.flush()
        return entity
