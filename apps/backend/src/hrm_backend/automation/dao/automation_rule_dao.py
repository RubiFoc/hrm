"""Data-access helpers for automation rule persistence."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from hrm_backend.automation.models.automation_rule import AutomationRule


class AutomationRuleDAO:
    """Persist and query automation rule rows."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with an active SQLAlchemy session."""
        self._session = session

    def create_rule(
        self,
        *,
        name: str,
        trigger: str,
        conditions_json: dict[str, object] | None,
        actions_json: Sequence[dict[str, object]],
        priority: int,
        created_by_staff_id: str,
        commit: bool = True,
    ) -> AutomationRule:
        """Insert one new rule row."""
        entity = AutomationRule(
            name=name,
            trigger=trigger,
            conditions_json=conditions_json,
            actions_json=list(actions_json),
            priority=priority,
            is_active=False,
            created_by_staff_id=created_by_staff_id,
            updated_by_staff_id=created_by_staff_id,
        )
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity

        self._session.flush()
        return entity

    def list_rules(
        self,
        *,
        trigger: str | None = None,
        is_active: bool | None = None,
    ) -> list[AutomationRule]:
        """List rules in deterministic order for operator/admin UX."""
        query = self._session.query(AutomationRule)
        if trigger is not None:
            query = query.filter(AutomationRule.trigger == trigger)
        if is_active is not None:
            query = query.filter(AutomationRule.is_active.is_(is_active))
        return list(
            query.order_by(
                AutomationRule.priority.desc(),
                AutomationRule.updated_at.desc(),
                AutomationRule.rule_id.asc(),
            ).all()
        )

    def get_by_id(self, rule_id: str) -> AutomationRule | None:
        """Load one rule row by identifier."""
        return self._session.get(AutomationRule, rule_id)

    def update_rule(
        self,
        *,
        entity: AutomationRule,
        name: str | None,
        set_conditions: bool,
        conditions_json: dict[str, object] | None,
        actions_json: Sequence[dict[str, object]] | None,
        priority: int | None,
        updated_by_staff_id: str,
        commit: bool = True,
    ) -> AutomationRule:
        """Apply partial updates to a rule row."""
        if name is not None:
            entity.name = name
        if set_conditions:
            entity.conditions_json = conditions_json
        if actions_json is not None:
            entity.actions_json = list(actions_json)
        if priority is not None:
            entity.priority = priority
        entity.updated_by_staff_id = updated_by_staff_id
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity

        self._session.flush()
        return entity

    def set_active(
        self,
        *,
        entity: AutomationRule,
        is_active: bool,
        updated_by_staff_id: str,
        commit: bool = True,
    ) -> AutomationRule:
        """Toggle activation state for a rule row."""
        entity.is_active = is_active
        entity.updated_by_staff_id = updated_by_staff_id
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity

        self._session.flush()
        return entity

    def list_active_by_trigger(self, trigger: str) -> list[AutomationRule]:
        """List active rules for trigger evaluation in deterministic order."""
        return list(
            self._session.query(AutomationRule)
            .filter(
                AutomationRule.trigger == trigger,
                AutomationRule.is_active.is_(True),
            )
            .order_by(
                AutomationRule.priority.desc(),
                AutomationRule.rule_id.asc(),
            )
            .all()
        )
