
#===== IMPORTS =====
import json
from pathlib import Path
from html import escape

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.error import BadRequest
from telegram.ext import ContextTypes

# Keep data paths independent of handlers.py
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CARDS_FILE = DATA_DIR / "cards.json"



#===== OPEN PACK CALLBACK =====
async def open_pack_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    if query is None:
        return

    await query.answer(
        text="Lavde ey Mod APK hai",
        show_alert=True
    )


#===== CARD CATEGORIES =====
FORMATS = {
    "IPL": "cricket",
    "ODI": "cricket",
    "Test": "cricket",
    "PKL": "pkl",
    "FIFA": "fifa",
    "WWE": "wwe",
}

FORMAT_ORDER = ["IPL", "ODI", "Test", "PKL", "FIFA", "WWE"]
PER_PAGE = 20


#===== LOAD MASTER CARDS =====
def load_master_cards():
    try:
        with CARDS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            return list(data.values())

    except (OSError, json.JSONDecodeError):
        pass

    return []


#===== COLLECTION KEYBOARD =====
def collection_keyboard(user_id, category, page, total_pages):
    rows = [
        [
            InlineKeyboardButton(
                "All", callback_data=f"mc:{user_id}:all:0"
            ),
            InlineKeyboardButton(
                "🏏", callback_data=f"mc:{user_id}:cricket:0"
            ),
            InlineKeyboardButton(
                "⚽", callback_data=f"mc:{user_id}:fifa:0"
            ),
            InlineKeyboardButton(
                "🤼", callback_data=f"mc:{user_id}:wwe:0"
            ),
            InlineKeyboardButton(
                "🤸", callback_data=f"mc:{user_id}:pkl:0"
            ),
        ]
    ]

    navigation = []

    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                "◀️",
                callback_data=f"mc:{user_id}:{category}:{page - 1}",
            )
        )

    if page < total_pages - 1:
        navigation.append(
            InlineKeyboardButton(
                "▶️",
                callback_data=f"mc:{user_id}:{category}:{page + 1}",
            )
        )

    if total_pages >= 10:
        for label, target in [
            ("-10", page - 10),
            ("-5", page - 5),
            ("+5", page + 5),
            ("+10", page + 10),
        ]:
            if 0 <= target < total_pages:
                navigation.append(
                    InlineKeyboardButton(
                        label,
                        callback_data=f"mc:{user_id}:{category}:{target}",
                    )
                )

    if navigation:
        rows.append(navigation)

    rows.append([
        InlineKeyboardButton(
            "📊 Collection",
            callback_data=f"mc:{user_id}:collection",
        )
    ])

    return InlineKeyboardMarkup(rows)




    

#===== SHOW MY CARDS =====
from handlers import load_users

async def show_my_cards(
    update=None,
    context=None,
    user_id=None,
    page=0,
    edit=True,
    category="all",
):
    users = load_users()
    record = users.get(str(user_id), {})
    cards = record.get("cards", [])

    #===== CATEGORY FILTER =====
    category_formats = {
        "cricket": ["IPL", "ODI", "Test"],
        "fifa": ["FIFA"],
        "wwe": ["WWE"],
        "pkl": ["PKL"],
    }

    if category in category_formats:
        allowed_formats = {
            fmt.casefold() for fmt in category_formats[category]
        }
        filtered_cards = [
            card for card in cards
            if str(card.get("format", "")).casefold() in allowed_formats
        ]
    else:
        filtered_cards = cards

    #===== PAGINATION =====
    total_cards = len(filtered_cards)
    total_pages = max(1, (total_cards + PER_PAGE - 1) // PER_PAGE)
    page = max(0, min(int(page), total_pages - 1))

    page_cards = filtered_cards[
        page * PER_PAGE:(page + 1) * PER_PAGE
    ]

    #===== MESSAGE HEADER =====
    text = (
        "🃏 <b>Your Collection</b> 📊\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )

    if not filtered_cards:
        text += "You don't own any cards in this category.\n"
    else:
        for index, card in enumerate(
            page_cards,
            start=page * PER_PAGE + 1,
        ):
            name = escape(str(card.get("name", "Unknown")))
            fmt = escape(str(card.get("format", "Unknown")))
            rarity = str(card.get("rarity", "⚪")).casefold()

            if "legendary" in rarity or "🟡" in rarity:
                rarity_icon = "🟡"
            elif "epic" in rarity or "🟣" in rarity:
                rarity_icon = "🟣"
            elif "rare" in rarity or "🔵" in rarity:
                rarity_icon = "🔵"
            else:
                rarity_icon = "⚪"

            text += f"{index}. {rarity_icon} {name} ({fmt})\n"

    text += (
        "\n━━━━━━━━━━━━━━━━━━\n"
        f"Page {page + 1}/{total_pages}"
    )

    #===== KEYBOARD =====
    reply_markup = collection_keyboard(
        user_id, category, page, total_pages
    )

    #===== EDIT OR SEND =====
    if update and update.callback_query and edit:
        try:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        except BadRequest as error:
            if "Message is not modified" not in str(error):
                raise

    elif update and update.effective_message:
        await update.effective_message.reply_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )


#===== SHOW COLLECTION STATISTICS =====
from handlers import load_users

async def show_collection(query, user_id):
    users = load_users()
    record = users.get(str(user_id), {})
    owned = record.get("cards", [])
    master = load_master_cards()

    lines = [
        "<b>📊 Your Collections</b>",
        "━━━━━━━━━━━━━━━━━━",
    ]

    grand_owned = 0
    grand_total = len(master)

    for fmt in FORMAT_ORDER:
        owned_format = [
            card for card in owned
            if str(card.get("format", "")).casefold() == fmt.casefold()
        ]

        master_format = [
            card for card in master
            if str(card.get("format", "")).casefold() == fmt.casefold()
        ]

        if fmt in ("IPL", "ODI", "Test"):
            emoji = "🏏"
        elif fmt == "PKL":
            emoji = "🤸"
        elif fmt == "FIFA":
            emoji = "⚽"
        else:
            emoji = "🤼"

        lines.append(f"\n\n<b>{emoji} {escape(fmt)}</b>")

        rarity_groups = [
            ("legendary", "🟡", "Legend"),
            ("epic", "🟣", "Epic"),
            ("rare", "🔵", "Rare"),
            ("common", "⚪", "Common"),
        ]

        for rarity_name, rarity_emoji, label in rarity_groups:
            def matches_rarity(card):
                rarity = str(card.get("rarity", "")).casefold()
                return (
                    rarity_name in rarity
                    or rarity == {
                        "legendary": "🟡",
                        "epic": "🟣",
                        "rare": "🔵",
                        "common": "⚪",
                    }[rarity_name].casefold()
                )

            owned_count = sum(
                1 for card in owned_format if matches_rarity(card)
            )
            total_count = sum(
                1 for card in master_format if matches_rarity(card)
            )

            if owned_count or total_count:
                lines.append(
                    f"\n  {rarity_emoji} {label}: "
                    f"{owned_count}/{total_count}"
                )

        lines.append(
            f"\n  Total: {len(owned_format)}/{len(master_format)} cards"
        )
        grand_owned += len(owned_format)

    lines.extend([
        "\n\n━━━━━━━━━━━━━━━━━━",
        f"\n🃏 <b>Grand Total:</b> {grand_owned}/{grand_total} cards",
    ])

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data=f"mc:{user_id}:all:0",
            )
        ]
    ])

    try:
        await query.edit_message_text(
            "".join(lines),
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except BadRequest as error:
        if "Message is not modified" not in str(error):
            raise


#===== MYCARD CALLBACK =====
async def mycard_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    if query is None:
        return

    #===== VALIDATE CALLBACK DATA =====
    parts = query.data.split(":")
    if len(parts) < 3 or parts[0] != "mc":
        await query.answer("Invalid request.", show_alert=True)
        return

    try:
        owner_id = int(parts[1])
    except ValueError:
        await query.answer("Invalid user.", show_alert=True)
        return

    #===== CHECK OWNER BEFORE PROCESSING =====
    if update.effective_user.id != owner_id:
        await query.answer(
            "This collection isn't yours!",
            show_alert=True,
        )
        return

    await query.answer()

    category = parts[2]

    #===== COLLECTION STATISTICS =====
    if category == "collection":
        await show_collection(query, owner_id)
        return

    #===== VALIDATE CATEGORY AND PAGE =====
    allowed_categories = {"all", "cricket", "fifa", "wwe", "pkl"}
    if category not in allowed_categories:
        await query.answer("Unknown category.", show_alert=True)
        return

    try:
        page = int(parts[3]) if len(parts) > 3 else 0
    except ValueError:
        page = 0

    #===== DISPLAY SELECTED CATEGORY =====
    await show_my_cards(
        update=update,
        context=context,
        user_id=owner_id,
        page=page,
        edit=True,
        category=category,
    )


#===== BUY PLAYER CALLBACK =====

from handlers import load_users, save_users


async def buypl_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query
    if query is None:
        return

    parts = query.data.split(":")

    if len(parts) != 4:
        await query.answer("Invalid request.", show_alert=True)
        return

    #===== CHECK USER =====
    try:
        owner_id = int(parts[1])
    except ValueError:
        await query.answer("Invalid user.", show_alert=True)
        return

    if query.from_user.id != owner_id:
        await query.answer(
            "This purchase menu belongs to another user.",
            show_alert=True,
        )
        return

    action = parts[2]
    card_id = parts[3]

    #===== LOAD CARD DATABASE =====
    try:
        with CARDS_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        cards = list(data.values()) if isinstance(data, dict) else data
        if not isinstance(cards, list):
            raise ValueError("Invalid card database")

    except (OSError, json.JSONDecodeError, ValueError):
        await query.answer(
            "Could not load the card database.",
            show_alert=True,
        )
        return

    card = next(
        (
            item for item in cards
            if isinstance(item, dict)
            and str(item.get("id")) == card_id
        ),
        None,
    )

    if card is None:
        await query.answer("Player not found.", show_alert=True)
        return

    #===== SELECT FORMAT =====
    if action == "format":
        await query.answer()
        from handlers import send_buypl_card

        await send_buypl_card(update, context, card, owner_id)
        return

    #===== LOAD USER DATA =====
    users = load_users()
    user_key = str(owner_id)

    if user_key not in users:
        await query.answer(
            "Start the bot first using /start.",
            show_alert=True,
        )
        return

    record = users[user_key]
    owned_cards = record.get("cards", [])

    #===== CHECK EXISTING OWNERSHIP =====
    already_owned = any(
        str(owned.get("id")) == str(card.get("id"))
        and str(owned.get("format", "")).casefold()
        == str(card.get("format", "")).casefold()
        for owned in owned_cards
    )

    if already_owned or action == "owned":
        await query.answer("You already own this card!", show_alert=True)
        return

    #===== CHECK VALUE =====
    try:
        value = int(card.get("value", 0))
        balance = int(record.get("jnventory", 0))
    except (TypeError, ValueError):
        await query.answer(
            "Invalid card value or balance.",
            show_alert=True,
        )
        return

    if value <= 0:
        await query.answer(
            "This card cannot be purchased right now.",
            show_alert=True,
        )
        return

    if action == "poor" or balance < value:
        await query.answer(
            f"Can't afford! You need {value:,} coins.",
            show_alert=True,
        )
        return

    if action != "buy":
        await query.answer("Invalid purchase action.", show_alert=True)
        return

    #===== COMPLETE PURCHASE =====
    record["jnventory"] = balance - value
    record.setdefault("cards", []).append(dict(card))
    users[user_key] = record
    save_users(users)

    #===== PURCHASE SUCCESS =====
    await query.answer("Purchase successful!", show_alert=True)

    from handlers import send_buypl_card
    await send_buypl_card(update, context, card, owner_id)

async def open_pack_callback(update, context):
    query = update.callback_query
    await query.answer("Mod BOT isko bhi nhi chodega 🤬", show_alert=True)
