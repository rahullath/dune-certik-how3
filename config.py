import os
from datetime import timedelta

# Dune Analytics API configuration
DUNE_API_KEY = os.environ.get("DUNE_API_KEY", "")
DUNE_API_BASE_URL = "https://api.dune.com/api/v1"

# Certik Skynet API configuration
CERTIK_API_KEY = os.environ.get("CERTIK_API_KEY", "")
CERTIK_API_BASE_URL = "https://api.certik.io/v1"

# Score calculation parameters
STABILITY_WEIGHT = 0.5  # Weight for stability in EQS calculation
MAGNITUDE_WEIGHT = 0.5  # Weight for magnitude in EQS calculation

USER_WEIGHTS = {
    'active_addresses': 0.4,
    'transaction_count': 0.3,
    'transaction_volume': 0.3
}

SCORE_RANGES = {
    'eqs': (0, 100),
    'ugs': (0, 100),
    'fvs': (0, 100),
    'ss': (0, 100)
}

# Categories for protocols
PROTOCOL_CATEGORIES = [
    'DeFi',
    'Layer 1',
    'Layer 2',
    'Oracle',
    'Infrastructure',
    'Gaming',
    'NFT',
    'DAO',
    'Privacy',
    'Storage',
    'Analytics',
    'Exchange'
]

# Fair Value Score parameters
# P/S ratio thresholds (market cap / annual revenue)
FVS_PS_RATIO_THRESHOLDS = {
    'DeFi': {'undervalued': 5, 'overvalued': 50},
    'Layer 1': {'undervalued': 15, 'overvalued': 150},
    'Layer 2': {'undervalued': 10, 'overvalued': 100},
    'Oracle': {'undervalued': 8, 'overvalued': 80},
    'Infrastructure': {'undervalued': 12, 'overvalued': 120},
    'Gaming': {'undervalued': 20, 'overvalued': 200},
    'NFT': {'undervalued': 18, 'overvalued': 180},
    'DAO': {'undervalued': 15, 'overvalued': 150},
    'Privacy': {'undervalued': 10, 'overvalued': 100},
    'Storage': {'undervalued': 8, 'overvalued': 80},
    'Analytics': {'undervalued': 12, 'overvalued': 120},
    'Exchange': {'undervalued': 6, 'overvalued': 60},
    'default': {'undervalued': 10, 'overvalued': 100}
}

# Data collection schedule
DATA_UPDATE_INTERVAL = timedelta(days=1)
