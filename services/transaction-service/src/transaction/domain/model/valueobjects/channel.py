from enum import Enum


class Channel(str, Enum):
    WEB = "WEB"
    MOBILE = "MOBILE"
    POS = "POS"
