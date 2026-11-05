"""第三方相依套件，不屬於此專案的功能。提供付款與寄信。"""


def charge(amount: int) -> bool:
    return amount > 0


def send_mail(address: str) -> bool:
    return bool(address)
