import os
import logging
import re

import httpx
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_TOKEN = os.getenv("TMDB_TOKEN")

TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_MOVIE_URL = "https://api.themoviedb.org/3/movie"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# TMDB SEARCH
# =========================================================

async def search_movies(movie_name: str):

    headers = {
        "Authorization": f"Bearer {TMDB_TOKEN}",
        "accept": "application/json",
    }

    params = {
        "query": movie_name,
        "language": "en-US",
        "include_adult": "false",
        "page": 1,
    }

    async with httpx.AsyncClient(timeout=20) as client:

        response = await client.get(
            TMDB_SEARCH_URL,
            headers=headers,
            params=params,
        )

        response.raise_for_status()

        data = response.json()

    return data.get("results", [])


# =========================================================
# MOVIE DETAILS
# =========================================================

async def get_movie_details(movie_id: int):

    headers = {
        "Authorization": f"Bearer {TMDB_TOKEN}",
        "accept": "application/json",
    }

    params = {
        "language": "en-US",
    }

    async with httpx.AsyncClient(timeout=20) as client:

        response = await client.get(
            f"{TMDB_MOVIE_URL}/{movie_id}",
            headers=headers,
            params=params,
        )

        response.raise_for_status()

        return response.json()


# =========================================================
# START
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

        "ကြည့်ရှုလိုသော Movie ကို အောက်ပါပုံစံအတိုင်း "
        "ရိုက်ထည့်ပြီး ရှာဖွေနိုင်ပါတယ် 👇\n\n"

        "📌 <b>အသုံးပြုပုံ</b>\n\n"

        "ဥပမာ —\n"
        "<code>/interstellar</code>\n\n"

        "ဒါမှမဟုတ်\n"
        "<code>/inception</code>\n\n"

        "🔎 Bot က Movie ကိုရှာပြီး —\n\n"

        "🎬 Movie Information\n"
        "📅 Release Year\n"
        "⭐ Rating\n"
        "📝 Overview\n"
        "🇲🇲 Myanmar Subtitle\n"
        "🇬🇧 English Subtitle\n\n"

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
# GENERIC MOVIE COMMAND
# =========================================================

async def movie_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message_text = update.message.text.strip()

    # / နောက်က movie title ကိုယူ
    movie_name = message_text[1:].strip()

    if not movie_name:

        await update.message.reply_text(
            "❌ Movie name ထည့်ပေးပါ။\n\n"
            "ဥပမာ:\n"
            "<code>/interstellar</code>",
            parse_mode="HTML",
        )

        return

    # Telegram command တွေကို movie search မလုပ်ရန်
    blocked_commands = {
        "start",
        "help",
        "settings",
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
                "Movie title ကို English လို ပြန်စမ်းကြည့်ပါ။",
                parse_mode="HTML",
            )

            return

        # ပထမဆုံး 5 ခုသာပြ
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
                f"{title} ({year}) ⭐ {rating:.1f}"
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
            "ကြည့်လိုသော Movie ကို ရွေးပါ 👇"
        )

        await searching_message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
        )

    except Exception:

        logger.exception(
            "Movie search error"
        )

        await searching_message.edit_text(
            "⚠️ Movie ရှာတဲ့အချိန် Error ဖြစ်သွားပါတယ်။\n\n"
            "ခဏနေပြီး ပြန်စမ်းကြည့်ပါ။"
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

    movie_id = int(
        query.data.split(":")[1]
    )

    try:

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
            "Overview မရှိပါ။",
        )

        poster_path = movie.get(
            "poster_path"
        )

        if not overview:
            overview = "Overview မရှိပါ။"

        text = (
            f"🎬 <b>{title}</b>\n"
            f"📅 Year: <b>{year}</b>\n"
            f"⭐ Rating: <b>{rating:.1f}/10</b>\n\n"

            f"📝 <b>Overview</b>\n"
            f"{overview}\n\n"

            "🇲🇲 Myanmar Subtitle: 🔎 Checking...\n"
            "🇬🇧 English Subtitle: 🔎 Checking..."
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

        if poster_path:

            poster_url = (
                TMDB_IMAGE_URL
                + poster_path
            )

            await query.message.delete()

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

    except Exception:

        logger.exception(
            "Movie details error"
        )

        await query.edit_message_text(
            "⚠️ Movie information ရယူလို့မရပါဘူး။"
        )


# =========================================================
# SUBTITLE LANGUAGE
# =========================================================

async def subtitle_language(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    parts = query.data.split(":")

    language = parts[1]
    movie_id = parts[2]

    if language == "mm":

        text = (
            "🇲🇲 <b>Myanmar Subtitle</b>\n\n"
            "🔎 Myanmar Subtitle ရှိ/မရှိ "
            "စစ်ဆေးနေပါတယ်..."
        )

    else:

        text = (
            "🇬🇧 <b>English Subtitle</b>\n\n"
            "🔎 English Subtitle ရှိ/မရှိ "
            "စစ်ဆေးနေပါတယ်..."
        )

    await query.message.reply_text(
        text,
        parse_mode="HTML",
    )


# =========================================================
# MAIN
# =========================================================

def main():

    if not BOT_TOKEN:

        raise ValueError(
            "BOT_TOKEN မတွေ့ပါ။ "
            "Render Environment Variables ကိုစစ်ပါ။"
        )

    if not TMDB_TOKEN:

        raise ValueError(
            "TMDB_TOKEN မတွေ့ပါ။ "
            "Render Environment Variables ကိုစစ်ပါ။"
        )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # /start
    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    # Any unknown /movie-name command
    application.add_handler(
        CommandHandler(
            ".*",
            movie_command,
        )
    )

    # Movie selection
    application.add_handler(
        CallbackQueryHandler(
            movie_selected,
            pattern=r"^movie:",
        )
    )

    # Subtitle selection
    application.add_handler(
        CallbackQueryHandler(
            subtitle_language,
            pattern=r"^subtitle:",
        )
    )

    logger.info(
        "🎬 Movie Search Bot Started"
    )

    application.run_polling()


if __name__ == "__main__":
    main()
