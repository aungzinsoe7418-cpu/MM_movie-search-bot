import os
import logging
import threading

from http.server import BaseHTTPRequestHandler, HTTPServer

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

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()


def clean_tmbd_token(value):
    """
    Clean TMDB Read Access Token from Render Environment Variable.

    Handles:
    - Leading/trailing spaces
    - New lines
    - Accidental quotes
    - Accidental 'Bearer ' prefix
    """

    value = value.strip()

    # Remove accidental quotation marks
    if (
        len(value) >= 2
        and value[0] == '"'
        and value[-1] == '"'
    ):
        value = value[1:-1].strip()

    if (
        len(value) >= 2
        and value[0] == "'"
        and value[-1] == "'"
    ):
        value = value[1:-1].strip()

    # Remove accidental Bearer prefix
    if value.lower().startswith("bearer "):
        value = value[7:].strip()

    # Remove invisible whitespace/newlines
    value = "".join(value.split())

    return value


TMDB_TOKEN = clean_tmbd_token(
    os.getenv("TMDB_TOKEN", "")
)


TMDB_BASE_URL = "https://api.themoviedb.org/3"

TMDB_IMAGE_URL = (
    "https://image.tmdb.org/t/p/w500"
)


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    ),
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================================================
# RENDER HEALTH CHECK SERVER
# =========================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8",
        )

        self.end_headers()

        self.wfile.write(
            b"MM Movie Search Bot is running!"
        )

    def log_message(
        self,
        format,
        *args,
    ):
        return


def start_health_server():

    port = int(
        os.getenv(
            "PORT",
            "10000",
        )
    )

    server = HTTPServer(
        (
            "0.0.0.0",
            port,
        ),
        HealthHandler,
    )

    logger.info(
        "Health server running on port %s",
        port,
    )

    server.serve_forever()


# =========================================================
# TMDB API REQUEST
# =========================================================

async def tmdb_request(
    endpoint,
    params=None,
):

    if not TMDB_TOKEN:

        raise ValueError(
            "TMDB_TOKEN မတွေ့ပါ။"
        )

    headers = {
        "Authorization": (
            f"Bearer {TMDB_TOKEN}"
        ),
        "accept": "application/json",
    }

    async with httpx.AsyncClient(
        timeout=20
    ) as client:

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

async def search_movies(
    movie_name,
):

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

    return data.get(
        "results",
        [],
    )


# =========================================================
# GET MOVIE DETAILS
# =========================================================

async def get_movie_details(
    movie_id,
):

    params = {
        "language": "en-US",
    }

    return await tmdb_request(
        f"/movie/{movie_id}",
        params,
    )


# =========================================================
# /START
# =========================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "👨‍💻 Contact Developer",
                url=(
                    "https://t.me/"
                    "superraizo7"
                ),
            )
        ]
    ])

    text = (
        "🎬 <b>Welcome to "
        "MM Movie Search Bot!</b>\n\n"

        "ကြည့်လိုသော Movie ကို "
        "အောက်ပါပုံစံအတိုင်း ရိုက်ထည့်ပြီး "
        "ရှာဖွေနိုင်ပါတယ် 👇\n\n"

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

        "💡 <b>Movie Title ကို "
        "English လို ရိုက်ထည့်ပေးပါ။</b>"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


# =========================================================
# /HELP
# =========================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    text = (
        "🎬 <b>MM Movie Search Bot</b>\n\n"

        "Movie ရှာရန်:\n\n"

        "<code>/interstellar</code>\n"
        "<code>/inception</code>\n"
        "<code>/avatar</code>\n\n"

        "Movie Title ကို English လို "
        "ရိုက်ထည့်ပါ။"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
    )


# =========================================================
# MOVIE COMMAND
# =========================================================

async def movie_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message:
        return

    if not update.message.text:
        return

    command_text = (
        update.message.text.strip()
    )

    if not command_text.startswith("/"):
        return

    # Remove /
    movie_name = (
        command_text[1:].strip()
    )

    # Remove @botusername if present
    if "@" in movie_name:

        movie_name = (
            movie_name
            .split("@", 1)[0]
            .strip()
        )

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

    searching_message = (
        await update.message.reply_text(
            "🔎 <b>Movie ရှာနေပါတယ်...</b>",
            parse_mode="HTML",
        )
    )

    try:

        movies = await search_movies(
            movie_name
        )

        if not movies:

            await searching_message.edit_text(
                f"❌ <b>{movie_name}</b> "
                "ကို မတွေ့ပါဘူး။\n\n"

                "Movie title ကို English လို "
                "ပြန်စမ်းကြည့်ပါ။",
                parse_mode="HTML",
            )

            return

        # Show first 5 results
        movies = movies[:5]

        keyboard = []

        for index, movie in enumerate(
            movies
        ):

            movie_id = movie.get(
                "id"
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

            button_text = (
                f"{index + 1}️⃣ "
                f"{title} ({year}) "
                f"⭐ {rating:.1f}"
            )

            keyboard.append([
                InlineKeyboardButton(
                    button_text,
                    callback_data=(
                        f"movie:{movie_id}"
                    ),
                )
            ])

        text = (
            "🔎 <b>Search Results</b>\n\n"

            f"Search: "
            f"<code>{movie_name}</code>\n\n"

            "မှန်ကန်တဲ့ Movie ကို "
            "ရွေးပါ 👇"
        )

        await searching_message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=(
                InlineKeyboardMarkup(
                    keyboard
                )
            ),
        )

    except httpx.HTTPStatusError as error:

        logger.error(
            "TMDB HTTP error: %s",
            error,
        )

        status_code = (
            error.response.status_code
            if error.response
            else "Unknown"
        )

        if status_code == 401:

            error_text = (
                "⚠️ TMDB Token "
                "မမှန်ကန်ပါ။\n\n"
                "Render Environment Variables "
                "ထဲက TMDB_TOKEN ကို "
                "စစ်ဆေးပါ။"
            )

        elif status_code == 429:

            error_text = (
                "⚠️ TMDB API request "
                "limit ရောက်နေပါတယ်။ "
                "ခဏစောင့်ပြီး ပြန်စမ်းပါ။"
            )

        else:

            error_text = (
                "⚠️ TMDB API နဲ့ "
                "ချိတ်ဆက်ရာမှာ ပြဿနာဖြစ်နေပါတယ်။"
            )

        await searching_message.edit_text(
            error_text
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

            overview = (
                "Overview မရှိပါ။"
            )

        poster_path = movie.get(
            "poster_path"
        )

        text = (
            f"🎬 <b>{title}</b>\n\n"

            f"📅 Year: "
            f"<b>{year}</b>\n"

            f"⭐ Rating: "
            f"<b>{rating:.1f}/10</b>\n\n"

            "📝 <b>Overview</b>\n"
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
                    callback_data=(
                        f"subtitle:mm:{movie_id}"
                    ),
                ),
                InlineKeyboardButton(
                    "🇬🇧 English",
                    callback_data=(
                        f"subtitle:en:{movie_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    "👨‍💻 Contact Developer",
                    url=(
                        "https://t.me/"
                        "superraizo7"
                    ),
                )
            ],
        ])

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
                chat_id=(
                    query.message.chat_id
                ),
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
# MAIN
# =========================================================

def main():

    # -----------------------------------------------------
    # Environment Variables Check
    # -----------------------------------------------------

    if not BOT_TOKEN:

        raise ValueError(
            "BOT_TOKEN မတွေ့ပါ။ "
            "Render Environment Variables "
            "ကို စစ်ဆေးပါ။"
        )

    if not TMDB_TOKEN:

        raise ValueError(
            "TMDB_TOKEN မတွေ့ပါ။ "
            "Render Environment Variables "
            "ကို စစ်ဆေးပါ။"
        )

    # -----------------------------------------------------
    # Render Health Server
    # -----------------------------------------------------

    health_thread = threading.Thread(
        target=start_health_server,
        daemon=True,
    )

    health_thread.start()

    # -----------------------------------------------------
    # Telegram Application
    # -----------------------------------------------------

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # -----------------------------------------------------
    # /start
    # -----------------------------------------------------

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    # -----------------------------------------------------
    # /help
    # -----------------------------------------------------

    application.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    # -----------------------------------------------------
    # Movie Commands
    #
    # /interstellar
    # /inception
    # /avatar
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.COMMAND,
            movie_command,
        )
    )

    # -----------------------------------------------------
    # Movie Result Button
    # -----------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            movie_selected,
            pattern=r"^movie:",
        )
    )

    # -----------------------------------------------------
    # Subtitle Button
    # -----------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            subtitle_button,
            pattern=r"^subtitle:",
        )
    )

    # -----------------------------------------------------
    # Start Bot
    # -----------------------------------------------------

    logger.info(
        "🎬 MM Movie Search Bot Started"
    )

    application.run_polling()


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()
