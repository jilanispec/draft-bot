# ===== IMPORTS =====
import os
import hmac
import logging
import callback

from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)

from handlers import (
    start_command,
    jnventory_command,
    clain_command,
    ggjve_command,
    mycard_command,
    buypl_command,
)

# ===== LOGGING =====
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ===== ENVIRONMENT VARIABLES =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing.")

if not WEBHOOK_SECRET:
    raise RuntimeError(
        "TELEGRAM_WEBHOOK_SECRET environment variable is missing."
    )

# ===== FASTAPI =====
app = FastAPI()

# ===== TELEGRAM APPLICATION =====
telegram_app = Application.builder().token(BOT_TOKEN).build()

# ===== COMMAND HANDLERS =====
telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(CommandHandler("jnventory", jnventory_command))
telegram_app.add_handler(CommandHandler("clain", clain_command))
telegram_app.add_handler(CommandHandler("ggjve", ggjve_command))
telegram_app.add_handler(CommandHandler("mycard", mycard_command))
telegram_app.add_handler(CommandHandler("buypl", buypl_command))

# ===== CALLBACK HANDLERS =====
telegram_app.add_handler(
    CallbackQueryHandler(callback.mycard_callback, pattern=r"^mc:")
)
telegram_app.add_handler(
    CallbackQueryHandler(callback.open_pack_callback, pattern=r"^open_pack$")
)
telegram_app.add_handler(
    CallbackQueryHandler(callback.buypl_callback, pattern=r"^buypl:")
)

# ===== WEBHOOK ENDPOINT =====
@app.post("/")
@app.post("/api")
async def telegram_webhook(request: Request):
    supplied_secret = request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token", ""
    )

    if not hmac.compare_digest(supplied_secret, WEBHOOK_SECRET):
        raise HTTPException(status_code=403, detail="Forbidden")

    try:
        payload = await request.json()
        update = Update.de_json(payload, telegram_app.bot)

        await telegram_app.initialize()
        try:
            await telegram_app.process_update(update)
        finally:
            await telegram_app.shutdown()

        return {"ok": True}

    except HTTPException:
        raise
    except Exception:
        logger.exception("Telegram update processing failed")
        raise HTTPException(
            status_code=500,
            detail="Update processing failed",
        )
