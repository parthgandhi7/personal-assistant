from __future__ import annotations

import platform
import shutil
import subprocess
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from agent.core.config import get_settings


def _run_command(command: list[str]) -> None:
    subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _open_with_default_app(path: Path) -> None:
    os_name = platform.system().lower()

    if os_name == "windows":
        subprocess.Popen(["cmd", "/c", "start", "", str(path)], shell=True)
        return

    if os_name == "darwin":
        _run_command(["open", str(path)])
        return

    _run_command(["xdg-open", str(path)])


def _launch_app(mac_app_name: str, linux_binary: str, windows_binary: str) -> bool:
    os_name = platform.system().lower()

    if os_name == "darwin":
        subprocess.run(["open", "-a", mac_app_name], check=True)
        return True

    if os_name == "windows":
        subprocess.Popen([windows_binary], shell=True)
        return True

    try:
        subprocess.Popen([linux_binary])
        return True
    except FileNotFoundError:
        return False


def _validate_volume_amount(payload: dict[str, Any]) -> int:
    raw_amount = payload.get("amount", 10)
    if not isinstance(raw_amount, int):
        raise RuntimeError("Volume amount must be an integer")

    if raw_amount <= 0 or raw_amount > 100:
        raise RuntimeError("Volume amount must be between 1 and 100")

    return raw_amount


def _change_linux_volume(direction: str, amount: int) -> None:
    if shutil.which("pactl"):
        subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{direction}{amount}%"], check=True)
        return

    if shutil.which("amixer"):
        subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{amount}%{direction}"], check=True)
        return

    raise RuntimeError("No supported Linux volume tool found. Install 'pactl' or 'amixer'.")


def _resolve_search_directory(payload: dict[str, Any]) -> Path:
    settings = get_settings()
    raw_directory = payload.get("directory")
    target_directory = Path(raw_directory).expanduser() if raw_directory else settings.default_directory
    target_directory = target_directory.resolve()

    if not target_directory.exists() or not target_directory.is_dir():
        raise RuntimeError(f"Directory does not exist: {target_directory}")

    return target_directory


def open_chrome(_: dict[str, Any]) -> str:
    opened = _launch_app(
        mac_app_name="Google Chrome",
        linux_binary="google-chrome",
        windows_binary="chrome",
    )
    if not opened:
        raise RuntimeError("Chrome binary not found on this machine")
    return "Chrome opened"


def open_vscode(_: dict[str, Any]) -> str:
    if _launch_app(mac_app_name="Visual Studio Code", linux_binary="code", windows_binary="code"):
        return "VS Code opened"

    if _launch_app(mac_app_name="Cursor", linux_binary="cursor", windows_binary="cursor"):
        return "Cursor opened"

    raise RuntimeError("Neither VS Code nor Cursor is available")


def open_application(payload: dict[str, Any]) -> str:
    app = payload.get("application")
    if not isinstance(app, str) or not app.strip():
        raise RuntimeError("Missing required field: application")

    candidate = app.strip().lower()
    if candidate in {"chrome", "google chrome"}:
        return open_chrome({})

    if candidate in {"vscode", "vs code", "visual studio code", "cursor"}:
        return open_vscode({})

    raise RuntimeError(f"Unsupported application: {app}")


def open_browser(payload: dict[str, Any]) -> str:
    browser = payload.get("browser", "chrome")
    if not isinstance(browser, str) or not browser.strip():
        browser = "chrome"
    return open_application({"application": browser})


def search_web(payload: dict[str, Any]) -> str:
    query = payload.get("query")
    if not isinstance(query, str) or not query.strip():
        raise RuntimeError("Missing required field: query")

    browser = payload.get("browser", "")
    q = quote_plus(query.strip())
    url = f"https://www.google.com/search?q={q}"

    if isinstance(browser, str) and browser.strip().lower() in {"chrome", "google chrome"}:
        opened = _launch_app(
            mac_app_name="Google Chrome",
            linux_binary="google-chrome",
            windows_binary="chrome",
        )
        webbrowser.open(url)
    else:
        webbrowser.open(url)

    return f"Searching web for: {query.strip()}"


def search_file(payload: dict[str, Any]) -> dict[str, Any]:
    query = payload.get("query")
    if not isinstance(query, str) or not query.strip():
        raise RuntimeError("Missing required field: query")

    target_directory = _resolve_search_directory(payload)
    needle = query.strip().lower()

    matches: list[str] = []
    for path in target_directory.rglob("*"):
        if not path.is_file():
            continue
        if needle in path.name.lower():
            matches.append(str(path))
        if len(matches) >= 50:
            break

    return {
        "directory": str(target_directory),
        "query": query.strip(),
        "matches": matches,
        "count": len(matches),
    }


def increase_volume(payload: dict[str, Any]) -> str:
    amount = _validate_volume_amount(payload)
    os_name = platform.system().lower()

    if os_name == "darwin":
        subprocess.run(
            [
                "osascript",
                "-e",
                f"set volume output volume (output volume of (get volume settings) + {amount})",
            ],
            check=True,
        )
        return "Volume increased"

    if os_name == "windows":
        raise RuntimeError("increase_volume is not implemented for Windows in this MVP")

    _change_linux_volume(direction="+", amount=amount)
    return "Volume increased"


def decrease_volume(payload: dict[str, Any]) -> str:
    amount = _validate_volume_amount(payload)
    os_name = platform.system().lower()

    if os_name == "darwin":
        subprocess.run(
            [
                "osascript",
                "-e",
                f"set volume output volume (output volume of (get volume settings) - {amount})",
            ],
            check=True,
        )
        return "Volume decreased"

    if os_name == "windows":
        raise RuntimeError("decrease_volume is not implemented for Windows in this MVP")

    _change_linux_volume(direction="-", amount=amount)
    return "Volume decreased"


def list_files(payload: dict[str, Any]) -> dict[str, Any]:
    target_directory = _resolve_search_directory(payload)
    items = sorted(p.name for p in target_directory.iterdir())
    return {
        "directory": str(target_directory),
        "items": items,
        "count": len(items),
    }


def open_file(payload: dict[str, Any]) -> str:
    raw_path = payload.get("path")
    if not raw_path:
        raise RuntimeError("Missing required field: path")

    target_path = Path(raw_path).expanduser().resolve()

    if not target_path.exists():
        raise RuntimeError(f"File does not exist: {target_path}")

    _open_with_default_app(target_path)
    return f"Opened {target_path.name}"
