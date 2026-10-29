
#===== IMPORTS =====
import logging
import os

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

from callback import (
    open_pack_callback,
    mycard_callback,
    buypl_callback,
)

#===== LOGGING =====
logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

#===== MAIN =====
def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable is not set."
        )

    application = Application.builder().token(BOT_TOKEN).build()

    #===== COMMANDS =====
    application.add_handler(
        CommandHandler("start", start_command)
    )
    application.add_handler(
        CommandHandler("jnventory", jnventory_command)
    )
    application.add_handler(
        CommandHandler("clain", clain_command)
    )
    application.add_handler(
        CommandHandler("ggjve", ggjve_command)
    )
    application.add_handler(
        CommandHandler("mycard", mycard_command)
    )
    application.add_handler(
        CommandHandler("buypl", buypl_command)
    )

    #===== CALLBACKS =====
    application.add_handler(
        CallbackQueryHandler(
            mycard_callback,
            pattern=r"^mc:"
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            open_pack_callback,
            pattern=r"^open_pack$"
        )
    )
    application.add_handler(
        CallbackQueryHandler(
            buypl_callback,
            pattern=r"^buypl:"
        )
    )

    #===== START BOT =====
    logger.warning("Cricket Card Bot started.")
    application.run_polling()


#===== RUN =====
if __name__ == "__main__":
    main()
