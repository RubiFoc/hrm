#!/usr/bin/env python3
"""Browser-level smoke verification for the public candidate interview flow.

The script opens a real public interview registration page in headless Chrome,
verifies that the browser loads the invite payload from the configured backend
origin, and confirms attendance through the public token flow. It is intended
to run after a fresh interview sync has produced a public invitation token.
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

from browser_auth_smoke import (  # type: ignore[attr-defined]
    DevToolsSession,
    NetworkRecord,
    find_chrome_binary,
    start_headless_chrome,
    wait_for_devtools_target,
)

SUCCESS_STATUSES = {200, 201}
PUBLIC_INTERVIEW_PATH_FRAGMENT = "/api/v1/public/interview-registrations/"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for browser candidate interview smoke execution."""
    parser = argparse.ArgumentParser(
        description="Verify the public candidate interview flow against the compose stack."
    )
    parser.add_argument(
        "--frontend-url",
        required=True,
        help=(
            "Frontend interview URL without token, for example "
            "http://localhost:5173/candidate/interview"
        ),
    )
    parser.add_argument(
        "--api-origin",
        required=True,
        help="Expected backend origin for public interview requests, for example http://localhost:8000",
    )
    parser.add_argument(
        "--interview-token",
        required=True,
        help="Opaque public interview token issued by the interview sync worker",
    )
    parser.add_argument(
        "--artifacts-dir",
        default="/tmp/hrm-browser-candidate-interview-smoke",
        help="Directory for failure artifacts such as screenshots",
    )
    return parser.parse_args()


def build_candidate_interview_url(frontend_url: str, interview_token: str) -> str:
    """Build the canonical public interview deep link for the smoke journey."""
    base_url = frontend_url.rstrip("/")
    if base_url.endswith("/candidate/interview"):
        return f"{base_url}/{interview_token}"
    if base_url.endswith("/candidate"):
        query = urlencode({"interviewToken": interview_token})
        return f"{base_url}?{query}"
    return f"{base_url}/{interview_token}"


def build_confirm_expression() -> str:
    """Build the JavaScript snippet that clicks the interview confirm button."""
    return """
(() => {
  const confirmButton = Array.from(document.querySelectorAll("button")).find((node) => {
    const label = (node.textContent || "").trim().toLowerCase();
    return label === "confirm" || label.startsWith("подтверд");
  });
  if (!(confirmButton instanceof HTMLButtonElement)) {
    throw new Error("Missing interview confirm button");
  }
  confirmButton.click();
  return true;
})()
""".strip()


def read_response_json(
    session: DevToolsSession,
    request_id: str,
    *,
    fallback_url: str | None = None,
) -> dict[str, Any]:
    """Read and decode one JSON response body from DevTools network storage."""
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
    screenshot_path = artifacts_dir / "browser-candidate-interview-smoke-failure.png"
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
    """Ensure every captured interview request targets the expected backend origin."""
    mismatched = [
        record
        for record in records
        if PUBLIC_INTERVIEW_PATH_FRAGMENT in record.url
        and not record.url.startswith(expected_api_origin)
    ]
    if mismatched:
        details = "\n".join(f"{record.method} {record.url}" for record in mismatched)
        raise RuntimeError(f"browser interview requests targeted the wrong origin:\n{details}")


def relevant_interview_records(records: list[NetworkRecord]) -> list[NetworkRecord]:
    """Filter network records to the public interview registration endpoints."""
    return [record for record in records if PUBLIC_INTERVIEW_PATH_FRAGMENT in record.url]


def run_browser_candidate_interview_smoke(args: argparse.Namespace) -> None:
    """Execute the browser public interview flow end to end."""
    frontend_url = build_candidate_interview_url(args.frontend_url, args.interview_token)
    expected_api_origin = args.api_origin.rstrip("/")
    artifacts_dir = Path(args.artifacts_dir)
    chrome_binary = find_chrome_binary()

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
            "candidate interview document ready state",
        )
        session.wait_for_condition(
            "Boolean(document.body) && document.body.innerText.length > 0",
            "candidate interview content render",
        )

        registration_url = (
            f"{expected_api_origin}/api/v1/public/interview-registrations/{args.interview_token}"
        )
        registration_record = session.wait_for_network_record(
            lambda record: (
                record.url == registration_url
                and record.method == "GET"
                and record.status in SUCCESS_STATUSES
            ),
            "public interview registration response",
        )
        registration_payload = read_response_json(
            session,
            registration_record.request_id,
            fallback_url=registration_record.url,
        )
        if registration_payload.get("status") != "awaiting_candidate_confirmation":
            raise RuntimeError(
                f"unexpected interview status before confirm: {registration_payload.get('status')}"
            )
        if registration_payload.get("candidate_response_status") != "pending":
            raise RuntimeError(
                "unexpected candidate response status before confirm: "
                f"{registration_payload.get('candidate_response_status')}"
            )

        session.wait_for_condition(
            """
(() => {
  const buttons = Array.from(document.querySelectorAll("button"));
  return buttons.some((node) => {
    const label = (node.textContent || "").trim().toLowerCase();
    return label === "confirm" || label.startsWith("подтверд");
  });
})()
""".strip(),
            "candidate interview confirm button",
        )

        print("[browser-smoke] confirming the public interview through the real browser UI...")
        session.evaluate(build_confirm_expression())

        confirm_url = f"{registration_url}/confirm"
        confirm_record = session.wait_for_network_record(
            lambda record: (
                record.url == confirm_url
                and record.method == "POST"
                and record.status in SUCCESS_STATUSES
            ),
            "public interview confirm response",
        )
        confirm_payload = read_response_json(session, confirm_record.request_id)
        if confirm_payload.get("status") != "confirmed":
            raise RuntimeError(f"unexpected interview status after confirm: {confirm_payload}")
        if confirm_payload.get("candidate_response_status") != "confirmed":
            raise RuntimeError(
                "unexpected candidate response status after confirm: "
                f"{confirm_payload.get('candidate_response_status')}"
            )

        session.wait_for_condition(
            """
(() => {
  const bodyText = document.body ? document.body.innerText : "";
  return bodyText.includes("Interview attendance confirmed.")
    || bodyText.includes("Участие в интервью подтверждено.");
})()
""".strip(),
            "candidate interview confirm success alert",
        )

        ensure_backend_origin(relevant_interview_records(session.network_records), expected_api_origin)
        print("[browser-smoke] public candidate interview flow completed successfully.")
    except Exception:
        screenshot_path = write_failure_artifacts(session, artifacts_dir)
        if session is not None:
            interview_records = relevant_interview_records(session.network_records)
            if interview_records:
                print("[browser-smoke] captured interview network log:")
                for record in interview_records:
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
    """Entrypoint for the browser candidate interview smoke command."""
    run_browser_candidate_interview_smoke(parse_args())


if __name__ == "__main__":
    main()
