"""Unit tests for department service helpers and validation rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from hrm_backend.departments.schemas.department import (
    DepartmentCreateRequest,
    DepartmentUpdateRequest,
)
from hrm_backend.departments.services.department_service import (
    DepartmentService,
    _normalize_department_name,
)


@dataclass
class DummyDepartment:
    """Lightweight department entity for unit tests."""

    department_id: str
    name: str
    created_at: datetime
    updated_at: datetime


class FakeDepartmentDAO:
    """In-memory DAO stub for department service tests."""

    def __init__(self) -> None:
        self.existing_by_name: DummyDepartment | None = None
        self.entity_by_id: DummyDepartment | None = None
        self.created: DummyDepartment | None = None
        self.updated: DummyDepartment | None = None

    def get_by_name(self, name: str) -> DummyDepartment | None:
        return self.existing_by_name

    def get_by_id(self, department_id: str) -> DummyDepartment | None:
        return self.entity_by_id

    def create_department(self, *, name: str) -> DummyDepartment:
        entity = DummyDepartment(
            department_id=str(uuid4()),
            name=name,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.created = entity
        return entity

    def update_department(self, *, entity: DummyDepartment, name: str) -> DummyDepartment:
        entity.name = name
        entity.updated_at = datetime.now(UTC)
        self.updated = entity
        return entity


def _make_entity(name: str = "Engineering") -> DummyDepartment:
    return DummyDepartment(
        department_id=str(uuid4()),
        name=name,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def test_normalize_department_name_trims_whitespace() -> None:
    """Ensure department name normalization trims input."""
    assert _normalize_department_name("  Engineering  ") == "Engineering"


def test_normalize_department_name_rejects_empty_string() -> None:
    """Ensure empty department names are rejected."""
    with pytest.raises(HTTPException) as excinfo:
        _normalize_department_name("   ")

    error = excinfo.value
    assert error.status_code == 422
    assert error.detail == "invalid_department_name"


def test_create_department_rejects_duplicate_name() -> None:
    """Ensure create rejects duplicate department names."""
    dao = FakeDepartmentDAO()
    dao.existing_by_name = _make_entity()
    service = DepartmentService(department_dao=dao)

    with pytest.raises(HTTPException) as excinfo:
        service.create_department(payload=DepartmentCreateRequest(name="Engineering"))

    error = excinfo.value
    assert error.status_code == 409
    assert error.detail == "department_name_exists"


def test_update_department_rejects_empty_patch() -> None:
    """Ensure update fails when no fields are provided."""
    dao = FakeDepartmentDAO()
    service = DepartmentService(department_dao=dao)

    with pytest.raises(HTTPException) as excinfo:
        service.update_department(
            department_id=uuid4(),
            payload=DepartmentUpdateRequest(name=None),
        )

    error = excinfo.value
    assert error.status_code == 422
    assert error.detail == "empty_patch"


def test_update_department_allows_same_name() -> None:
    """Ensure update succeeds when name remains unchanged."""
    dao = FakeDepartmentDAO()
    entity = _make_entity(name="Operations")
    dao.entity_by_id = entity
    dao.existing_by_name = entity
    service = DepartmentService(department_dao=dao)

    result = service.update_department(
        department_id=UUID(entity.department_id),
        payload=DepartmentUpdateRequest(name="Operations"),
    )

    assert result.name == "Operations"
    assert dao.updated is entity
