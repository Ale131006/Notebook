# notify_script.py
import sys
try:
    from win10toast import ToastNotifier
    t = ToastNotifier()
    title = sys.argv[1] if len(sys.argv) > 1 else "Smartbook"
    msg = sys.argv[2] if len(sys.argv) > 2 else "Deadline"
    t.show_toast(title, msg, duration=10)
except Exception:
    # minimal fallback: print
    print("Notification:", sys.argv[1] if len(sys.argv)>1 else "Smartbook", sys.argv[2] if len(sys.argv)>2 else "Deadline")
