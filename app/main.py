import asyncio
import threading
from fastapi import FastAPI
from .bot import app_bot, register_handlers
from .config import settings

app = FastAPI(title="GoMarket Bot API", version="1.0")

def run_bot_in_thread():
    """
    Run the Telegram bot in a separate thread with its own event loop.
    This avoids conflicts with FastAPI's event loop.
    """
    # Create and set a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Run the bot with loop
    async def start_bot():
        await app_bot.initialize()
        await app_bot.updater.start_polling()
        await app_bot.start()
    
    try:
        loop.run_until_complete(start_bot())
        loop.run_forever()
    except Exception as e:
        print(f"Bot error: {e}")
    finally:
        loop.close()

@app.on_event("startup")
async def startup_event():
    """
    FastAPI startup event handler.
    Registers bot handlers and starts the bot in a separate thread.
    """
    register_handlers()
    # Start the bot in a separate thread
    bot_thread = threading.Thread(target=run_bot_in_thread)
    bot_thread.daemon = True  # So the thread will close when the main app closes
    bot_thread.start()

@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring service status.
    """
    return {"status": "ok", "version": settings.default_threshold}