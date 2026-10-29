
#===== IMPORTS =====
import random
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from html import escape

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import BadRequest


#===== TIMEZONE =====
IST = ZoneInfo("Asia/Kolkata")


#===== DATA FILES =====
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

#===== CARD DATABASE =====
CARDS_FILE = DATA_DIR / "cards.json"

if not CARDS_FILE.exists():
    CARDS_FILE = BASE_DIR / "cards.json"

#===== USER DATA =====
DATA_DIR = Path(
    os.environ.get("DATA_DIR", str(Path(__file__).resolve().parent / "data"))
)
DATA_DIR.mkdir(parents=True, exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
TEMP_USERS_FILE = DATA_DIR / "users.tmp"


#===== LOAD USERS =====
def load_users():
    if not USERS_FILE.exists():
        return {}

    with USERS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("users.json must contain a JSON object")

    return data


#===== SAVE USERS =====
def save_users(users):
    with TEMP_USERS_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            users,
            file,
            indent=4,
            ensure_ascii=False,
        )
        file.flush()

    TEMP_USERS_FILE.replace(USERS_FILE)


#===== GET USER RECORD =====
def get_user_record(user):
    users = load_users()
    user_id = str(user.id)

    if user_id not in users:
        users[user_id] = {
            "first_name": user.first_name,
            "id": user.id,
            "username": user.username,
            "jnventory": 0,
            "cards": [],
            "total_packs": 0,
            "last_claim_day": None,
            "claim_streak": 0,
            "last_bonus_streak": 0,
        }
    else:
        record = users[user_id]
        record["first_name"] = user.first_name
        record["username"] = user.username

        record.setdefault("jnventory", 0)
        record.setdefault("cards", [])
        record.setdefault("total_packs", 0)
        record.setdefault("last_claim_day", None)
        record.setdefault("claim_streak", 0)
        record.setdefault("last_bonus_streak", 0)

    save_users(users)
    return users[user_id]


#===== START COMMAND =====
async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    get_user_record(user)

    await message.reply_text(
        "<b>🏏 Welcome to Cricket Card Bot!</b>\n\n"
        "Your account is ready!\n\n"
        "💰 Use /jnventory to view your inventory.\n"
        "🎁 Use /clain to claim your daily coins.\n"
        "🃏 Use /mycard to view your collection.\n"
        "🛒 Use /buypl PLAYER NAME to find a player.",
        parse_mode=ParseMode.HTML,
    )


#===== INVENTORY COMMAND =====
async def jnventory_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    record = get_user_record(user)
    coins = int(record.get("jnventory", 0))
    total_packs = int(record.get("total_packs", 0))

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📦 Open pack",
                callback_data="open_pack",
            )
        ]
    ])

    await message.reply_text(
        "<b>💼 Your Inventory</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"💰 Card Coins: <b>{coins:,}</b>🪙\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📦 Total Packs: <b>{total_packs}</b>\n"
        "━━━━━━━━━━━━━━━━━━",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )


#===== DAILY CLAIM COMMAND =====
async def clain_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    users = load_users()
    user_id = str(user.id)

    if user_id not in users:
        get_user_record(user)
        users = load_users()

    record = users[user_id]

    #===== CLAIM DAY STARTS AT 4 AM IST =====
    now = datetime.now(IST)
    claim_date = (now - timedelta(hours=4)).date().isoformat()
    last_claim_day = record.get("last_claim_day")

    if last_claim_day == claim_date:
        await message.reply_text(
            "<b>⏳ You have already claimed your daily coins!</b>\n\n"
            "🕓 Your next claim starts at <b>4:00 AM IST.</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    #===== STREAK =====
    yesterday = (
        datetime.fromisoformat(claim_date).date()
        - timedelta(days=1)
    ).isoformat()

    if last_claim_day == yesterday:
        record["claim_streak"] = int(
            record.get("claim_streak", 0)
        ) + 1
    else:
        record["claim_streak"] = 1
        record["last_bonus_streak"] = 0

    #===== DAILY REWARD =====
    daily_reward = 10000
    record["jnventory"] = int(
        record.get("jnventory", 0)
    ) + daily_reward

    streak = record["claim_streak"]
    bonus = 0

    #===== SEVEN-DAY BONUS =====
    if streak > 0 and streak % 7 == 0:
        last_bonus = int(record.get("last_bonus_streak", 0))

        if last_bonus < streak:
            bonus = 50000
            record["jnventory"] += bonus
            record["last_bonus_streak"] = streak

    #===== SAVE CLAIM =====
    record["last_claim_day"] = claim_date
    users[user_id] = record
    save_users(users)

    bonus_message = (
        "\n\n🎉 <b>7-Day Streak Bonus:</b> +50,000🪙"
        if bonus else ""
    )

    await message.reply_text(
        "<b>🎁 Daily Claim Successful!</b>\n\n"
        f"💰 Daily Reward: <b>+{daily_reward:,}</b>🪙\n"
        f"🔥 Current Streak: <b>{streak} day(s)</b>"
        f"{bonus_message}\n\n"
        f"💳 Current Balance: "
        f"<b>{record['jnventory']:,}</b>🪙",
        parse_mode=ParseMode.HTML,
    )


#===== GIVE COINS COMMAND =====
async def ggjve_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    sender = update.effective_user

    if message is None or sender is None:
        return

    #===== REPLY MODE =====
    if not message.reply_to_message:
        await message.reply_text(
            "<b>💸 Reply to the target user's message and use:</b>\n\n"
            "<code>/ggjve &lt;amount&gt;</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    recipient = message.reply_to_message.from_user

    if recipient is None:
        await message.reply_text(
            "❌ <b>Could not identify the recipient.</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    if recipient.is_bot:
        await message.reply_text(
            "❌ <b>You cannot send coins to a bot.</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    if recipient.id == sender.id:
        await message.reply_text(
            "❌ <b>You cannot send coins to yourself.</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    #===== VALIDATE AMOUNT =====
    if len(context.args) != 1:
        await message.reply_text(
            "❌ <b>Invalid amount.</b>\n"
            "Usage: <code>/ggjve &lt;amount&gt;</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        amount = int(context.args[0])
    except ValueError:
        await message.reply_text(
            "❌ <b>Amount must be a whole number.</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    if amount <= 0:
        await message.reply_text(
            "❌ <b>Amount must be greater than zero.</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    #===== LOAD USERS =====
    users = load_users()
    sender_id = str(sender.id)
    recipient_id = str(recipient.id)

    if sender_id not in users:
        get_user_record(sender)
        users = load_users()

    #===== CREATE RECIPIENT RECORD =====
    if recipient_id not in users:
        users[recipient_id] = {
            "first_name": recipient.first_name,
            "id": recipient.id,
            "username": recipient.username,
            "jnventory": 0,
            "cards": [],
            "total_packs": 0,
            "last_claim_day": None,
            "claim_streak": 0,
            "last_bonus_streak": 0,
        }
    else:
        recipient_record = users[recipient_id]
        recipient_record["first_name"] = recipient.first_name
        recipient_record["username"] = recipient.username
        recipient_record.setdefault("jnventory", 0)
        recipient_record.setdefault("cards", [])
        recipient_record.setdefault("total_packs", 0)
        recipient_record.setdefault("last_claim_day", None)
        recipient_record.setdefault("claim_streak", 0)
        recipient_record.setdefault("last_bonus_streak", 0)

    #===== CHECK BALANCES =====
    sender_record = users[sender_id]

    try:
        sender_balance = int(sender_record.get("jnventory", 0))
        recipient_balance = int(
            users[recipient_id].get("jnventory", 0)
        )
    except (TypeError, ValueError):
        await message.reply_text(
            "❌ <b>Could not read a user's coin balance.</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    if sender_balance < amount:
        await message.reply_text(
            "❌ <b>Insufficient coins!</b>\n\n"
            f"💰 Your balance: <b>{sender_balance:,}🪙</b>\n"
            f"💸 Transfer amount: <b>{amount:,}🪙</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    #===== TRANSFER =====
    sender_record["jnventory"] = sender_balance - amount
    users[recipient_id]["jnventory"] = recipient_balance + amount

    #===== SAVE =====
    try:
        save_users(users)
    except (OSError, ValueError):
        await message.reply_text(
            "❌ <b>Transfer failed: could not save user data.</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    #===== SUCCESS =====
    await message.reply_text(
        "✅ <b>Coin Transfer Successful!</b>\n\n"
        f"👤 Recipient: <b>{escape(recipient.first_name)}</b>\n"
        f"💸 Sent: <b>{amount:,}🪙</b>\n\n"
        f"💰 Your balance: "
        f"<b>{sender_record['jnventory']:,}🪙</b>",
        parse_mode=ParseMode.HTML,
    )



#===== ADMIN TOHFA COMMAND =====
TOHFA_ADMIN_IDS = {2079655933}


async def tohfa_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    admin = update.effective_user

    if message is None or admin is None:
        return

    # Only approved admin IDs can use this command
    if admin.id not in TOHFA_ADMIN_IDS:
        await message.reply_text("⛔ You are not authorized to use /tohfa.")
        return

    # Usage: /tohfa <amount> (reply)
    #        /tohfa <amount> <telegram_user_id>
    if len(context.args) not in (1, 2):
        await message.reply_text(
            "🎁 Usage:\n"
            "• Reply to a user's message: /tohfa <amount>\n"
            "• By Telegram ID: /tohfa <amount> <user_id>"
        )
        return

    # Validate amount
    try:
        amount = int(context.args[0])
    except ValueError:
        await message.reply_text("❌ Amount must be a whole number.")
        return

    if amount <= 0:
        await message.reply_text("❌ Amount must be greater than zero.")
        return

    # Identify recipient
    recipient = None

    if len(context.args) == 2:
        try:
            recipient_id = int(context.args[1])
            if recipient_id <= 0:
                raise ValueError
        except ValueError:
            await message.reply_text("❌ Invalid Telegram user ID.")
            return
    else:
        replied = message.reply_to_message
        if replied is None or replied.from_user is None:
            await message.reply_text(
                "❌ Reply to the user's message, or provide their Telegram ID.\n"
                "Example: /tohfa 5000 123456789"
            )
            return

        recipient = replied.from_user

        if recipient.is_bot:
            await message.reply_text("❌ You cannot gift coins to a bot.")
            return

        recipient_id = recipient.id

    # Load current user data
    try:
        users = load_users()
    except (OSError, ValueError):
        await message.reply_text("❌ Could not load user data.")
        return

    key = str(recipient_id)

    # Create a record if this ID is not in the database yet
    if key not in users:
        users[key] = {
            "first_name": (
                recipient.first_name if recipient else f"User {recipient_id}"
            ),
            "id": recipient_id,
            "username": recipient.username if recipient else None,
            "jnventory": 0,
            "cards": [],
            "total_packs": 0,
            "last_claim_day": None,
            "claim_streak": 0,
            "last_bonus_streak": 0,
        }
    else:
        users[key].setdefault("jnventory", 0)
        users[key].setdefault("cards", [])
        users[key].setdefault("total_packs", 0)
        users[key].setdefault("last_claim_day", None)
        users[key].setdefault("claim_streak", 0)
        users[key].setdefault("last_bonus_streak", 0)

        if recipient:
            users[key]["first_name"] = recipient.first_name
            users[key]["username"] = recipient.username

    # Add coins without deducting from the admin
    try:
        old_balance = int(users[key]["jnventory"])
        if old_balance < 0:
            raise ValueError
        new_balance = old_balance + amount
        users[key]["jnventory"] = new_balance
        save_users(users)
    except (OSError, ValueError, TypeError):
        await message.reply_text("❌ Could not update the user's coin balance.")
        return

    display_name = (
        recipient.first_name if recipient else f"User ID {recipient_id}"
    )

    await message.reply_text(
        "🎁 <b>Tohfa Sent Successfully!</b>\n\n"
        f"👤 Recipient: <b>{escape(display_name)}</b>\n"
        f"🆔 Telegram ID: <code>{recipient_id}</code>\n"
        f"💰 Coins gifted: <b>+{amount:,} 🪙</b>\n"
        f"💳 New balance: <b>{new_balance:,} 🪙</b>",
        parse_mode=ParseMode.HTML,
    )
    

#===== MY CARD COMMAND =====
async def mycard_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    from callback import show_my_cards

    user = update.effective_user

    if user is None or update.effective_message is None:
        return

    get_user_record(user)

    await show_my_cards(
        update=update,
        context=context,
        user_id=user.id,
        page=0,
        edit=False,
        category="all",
    )


#===== BUY PLAYER COMMAND =====
async def buypl_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    if not context.args:
        await message.reply_text(
            "<b>🛒 Buy Player</b>\n\n"
            "Usage: <code>/buypl PLAYER NAME</code>\n\n"
            "Example: <code>/buypl Virat Kohli</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    search_name = " ".join(context.args).strip().casefold()

    #===== LOAD PLAYER DATABASE =====
    try:
        with CARDS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict):
            cards = list(data.values())
        elif isinstance(data, list):
            cards = data
        else:
            cards = []

    except (OSError, json.JSONDecodeError):
        await message.reply_text(
            "❌ <b>Could not load the player database.</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    #===== SEARCH PLAYERS =====
    matches = [
        card for card in cards
        if isinstance(card, dict)
        and search_name in str(card.get("name", "")).casefold()
    ]

    if not matches:
        await message.reply_text(
            f"❌ No players found for "
            f"<b>“{escape(' '.join(context.args))}”</b>.",
            parse_mode=ParseMode.HTML,
        )
        return

    #===== GROUP BY PLAYER NAME =====
    players = {}

    for card in matches:
        name = str(card.get("name", "")).strip()

        if name:
            players.setdefault(
                name.casefold(),
                {"name": name, "cards": []},
            )
            players[name.casefold()]["cards"].append(card)

    if len(players) > 1:
        lines = [
            "<b>🔎 Multiple players found.</b>",
            "",
            "Run the command again with the full name:",
            "",
        ]

        for player in list(players.values())[:20]:
            lines.append(
                f"• <code>/buypl {escape(player['name'])}</code>"
            )

        await message.reply_text(
            "\n".join(lines),
            parse_mode=ParseMode.HTML,
        )
        return

    player = next(iter(players.values()))
    player_cards = player["cards"]

    #===== GROUP BY FORMAT =====
    formats = {}

    for card in player_cards:
        fmt = str(card.get("format", "Unknown"))
        formats.setdefault(
            fmt.casefold(),
            {"format": fmt, "card": card},
        )

    if len(formats) > 1:
        buttons = []

        for item in formats.values():
            card = item["card"]
            fmt = item["format"]
            card_id = card.get("id")

            if card_id is None:
                continue

            buttons.append(
                InlineKeyboardButton(
                    fmt.upper(),
                    callback_data=f"buypl:{user.id}:format:{card_id}",
                )
            )

        if not buttons:
            await message.reply_text(
                "❌ Player format data is incomplete."
            )
            return

        keyboard = InlineKeyboardMarkup([
            buttons[i:i + 3]
            for i in range(0, len(buttons), 3)
        ])

        await message.reply_text(
            f"<b>📛 {escape(player['name'])} ⭐</b>\n\n"
            "Different formats are available.\n"
            "Choose a format:",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )
        return

    #===== SHOW PLAYER =====
    card = next(iter(formats.values()))["card"]

    await send_buypl_card(
        update,
        context,
        card,
        user.id,
    )


#===== SEND PLAYER CARD =====
async def send_buypl_card(update, context, card, user_id):
    users = load_users()
    record = users.get(str(user_id), {})

    owned_cards = record.get("cards", [])
    card_id = card.get("id")

    is_owned = any(
        str(owned.get("id")) == str(card_id)
        and str(owned.get("format", "")).casefold()
        == str(card.get("format", "")).casefold()
        for owned in owned_cards
    )

    try:
        value = int(card.get("value", 0))
    except (TypeError, ValueError):
        value = 0

    try:
        balance = int(record.get("jnventory", 0))
    except (TypeError, ValueError):
        balance = 0

    rarity = escape(str(card.get("rarity", "⚪ Common")))
    name = escape(str(card.get("name", "Unknown")))
    fmt = escape(str(card.get("format", "Unknown")))

    #===== PURCHASE STATUS BUTTON =====
    if card_id is None:
        button = InlineKeyboardButton(
            "❌ Invalid card ID",
            callback_data="buypl:0:owned:0",
        )
    elif is_owned:
        button = InlineKeyboardButton(
            "✅ Already Owned",
            callback_data=f"buypl:{user_id}:owned:{card_id}",
        )
    elif value > 0 and balance >= value:
        button = InlineKeyboardButton(
            "🛒 Buy",
            callback_data=f"buypl:{user_id}:buy:{card_id}",
        )
    else:
        button = InlineKeyboardButton(
            "❌ Can't afford",
            callback_data=f"buypl:{user_id}:poor:{card_id}",
        )

    keyboard = InlineKeyboardMarkup([[button]])

    #===== PLAYER DETAILS =====
    text = (
        f"<b>📛 {name} ⭐</b>\n\n"
        "<b>👤 Info:</b>\n\n"
        f"📋 <b>Format:</b> {fmt}\n"
        f"🧺 <b>Status:</b> {'Owned' if is_owned else 'Not owned'}\n"
        f"🪒 <b>Rarity:</b> {rarity}\n"
        f"💰 <b>Value:</b> {value:,}🪙\n\n"
        "Tap below to purchase this card."
    )

    #===== SEND OR EDIT =====
    query = getattr(update, "callback_query", None)

    if query:
        try:
            await query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
            )
        except BadRequest as error:
            if "Message is not modified" not in str(error):
                raise
    else:
        message = update.effective_message

        if message:
            await message.reply_text(
                text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
            )



#===== BET PATTERNS =====

BET_PATTERNS = [
    "HTHTHTH", "THTHTHT", "HHTTHHT", "TTHHTTH", "HHHTTTH",
    "TTTHHHT", "HTTHHTT", "THHTTHH", "HHTHTTH", "TTHTHHT",
    "HTHHTHT", "THTTHTH", "HHHHTTT", "TTTTHHH", "HTTTHHH",
    "THHHTTT", "HHTTTHH", "TTHHHTT", "HTHTTHH", "THTHHTT",
    "HHTHHTT", "TTHTTHH", "HTTHTHH", "THHTHTT", "HHHTHTT",
    "TTTHTHH", "HTHHHTT", "THTTTHH", "HHTHTHT", "TTHTHTH",
    "HTTTTHH", "THHHHTT", "HHTTHTH", "TTHHTHT", "HTHTTTH",
    "THTHHHT", "HHHTHHT", "TTTHTTH", "HTHHTTH", "THTTHHT",
    "HHTHTTT", "TTHTHHH", "HTTHHHT", "THHTTTH", "HHHHHTT",
    "TTTTTHH", "HTHTHHT", "THTHTTH", "HHTTTTH", "TTHHHHT"
]


#===== BET COMMAND =====

async def bett_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user

    if message is None or user is None:
        return

    #===== CHECK ARGUMENTS =====

    if len(context.args) != 2:
        await message.reply_text(
            "<b>🎲 Head / Tail Betting</b>\n\n"
            "Usage:\n"
            "<code>/bett h 100</code>\n"
            "<code>/bett 100 heads</code>\n\n"
            "Choices: <code>h</code>, <code>head</code>, "
            "<code>heads</code>, <code>t</code>, "
            "<code>tail</code>, <code>tails</code>",
            parse_mode=ParseMode.HTML
        )
        return

    #===== PARSE BET =====

    choices = {
        "h": "H",
        "head": "H",
        "heads": "H",
        "t": "T",
        "tail": "T",
        "tails": "T"
    }

    first = context.args[0].casefold()
    second = context.args[1].casefold()

    if first in choices:
        choice = choices[first]
        amount_text = context.args[1]
    elif second in choices:
        choice = choices[second]
        amount_text = context.args[0]
    else:
        await message.reply_text(
            "❌ <b>Invalid choice!</b>\n"
            "Choose Heads or Tails.",
            parse_mode=ParseMode.HTML
        )
        return

    #===== VALIDATE AMOUNT =====

    try:
        amount = int(amount_text)
    except ValueError:
        await message.reply_text(
            "❌ <b>Bet amount must be a whole number.</b>",
            parse_mode=ParseMode.HTML
        )
        return

    if amount <= 0:
        await message.reply_text(
            "❌ <b>Bet amount must be greater than zero.</b>",
            parse_mode=ParseMode.HTML
        )
        return

    #===== LOAD USER DATA =====

    users = load_users()
    user_id = str(user.id)

    if user_id not in users:
        get_user_record(user)
        users = load_users()

    record = users[user_id]

    #===== CURRENT GAME DAY (IST) =====

    now = datetime.now(IST)
    game_day = (now - timedelta(hours=4)).date().isoformat()

    #===== RESET DAILY LIMITS =====

    if record.get("bet_game_day") != game_day:
        record["bet_game_day"] = game_day
        record["bet_daily_count"] = 0
        record["bet_daily_earnings"] = 0
        record["bet_pattern"] = random.choice(BET_PATTERNS)
        record["bet_pattern_position"] = 0

    bet_count = int(record.get("bet_daily_count", 0))
    earnings = int(record.get("bet_daily_earnings", 0))

    #===== CHECK BET LIMIT =====

    if bet_count >= 30:
        await message.reply_text(
            "❌ <b>You have used all 30 bets today!</b>\n"
            "🕓 Come back after <b>4:00 AM IST.</b>",
            parse_mode=ParseMode.HTML
        )
        return

    #===== CHECK EARNING LIMIT =====

    earning_limit = 100000
    remaining_earnings = earning_limit - earnings

    if remaining_earnings <= 0:
        await message.reply_text(
            "🏆 <b>You have reached today's earning limit!</b>\n"
            "🕓 Come back after <b>4:00 AM IST.</b>",
            parse_mode=ParseMode.HTML
        )
        return

    if amount > remaining_earnings:
        await message.reply_text(
            "⚠️ <b>Bet exceeds your remaining daily earning limit.</b>\n\n"
            f"💰 Remaining earning capacity: "
            f"<b>{remaining_earnings:,}🪙</b>",
            parse_mode=ParseMode.HTML
        )
        return

    #===== CHECK BALANCE =====

    balance = int(record.get("jnventory", 0))

    if balance < amount:
        await message.reply_text(
            "❌ <b>Insufficient coins!</b>\n\n"
            f"💰 Balance: <b>{balance:,}🪙</b>\n"
            f"🎲 Bet: <b>{amount:,}🪙</b>",
            parse_mode=ParseMode.HTML
        )
        return

    #===== GET PATTERN OUTCOME =====

    pattern = record.get("bet_pattern")
    position = int(record.get("bet_pattern_position", 0))

    if not pattern or len(pattern) != 7 or not 0 <= position < 7:
        pattern = random.choice(BET_PATTERNS)
        position = 0

    outcome = pattern[position]

    #===== ADVANCE PATTERN =====

    position += 1

    if position >= 7:
        record["bet_pattern"] = random.choice(BET_PATTERNS)
        record["bet_pattern_position"] = 0
    else:
        record["bet_pattern"] = pattern
        record["bet_pattern_position"] = position

    #===== CALCULATE RESULT =====

    bet_count += 1

    if choice == outcome:
        # 2x total return: original stake plus equal net winnings.
        balance += amount
        earnings += amount
        result_line = f"🟢 <b>You won!</b> +{amount:,}🪙 🎉"
    else:
        balance -= amount
        result_line = f"🔴 <b>You lost!</b> -{amount:,}🪙 💸"

    #===== SAVE RESULT =====

    record["jnventory"] = balance
    record["bet_daily_count"] = bet_count
    record["bet_daily_earnings"] = earnings
    users[user_id] = record
    save_users(users)

    #===== RESULT MESSAGE =====

    choice_name = "Heads" if choice == "H" else "Tails"
    outcome_name = "Heads" if outcome == "H" else "Tails"
    outcome_icon = "⬆️" if outcome == "H" else "⬇️"

    await message.reply_text(
        "🎲 <b>Coin Flip Result</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"You chose: <b>{choice_name}</b>\n"
        f"Result: {outcome_icon} <b>{outcome_name}</b>\n\n"
        f"{result_line}\n\n"
        f"💰 Balance: <b>{balance:,}🪙</b>\n"
        f"🎯 Bets used today: <b>{bet_count}/30</b>",
        parse_mode=ParseMode.HTML
    )
    
