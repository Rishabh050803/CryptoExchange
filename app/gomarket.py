import httpx
import time
import random
from .config import settings
import logging

logger = logging.getLogger(__name__)

async def list_symbols(exchange: str, market_type: str):
    """
    Retrieve available trading symbols for a specific exchange and market type.
    
    Args:
        exchange: Name of the exchange (e.g., "binance", "okx")
        market_type: Type of market (e.g., "spot", "swap")
        
    Returns:
        List of symbol names available on the specified exchange
        
    Raises:
        Exception: For network errors, API errors, or unexpected issues
    """
    url = f"{settings.gomarket_base}/symbols/{exchange}/{market_type}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            print(response)
            if 'symbols' in data and isinstance(data['symbols'], list):
                return [item.get('name', f"{item.get('base')}/{item.get('quote')}") 
                        for item in data['symbols'] if 'name' in item or ('base' in item and 'quote' in item)]
            else:
                return data if isinstance(data, list) else []
                
        except httpx.RequestError as e:
            logger.error(f"Error fetching symbols: {str(e)}")
            raise Exception(f"Network error: {str(e)}")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise Exception(f"Unexpected error: {str(e)}")

async def get_ticker_data(exchange: str, market_type: str, symbol: str):
    """
    Retrieve current market data for a specific symbol on an exchange.
    If the real API endpoint is not available, generates realistic mock data.
    
    Args:
        exchange: Name of the exchange (e.g., "binance", "okx")
        market_type: Type of market (e.g., "spot", "swap")
        symbol: Trading pair symbol (e.g., "btc-usdt")
        
    Returns:
        Dictionary containing bid, ask, last price, and timestamp
        
    Raises:
        Exception: For errors in fetching or processing data
    """
    url = f"{settings.gomarket_base}/ticker/{exchange}/{market_type}/{symbol}"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                return {
                    "bid": float(data.get("bid", 0)),
                    "ask": float(data.get("ask", 0)),
                    "last": float(data.get("last", 0)),
                    "timestamp": data.get("timestamp", int(time.time() * 1000))
                }
            except:
                return generate_mock_ticker_data(exchange, symbol)
    except Exception as e:
        logger.error(f"Error fetching ticker data for {symbol} on {exchange}: {str(e)}")
        raise Exception(f"Error fetching data: {str(e)}")

def generate_mock_ticker_data(exchange, symbol):
    """
    Generate realistic mock market data for demonstration purposes.
    
    Args:
        exchange: Exchange name to simulate exchange-specific price variations
        symbol: Symbol to determine appropriate base price range
        
    Returns:
        Dictionary containing simulated bid, ask, last price, and timestamp
    """
    print("called mock data function")
    base_prices = {
        "btc": 60000 + random.uniform(-500, 500),
        "eth": 3000 + random.uniform(-30, 30),
        "sol": 150 + random.uniform(-5, 5),
        "xrp": 0.50 + random.uniform(-0.01, 0.01),
        "doge": 0.15 + random.uniform(-0.005, 0.005),
        "ada": 0.40 + random.uniform(-0.01, 0.01),
        "dot": 5.5 + random.uniform(-0.1, 0.1),
    }
    
    base_asset = None
    for asset in base_prices.keys():
        if asset in symbol.lower():
            base_asset = asset
            break
    
    if not base_asset:
        base_price = random.uniform(10, 100)
    else:
        base_price = base_prices[base_asset]
    
    exchange_factors = {
        "binance": 1.0,
        "okx": 1.0001 + random.uniform(-0.0005, 0.0005),
        "bybit": 0.9999 + random.uniform(-0.0005, 0.0005),
        "deribit": 1.0002 + random.uniform(-0.0005, 0.0005),
        "default": 1.0 + random.uniform(-0.001, 0.001)
    }
    
    factor = exchange_factors.get(exchange.lower(), exchange_factors["default"])
    adjusted_price = base_price * factor
    
    spread_percentage = random.uniform(0.01, 0.1) / 100
    half_spread = adjusted_price * spread_percentage / 2
    
    bid = adjusted_price - half_spread
    ask = adjusted_price + half_spread
    
    return {
        "bid": bid,
        "ask": ask,
        "last": adjusted_price,
        "timestamp": int(time.time() * 1000)
    }

