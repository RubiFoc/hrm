#!/usr/bin/env python3
"""Browser-level smoke verification for the local frontend auth flow.

This script launches a headless Chrome instance, opens the frontend login page,
submits credentials through the real browser UI, validates that auth requests
target the configured backend origin, and confirms logout clears the client
session.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen

DEVTOOLS_WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
AUTH_STORAGE_KEYS = (
    "hrm_access_token",
    "hrm_refresh_token",
    "hrm_user_role",
)
DEFAULT_TIMEOUT_SECONDS = 45.0


@dataclass
class NetworkRecord:
    """Captured DevTools network record for one browser request."""

    request_id: str
    url: str
    method: str
    status: int | None = None
    error_text: str | None = None


class DevToolsWebSocket:
    """Minimal WebSocket client for plain-text Chrome DevTools traffic."""

    def __init__(self, websocket_url: str, timeout_seconds: float) -> None:
        """Open a DevTools WebSocket connection.

        Args:
            websocket_url: Chrome DevTools WebSocket URL.
            timeout_seconds: Socket timeout for low-level I/O operations.
        """
        parsed = urlparse(websocket_url)
        if parsed.scheme != "ws":
            raise RuntimeError(f"unsupported DevTools WebSocket scheme: {parsed.scheme}")
        if parsed.hostname is None or parsed.port is None:
            raise RuntimeError(f"invalid DevTools WebSocket URL: {websocket_url}")

        resource = parsed.path or "/"
        if parsed.query:
            resource = f"{resource}?{parsed.query}"

        self._socket = socket.create_connection((parsed.hostname, parsed.port), timeout=timeout_seconds)
        self._socket.settimeout(timeout_seconds)

        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {resource} HTTP/1.1\r\n"
            f"Host: {parsed.hostname}:{parsed.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        self._socket.sendall(request.encode("ascii"))
        response_headers = self._read_http_headers()
        expected_accept = base64.b64encode(
            hashlib.sha1(f"{key}{DEVTOOLS_WEBSOCKET_GUID}".encode("ascii")).digest()
        ).decode("ascii")
        if " 101 " not in response_headers.splitlines()[0]:
            raise RuntimeError(f"DevTools handshake failed: {response_headers.splitlines()[0]}")
        if f"Sec-WebSocket-Accept: {expected_accept}" not in response_headers:
            raise RuntimeError("DevTools handshake returned unexpected Sec-WebSocket-Accept")

    def close(self) -> None:
        """Close the underlying WebSocket socket."""
        try:
            self._socket.close()
        except OSError:
            pass

    def send_json(self, payload: dict[str, Any]) -> None:
        """Send one JSON text message to DevTools."""
        raw = json.dumps(payload).encode("utf-8")
        self._send_frame(opcode=0x1, payload=raw)

    def recv_json(self, timeout_seconds: float) -> dict[str, Any]:
        """Receive one JSON text message from DevTools.

        Args:
            timeout_seconds: Maximum wait time for the next complete message.

        Returns:
            dict[str, Any]: Parsed JSON payload from DevTools.
        """
        deadline = time.monotonic() + timeout_seconds
        while True:
            remaining = max(deadline - time.monotonic(), 0.05)
            self._socket.settimeout(remaining)
            opcode, payload = self._recv_frame()
            if opcode == 0x1:
                return json.loads(payload.decode("utf-8"))
            if opcode == 0x8:
                raise RuntimeError("Chrome closed the DevTools connection")
            if opcode == 0x9:
                self._send_frame(opcode=0xA, payload=payload)

    def _read_http_headers(self) -> str:
        """Read the HTTP handshake header block from the socket."""
        buffer = bytearray()
        while b"\r\n\r\n" not in buffer:
            chunk = self._socket.recv(4096)
            if not chunk:
                raise RuntimeError("DevTools socket closed during HTTP handshake")
            buffer.extend(chunk)
        header_block, _, _ = buffer.partition(b"\r\n\r\n")
        return header_block.decode("iso-8859-1")

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        """Send one WebSocket frame with a masked client payload."""
        header = bytearray([0x80 | opcode])
        payload_length = len(payload)
        if payload_length < 126:
            header.append(0x80 | payload_length)
        elif payload_length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", payload_length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", payload_length))

        mask = os.urandom(4)
        masked_payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self._socket.sendall(header + mask + masked_payload)

    def _recv_frame(self) -> tuple[int, bytes]:
        """Receive one WebSocket frame from the socket."""
        first_two_bytes = self._read_exact(2)
        opcode = first_two_bytes[0] & 0x0F
        masked = bool(first_two_bytes[1] & 0x80)
        payload_length = first_two_bytes[1] & 0x7F

        if payload_length == 126:
            payload_length = struct.unpack("!H", self._read_exact(2))[0]
        elif payload_length == 127:
            payload_length = struct.unpack("!Q", self._read_exact(8))[0]

        mask = self._read_exact(4) if masked else b""
        payload = self._read_exact(payload_length) if payload_length else b""
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        return opcode, payload

    def _read_exact(self, size: int) -> bytes:
        """Read exactly ``size`` bytes from the socket."""
        buffer = bytearray()
        while len(buffer) < size:
            chunk = self._socket.recv(size - len(buffer))
            if not chunk:
                raise RuntimeError("DevTools socket closed while reading a frame")
            buffer.extend(chunk)
        return bytes(buffer)


class DevToolsSession:
    """Small synchronous Chrome DevTools Protocol session helper."""

    def __init__(self, websocket_url: str, timeout_seconds: float) -> None:
        """Create a page-level CDP session.

        Args:
            websocket_url: Target page DevTools WebSocket URL.
            timeout_seconds: Per-message wait timeout for CDP traffic.
        """
        self._socket = DevToolsWebSocket(websocket_url, timeout_seconds=timeout_seconds)
        self._next_message_id = 0
        self._network_records: dict[str, NetworkRecord] = {}

    @property
    def network_records(self) -> list[NetworkRecord]:
        """Return the captured network records in arrival order."""
        return list(self._network_records.values())

    def close(self) -> None:
        """Close the underlying DevTools connection."""
        self._socket.close()

    def send(self, method: str, params: dict[str, Any] | None = None, timeout_seconds: float = 10.0) -> dict[str, Any]:
        """Send one CDP command and return its result payload.

        Args:
            method: DevTools protocol method name.
            params: Optional protocol parameters.
            timeout_seconds: Maximum wait time for the response.

        Returns:
            dict[str, Any]: Command result payload.
        """
        self._next_message_id += 1
        message_id = self._next_message_id
        self._socket.send_json(
            {
                "id": message_id,
                "method": method,
                "params": params or {},
            }
        )

        deadline = time.monotonic() + timeout_seconds
        while True:
            message = self._socket.recv_json(max(deadline - time.monotonic(), 0.05))
            if "id" in message:
                if message["id"] != message_id:
                    raise RuntimeError(
                        f"unexpected DevTools response id {message['id']} while waiting for {message_id}"
                    )
                if "error" in message:
                    raise RuntimeError(f"DevTools command failed: {message['error']}")
                return message.get("result", {})
            self._record_event(message)

    def evaluate(self, expression: str, timeout_seconds: float = 10.0) -> Any:
        """Evaluate one JavaScript expression inside the page context.

        Args:
            expression: JavaScript expression to evaluate.
            timeout_seconds: Maximum wait time for the result.

        Returns:
            Any: JSON-serializable return value from the expression.
        """
        result = self.send(
            "Runtime.evaluate",
            {
                "expression": expression,
                "awaitPromise": True,
                "returnByValue": True,
            },
            timeout_seconds=timeout_seconds,
        )
        if result.get("exceptionDetails"):
            description = result["exceptionDetails"].get("text", "JavaScript evaluation failed")
            raise RuntimeError(description)
        remote_result = result.get("result", {})
        return remote_result.get("value")

    def wait_for_condition(
        self,
        expression: str,
        description: str,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        poll_interval_seconds: float = 0.25,
    ) -> Any:
        """Poll a JavaScript condition until it returns a truthy value.

        Args:
            expression: JavaScript expression to evaluate repeatedly.
            description: Human-readable wait target used in failure output.
            timeout_seconds: Maximum wait time.
            poll_interval_seconds: Delay between polls.

        Returns:
            Any: Truthy value returned by the expression.
        """
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            value = self.evaluate(expression, timeout_seconds=min(5.0, timeout_seconds))
            if value:
                return value
            time.sleep(poll_interval_seconds)
        raise RuntimeError(f"timed out waiting for: {description}")

    def wait_for_network_record(
        self,
        predicate,
        description: str,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> NetworkRecord:
        """Wait until a captured network record matches the supplied predicate.

        Args:
            predicate: Callable that receives one ``NetworkRecord``.
            description: Human-readable wait target used in failure output.
            timeout_seconds: Maximum wait time.

        Returns:
            NetworkRecord: First matching network record.
        """
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            for record in self.network_records:
                if predicate(record):
                    return record
            message = self._socket.recv_json(max(deadline - time.monotonic(), 0.05))
            if "id" in message:
                raise RuntimeError(f"unexpected DevTools response while waiting for {description}: {message}")
            self._record_event(message)
        raise RuntimeError(f"timed out waiting for network event: {description}")

    def _record_event(self, message: dict[str, Any]) -> None:
        """Record network-relevant CDP events for later assertions."""
        method = message.get("method")
        params = message.get("params", {})
        request_id = params.get("requestId")

        if method == "Network.requestWillBeSent" and request_id:
            request = params.get("request", {})
            self._network_records[request_id] = NetworkRecord(
                request_id=request_id,
                url=str(request.get("url", "")),
                method=str(request.get("method", "")),
            )
            return

        if method == "Network.responseReceived" and request_id:
            response = params.get("response", {})
            record = self._network_records.setdefault(
                request_id,
                NetworkRecord(
                    request_id=request_id,
                    url=str(response.get("url", "")),
                    method="",
                ),
            )
            record.url = str(response.get("url", record.url))
            status = response.get("status")
            record.status = int(status) if status is not None else None
            return

        if method == "Network.loadingFailed" and request_id:
            record = self._network_records.setdefault(
                request_id,
                NetworkRecord(request_id=request_id, url="", method=""),
            )
            record.error_text = str(params.get("errorText", "unknown network failure"))


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for browser auth smoke execution."""
    parser = argparse.ArgumentParser(description="Verify browser login/me/logout flow against the compose stack.")
    parser.add_argument("--frontend-url", required=True, help="Frontend login URL, for example http://localhost:5173/login")
    parser.add_argument("--api-origin", required=True, help="Expected backend origin for auth requests, for example http://localhost:8000")
    parser.add_argument("--login", required=True, help="Smoke admin login to submit in the browser form")
    parser.add_argument("--password", required=True, help="Smoke admin password to submit in the browser form")
    parser.add_argument(
        "--artifacts-dir",
        default="/tmp/hrm-browser-auth-smoke",
        help="Directory for failure artifacts such as screenshots",
    )
    return parser.parse_args()


def find_chrome_binary() -> str:
    """Resolve a Chrome/Chromium executable path from env or PATH."""
    configured_path = os.environ.get("CHROME_BIN")
    if configured_path:
        return configured_path

    for candidate in ("google-chrome", "google-chrome-stable", "chromium-browser", "chromium"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise RuntimeError("Chrome binary not found. Install Google Chrome or set CHROME_BIN explicitly.")


def reserve_tcp_port() -> int:
    """Reserve and release one ephemeral localhost TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def start_headless_chrome(chrome_binary: str) -> tuple[subprocess.Popen[bytes], tempfile.TemporaryDirectory[str], int]:
    """Launch headless Chrome with remote debugging enabled.

    Args:
        chrome_binary: Chrome executable path.

    Returns:
        tuple[subprocess.Popen[bytes], tempfile.TemporaryDirectory[str], int]:
            Running Chrome process, temporary profile directory wrapper, and debugging port.
    """
    debugging_port = reserve_tcp_port()
    profile_dir = tempfile.TemporaryDirectory(
        prefix="hrm-browser-auth-smoke-",
        ignore_cleanup_errors=True,
    )
    process = subprocess.Popen(
        [
            chrome_binary,
            "--headless=new",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-default-browser-check",
            "--no-sandbox",
            f"--remote-debugging-port={debugging_port}",
            f"--user-data-dir={profile_dir.name}",
            "--window-size=1400,900",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return process, profile_dir, debugging_port


def wait_for_devtools_target(process: subprocess.Popen[bytes], debugging_port: int) -> str:
    """Wait until Chrome exposes a page-level DevTools WebSocket target."""
    deadline = time.monotonic() + DEFAULT_TIMEOUT_SECONDS
    list_url = f"http://127.0.0.1:{debugging_port}/json/list"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Chrome exited early with code {process.returncode}")
        try:
            with urlopen(list_url, timeout=2.0) as response:
                targets = json.load(response)
        except OSError:
            time.sleep(0.2)
            continue

        for target in targets:
            if target.get("type") == "page" and target.get("webSocketDebuggerUrl"):
                return str(target["webSocketDebuggerUrl"])
        time.sleep(0.2)
    raise RuntimeError("timed out waiting for Chrome DevTools page target")


def build_set_login_form_expression(login: str, password: str) -> str:
    """Build the JavaScript snippet that fills the login form and submits it."""
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
  setValue('input[name="identifier"]', {json.dumps(login)});
  setValue('input[name="password"]', {json.dumps(password)});
  const submit = document.querySelector('button[type="submit"]');
  if (!(submit instanceof HTMLButtonElement)) {{
    throw new Error("Missing login submit button");
  }}
  submit.click();
  return true;
}})()
""".strip()


def build_logout_expression() -> str:
    """Build the JavaScript snippet that clicks the logout button."""
    return """
(() => {
  const logoutButton = Array.from(document.querySelectorAll("button")).find((node) => {
    const label = (node.textContent || "").trim();
    return /^(logout|logging out\\.\\.\\.|выйти|выход\\.\\.\\.)$/i.test(label);
  });
  if (!(logoutButton instanceof HTMLButtonElement)) {
    throw new Error("Missing logout button in app shell");
  }
  logoutButton.click();
  return true;
})()
""".strip()


def auth_records_for_path(records: list[NetworkRecord], path_suffix: str) -> list[NetworkRecord]:
    """Filter network records to one auth endpoint path suffix."""
    return [record for record in records if record.url.endswith(path_suffix)]


def ensure_backend_origin(records: list[NetworkRecord], expected_api_origin: str) -> None:
    """Ensure every captured auth request targets the expected backend origin."""
    mismatched = [
        record
        for record in records
        if "/api/v1/auth/" in record.url and not record.url.startswith(expected_api_origin)
    ]
    if mismatched:
        details = "\n".join(f"{record.method} {record.url}" for record in mismatched)
        raise RuntimeError(f"browser auth requests targeted the wrong origin:\n{details}")


def wait_for_auth_flow(session: DevToolsSession, expected_api_origin: str) -> None:
    """Wait for the required auth requests to complete successfully."""
    login_path = f"{expected_api_origin}/api/v1/auth/login"
    me_path = f"{expected_api_origin}/api/v1/auth/me"
    logout_path = f"{expected_api_origin}/api/v1/auth/logout"

    session.wait_for_network_record(
        lambda record: record.url == login_path and record.method == "OPTIONS" and record.status == 200,
        "login CORS preflight",
    )
    session.wait_for_network_record(
        lambda record: record.url == login_path and record.method == "POST" and record.status == 200,
        "login POST response",
    )
    session.wait_for_network_record(
        lambda record: record.url == me_path and record.method == "GET" and record.status == 200,
        "identity bootstrap GET /me",
    )
    session.wait_for_network_record(
        lambda record: record.url == logout_path and record.method == "OPTIONS" and record.status == 200,
        "logout CORS preflight",
    )
    session.wait_for_network_record(
        lambda record: record.url == logout_path and record.method == "POST" and record.status == 204,
        "logout POST response",
    )


def write_failure_artifacts(session: DevToolsSession | None, artifacts_dir: Path) -> Path | None:
    """Capture a screenshot artifact on smoke failure when DevTools is available."""
    if session is None:
        return None
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    screenshot_path = artifacts_dir / "browser-auth-smoke-failure.png"
    try:
        result = session.send("Page.captureScreenshot", {"format": "png"}, timeout_seconds=10.0)
        screenshot_data = result.get("data")
        if not isinstance(screenshot_data, str) or not screenshot_data:
            return None
        screenshot_path.write_bytes(base64.b64decode(screenshot_data))
    except Exception:
        return None
    return screenshot_path


def run_browser_auth_smoke(args: argparse.Namespace) -> None:
    """Execute the browser auth smoke flow end to end."""
    frontend_url = args.frontend_url.rstrip("/")
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
            "frontend document ready state",
        )
        session.wait_for_condition(
            "Boolean(document.querySelector('input[name=\"identifier\"]')) && "
            "Boolean(document.querySelector('input[name=\"password\"]')) && "
            "Boolean(document.querySelector('button[type=\"submit\"]'))",
            "login form inputs",
        )

        print("[browser-smoke] submitting login form through real browser UI...")
        session.evaluate(build_set_login_form_expression(args.login, args.password))

        session.wait_for_condition(
            "window.location.pathname === '/admin'",
            "redirect to /admin after login",
        )
        session.wait_for_condition(
            "window.localStorage.getItem('hrm_access_token') && "
            "window.localStorage.getItem('hrm_refresh_token') && "
            "window.localStorage.getItem('hrm_user_role') === 'admin'",
            "persisted auth session in localStorage",
        )
        session.wait_for_condition(
            "Array.from(document.querySelectorAll('button')).some((node) => "
            "/^(logout|logging out\\.\\.\\.|выйти|выход\\.\\.\\.)$/i.test((node.textContent || '').trim()))",
            "logout button in app shell",
        )

        print("[browser-smoke] submitting logout through app shell...")
        session.evaluate(build_logout_expression())

        session.wait_for_condition(
            "window.location.pathname === '/login'",
            "redirect back to /login after logout",
        )
        session.wait_for_condition(
            "['hrm_access_token', 'hrm_refresh_token', 'hrm_user_role'].every((key) => !window.localStorage.getItem(key))",
            "cleared auth session in localStorage after logout",
        )

        auth_records = [record for record in session.network_records if "/api/v1/auth/" in record.url]
        ensure_backend_origin(auth_records, expected_api_origin)
        wait_for_auth_flow(session, expected_api_origin)
        print("[browser-smoke] browser auth flow completed successfully.")
    except Exception:
        screenshot_path = write_failure_artifacts(session, artifacts_dir)
        if session is not None:
            auth_records = [record for record in session.network_records if "/api/v1/auth/" in record.url]
            if auth_records:
                print("[browser-smoke] captured auth network log:")
                for record in auth_records:
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
    """Entrypoint for the browser auth smoke command."""
    run_browser_auth_smoke(parse_args())


if __name__ == "__main__":
    main()
