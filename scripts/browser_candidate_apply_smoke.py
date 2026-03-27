#!/usr/bin/env python3
"""Browser-level smoke verification for the public candidate application flow.

This script opens the public candidate application route in a real headless
Chrome session, submits a CV application through the React UI, verifies that
browser requests target the configured backend origin, and confirms tracking
state is persisted to session storage. Legacy `/candidate` deep links remain
supported when the caller passes that base URL. When ``--result-file`` is set,
the script also writes the created vacancy/candidate identifiers so a follow-up
interview smoke can continue from the same compose data.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from browser_auth_smoke import (
    DevToolsSession,
    NetworkRecord,
    find_chrome_binary,
    start_headless_chrome,
    wait_for_devtools_target,
)

CANDIDATE_STORAGE_KEY = "hrm_candidate_application_context"
APPLY_SUCCESS_STATUSES = {200, 201}
TRACKING_ACTIVE_STATUSES = {"queued", "running", "succeeded"}
PDF_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "apps/backend/tests/fixtures/candidates/sample_cv_en.pdf"
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for browser candidate smoke execution."""
    parser = argparse.ArgumentParser(
        description="Verify browser public apply flow against the compose stack."
    )
    parser.add_argument(
        "--frontend-url",
        required=True,
        help=(
            "Frontend careers or candidate URL without query string, for example "
            "http://localhost:5173/careers"
        ),
    )
    parser.add_argument(
        "--api-origin",
        required=True,
        help="Expected backend origin for public candidate requests, for example http://localhost:8000",
    )
    parser.add_argument(
        "--vacancy-id",
        required=True,
        help="Open vacancy UUID to use for the public apply journey",
    )
    parser.add_argument(
        "--vacancy-title",
        required=True,
        help="Display-only vacancy title used in the deep link",
    )
    parser.add_argument(
        "--artifacts-dir",
        default="/tmp/hrm-browser-candidate-smoke",
        help="Directory for failure artifacts such as screenshots",
    )
    parser.add_argument(
        "--result-file",
        default=None,
        help="Optional JSON file for downstream smoke steps to read the generated candidate id.",
    )
    return parser.parse_args()


def build_candidate_url(frontend_url: str, vacancy_id: str, vacancy_title: str) -> str:
    """Build the canonical public vacancy deep link for the smoke journey.

    Legacy `/candidate` bases remain query-based. Dedicated apply bases keep
    query-based vacancy context. Public careers bases use the shareable vacancy
    detail route.
    """
    base_url = frontend_url.rstrip("/")
    if base_url.endswith("/candidate"):
        query = urlencode(
            {
                "vacancyId": vacancy_id,
                "vacancyTitle": vacancy_title,
            }
        )
        return f"{base_url}?{query}"
    if base_url.endswith("/candidate/apply"):
        query = urlencode(
            {
                "vacancyId": vacancy_id,
                "vacancyTitle": vacancy_title,
            }
        )
        return f"{base_url}?{query}"

    query = urlencode({"vacancyTitle": vacancy_title})
    return f"{base_url}/{vacancy_id}?{query}"


def build_submit_expression(email: str) -> str:
    """Build the JavaScript snippet that fills and submits the candidate form."""
    file_base64 = base64.b64encode(PDF_FIXTURE_PATH.read_bytes()).decode("ascii")
    return f"""
(() => {{
  const setValue = (selector, value) => {{
    const input = document.querySelector(selector);
    if (!(input instanceof HTMLInputElement)) {{
      throw new Error("Missing input for selector: " + selector);
    }}
    const prototype = Object.getPrototypeOf(input);
    const descriptor = Object.getOwnPropertyDescriptor(prototype, "value");
    if (!descriptor || typeof descriptor.set !== "function") {{
      throw new Error("Input value setter is unavailable for selector: " + selector);
    }}
    input.focus();
    descriptor.set.call(input, value);
    input.dispatchEvent(new Event("input", {{ bubbles: true }}));
    input.dispatchEvent(new Event("change", {{ bubbles: true }}));
    input.dispatchEvent(new Event("blur", {{ bubbles: true }}));
  }};

  const attachFile = (selector, filename, mimeType, base64Contents) => {{
    const input = document.querySelector(selector);
    if (!(input instanceof HTMLInputElement)) {{
      throw new Error("Missing file input for selector: " + selector);
    }}
    const dataTransfer = new DataTransfer();
    const binary = atob(base64Contents);
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
    const file = new File([bytes], filename, {{ type: mimeType }});
    dataTransfer.items.add(file);
    input.files = dataTransfer.files;
    input.dispatchEvent(new Event("change", {{ bubbles: true }}));
  }};

  setValue('input[name="first_name"]', "Browser");
  setValue('input[name="last_name"]', "Smoke");
  setValue('input[name="email"]', {json.dumps(email)});
  setValue('input[name="phone"]', "+375291234567");
  setValue('input[name="location"]', "Minsk");
  setValue('input[name="current_title"]', "QA smoke candidate");
  attachFile(
    'input[type="file"]',
    "browser-smoke-cv.pdf",
    "application/pdf",
    {json.dumps(file_base64)},
  );

  const submit = document.querySelector('button[type="submit"]');
  if (!(submit instanceof HTMLButtonElement)) {{
    throw new Error("Missing candidate submit button");
  }}
  const consent = document.querySelector('input[name="consent_confirmed"]');
  if (!(consent instanceof HTMLInputElement)) {{
    throw new Error("Missing consent checkbox input");
  }}
  if (!consent.checked) {{
    consent.click();
  }}
  submit.click();
  return true;
}})()
""".strip()


def read_response_json(
    session: DevToolsSession,
    request_id: str,
    *,
    fallback_url: str | None = None,
) -> dict[str, Any]:
    """Read and decode one JSON response body from DevTools network storage.

    Some Chrome/DevTools versions may evict response bodies before retrieval, especially for fast
    GET polling requests. When `fallback_url` is provided, the helper falls back to a direct HTTP
    GET read (safe only for idempotent endpoints).
    """
    last_error: RuntimeError | None = None
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        try:
            result = session.send(
                "Network.getResponseBody",
                {"requestId": request_id},
                timeout_seconds=10.0,
            )
            body = result.get("body")
            if not isinstance(body, str) or not body:
                raise RuntimeError(f"DevTools returned empty body for request {request_id}")
            if result.get("base64Encoded"):
                body = base64.b64decode(body).decode("utf-8")
            return json.loads(body)
        except RuntimeError as exc:
            last_error = exc
            if "No data found for resource with given identifier" not in str(exc):
                raise
            if fallback_url is not None:
                try:
                    with urllib.request.urlopen(fallback_url, timeout=10.0) as response:  # noqa: S310
                        payload = response.read().decode("utf-8")
                    return json.loads(payload)
                except Exception as fallback_exc:
                    raise RuntimeError(
                        f"failed to load fallback response body for request {request_id}"
                    ) from fallback_exc
            time.sleep(0.25)
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"failed to read response body for request {request_id}")


def write_failure_artifacts(session: DevToolsSession | None, artifacts_dir: Path) -> Path | None:
    """Capture a screenshot artifact on smoke failure when DevTools is available."""
    if session is None:
        return None
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = artifacts_dir / "browser-candidate-smoke-failure.png"
    try:
        result = session.send("Page.captureScreenshot", {"format": "png"}, timeout_seconds=10.0)
        screenshot_data = result.get("data")
        if not isinstance(screenshot_data, str) or not screenshot_data:
            return None
        screenshot_path.write_bytes(base64.b64decode(screenshot_data))
    except Exception:
        return None
    return screenshot_path


def ensure_backend_origin(records: list[NetworkRecord], expected_api_origin: str) -> None:
    """Ensure every captured candidate request targets the expected backend origin."""
    mismatched = [
        record
        for record in records
        if (
            "/api/v1/vacancies/" in record.url
            or "/api/v1/public/cv-parsing-jobs/" in record.url
        )
        and not record.url.startswith(expected_api_origin)
    ]
    if mismatched:
        details = "\n".join(f"{record.method} {record.url}" for record in mismatched)
        raise RuntimeError(f"browser candidate requests targeted the wrong origin:\n{details}")


def relevant_candidate_records(records: list[NetworkRecord]) -> list[NetworkRecord]:
    """Filter network records to the public candidate apply and tracking endpoints."""
    return [
        record
        for record in records
        if "/api/v1/vacancies/" in record.url or "/api/v1/public/cv-parsing-jobs/" in record.url
    ]


def run_browser_candidate_smoke(args: argparse.Namespace) -> None:
    """Execute the browser public candidate apply flow end to end."""
    frontend_url = build_candidate_url(
        args.frontend_url,
        args.vacancy_id,
        args.vacancy_title,
    )
    expected_api_origin = args.api_origin.rstrip("/")
    artifacts_dir = Path(args.artifacts_dir)
    chrome_binary = find_chrome_binary()
    browser_email = f"browser-smoke-{int(time.time())}@local.test"

    print(f"[browser-smoke] using Chrome binary: {chrome_binary}")
    chrome_process, profile_dir, debugging_port = start_headless_chrome(chrome_binary)
    session: DevToolsSession | None = None

    try:
        websocket_url = wait_for_devtools_target(chrome_process, debugging_port)
        session = DevToolsSession(websocket_url, timeout_seconds=5.0)
        session.send("Page.enable")
        session.send("Runtime.enable")
        session.send("Network.enable")
        session.send("Page.navigate", {"url": frontend_url})

        session.wait_for_condition(
            "document.readyState === 'complete'",
            "frontend document ready state",
        )
        session.wait_for_condition(
            "Boolean(document.querySelector('input[name=\"first_name\"]')) && "
            "Boolean(document.querySelector('input[name=\"last_name\"]')) && "
            "Boolean(document.querySelector('input[name=\"email\"]')) && "
            "Boolean(document.querySelector('input[name=\"phone\"]')) && "
            "Boolean(document.querySelector('input[type=\"file\"]')) && "
            "Boolean(document.querySelector('input[name=\"consent_confirmed\"]')) && "
            "Boolean(document.querySelector('button[type=\"submit\"]'))",
            "candidate application form inputs",
        )

        print("[browser-smoke] submitting public candidate application through real browser UI...")
        session.evaluate(build_submit_expression(browser_email))

        apply_record = session.wait_for_network_record(
            lambda record: (
                record.url
                == f"{expected_api_origin}/api/v1/vacancies/{args.vacancy_id}/applications"
                and record.method == "POST"
                and record.status in APPLY_SUCCESS_STATUSES
            ),
            "public vacancy application response",
        )
        apply_payload = read_response_json(session, apply_record.request_id)
        parsing_job_id = str(apply_payload["parsing_job_id"])
        candidate_id = str(apply_payload["candidate_id"])

        session.wait_for_condition(
            f"""
(() => {{
  const raw = window.sessionStorage.getItem({json.dumps(CANDIDATE_STORAGE_KEY)});
  if (!raw) {{
    return false;
  }}
  try {{
    const parsed = JSON.parse(raw);
    return parsed.parsingJobId === {json.dumps(parsing_job_id)}
      && parsed.candidateId === {json.dumps(candidate_id)}
      && parsed.vacancyId === {json.dumps(args.vacancy_id)};
  }} catch (error) {{
    return false;
  }}
}})()
""".strip(),
            "persisted candidate application context in sessionStorage",
        )

        status_record = session.wait_for_network_record(
            lambda record: (
                record.url == f"{expected_api_origin}/api/v1/public/cv-parsing-jobs/{parsing_job_id}"
                and record.method == "GET"
                and record.status == 200
            ),
            "public parsing status response",
        )
        status_payload = read_response_json(
            session,
            status_record.request_id,
            fallback_url=status_record.url,
        )
        current_status = str(status_payload["status"])
        if current_status not in TRACKING_ACTIVE_STATUSES:
            raise RuntimeError(f"unexpected public parsing status: {current_status}")

        ensure_backend_origin(relevant_candidate_records(session.network_records), expected_api_origin)

        if status_payload.get("analysis_ready") is True:
            analysis_record = session.wait_for_network_record(
                lambda record: (
                    record.url
                    == f"{expected_api_origin}/api/v1/public/cv-parsing-jobs/{parsing_job_id}/analysis"
                    and record.method == "GET"
                    and record.status == 200
                ),
                "public analysis response",
            )
            analysis_payload = read_response_json(
                session,
                analysis_record.request_id,
                fallback_url=analysis_record.url,
            )
            if str(analysis_payload["candidate_id"]) != candidate_id:
                raise RuntimeError("public analysis response candidate_id does not match application")
            print("[browser-smoke] public candidate apply flow completed successfully with analysis ready.")
        else:
            print(
                "[browser-smoke] public candidate apply flow completed successfully with "
                f"tracking status={current_status}."
            )

        if args.result_file:
            result_path = Path(args.result_file)
            result_path.parent.mkdir(parents=True, exist_ok=True)
            result_payload = {
                "vacancy_id": args.vacancy_id,
                "vacancy_title": args.vacancy_title,
                "candidate_id": candidate_id,
                "parsing_job_id": parsing_job_id,
            }
            result_path.write_text(
                json.dumps(result_payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    except Exception:
        screenshot_path = write_failure_artifacts(session, artifacts_dir)
        if session is not None:
            candidate_records = relevant_candidate_records(session.network_records)
            if candidate_records:
                print("[browser-smoke] captured candidate network log:")
                for record in candidate_records:
                    print(
                        f"[browser-smoke] {record.method or '-'} {record.url or '-'} "
                        f"status={record.status!s} error={record.error_text or '-'}"
                    )
        if screenshot_path is not None:
            print(f"[browser-smoke] failure screenshot saved to: {screenshot_path}")
        raise
    finally:
        if session is not None:
            session.close()
        chrome_process.terminate()
        try:
            chrome_process.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            chrome_process.kill()
            chrome_process.wait(timeout=5.0)
        try:
            profile_dir.cleanup()
        except OSError:
            pass


def main() -> None:
    """Entrypoint for the browser candidate smoke command."""
    run_browser_candidate_smoke(parse_args())


if __name__ == "__main__":
    main()
