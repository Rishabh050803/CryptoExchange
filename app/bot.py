from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, filters
from .config import settings
from .gomarket import list_symbols, get_ticker_data
import asyncio
import json
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize bot
app_bot = ApplicationBuilder().token(settings.telegram_token).job_queue(None).build()

# Global state storage
active_monitors = {}  # Store active arbitrage monitors
active_market_views = {}  # Store active market views
arb_history = {}  # Store historical arbitrage opportunities

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /start command - introduce the bot and display available commands.
    """
    await update.message.reply_text(
        "Welcome to the GoMarket Bot! Use the following commands:\n"
        "/help - Show available commands\n"
        "/list_symbols <exchange> <market_type> - List available symbols\n"
        "/monitor_arb <asset1@exchange1> <asset2@exchange2> <threshold> - Monitor arbitrage\n"
        "/view_market <symbol> <exchange1> <exchange2> ... - View consolidated market data"
    )

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /help command - display detailed usage instructions for all commands.
    """
    help_text = (
        "Available commands:\n\n"
        "*/start* - Start the bot\n\n"
        "*/list_symbols <exchange> <market_type>* - List symbols for a given exchange and market type\n"
        "Example: `/list_symbols binance spot`\n\n"
        "*/monitor_arb <asset1@exchange1> <asset2@exchange2> <threshold>* - Monitor arbitrage opportunities\n"
        "Example: `/monitor_arb btc-usdt@binance btc-usdt@okx 0.5`\n\n"
        "*/stop_all_arb* - Stop all active arbitrage monitors\n\n"
        "*/view_market <symbol> <exchange1> <exchange2> ...* - View consolidated market data\n"
        "Example: `/view_market btc-usdt binance okx bybit`\n\n"
        "*/get_cbbo <symbol>* - Get current consolidated BBO for a symbol\n"
        "Example: `/get_cbbo btc-usdt`\n\n"
        "*/arb_stats <symbol>* - View arbitrage statistics for a symbol\n"
        "Example: `/arb_stats btc-usdt`"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def cmd_list_symbols(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /list_symbols command - display available symbols for a specific exchange.
    
    Args:
        exchange: Name of the exchange to query
        market_type: Type of market to query (spot, futures, etc.)
    """
    if not context.args or len(context.args) < 2:
        return await update.message.reply_text("Usage: /list_symbols <exchange> <market_type>")
        
    exchange = context.args[0].lower()
    market_type = context.args[1].lower()
    
    try:
        symbols = await list_symbols(exchange, market_type)
        if not symbols:
            return await update.message.reply_text(f"No symbols found for {exchange} {market_type}")
            
        # Create paginated response for potentially large lists
        text = f"Symbols on {exchange} ({market_type}):\n"
        text += '\n'.join(symbols[:20])  # Show first 20 symbols
        
        if len(symbols) > 20:
            text += f"\n\n...and {len(symbols) - 20} more symbols."
            
        keyboard = []
        for symbol in symbols[:5]:  # Add buttons for first 5 symbols for convenience
            monitor_text = f"Monitor {symbol}"
            callback_data = f"quick_monitor_{exchange}_{market_type}_{symbol}"
            keyboard.append([InlineKeyboardButton(monitor_text, callback_data=callback_data)])
            
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error listing symbols: {str(e)}")
        await update.message.reply_text(f"Error fetching symbols for {exchange}: {str(e)}")

async def cmd_monitor_arb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /monitor_arb command - set up monitoring for arbitrage opportunities.
    
    Args:
        asset1@exchange1: First asset specification (e.g., "btc-usdt@binance")
        asset2@exchange2: Second asset specification (e.g., "btc-usdt@okx")
        threshold: Price difference threshold for alerts (in %)
    """
    if not context.args or len(context.args) < 3:
        return await update.message.reply_text(
            "Usage: /monitor_arb <asset1@exchange1> <asset2@exchange2> <threshold>\n"
            "Example: /monitor_arb btc-usdt@binance btc-usdt@okx 0.5"
        )
    
    try:
        asset1 = context.args[0].lower()
        asset2 = context.args[1].lower()
        threshold = float(context.args[2])
        
        # Parse exchange and symbol information
        if '@' not in asset1 or '@' not in asset2:
            return await update.message.reply_text(
                "Asset format should be: symbol@exchange (e.g., btc-usdt@binance)"
            )
        
        symbol1, exchange1 = asset1.split('@')
        symbol2, exchange2 = asset2.split('@')
        
        # Generate a unique ID for this monitor
        monitor_id = f"{symbol1}_{exchange1}_{symbol2}_{exchange2}_{threshold}"
        
        # Check if already monitoring
        if monitor_id in active_monitors:
            return await update.message.reply_text(
                f"Already monitoring arbitrage between {asset1} and {asset2} with threshold {threshold}%"
            )
        
        # Start monitoring
        message = await update.message.reply_text(
            f"Starting arbitrage monitoring between {asset1} and {asset2} with threshold {threshold}%\n"
            f"Status: Initializing..."
        )
        
        # Store monitor details
        active_monitors[monitor_id] = {
            "symbol1": symbol1,
            "exchange1": exchange1,
            "symbol2": symbol2,
            "exchange2": exchange2,
            "threshold": threshold,
            "chat_id": update.effective_chat.id,
            "message_id": message.message_id,
            "active": True,
            "last_updated": time.time(),
            "alerts_sent": 0,
            "max_spread": 0.0
        }
        
        # Initialize history for this pair if not exists
        pair_key = f"{symbol1}_{symbol2}"
        if pair_key not in arb_history:
            arb_history[pair_key] = []
        
        # Create keyboard for stopping the monitor
        keyboard = [
            [InlineKeyboardButton("Stop Monitoring", callback_data=f"stop_arb_{monitor_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.edit_message_text(
            text=f"Monitoring arbitrage between {asset1} and {asset2} with threshold {threshold}%\n"
                f"Status: Active\nLast check: N/A\nSpread: N/A",
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
            reply_markup=reply_markup
        )
        
        # Start the monitoring loop in a separate task
        asyncio.create_task(arbitrage_monitor_loop(context, monitor_id))
    except ValueError:
        await update.message.reply_text("Threshold must be a valid number.")
    except Exception as e:
        logger.error(f"Error setting up arbitrage monitor: {str(e)}")
        await update.message.reply_text(f"Error setting up arbitrage monitor: {str(e)}")

async def cmd_stop_all_arb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /stop_all_arb command - stop all active arbitrage monitors for the current user.
    """
    chat_id = update.effective_chat.id
    count = 0
    
    for monitor_id, monitor in list(active_monitors.items()):
        if monitor["chat_id"] == chat_id and monitor["active"]:
            monitor["active"] = False
            count += 1
    
    if count > 0:
        await update.message.reply_text(f"Stopped {count} active arbitrage monitors.")
    else:
        await update.message.reply_text("No active arbitrage monitors to stop.")

async def cmd_arb_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /arb_stats command - display statistics for monitored arbitrage pairs.
    
    Args:
        symbol: Symbol to show statistics for (e.g., "btc-usdt")
    """
    if not context.args:
        return await update.message.reply_text("Usage: /arb_stats <symbol>")
    
    symbol = context.args[0].lower()
    
    # Look for all history records containing this symbol
    relevant_history = {}
    for pair_key, history in arb_history.items():
        if symbol in pair_key:
            relevant_history[pair_key] = history
    
    if not relevant_history:
        return await update.message.reply_text(f"No arbitrage history found for {symbol}")
    
    stats_text = f"Arbitrage Statistics for {symbol}:\n\n"
    
    for pair_key, history in relevant_history.items():
        if not history:
            continue
            
        # Calculate statistics
        max_spread = max([entry["spread"] for entry in history], default=0)
        avg_spread = sum([entry["spread"] for entry in history]) / len(history) if history else 0
        opportunity_count = sum(1 for entry in history if entry["is_opportunity"])
        
        # Extract symbol names from the pair key
        symbol1, symbol2 = pair_key.split('_')
        
        stats_text += f"*{symbol1} vs {symbol2}*\n"
        stats_text += f"Opportunities detected: {opportunity_count}\n"
        stats_text += f"Maximum spread: {max_spread:.2f}%\n"
        stats_text += f"Average spread: {avg_spread:.2f}%\n"
        
        if history:
            last_entry = history[-1]
            stats_text += f"Last spread: {last_entry['spread']:.2f}% at {datetime.fromtimestamp(last_entry['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        stats_text += "\n"
    
    await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)

async def cmd_view_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /view_market command - display consolidated market data across exchanges.
    
    Args:
        symbol: Trading pair to monitor (e.g., "btc-usdt")
        exchanges: List of exchanges to include in the view
    """
    if not context.args or len(context.args) < 2:
        return await update.message.reply_text(
            "Usage: /view_market <symbol> <exchange1> <exchange2> ...\n"
            "Example: /view_market btc-usdt binance okx bybit"
        )
    
    try:
        symbol = context.args[0].lower()
        exchanges = [exchange.lower() for exchange in context.args[1:]]
        
        # Generate a unique ID for this market view
        view_id = f"{symbol}_{'_'.join(exchanges)}"
        
        # Check if already viewing
        if view_id in active_market_views:
            return await update.message.reply_text(
                f"Already viewing market data for {symbol} on {', '.join(exchanges)}"
            )
        
        # Start viewing
        message = await update.message.reply_text(
            f"Starting consolidated market view for {symbol} on {', '.join(exchanges)}\n"
            f"Status: Initializing..."
        )
        
        # Store view details
        active_market_views[view_id] = {
            "symbol": symbol,
            "exchanges": exchanges,
            "chat_id": update.effective_chat.id,
            "message_id": message.message_id,
            "active": True,
            "market_type": "spot"  # Default to spot market
        }
        
        # Create keyboard for stopping the view
        keyboard = [
            [InlineKeyboardButton("Stop Viewing", callback_data=f"stop_view_{view_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.edit_message_text(
            text=f"Consolidated market view for {symbol} on {', '.join(exchanges)}\n"
                f"Status: Active\nLast check: N/A",
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
            reply_markup=reply_markup
        )
        
        # Start the market view loop in a separate task
        asyncio.create_task(market_view_loop(context, view_id))
    except Exception as e:
        logger.error(f"Error setting up market view: {str(e)}")
        await update.message.reply_text(f"Error setting up market view: {str(e)}")

async def cmd_get_cbbo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /get_cbbo command - get consolidated best bid and offer for a symbol.
    
    Args:
        symbol: Trading pair to check (e.g., "btc-usdt")
    """
    if not context.args:
        return await update.message.reply_text("Usage: /get_cbbo <symbol>")
    
    symbol = context.args[0].lower()
    
    # Look for active market views for this symbol
    for view_id, view in active_market_views.items():
        if view["symbol"] == symbol and view["active"]:
            # We found an active view for this symbol, return its latest data
            await update.message.reply_text(
                f"Please check the active market view for {symbol}. "
                f"It's already being monitored."
            )
            return
    
    # If no active view, suggest exchanges to check
    default_exchanges = ["binance", "okx", "bybit"]
    keyboard = []
    for exchange in default_exchanges:
        callback_data = f"quick_view_{symbol}_{exchange}"
        keyboard.append([InlineKeyboardButton(f"Check on {exchange}", callback_data=callback_data)])
    
    # Add a button to check on all exchanges
    all_exchanges = "_".join(default_exchanges)
    keyboard.append([InlineKeyboardButton("Check on all exchanges", 
                                         callback_data=f"quick_view_{symbol}_{all_exchanges}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"No active market view for {symbol}. Select an exchange to check:",
        reply_markup=reply_markup
    )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle button callbacks from inline keyboards.
    
    Supports:
    - Starting/stopping arbitrage monitors
    - Starting/stopping market views
    - Quick setup of monitors and views
    """
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("stop_arb_"):
        monitor_id = data.replace("stop_arb_", "")
        if monitor_id in active_monitors:
            active_monitors[monitor_id]["active"] = False
            await query.edit_message_text(
                f"Arbitrage monitoring stopped. Use /monitor_arb to start a new monitor."
            )
    
    elif data.startswith("restart_arb_"):
        monitor_id = data.replace("restart_arb_", "")
        if monitor_id in active_monitors:
            monitor = active_monitors[monitor_id]
            monitor["active"] = True
            
            # Update message
            await query.edit_message_text(
                f"Restarting arbitrage monitoring between "
                f"{monitor['symbol1']}@{monitor['exchange1']} and "
                f"{monitor['symbol2']}@{monitor['exchange2']} with threshold {monitor['threshold']}%\n"
                f"Status: Active\nLast check: N/A\nSpread: N/A",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Stop Monitoring", callback_data=f"stop_arb_{monitor_id}")]
                ])
            )
            
            # Start the monitoring loop again
            asyncio.create_task(arbitrage_monitor_loop(context, monitor_id))
    
    elif data.startswith("stop_view_"):
        view_id = data.replace("stop_view_", "")
        if view_id in active_market_views:
            active_market_views[view_id]["active"] = False
            await query.edit_message_text(
                f"Market view stopped. Use /view_market to start a new view."
            )
    
    elif data.startswith("quick_monitor_"):
        # Format: quick_monitor_exchange_market_type_symbol
        parts = data.replace("quick_monitor_", "").split("_")
        if len(parts) >= 3:
            exchange = parts[0]
            market_type = parts[1]
            symbol = "_".join(parts[2:])  # In case symbol contains underscores
            
            # Create command to compare with another major exchange
            alt_exchange = "binance" if exchange != "binance" else "okx"
            threshold = settings.default_threshold
            
            command_text = f"/monitor_arb {symbol}@{exchange} {symbol}@{alt_exchange} {threshold}"
            
            # Use send_message instead of update.message.reply_text
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"Starting quick monitor with command: {command_text}"
            )
            
            # Create context args for the monitor command
            context.args = [f"{symbol}@{exchange}", f"{symbol}@{alt_exchange}", str(threshold)]
            
            # Use the query.message for the reply
            try:
                # Use a custom message for the callback query scenario
                message = await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"Starting arbitrage monitoring between {symbol}@{exchange} and {symbol}@{alt_exchange} with threshold {threshold}%\nStatus: Initializing..."
                )
                
                # Create a monitor_id and set up monitoring as in cmd_monitor_arb
                monitor_id = f"{symbol}_{exchange}_{symbol}_{alt_exchange}_{threshold}"
                
                # Only proceed if not already monitoring
                if monitor_id not in active_monitors:
                    # Set up monitoring here
                    active_monitors[monitor_id] = {
                        "symbol1": symbol,
                        "exchange1": exchange,
                        "symbol2": symbol,
                        "exchange2": alt_exchange,
                        "threshold": threshold,
                        "chat_id": query.message.chat_id,
                        "message_id": message.message_id,
                        "active": True,
                        "last_updated": time.time(),
                        "alerts_sent": 0,
                        "max_spread": 0.0
                    }
                    
                    # Initialize history if needed
                    pair_key = f"{symbol}_{symbol}"
                    if pair_key not in arb_history:
                        arb_history[pair_key] = []
                    
                    # Create keyboard for stopping
                    keyboard = [
                        [InlineKeyboardButton("Stop Monitoring", callback_data=f"stop_arb_{monitor_id}")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await context.bot.edit_message_text(
                        text=f"Monitoring arbitrage between {symbol}@{exchange} and {symbol}@{alt_exchange} with threshold {threshold}%\nStatus: Active\nLast check: N/A\nSpread: N/A",
                        chat_id=query.message.chat_id,
                        message_id=message.message_id,
                        reply_markup=reply_markup
                    )
                    
                    # Start monitoring
                    asyncio.create_task(arbitrage_monitor_loop(context, monitor_id))
                else:
                    await context.bot.edit_message_text(
                        text=f"Already monitoring arbitrage between {symbol}@{exchange} and {symbol}@{alt_exchange} with threshold {threshold}%",
                        chat_id=query.message.chat_id,
                        message_id=message.message_id
                    )
            except Exception as e:
                logger.error(f"Error setting up arbitrage monitor: {str(e)}")
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"Error setting up arbitrage monitor: {str(e)}"
                )
    
    elif data.startswith("quick_view_"):
        # Format: quick_view_symbol_exchange1_exchange2_...
        parts = data.replace("quick_view_", "").split("_")
        if len(parts) >= 2:
            symbol = parts[0]
            exchanges = parts[1:]
            
            try:
                # Generate a unique ID for this market view
                view_id = f"{symbol}_{'_'.join(exchanges)}"
                
                # Check if already viewing
                if view_id in active_market_views:
                    await context.bot.send_message(
                        chat_id=query.message.chat_id,
                        text=f"Already viewing market data for {symbol} on {', '.join(exchanges)}"
                    )
                    return
                
                # Start viewing
                message = await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"Starting consolidated market view for {symbol} on {', '.join(exchanges)}\n"
                    f"Status: Initializing..."
                )
                
                # Store view details
                active_market_views[view_id] = {
                    "symbol": symbol,
                    "exchanges": exchanges,
                    "chat_id": query.message.chat_id,
                    "message_id": message.message_id,
                    "active": True,
                    "market_type": "spot"  # Default to spot market
                }
                
                # Create keyboard for stopping the view
                keyboard = [
                    [InlineKeyboardButton("Stop Viewing", callback_data=f"stop_view_{view_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.edit_message_text(
                    text=f"Consolidated market view for {symbol} on {', '.join(exchanges)}\n"
                        f"Status: Active\nLast check: N/A",
                    chat_id=query.message.chat_id,
                    message_id=message.message_id,
                    reply_markup=reply_markup
                )
                
                # Start the market view loop in a separate task
                asyncio.create_task(market_view_loop(context, view_id))
                
            except Exception as e:
                logger.error(f"Error setting up market view: {str(e)}")
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"Error setting up market view: {str(e)}"
                )

async def arbitrage_monitor_loop(context, monitor_id):
    """
    Background task that continuously monitors arbitrage opportunities.
    
    Args:
        context: Telegram context for sending messages
        monitor_id: Identifier for the specific arbitrage monitor
        
    Continuously:
    1. Fetches current prices from both exchanges
    2. Calculates the spread percentage
    3. Updates the status message
    4. Sends alerts when spread exceeds threshold
    """
    monitor = active_monitors[monitor_id]
    
    while monitor["active"]:
        try:
            # Get necessary data
            symbol1 = monitor["symbol1"]
            exchange1 = monitor["exchange1"]
            symbol2 = monitor["symbol2"]
            exchange2 = monitor["exchange2"]
            threshold = monitor["threshold"]
            market_type = "spot"  # Assuming spot market for simplicity
            
            # Fetch price data
            data1 = await get_ticker_data(exchange1, market_type, symbol1)
            data2 = await get_ticker_data(exchange2, market_type, symbol2)
            
            # Calculate mid prices
            mid_price1 = (data1["bid"] + data1["ask"]) / 2 if data1["bid"] > 0 and data1["ask"] > 0 else data1["last"]
            mid_price2 = (data2["bid"] + data2["ask"]) / 2 if data2["bid"] > 0 and data2["ask"] > 0 else data2["last"]
            
            # Calculate spread percentage
            if mid_price1 <= 0 or mid_price2 <= 0:
                spread_pct = 0
            else:
                spread_pct = abs(mid_price1 - mid_price2) / min(mid_price1, mid_price2) * 100
            
            # Update max spread if higher
            monitor["max_spread"] = max(monitor["max_spread"], spread_pct)
            monitor["last_updated"] = time.time()
            
            # Check if this is an arbitrage opportunity
            is_opportunity = spread_pct >= threshold
            
            # Record in history
            pair_key = f"{symbol1}_{symbol2}"
            arb_history[pair_key].append({
                "timestamp": time.time(),
                "exchange1": exchange1,
                "price1": mid_price1,
                "exchange2": exchange2,
                "price2": mid_price2,
                "spread": spread_pct,
                "is_opportunity": is_opportunity
            })
            
            # Limit history size
            if len(arb_history[pair_key]) > 100:
                arb_history[pair_key] = arb_history[pair_key][-100:]
            
            # Update message with current information
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status_text = (
                f"Monitoring arbitrage between {symbol1}@{exchange1} and {symbol2}@{exchange2}\n"
                f"Threshold: {threshold}%\n"
                f"Status: Active\n"
                f"Last check: {current_time}\n"
                f"Price {symbol1}@{exchange1}: {mid_price1:.8f}\n"
                f"Price {symbol2}@{exchange2}: {mid_price2:.8f}\n"
                f"Current spread: {spread_pct:.2f}%\n"
                f"Max spread: {monitor['max_spread']:.2f}%\n"
                f"Alerts sent: {monitor['alerts_sent']}"
            )
            
            # Create keyboard
            keyboard = [
                [InlineKeyboardButton("Stop Monitoring", callback_data=f"stop_arb_{monitor_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await context.bot.edit_message_text(
                    text=status_text,
                    chat_id=monitor["chat_id"],
                    message_id=monitor["message_id"],
                    reply_markup=reply_markup
                )
            except Exception as e:
                # Message might be unchanged, which Telegram API doesn't allow
                pass
            
            # Check if spread exceeds threshold and send alert
            if is_opportunity:
                monitor["alerts_sent"] += 1
                
                # Determine which exchange has better price
                cheaper_exchange = exchange1 if mid_price1 < mid_price2 else exchange2
                expensive_exchange = exchange2 if cheaper_exchange == exchange1 else exchange1
                cheaper_price = min(mid_price1, mid_price2)
                expensive_price = max(mid_price1, mid_price2)
                
                alert_text = (
                    f"🚨 ARBITRAGE OPPORTUNITY 🚨\n\n"
                    f"*Symbol:* {symbol1}\n"
                    f"*Buy on:* {cheaper_exchange} @ {cheaper_price:.8f}\n"
                    f"*Sell on:* {expensive_exchange} @ {expensive_price:.8f}\n"
                    f"*Spread:* {spread_pct:.2f}% (Threshold: {threshold}%)\n"
                    f"*Potential profit:* {(expensive_price - cheaper_price):.8f} per unit\n"
                    f"*Time:* {current_time}"
                )
                
                await context.bot.send_message(
                    chat_id=monitor["chat_id"],
                    text=alert_text,
                    parse_mode=ParseMode.MARKDOWN
                )
            
            # Wait before next check
            await asyncio.sleep(15)
            
        except Exception as e:
            logger.error(f"Error in arbitrage monitor {monitor_id}: {str(e)}")
            
            try:
                # Notify about the error but don't spam
                if time.time() - monitor.get("last_error_notification", 0) > 60:
                    await context.bot.send_message(
                        chat_id=monitor["chat_id"],
                        text=f"Error in arbitrage monitor: {str(e)}\nMonitoring will continue."
                    )
                    monitor["last_error_notification"] = time.time()
            except:
                pass
                
            # Wait longer after an error
            await asyncio.sleep(30)
    
    # If we exit the loop, update the message if possible
    try:
        await context.bot.edit_message_text(
            text=f"Arbitrage monitoring for {monitor['symbol1']}@{monitor['exchange1']} and "
                 f"{monitor['symbol2']}@{monitor['exchange2']} has been stopped.",
            chat_id=monitor["chat_id"],
            message_id=monitor["message_id"],
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Restart Monitoring", callback_data=f"restart_arb_{monitor_id}")]
            ])
        )
    except:
        pass

async def market_view_loop(context, view_id):
    """
    Background task that continuously updates consolidated market view.
    
    Args:
        context: Telegram context for sending messages
        view_id: Identifier for the specific market view
        
    Continuously:
    1. Fetches current prices from all specified exchanges
    2. Identifies best bid and ask across all exchanges (CBBO)
    3. Calculates consolidated mid price and spread
    4. Updates the view message with formatted data
    """
    view = active_market_views[view_id]
    
    while view["active"]:
        try:
            symbol = view["symbol"]
            exchanges = view["exchanges"]
            market_type = view["market_type"]
            
            # Fetch data from all exchanges
            exchange_data = {}
            for exchange in exchanges:
                try:
                    data = await get_ticker_data(exchange, market_type, symbol)
                    if data["bid"] > 0 and data["ask"] > 0:
                        exchange_data[exchange] = data
                except Exception as e:
                    logger.error(f"Error fetching data for {exchange}: {str(e)}")
            
            if not exchange_data:
                await asyncio.sleep(10)
                continue
            
            # Find best bid and ask
            best_bid = {"price": 0, "exchange": None}
            best_ask = {"price": float('inf'), "exchange": None}
            
            for exchange, data in exchange_data.items():
                if data["bid"] > best_bid["price"]:
                    best_bid = {"price": data["bid"], "exchange": exchange}
                
                if data["ask"] < best_ask["price"] and data["ask"] > 0:
                    best_ask = {"price": data["ask"], "exchange": exchange}
            
            # Calculate CBBO mid price
            if best_bid["price"] > 0 and best_ask["price"] < float('inf'):
                cbbo_mid = (best_bid["price"] + best_ask["price"]) / 2
            else:
                cbbo_mid = 0
            
            # Format market view text
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            view_text = f"📊 *Consolidated Market View for {symbol}*\n\n"
            
            # Add CBBO information
            if best_bid["exchange"] and best_ask["exchange"]:
                view_text += f"*CBBO:* Best Bid on {best_bid['exchange']} @ {best_bid['price']:.8f}, "
                view_text += f"Best Ask on {best_ask['exchange']} @ {best_ask['price']:.8f}\n"
                view_text += f"*CBBO Mid:* {cbbo_mid:.8f}\n"
                view_text += f"*CBBO Spread:* {((best_ask['price'] - best_bid['price']) / cbbo_mid * 100):.4f}%\n\n"
            
            # Add individual exchange data
            view_text += "*Exchange Data:*\n"
            for exchange in exchanges:
                if exchange in exchange_data:
                    data = exchange_data[exchange]
                    mid_price = (data["bid"] + data["ask"]) / 2 if data["bid"] > 0 and data["ask"] > 0 else data["last"]
                    spread = (data["ask"] - data["bid"]) / mid_price * 100 if mid_price > 0 else 0
                    
                    view_text += f"*{exchange.capitalize()}:* Bid: {data['bid']:.8f}, Ask: {data['ask']:.8f}, "
                    view_text += f"Mid: {mid_price:.8f}, Spread: {spread:.4f}%\n"
                    
                    # Highlight if this exchange has the best bid or ask
                    if exchange == best_bid["exchange"]:
                        view_text += "  ✅ Best Bid\n"
                    if exchange == best_ask["exchange"]:
                        view_text += "  ✅ Best Ask\n"
                else:
                    view_text += f"*{exchange.capitalize()}:* Data unavailable\n"
            
            view_text += f"\n*Last updated:* {current_time}"
            
            # Create keyboard
            keyboard = [
                [InlineKeyboardButton("Stop Viewing", callback_data=f"stop_view_{view_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Update message
            try:
                await context.bot.edit_message_text(
                    text=view_text,
                    chat_id=view["chat_id"],
                    message_id=view["message_id"],
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                # Message might be unchanged
                pass
            
            # Wait before next update
            await asyncio.sleep(15)
            
        except Exception as e:
            logger.error(f"Error in market view {view_id}: {str(e)}")
            await asyncio.sleep(30)
    
    # If we exit the loop, update the message
    try:
        await context.bot.edit_message_text(
            text=f"Market view for {view['symbol']} has been stopped.",
            chat_id=view["chat_id"],
            message_id=view["message_id"]
        )
    except:
        pass

def register_handlers():
    """
    Register all command handlers and callback handlers with the bot.
    Should be called during application startup.
    """
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("help", help))
    app_bot.add_handler(CommandHandler("list_symbols", cmd_list_symbols))
    app_bot.add_handler(CommandHandler("monitor_arb", cmd_monitor_arb))
    app_bot.add_handler(CommandHandler("stop_all_arb", cmd_stop_all_arb))
    app_bot.add_handler(CommandHandler("arb_stats", cmd_arb_stats))
    app_bot.add_handler(CommandHandler("view_market", cmd_view_market))
    app_bot.add_handler(CommandHandler("get_cbbo", cmd_get_cbbo))
    app_bot.add_handler(CallbackQueryHandler(callback_handler))
    
    # Register error handler
    app_bot.add_error_handler(error_handler)
    
    logger.info("All handlers registered")

async def error_handler(update, context):
    """
    Handle errors occurring in the bot.
    Logs errors and notifies users when possible.
    """
    logger.error(f"Update {update} caused error {context.error}")
    try:
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"An error occurred: pleace enter correct command or check your input.\n"
                f"Error details: {context.error}\n"
                f"Please try again or contact support if the issue persists."
            )
    except:
        pass