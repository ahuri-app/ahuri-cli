__all__ = [
    "log",
    "warn",
    "info",
    "winfo"
]

def log(msg = " "):
    """
    Log outputs.

    Args:
        msg (str, optional): message to log. Defaults to " ".
    """
    msg = msg.splitlines()
    pmsg = ""
    for x in msg:
        pmsg += "[INFO] " + x + "\n"
    print(pmsg, end="")

def warn(msg = " "):
    """
    Warn a message to user.

    Args:
        msg (str, optional): message to warn the user with. Defaults to " ".
    """
    msg = msg.splitlines()
    pmsg = ""
    for x in msg:
        pmsg += "[WARN] " + x + "\n"
    print(pmsg, end="")

def info(msg = " "):
    """
    Show info to user.

    Args:
        msg (str, optional): info message. Defaults to " ".
    """
    msg = msg.splitlines()
    pmsg = ""
    for x in msg:
        pmsg += "<i> " + x + "\n"
    print(pmsg, end="")

def winfo(msg = " "):
    """
    Show info to user.

    Args:
        msg (str, optional): info message. Defaults to " ".
    """
    msg = msg.splitlines()
    pmsg = ""
    for x in msg:
        pmsg += "<!> " + x + "\n"
    print(pmsg, end="")