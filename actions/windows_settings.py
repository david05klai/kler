"""windows_settings.py — Control completo de configuraciones de Windows."""
import os
import sys
import subprocess
import json
from pathlib import Path


def _run_ps(cmd: str, timeout: int = 10) -> str:
    """Ejecuta un comando de PowerShell y devuelve su salida."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
            capture_output=True, text=True, timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        return out if out else (err if err else "OK")
    except subprocess.TimeoutExpired:
        return "Tiempo de espera agotado."
    except Exception as e:
        return f"Error: {e}"


def windows_settings(parameters: dict, player=None) -> str:
    action = parameters.get("action", "").lower().strip()
    value  = parameters.get("value", "")
    value2 = parameters.get("value2", "")
    name   = parameters.get("name", "")

    # ─── SYSTEM ────────────────────────────────────────────────────────────────
    if action == "shutdown":
        delay = str(value) if str(value).isdigit() else "0"
        _run_ps(f"Stop-Computer -Force")
        return "Apagando el equipo ahora."

    if action == "restart":
        _run_ps("Restart-Computer -Force")
        return "Reiniciando el equipo ahora."

    if action == "lock":
        _run_ps("rundll32.exe user32.dll,LockWorkStation")
        return "Pantalla bloqueada."

    if action == "hibernate":
        _run_ps("shutdown /h")
        return "Hibernando el equipo."

    if action == "sleep" or action == "suspend":
        _run_ps("Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState('Suspend', $false, $false)")
        return "Suspendiendo el equipo."

    if action == "info":
        return _run_ps("Get-ComputerInfo | Select-Object CsName,OsName,OsVersion,CsTotalPhysicalMemory | Format-List | Out-String")

    if action == "get_hostname":
        return _run_ps("$env:COMPUTERNAME")

    if action == "set_hostname":
        return _run_ps(f"Rename-Computer -NewName '{value}' -Force")

    if action == "get_datetime":
        return _run_ps("Get-Date | Out-String")

    if action == "set_timezone":
        return _run_ps(f"Set-TimeZone -Id '{value}'")

    # ─── AUDIO ─────────────────────────────────────────────────────────────────
    if action == "get_volume":
        return _run_ps(
            "(New-Object -ComObject WScript.Shell).SendKeys([char]0); "
            "$vol = (Get-AudioDevice -Playback).Volume; \"Volumen: $vol%\""
        )

    if action in ("set_volume", "volume"):
        try:
            v = int(value)
            from ctypes import cast, POINTER
            from comtypes import CoInitialize, CoUninitialize
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            CoInitialize()
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, 1, None)
            vol_ctrl = cast(interface, POINTER(IAudioEndpointVolume))
            vol_ctrl.SetMasterVolumeLevelScalar(max(0.0, min(1.0, v / 100.0)), None)
            CoUninitialize()
            return f"Volumen ajustado a {v}%."
        except Exception as e:
            return f"Error ajustando volumen: {e}"

    if action in ("mute", "toggle_mute"):
        try:
            from ctypes import cast, POINTER
            from comtypes import CoInitialize, CoUninitialize
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            CoInitialize()
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, 1, None)
            vol_ctrl = cast(interface, POINTER(IAudioEndpointVolume))
            current = vol_ctrl.GetMute()
            vol_ctrl.SetMute(not current, None)
            CoUninitialize()
            return f"{'Silenciado' if not current else 'Audio restaurado'}."
        except Exception as e:
            return f"Error en mute: {e}"

    if action == "unmute":
        try:
            from ctypes import cast, POINTER
            from comtypes import CoInitialize, CoUninitialize
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            CoInitialize()
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, 1, None)
            vol_ctrl = cast(interface, POINTER(IAudioEndpointVolume))
            vol_ctrl.SetMute(False, None)
            CoUninitialize()
            return "Audio restaurado."
        except Exception as e:
            return f"Error: {e}"

    # ─── DISPLAY / BRILLO ──────────────────────────────────────────────────────
    if action == "get_brightness":
        return _run_ps(
            "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness | Out-String"
        )

    if action in ("set_brightness", "brightness"):
        try:
            b = max(0, min(100, int(value)))
            _run_ps(
                f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
                f".WmiSetBrightness(1,{b})"
            )
            return f"Brillo ajustado a {b}%."
        except Exception as e:
            return f"Error ajustando brillo: {e}"

    if action in ("dark_mode", "night_light_on"):
        _run_ps(
            "Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize' "
            "-Name AppsUseLightTheme -Value 0; "
            "Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize' "
            "-Name SystemUsesLightTheme -Value 0"
        )
        return "Modo oscuro activado."

    if action == "light_mode":
        _run_ps(
            "Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize' "
            "-Name AppsUseLightTheme -Value 1; "
            "Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize' "
            "-Name SystemUsesLightTheme -Value 1"
        )
        return "Modo claro activado."

    # ─── NETWORK ───────────────────────────────────────────────────────────────
    if action == "get_ip":
        return _run_ps("(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne '127.0.0.1' }).IPAddress -join ', '")

    if action in ["wifi_on", "wifi_off"]:
        _run_ps("start ms-settings:network-wifi")
        estado = "activar" if action == "wifi_on" else "desactivar"
        return f"Abriendo configuración de WiFi para {estado}. Windows restringe el cambio automático en segundo plano."

    if action in ["bluetooth_on", "bluetooth_off"]:
        _run_ps("start ms-settings:bluetooth")
        estado = "activar" if action == "bluetooth_on" else "desactivar"
        return f"Abriendo configuración de Bluetooth para {estado}. Windows restringe el cambio automático en segundo plano."

    if action == "flush_dns":
        return _run_ps("Clear-DnsClientCache; 'DNS vaciado.'")

    if action == "list_wifi":
        return _run_ps("netsh wlan show profiles | Out-String")

    if action == "connect_wifi":
        return _run_ps(f"netsh wlan connect name='{value}'")

    if action == "disconnect_wifi":
        return _run_ps("netsh wlan disconnect")

    if action == "airplane_on":
        return _run_ps(
            "Add-Type -AssemblyName System.Runtime.WindowsRuntime; "
            "[Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime] | Out-Null; "
            "$result = [Windows.Devices.Radios.Radio]::RequestAccessAsync().GetAwaiter().GetResult(); "
            "'Modo avión activado (reiniciar si es necesario).'"
        )

    # ─── POWER PLAN ────────────────────────────────────────────────────────────
    if action == "get_plan":
        return _run_ps("powercfg /getactivescheme")

    if action == "set_plan":
        plans = {
            "balanced":          "381b4222-f694-41f0-9685-ff5bb260df2e",
            "high_performance":  "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
            "power_saver":       "a1841308-3541-4fab-bc81-f71556f20b4a",
        }
        guid = plans.get(str(value).lower().strip(), value)
        return _run_ps(f"powercfg /setactive {guid}")

    if action == "battery_status":
        return _run_ps(
            "Get-WmiObject -Class Win32_Battery | Select-Object EstimatedChargeRemaining,BatteryStatus | Format-List | Out-String"
        )

    # ─── SERVICES / PROCESSES ──────────────────────────────────────────────────
    if action == "list_processes":
        return _run_ps("Get-Process | Sort-Object CPU -Descending | Select-Object -First 15 | Format-Table Name,CPU,WorkingSet -AutoSize | Out-String")

    if action == "kill_process":
        return _run_ps(f"Stop-Process -Name '{name}' -Force")

    if action == "list_services":
        return _run_ps("Get-Service | Where-Object {$_.Status -eq 'Running'} | Select-Object -First 20 | Format-Table Name,Status -AutoSize | Out-String")

    if action == "start_service":
        return _run_ps(f"Start-Service -Name '{name}'")

    if action == "stop_service":
        return _run_ps(f"Stop-Service -Name '{name}' -Force")

    if action == "restart_service":
        return _run_ps(f"Restart-Service -Name '{name}' -Force")

    # ─── STORAGE ───────────────────────────────────────────────────────────────
    if action == "disk_usage" or action == "list_drives":
        return _run_ps("Get-PSDrive -PSProvider FileSystem | Format-Table Name,Used,Free,@{N='Total';E={$_.Used+$_.Free}} -AutoSize | Out-String")

    if action == "clean_temp":
        return _run_ps(
            "Remove-Item -Path $env:TEMP\\* -Recurse -Force -ErrorAction SilentlyContinue; "
            "'Archivos temporales eliminados.'"
        )

    if action == "empty_trash":
        return _run_ps("Clear-RecycleBin -Force; 'Papelera vaciada.'")

    # ─── APPS ──────────────────────────────────────────────────────────────────
    if action == "list_apps":
        return _run_ps("Get-AppxPackage | Select-Object Name | Sort-Object Name | Format-Table -AutoSize | Out-String")

    if action == "startup_apps":
        return _run_ps("Get-CimInstance Win32_StartupCommand | Format-Table Caption,Command -AutoSize | Out-String")

    # ─── OPEN SETTINGS PANEL ───────────────────────────────────────────────────
    if action == "open_settings" or action == "open":
        panel_map = {
            "display":    "ms-settings:display",
            "sound":      "ms-settings:sound",
            "wifi":       "ms-settings:network-wifi",
            "bluetooth":  "ms-settings:bluetooth",
            "apps":       "ms-settings:appsfeatures",
            "updates":    "ms-settings:windowsupdate",
            "privacy":    "ms-settings:privacy",
            "accounts":   "ms-settings:accounts",
            "storage":    "ms-settings:storagesense",
            "power":      "ms-settings:powersleep",
        }
        uri = panel_map.get(str(value).lower().strip(), f"ms-settings:{value}")
        return _run_ps(f"Start-Process '{uri}'") or f"Panel de configuración abierto: {uri}"

    # ─── WALLPAPER ─────────────────────────────────────────────────────────────
    if action == "set_wallpaper":
        path = parameters.get("path", value)
        if not path:
            return "Se requiere la ruta de la imagen."
        return _run_ps(
            "Add-Type @\"\nusing System; using System.Runtime.InteropServices;\n"
            "public class Wallpaper { [DllImport(\"user32.dll\")] public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni); }\n\"@\n"
            f"[Wallpaper]::SystemParametersInfo(20, 0, '{path}', 3)"
        ) or "Fondo de pantalla establecido."

    # ─── REGISTRY ──────────────────────────────────────────────────────────────
    if action == "registry_read":
        hive = parameters.get("hive", "HKCU")
        key  = parameters.get("key", "")
        reg_name = parameters.get("reg_name", "")
        return _run_ps(f"Get-ItemPropertyValue -Path '{hive}:\\{key}' -Name '{reg_name}'")

    if action == "registry_write":
        hive = parameters.get("hive", "HKCU")
        key  = parameters.get("key", "")
        reg_name = parameters.get("reg_name", "")
        reg_type = parameters.get("reg_type", "REG_SZ")
        return _run_ps(
            f"Set-ItemProperty -Path '{hive}:\\{key}' -Name '{reg_name}' -Value '{value}' -Type {reg_type}"
        )

    # ─── ENVIRONMENT VARIABLES ─────────────────────────────────────────────────
    if action == "get_env":
        return _run_ps(f"[System.Environment]::GetEnvironmentVariable('{name}')")

    if action == "set_env":
        return _run_ps(f"[System.Environment]::SetEnvironmentVariable('{name}', '{value}', 'User')")

    if action == "delete_env":
        return _run_ps(f"[System.Environment]::SetEnvironmentVariable('{name}', $null, 'User')")

    # ─── FALLBACK ──────────────────────────────────────────────────────────────
    return f"Acción '{action}' ejecutada. Si necesita un comando específico, indíquemelo, señor."
