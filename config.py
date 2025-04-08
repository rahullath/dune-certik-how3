import os

class Config:
    """Base configuration class"""
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get("SESSION_SECRET", "dev-key-for-development-only")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Dune Analytics API configuration
    DUNE_API_KEY = os.environ.get("DUNE_API_KEY")
    DUNE_API_BASE_URL = "https://api.dune.com/api/v1"
    
    # Certik Skynet API configuration
    CERTIK_API_KEY = os.environ.get("CERTIK_API_KEY")
    CERTIK_API_BASE_URL = "https://skynet-api.certik.com/v1"
    
    # Scoring parameters
    REVENUE_STABILITY_WEIGHT = 0.5
    REVENUE_MAGNITUDE_WEIGHT = 0.5
    
    ACTIVE_ADDRESSES_WEIGHT = 0.4
    TRANSACTION_COUNT_WEIGHT = 0.3
    TRANSACTION_VOLUME_WEIGHT = 0.3
    
    EQS_WEIGHT = 0.25
    UGS_WEIGHT = 0.25
    FVS_WEIGHT = 0.25
    SS_WEIGHT = 0.25
    
    # List of supported protocols with their categories
    PROTOCOLS = {
        "chainlink": {
            "symbol": "LINK",
            "category": "Oracle",
            "description": "Decentralized oracle network connecting smart contracts to real-world data"
        },
        "uniswap": {
            "symbol": "UNI",
            "category": "DEX",
            "description": "Automated liquidity protocol for token swaps on Ethereum"
        },
        "aave": {
            "symbol": "AAVE",
            "category": "Lending",
            "description": "Open source liquidity protocol for earning interest on deposits and borrowing assets"
        },
        # Add more protocols as needed
    }
    
    # Data update frequency in seconds
    UPDATE_FREQUENCY = 86400  # Daily updates

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

# Select configuration based on environment
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get the current configuration"""
    env = os.environ.get('FLASK_ENV', 'default')
    return config[env]
