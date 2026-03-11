"""Business service for onboarding checklist template management."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.employee.dao.onboarding_template_dao import OnboardingTemplateDAO
from hrm_backend.employee.models.template import OnboardingTemplate, OnboardingTemplateItem
from hrm_backend.employee.schemas.template import (
    OnboardingChecklistTemplateCreateRequest,
    OnboardingChecklistTemplateItemResponse,
    OnboardingChecklistTemplateItemUpsert,
    OnboardingChecklistTemplateListResponse,
    OnboardingChecklistTemplateResponse,
    OnboardingChecklistTemplateUpdateRequest,
    OnboardingChecklistTemplateUpsert,
)

ONBOARDING_TEMPLATE_NOT_FOUND = "onboarding_template_not_found"
ONBOARDING_TEMPLATE_NAME_CONFLICT = "onboarding_template_name_conflict"
ONBOARDING_TEMPLATE_INVALID = "onboarding_template_invalid"


class OnboardingTemplateService:
    """Create, read, list, and update onboarding checklist templates."""

    def __init__(
        self,
        *,
        session: Session,
        dao: OnboardingTemplateDAO,
        audit_service: AuditService,
    ) -> None:
        """Initialize onboarding template service dependencies.

        Args:
            session: SQLAlchemy session used to bundle template and item writes atomically.
            dao: DAO for onboarding templates and items.
            audit_service: Audit service for success and failure traces.
        """
        self._session = session
        self._dao = dao
        self._audit_service = audit_service

    def build_upsert_payload(
        self,
        *,
        payload: OnboardingChecklistTemplateCreateRequest
        | OnboardingChecklistTemplateUpdateRequest,
    ) -> OnboardingChecklistTemplateUpsert:
        """Normalize and validate template payload before persistence.

        Args:
            payload: Staff-facing create or update request.

        Returns:
            OnboardingChecklistTemplateUpsert: Normalized payload with sorted items.

        Raises:
            ValueError: If item codes or sort orders are duplicated.
        """
        seen_codes: set[str] = set()
        seen_sort_orders: set[int] = set()
        normalized_items: list[OnboardingChecklistTemplateItemUpsert] = []

        for item in payload.items:
            code = item.code.strip()
            title = item.title.strip()
            if code in seen_codes:
                raise ValueError("Onboarding template item codes must be unique")
            if item.sort_order in seen_sort_orders:
                raise ValueError("Onboarding template item sort orders must be unique")
            seen_codes.add(code)
            seen_sort_orders.add(item.sort_order)
            normalized_items.append(
                OnboardingChecklistTemplateItemUpsert(
                    code=code,
                    title=title,
                    description=item.description.strip() if item.description else None,
                    sort_order=item.sort_order,
                    is_required=item.is_required,
                )
            )

        return OnboardingChecklistTemplateUpsert(
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            is_active=payload.is_active,
            items=sorted(
                normalized_items,
                key=lambda item: (item.sort_order, item.code),
            ),
        )

    def create_template(
        self,
        *,
        payload: OnboardingChecklistTemplateCreateRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> OnboardingChecklistTemplateResponse:
        """Create one onboarding checklist template with its items."""
        actor_sub, _ = actor_from_auth_context(auth_context)
        try:
            upsert_payload = self.build_upsert_payload(payload=payload)
        except ValueError as exc:
            self._audit_failure(
                action="onboarding_template:create",
                auth_context=auth_context,
                request=request,
                reason=ONBOARDING_TEMPLATE_INVALID,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=ONBOARDING_TEMPLATE_INVALID,
            ) from exc

        existing = self._dao.get_by_name(upsert_payload.name)
        if existing is not None:
            self._audit_failure(
                action="onboarding_template:create",
                auth_context=auth_context,
                request=request,
                resource_id=existing.template_id,
                reason=ONBOARDING_TEMPLATE_NAME_CONFLICT,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ONBOARDING_TEMPLATE_NAME_CONFLICT,
            )

        template, items = self._persist_create_bundle(
            payload=upsert_payload,
            created_by_staff_id=actor_sub,
        )
        self._audit_success(
            action="onboarding_template:create",
            auth_context=auth_context,
            request=request,
            resource_id=template.template_id,
        )
        return _to_template_response(template, items)

    def list_templates(
        self,
        *,
        active_only: bool,
        auth_context: AuthContext,
        request: Request,
    ) -> OnboardingChecklistTemplateListResponse:
        """List onboarding checklist templates with optional active-only filtering."""
        templates = self._dao.list_templates(active_only=active_only)
        items = self._dao.list_items_for_template_ids(
            [template.template_id for template in templates]
        )
        grouped_items = _group_items(items)
        self._audit_success(
            action="onboarding_template:list",
            auth_context=auth_context,
            request=request,
        )
        return OnboardingChecklistTemplateListResponse(
            items=[
                _to_template_response(template, grouped_items.get(template.template_id, []))
                for template in templates
            ]
        )

    def get_template(
        self,
        *,
        template_id: UUID,
        auth_context: AuthContext,
        request: Request,
    ) -> OnboardingChecklistTemplateResponse:
        """Read one onboarding checklist template by identifier."""
        entity = self._dao.get_by_id(str(template_id))
        if entity is None:
            self._audit_failure(
                action="onboarding_template:read",
                auth_context=auth_context,
                request=request,
                reason=ONBOARDING_TEMPLATE_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ONBOARDING_TEMPLATE_NOT_FOUND,
            )

        items = self._dao.list_items_for_template_ids([entity.template_id])
        self._audit_success(
            action="onboarding_template:read",
            auth_context=auth_context,
            request=request,
            resource_id=entity.template_id,
        )
        return _to_template_response(entity, items)

    def update_template(
        self,
        *,
        template_id: UUID,
        payload: OnboardingChecklistTemplateUpdateRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> OnboardingChecklistTemplateResponse:
        """Replace one onboarding checklist template and its items."""
        entity = self._dao.get_by_id(str(template_id))
        if entity is None:
            self._audit_failure(
                action="onboarding_template:update",
                auth_context=auth_context,
                request=request,
                reason=ONBOARDING_TEMPLATE_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ONBOARDING_TEMPLATE_NOT_FOUND,
            )

        try:
            upsert_payload = self.build_upsert_payload(payload=payload)
        except ValueError as exc:
            self._audit_failure(
                action="onboarding_template:update",
                auth_context=auth_context,
                request=request,
                resource_id=entity.template_id,
                reason=ONBOARDING_TEMPLATE_INVALID,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=ONBOARDING_TEMPLATE_INVALID,
            ) from exc

        existing_by_name = self._dao.get_by_name(upsert_payload.name)
        if existing_by_name is not None and existing_by_name.template_id != entity.template_id:
            self._audit_failure(
                action="onboarding_template:update",
                auth_context=auth_context,
                request=request,
                resource_id=entity.template_id,
                reason=ONBOARDING_TEMPLATE_NAME_CONFLICT,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ONBOARDING_TEMPLATE_NAME_CONFLICT,
            )

        updated_template, updated_items = self._persist_update_bundle(
            entity=entity,
            payload=upsert_payload,
        )
        self._audit_success(
            action="onboarding_template:update",
            auth_context=auth_context,
            request=request,
            resource_id=updated_template.template_id,
        )
        return _to_template_response(updated_template, updated_items)

    def _persist_create_bundle(
        self,
        *,
        payload: OnboardingChecklistTemplateUpsert,
        created_by_staff_id: str,
    ) -> tuple[OnboardingTemplate, list[OnboardingTemplateItem]]:
        """Persist template row and items in one transaction."""
        try:
            template = self._dao.create_template(
                payload=payload,
                created_by_staff_id=created_by_staff_id,
                commit=False,
            )
            items = self._dao.replace_items(
                template_id=template.template_id,
                payload=payload,
                commit=False,
            )
            if payload.is_active:
                self._dao.deactivate_other_templates(
                    active_template_id=template.template_id,
                    commit=False,
                )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        self._session.refresh(template)
        for item in items:
            self._session.refresh(item)
        return template, items

    def _persist_update_bundle(
        self,
        *,
        entity: OnboardingTemplate,
        payload: OnboardingChecklistTemplateUpsert,
    ) -> tuple[OnboardingTemplate, list[OnboardingTemplateItem]]:
        """Persist template update and full item replacement in one transaction."""
        try:
            updated_template = self._dao.update_template(
                entity=entity,
                payload=payload,
                commit=False,
            )
            updated_items = self._dao.replace_items(
                template_id=updated_template.template_id,
                payload=payload,
                commit=False,
            )
            if payload.is_active:
                self._dao.deactivate_other_templates(
                    active_template_id=updated_template.template_id,
                    commit=False,
                )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        self._session.refresh(updated_template)
        for item in updated_items:
            self._session.refresh(item)
        return updated_template, updated_items

    def _audit_success(
        self,
        *,
        action: str,
        auth_context: AuthContext,
        request: Request,
        resource_id: str | None = None,
    ) -> None:
        """Record one successful onboarding-template audit event."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action=action,
            resource_type="onboarding_template",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=resource_id,
        )

    def _audit_failure(
        self,
        *,
        action: str,
        auth_context: AuthContext,
        request: Request,
        reason: str,
        resource_id: str | None = None,
    ) -> None:
        """Record one failed onboarding-template audit event."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action=action,
            resource_type="onboarding_template",
            result="failure",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=resource_id,
            reason=reason,
        )


def _group_items(
    items: list[OnboardingTemplateItem],
) -> dict[str, list[OnboardingTemplateItem]]:
    """Group template items by template identifier for list responses."""
    grouped: dict[str, list[OnboardingTemplateItem]] = defaultdict(list)
    for item in items:
        grouped[item.template_id].append(item)
    return grouped


def _to_template_response(
    entity: OnboardingTemplate,
    items: list[OnboardingTemplateItem],
) -> OnboardingChecklistTemplateResponse:
    """Map onboarding template entities to API response schema."""
    return OnboardingChecklistTemplateResponse(
        template_id=entity.template_id,
        name=entity.name,
        description=entity.description,
        is_active=entity.is_active,
        items=[
            OnboardingChecklistTemplateItemResponse(
                template_item_id=item.template_item_id,
                code=item.code,
                title=item.title,
                description=item.description,
                sort_order=item.sort_order,
                is_required=item.is_required,
            )
            for item in items
        ],
        created_by_staff_id=entity.created_by_staff_id,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
