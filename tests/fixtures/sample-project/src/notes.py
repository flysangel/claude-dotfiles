"""筆記。依賴帳號功能：只有登入的使用者才能操作。"""

from accounts import login

_notes: dict[str, list[str]] = {}


def add_note(name: str, password: str, text: str) -> None:
    if not login(name, password):
        raise PermissionError("not logged in")
    _notes.setdefault(name, []).append(text)


def list_notes(name: str, password: str) -> list[str]:
    if not login(name, password):
        raise PermissionError("not logged in")
    return list(_notes.get(name, []))
