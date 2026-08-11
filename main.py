import os
import logging

import httpx

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_TOKEN = os.getenv("TMDB_TOKEN")

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# TMDB API
# =========================================================

async def tmdb_request(endpoint, params=None):
    if not TMDB_TOKEN:
        raise ValueError("TMDB_TOKEN မတွေ့ပါ။")

    headers = {
        "Authorization": f"Bearer {TMDB_TOKEN}",
        "accept": "application/json",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"{TMDB_BASE_URL}{endpoint}",
            headers=headers,
            params=params,
        )

        response.raise_for_status()

        return response.json()


# =========================================================
# SEARCH MOVIES
# =========================================================

async def search_movies(movie_name):
    params = {
        "query": movie_name,
        "language": "en-US",
        "include_adult": "false",
        "page": 1,
    }

    data = await tmdb_request(
        "/search/movie",
        params,
    )

    return data.get("results", [])


# =========================================================
# MOVIE DETAILS
# =========================================================

async def get_movie_details(movie_id):
    params = {
        "language": "en-US",
    }

    return await tmdb_request(
        f"/movie/{movie_id}",
        params,
    )


# =========================================================
# START COMMAND
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "👨‍💻 Contact Developer",
                url="https://t.me/superraizo7",
            )
        ]
    ])

    text = (
        "🎬 <b>Welcome to Movie Search Bot!</b>\n\n"

        "ကြည့်လိုသော Movie ကို အောက်ပါပုံစံအတိုင်း "
        "ရိုက်ထည့်ပြီး ရှာဖွေနိုင်ပါတယ် 👇\n\n"

        "📌 <b>အသုံးပြုပုံ</b>\n\n"

        "ဥပမာ —\n"
        "<code>/interstellar</code>\n\n"

        "<code>/inception</code>\n\n"

        "<code>/avatar</code>\n\n"

        "🔎 Bot က Movie ကိုရှာပြီး —\n\n"

        "🎬 Movie Title\n"
        "🖼️ Poster\n"
        "📅 Release Year\n"
        "⭐ Rating\n"
        "📝 Overview\n\n"

        "တို့ကို ပြသပေးပါမယ်။\n\n"

        "💡 <b>Movie Title ကို English လို "
        "ရိုက်ထည့်ပေးပါ။</b>"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


# =========================================================
# MOVIE COMMAND
# =========================================================

async def movie_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message or not update.message.text:
        return

    command_text = update.message.text.strip()

    # "/" ဖယ်ပြီး Movie title ရယူ
    movie_name = command_text[1:].strip()

    if not movie_name:
        await update.message.reply_text(
            "❌ Movie name ထည့်ပေးပါ။\n\n"
            "ဥပမာ:\n"
            "<code>/interstellar</code>",
            parse_mode="HTML",
        )
        return

    # System commands
    blocked_commands = {
        "start",
        "help",
    }

    if movie_name.lower() in blocked_commands:
        return

    searching_message = await update.message.reply_text(
        "🔎 <b>Movie ရှာနေပါတယ်...</b>",
        parse_mode="HTML",
    )

    try:

        movies = await search_movies(movie_name)

        if not movies:

            await searching_message.edit_text(
                f"❌ <b>{movie_name}</b> ကို မတွေ့ပါဘူး။\n\n"
                "Movie title ကို English လို "
                "ပြန်စမ်းကြည့်ပါ။",
                parse_mode="HTML",
            )

            return

        # ပထမဆုံး result 5 ခု
        movies = movies[:5]

        keyboard = []

        for index, movie in enumerate(movies):

            movie_id = movie.get("id")

            title = movie.get(
                "title",
                "Unknown",
            )

            release_date = movie.get(
                "release_date",
                "",
            )

            year = (
                release_date[:4]
                if release_date
                else "N/A"
            )

            rating = movie.get(
                "vote_average",
                0,
            )

            button_text = (
                f"{index + 1}️⃣ "
                f"{title} ({year}) "
                f"⭐ {rating:.1f}"
            )

            keyboard.append([
                InlineKeyboardButton(
                    button_text,
                    callback_data=f"movie:{movie_id}",
                )
            ])

        text = (
            "🔎 <b>Search Results</b>\n\n"
            f"Search: <code>{movie_name}</code>\n\n"
            "မှန်ကန်တဲ့ Movie ကို ရွေးပါ 👇"
        )

        await searching_message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
        )

    except httpx.HTTPStatusError as error:

        logger.error(
            "TMDB HTTP error: %s",
            error,
        )

        await searching_message.edit_text(
            "⚠️ TMDB API နဲ့ ချိတ်ဆက်ရာမှာ "
            "ပြဿနာဖြစ်နေပါတယ်။\n\n"
            "TMDB_TOKEN ကို စစ်ဆေးပေးပါ။"
        )

    except Exception as error:

        logger.exception(
            "Movie search error: %s",
            error,
        )

        await searching_message.edit_text(
            "⚠️ Movie ရှာတဲ့အချိန် "
            "Error ဖြစ်သွားပါတယ်။"
        )


# =========================================================
# MOVIE SELECTED
# =========================================================

async def movie_selected(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    try:

        movie_id = int(
            query.data.split(":")[1]
        )

        movie = await get_movie_details(
            movie_id
        )

        title = movie.get(
            "title",
            "Unknown",
        )

        release_date = movie.get(
            "release_date",
            "",
        )

        year = (
            release_date[:4]
            if release_date
            else "N/A"
        )

        rating = movie.get(
            "vote_average",
            0,
        )

        overview = movie.get(
            "overview",
            "",
        )

        if not overview:
            overview = "Overview မရှိပါ။"

        poster_path = movie.get(
            "poster_path"
        )

        text = (
            f"🎬 <b>{title}</b>\n\n"
            f"📅 Year: <b>{year}</b>\n"
            f"⭐ Rating: <b>{rating:.1f}/10</b>\n\n"

            f"📝 <b>Overview</b>\n"
            f"{overview}\n\n"

            "🇲🇲 Myanmar Subtitle: "
            "🔎 Checking...\n"

            "🇬🇧 English Subtitle: "
            "🔎 Checking..."
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🇲🇲 Myanmar",
                    callback_data=f"subtitle:mm:{movie_id}",
                ),
                InlineKeyboardButton(
                    "🇬🇧 English",
                    callback_data=f"subtitle:en:{movie_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "👨‍💻 Contact Developer",
                    url="https://t.me/superraizo7",
                )
            ],
        ])

        # Poster ရှိရင်
        if poster_path:

            poster_url = (
                TMDB_IMAGE_URL
                + poster_path
            )

            try:
                await query.message.delete()
            except Exception:
                pass

            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=poster_url,
                caption=text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

        else:

            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

    except httpx.HTTPStatusError as error:

        logger.error(
            "TMDB details HTTP error: %s",
            error,
        )

        await query.edit_message_text(
            "⚠️ Movie information ရယူရာမှာ "
            "TMDB API error ဖြစ်နေပါတယ်။"
        )

    except Exception as error:

        logger.exception(
            "Movie details error: %s",
            error,
        )

        await query.edit_message_text(
            "⚠️ Movie information ရယူလို့ "
            "မရပါဘူး။"
        )


# =========================================================
# SUBTITLE BUTTON
# =========================================================

async def subtitle_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    parts = query.data.split(":")

    if len(parts) < 3:
        return

    language = parts[1]

    if language == "mm":

        text = (
            "🇲🇲 <b>Myanmar Subtitle</b>\n\n"
            "🔎 Myanmar Subtitle ရှိ/မရှိ "
            "စစ်ဆေးမယ့် system ကို "
            "နောက်အဆင့်မှာ ထည့်မယ်။"
        )

    else:

        text = (
            "🇬🇧 <b>English Subtitle</b>\n\n"
            "🔎 English Subtitle ရှိ/မရှိ "
            "စစ်ဆေးမယ့် system ကို "
            "နောက်အဆင့်မှာ ထည့်မယ်။"
        )

    await query.message.reply_text(
        text,
        parse_mode="HTML",
    )


# =========================================================
# HELP COMMAND
# =========================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    text = (
        "🎬 <b>Movie Search Bot</b>\n\n"

        "Movie ရှာရန်:\n"
        "<code>/interstellar</code>\n\n"

        "<code>/inception</code>\n\n"

        "<code>/avatar</code>"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:
        raise ValueError(
            "BOT_TOKEN မတွေ့ပါ။"
        )

    if not TMDB_TOKEN:
        raise ValueError(
            "TMDB_TOKEN မတွေ့ပါ။"
        )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # =====================================================
    # COMMAND HANDLERS
    # =====================================================

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    # =====================================================
    # MOVIE COMMANDS
    # /interstellar
    # /avatar
    # /inception
    # =====================================================

    application.add_handler(
        MessageHandler(
            filters.COMMAND,
            movie_command,
        )
    )

    # =====================================================
    # CALLBACK HANDLERS
    # =====================================================

    application.add_handler(
        CallbackQueryHandler(
            movie_selected,
            pattern=r"^movie:",
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            subtitle_button,
            pattern=r"^subtitle:",
        )
    )

    # =====================================================
    # START BOT
    # =====================================================

    logger.info(
        "🎬 Movie Search Bot Started"
    )

    application.run_polling()


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()
