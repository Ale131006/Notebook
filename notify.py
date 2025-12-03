import sys
import subprocess
import shlex
import os
from pathlib import Path

# Try to use win10toast for native toasts while the app runs
try:
    from win10toast import ToastNotifier
    _toaster = ToastNotifier()
    def show_toast(title, msg, duration=6):
        # threaded=True so it doesn't block
        try:
            _toaster.show_toast(title, msg, duration=duration, threaded=True)
        except Exception:
            # fallback to nothing (Main app will show QMessageBox if needed)
            pass
except Exception:
    _toaster = None
    def show_toast(title, msg, duration=6):
        # no-op here; MainWindow will fall back to Qt dialog if needed
        pass


# ------------------------------
# Optional: schedule a Windows task
# ------------------------------
def schedule_windows_notification(task_name: str, run_at_dt, title: str, message: str, python_exe: str = None, notify_script: str = None):
    """
    Create an ONCE schtask that runs a Python script/exe at run_at_dt to show a notification.
    - task_name: unique name for the task (e.g. "SmartbookDeadline_123")
    - run_at_dt: datetime.datetime (local time)
    - python_exe: path to python.exe (defaults to sys.executable)
    - notify_script: path to a script or exe that shows a toast; if None, assume notify_script.py next to this file.
    """
    if sys.platform != "win32":
        raise RuntimeError("schedule_windows_notification only supported on Windows")

    import datetime
    if python_exe is None:
        python_exe = sys.executable

    if notify_script is None:
        notify_script = os.path.join(os.path.dirname(__file__), "notify_script.py")

    # Make sure path exists
    notify_script = str(Path(notify_script).resolve())

    # schtasks expects time and date in certain local formats; use yyyy-MM-dd for /SD and HH:mm for /ST
    date_str = run_at_dt.strftime("%Y-%m-%d")
    time_str = run_at_dt.strftime("%H:%M")

    # Command to run; quote args
    cmd = f'"{python_exe}" "{notify_script}" "{title}" "{message}"'

    schtask_cmd = [
        "schtasks", "/Create",
        "/SC", "ONCE",
        "/TN", task_name,
        "/TR", cmd,
        "/ST", time_str,
        "/SD", date_str,
        "/F"  # force replace if exists
    ]

    # run
    subprocess.run(schtask_cmd, check=True)


def delete_scheduled_task(task_name: str):
    if sys.platform != "win32":
        return
    subprocess.run(["schtasks", "/Delete", "/TN", task_name, "/F"], check=False)
