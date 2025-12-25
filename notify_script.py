# notify_script.py
# Used by scheduled Windows tasks to show a toast via the project's notify module.
# The scheduled schtask will run: python notify_script.py "Title" "Message"

import sys
from pathlib import Path

# add project dir to path so we can import notify
project_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(project_dir))

try:
    import notify
except Exception:
    notify = None

def main(argv):
    if len(argv) >= 3:
        title = argv[1]
        message = argv[2]
    else:
        title = "Smartbook"
        message = "Erinnerung"

    if notify and hasattr(notify, "show_toast"):
        try:
            notify.show_toast(title, message)
        except Exception:
            # best-effort
            pass
    else:
        # fallback: print (schtasks output capture)
        print(title)
        print(message)


if __name__ == "__main__":
    main(sys.argv)

