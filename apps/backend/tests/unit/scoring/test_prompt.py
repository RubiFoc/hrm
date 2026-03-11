"""Unit tests for scoring prompt construction with enriched parsed CV profiles."""

from __future__ import annotations

from types import SimpleNamespace

from hrm_backend.scoring.utils.prompt import build_match_score_prompt


def test_build_match_score_prompt_embeds_enriched_parsed_profile_without_breaking() -> None:
    """Verify scoring prompt accepts additive workplace and education profile fields."""
    vacancy = SimpleNamespace(
        title="Warehouse Supervisor",
        description="Lead warehouse operations and staff scheduling.",
        department="Operations",
        status="open",
    )
    document = SimpleNamespace(
        parsed_profile_json={
            "skills": ["inventory control", "forklift operation"],
            "experience": {
                "years_total": 5,
                "entries": [
                    {
                        "employer": "Acme Logistics",
                        "position": {
                            "raw": "Warehouse Supervisor",
                            "normalized": "warehouse supervisor",
                        },
                        "date_range": {
                            "raw": "Jan 2022 - Present",
                            "start": "2022-01",
                            "end": None,
                            "is_current": True,
                        },
                        "summary": "Managed shifts, inventory, and staff scheduling.",
                    }
                ],
            },
            "workplaces": {
                "entries": [
                    {
                        "employer": "Acme Logistics",
                        "position": {
                            "raw": "Warehouse Supervisor",
                            "normalized": "warehouse supervisor",
                        },
                        "date_range": {
                            "raw": "Jan 2022 - Present",
                            "start": "2022-01",
                            "end": None,
                            "is_current": True,
                        },
                        "summary": "Managed shifts, inventory, and staff scheduling.",
                    }
                ]
            },
            "education": {
                "entries": [
                    {
                        "institution": "Minsk State College",
                        "degree": "Logistics Technician",
                        "date_range": {
                            "raw": "2016 - 2019",
                            "start": "2016",
                            "end": "2019",
                            "is_current": False,
                        },
                        "summary": None,
                    }
                ]
            },
            "titles": {
                "current": {
                    "raw": "Warehouse Supervisor",
                    "normalized": "warehouse supervisor",
                },
                "past": [{"raw": "Storekeeper", "normalized": "storekeeper"}],
            },
            "summary": "Experienced warehouse operations leader.",
        },
        evidence_json=[
            {
                "field": "experience.entries[0].position.raw",
                "snippet": "Acme Logistics | Warehouse Supervisor | Jan 2022 - Present",
            }
        ],
        detected_language="en",
        parsed_at=SimpleNamespace(isoformat=lambda: "2026-03-11T10:00:00+00:00"),
    )

    prompt = build_match_score_prompt(vacancy=vacancy, document=document)

    assert '"workplaces"' in prompt
    assert '"education"' in prompt
    assert '"titles"' in prompt
    assert '"inventory control"' in prompt
