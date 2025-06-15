from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """
    Application configuration settings loaded from environment variables and .env file.
    
    Attributes:
        telegram_token: API token for Telegram bot authentication
        gomarket_base: Base URL for the GoMarket API
        default_threshold: Default spread threshold for arbitrage alerts (in %)
        update_interval: Time between data updates (in seconds)
        history_limit: Maximum number of historical entries to keep
        supported_exchanges: List of supported cryptocurrency exchanges
        supported_market_types: List of supported market types (spot, futures, etc.)
    """
    telegram_token: str = Field(..., env='TELEGRAM_TOKEN')
    gomarket_base: str = 'https://gomarket-api.goquant.io/api'
    default_threshold: float = 0.5
    update_interval: int = 15
    history_limit: int = 100
    
    supported_exchanges: list = ["binance", "okx", "bybit", "deribit"]
    supported_market_types: list = ["spot", "swap", "future", "option"]

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


settings = Settings()

