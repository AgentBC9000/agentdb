from enum import Enum


class APIKeyTier(str, Enum):
    TRIAL = "trial"
    BASIC = "basic"
    PRO = "pro"
    FLEET = "fleet"
