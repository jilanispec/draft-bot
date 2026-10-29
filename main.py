
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from handlers import (
    start_command,
    jnventory_command,
    clain_command,
    ggjve_command,
    mycard_command,
    buypl_command,
    bett_command,
)
from callback import (
    open_pack_callback,
    mycard_callback,
    buypl_callback,
)

logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# Minimal HTTP server for Render's port check
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Cricket Card Bot is running")

    def log_message(self, format, *args):
        pass


def start_health_server():
    port = int(os.environ.get("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)

    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    logger.warning("Health server listening on port %s", port)


def main():
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN environment variable is not set.")

    start_health_server()

    application = Application.builder().token(bot_token).build()

    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("jnventory", jnventory_command))
    application.add_handler(CommandHandler("clain", clain_command))
    application.add_handler(CommandHandler("ggjve", ggjve_command))
    application.add_handler(CommandHandler("mycard", mycard_command))
    application.add_handler(CommandHandler("buypl", buypl_command))
    application.add_handler(CommandHandler("bett", bett_command))

    # Callbacks
    application.add_handler(
        CallbackQueryHandler(mycard_callback, pattern=r"^mc:")
    )
    application.add_handler(
        CallbackQueryHandler(open_pack_callback, pattern=r"^open_pack$")
    )
    application.add_handler(
        CallbackQueryHandler(buypl_callback, pattern=r"^buypl:")
    )

    logger.warning("Cricket Card Bot starting.")
    application.run_polling()


if __name__ == "__main__":
    main()
