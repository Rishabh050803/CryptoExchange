# GoMarket Trading Bot

A sophisticated trading information system that leverages GoQuant's GoMarket data product to provide real-time market data, arbitrage signals, and consolidated market views across multiple cryptocurrency exchanges.

## Features

- **Multi-Exchange Arbitrage Monitoring**
  - Track price differences between the same asset on different exchanges
  - Receive alerts when arbitrage opportunities exceed configurable thresholds
  - View detailed statistics on historical arbitrage opportunities

- **Consolidated Market View**
  - View consolidated best bid and offer (CBBO) across multiple exchanges
  - Identify best execution venues for buying and selling
  - Monitor market data from Binance, OKX, Bybit, and Deribit

- **Interactive Telegram Interface**
  - User-friendly commands and interactive buttons
  - Real-time updates through message editing
  - Configurable monitoring parameters

## System Architecture

The system consists of:
- Telegram bot for user interaction
- FastAPI backend for API endpoints
- GoMarket API integration for market data
- Background tasks for continuous monitoring

## Setup Instructions

### Prerequisites
- Python 3.10 

### Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/GoQuantProject.git
cd GoQuantProject
```

2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your Telegram token
```
telegram_token=YOUR_TELEGRAM_BOT_TOKEN
```

5. Start the application
```bash
uvicorn app.main:app --reload
```

## Usage Guide

### Basic Commands

- `/start` - Start the bot and see available commands
- `/help` - Display detailed help information

### List Available Symbols
```
/list_symbols <exchange> <market_type>
```
Example: `/list_symbols binance spot`

### Monitor Arbitrage Opportunities
```
/monitor_arb <asset1@exchange1> <asset2@exchange2> <threshold>
```
Example: `/monitor_arb btc-usdt@binance btc-usdt@okx 0.5`

### Stop All Arbitrage Monitors
```
/stop_all_arb
```

### View Consolidated Market Data
```
/view_market <symbol> <exchange1> <exchange2> ...
```
Example: `/view_market btc-usdt binance okx bybit`

### Get Consolidated Best Bid and Offer
```
/get_cbbo <symbol>
```
Example: `/get_cbbo btc-usdt`

### View Arbitrage Statistics
```
/arb_stats <symbol>
```
Example: `/arb_stats btc-usdt`

## Configuration

The application can be configured through the settings in `app/config.py`:

- `telegram_token`: Your Telegram Bot API token
- `gomarket_base`: Base URL for the GoMarket API
- `default_threshold`: Default arbitrage threshold percentage
- `update_interval`: Time between data updates (seconds)
- `history_limit`: Maximum number of historical entries to keep
- `supported_exchanges`: List of supported exchanges
- `supported_market_types`: List of supported market types

## Dependencies

- python-telegram-bot: Telegram bot API integration
- fastapi: API framework
- uvicorn: ASGI server
- httpx: Async HTTP client
- pydantic: Data validation and settings management

## License

This project is proprietary and confidential to GoQuant.

## Disclaimer

This software is for educational and demonstration purposes only. Trading cryptocurrencies involves significant risk and may not be suitable for everyone. Always do your own research before making investment decisions.