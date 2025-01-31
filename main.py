import telegram # noqa: F401
from astrbot.api.all import Context


class Main:
    def __init__(self, context: Context) -> None:
        from .bale_message_adapter import BalePlatformAdapter # noqa
