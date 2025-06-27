# GoMarket Trading Bot

A sophisticated trading information system that leverages GoQuant's GoMarket data product to provide real-time market data, arbitrage signals, and consolidated market views across multiple cryptocurrency exchanges.

---

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

---

## System Architecture

The system consists of:
- Telegram bot for user interaction
- FastAPI backend for API endpoints
- GoMarket API integration for market data
- Background tasks for continuous monitoring

---

## Project Structure

```
GoQuantProject/
├── app/                    # Main application package
│   ├── __init__.py         # Package initializer
│   ├── main.py             # FastAPI application entry point
│   ├── bot.py              # Telegram bot implementation
│   ├── gomarket.py         # Market data API client
│   └── config.py           # Configuration settings
├── .env                    # Environment variables (not committed to repo)
├── requirements.txt        # Project dependencies
└── README.md               # Project documentation
```

---

## Implementation Details

### Asynchronous Programming

The application uses Python's `asyncio` library to handle multiple concurrent operations such as:
- Command processing
- API requests
- Background monitoring tasks
- Message updates

This allows the bot to remain responsive while performing background operations.

### Error Handling

Comprehensive error handling is implemented across the codebase for:
- API connection errors
- Data validation issues
- Telegram API failures
- Runtime exceptions

All errors are logged with context, and user-friendly messages are sent via Telegram.

### Mock Data Generation

In case the GoMarket API is unavailable or for testing purposes, the system generates realistic mock data:
- Base prices for common assets like BTC, ETH
- Exchange-specific price variations
- Realistic bid-ask spreads
- Timestamped historical data

This makes it possible to demonstrate and test the system without real-time API access.

---

## Component Details

### 1. FastAPI Application (`app/main.py`)

- Initializes FastAPI app
- Runs Telegram bot in a separate thread
- Offers a health check endpoint
- Manages app startup/shutdown events

### 2. Telegram Bot (`app/bot.py`)

Implements user interface and logic including:
- Command Handlers (`/list_symbols`, `/monitor_arb`, etc.)
- Callback Handlers for interactive buttons
- Monitor Loops for arbitrage scanning
- Market View Loops for live data display

### 3. Market Data Client (`app/gomarket.py`)

- Fetches symbol and ticker data
- Handles API connection and retry logic
- Provides mock data fallback
- Normalizes data from multiple exchanges

### 4. Configuration (`app/config.py`)

- Manages all settings using Pydantic
- Reads from `.env` and fallback defaults
- Defines valid exchanges and market types

---

## Setup Instructions

### Prerequisites

- Python 3.10 
- Telegram Bot Token (via BotFather)
- Internet connection for GoMarket API

### Installation

1. Clone the repository
```bash
git clone https://github.com/Rishabh050803/GoQuantProject.git
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

5. Run the app
```bash
uvicorn app.main:app --reload
```

---

## Usage Guide

### Basic Commands

- `/start` — Start the bot and show main menu  
- `/help` — Show help details

### List Available Symbols
```bash
/list_symbols <exchange> <market_type>
# Example: /list_symbols binance spot
```

### Monitor Arbitrage
```bash
/monitor_arb <asset1@exchange1> <asset2@exchange2> <threshold>
# Example: /monitor_arb btc-usdt@binance btc-usdt@okx 0.5
```

### Stop All Monitors
```bash
/stop_all_arb
```

### View Market Data
```bash
/view_market <symbol> <exchange1> <exchange2> ...
# Example: /view_market btc-usdt binance okx bybit
```

### Get CBBO
```bash
/get_cbbo <symbol>
# Example: /get_cbbo btc-usdt
```

### Arbitrage Stats
```bash
/arb_stats <symbol>
# Example: /arb_stats btc-usdt
```

---

## Configuration

Set values inside `app/config.py` or override via `.env`:

- `telegram_token`: Telegram Bot API token
- `gomarket_base`: Base URL for GoMarket API
- `default_threshold`: Arbitrage threshold (%)
- `update_interval`: Data update frequency (sec)
- `history_limit`: Max number of historical records
- `supported_exchanges`: Valid exchanges
- `supported_market_types`: Valid market types

---

## Dependencies

- `python-telegram-bot`: Telegram bot integration
- `fastapi`: API framework
- `uvicorn`: ASGI server
- `httpx`: Async HTTP client
- `pydantic`: Configuration + validation

---

## License

This project is proprietary and confidential to GoQuant.

---

## Disclaimer

This software is for **educational and demonstration purposes only**.  
Cryptocurrency trading involves substantial risk. Always do your own research before making financial decisions.
