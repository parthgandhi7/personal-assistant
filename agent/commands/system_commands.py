from __future__ import annotations

import platform
import subprocess
from pathlib import Path
from typing import Any

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


def increase_volume(_: dict[str, Any]) -> str:
    os_name = platform.system().lower()

    if os_name == "darwin":
        subprocess.run(
            [
                "osascript",
                "-e",
                "set volume output volume (output volume of (get volume settings) + 10)",
            ],
            check=True,
        )
        return "Volume increased"

    if os_name == "windows":
        raise RuntimeError("increase_volume is not implemented for Windows in this MVP")

    # Linux fallback using pactl; this may vary by distro.
    subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"], check=True)
    return "Volume increased"


def list_files(payload: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    raw_directory = payload.get("directory")
    target_directory = Path(raw_directory).expanduser() if raw_directory else settings.default_directory
    target_directory = target_directory.resolve()

    if not target_directory.exists() or not target_directory.is_dir():
        raise RuntimeError(f"Directory does not exist: {target_directory}")

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
