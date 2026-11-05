"""使用者帳號。"""

MIN_PASSWORD_LENGTH = 8
_users: dict[str, str] = {}


def register(name: str, password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError("password too short")
    _users[name] = password


def login(name: str, password: str) -> bool:
    return _users.get(name) == password
