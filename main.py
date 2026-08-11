import os
import logging
import html

import httpx

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
TMDB_TOKEN = os.getenv("TMDB_TOKEN", "").strip()
OPENSUBTITLES_API_KEY = os.getenv(
    "OPENSUBTITLES_API_KEY",
    "",
).strip()

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_URL = "https://image.tmdb.org/t/p/w500"

OPENSUBTITLES_BASE_URL = (
    "https://api.opensubtitles.com/api/v1"
)

OPENSUBTITLES_USER_AGENT = (
    "MMMovieSearchBot v1.0"
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
# TMDB API
# =========================================================

async def tmdb_request(
    endpoint,
    params=None,
):
    """
    TMDB API request.

    TMDB_TOKEN က Read Access Token ဖြစ်လို့
    Authorization: Bearer TOKEN ကို အသုံးပြုပါတယ်။
    """

    if not TMDB_TOKEN:
        raise RuntimeError(
            "TMDB_TOKEN is not configured."
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

    return data.get(
        "results",
        [],
    )


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
# OPENSUBTITLES API
# =========================================================

async def search_opensubtitles(
    movie_name,
    language,
    year=None,
):
    """
    OpenSubtitles subtitle search.

    language:
        my = Myanmar/Burmese
        en = English

    Returns:
        list
    """

    if not OPENSUBTITLES_API_KEY:
        logger.warning(
            "OPENSUBTITLES_API_KEY is not configured."
        )

        return []

    headers = {
        "Api-Key": OPENSUBTITLES_API_KEY,
        "User-Agent": OPENSUBTITLES_USER_AGENT,
        "Accept": "application/json",
    }

    params = {
        "query": movie_name,
        "languages": language,
    }

    if year:
        params["year"] = year

    try:

        async with httpx.AsyncClient(
            timeout=20
        ) as client:

            response = await client.get(
                f"{OPENSUBTITLES_BASE_URL}/subtitles",
                headers=headers,
                params=params,
            )

            response.raise_for_status()

            data = response.json()

            return data.get(
                "data",
                [],
            )

    except httpx.HTTPStatusError as error:

        status_code = (
            error.response.status_code
            if error.response
            else "unknown"
        )

        logger.error(
            "OpenSubtitles HTTP error: %s",
            status_code,
        )

        return []

    except Exception:

        logger.exception(
            "OpenSubtitles search error"
        )

        return []


# =========================================================
# CHECK SUBTITLE
# =========================================================

async def check_subtitle(
    movie_name,
    language,
    year=None,
):
    """
    Returns True if at least one subtitle
    result is found.
    """

    results = await search_opensubtitles(
        movie_name=movie_name,
        language=language,
        year=year,
    )

    return len(results) > 0


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

        "🇲🇲 Myanmar Subtitle ရှိ/မရှိ\n"
        "🇬🇧 English Subtitle ရှိ/မရှိ\n\n"

        "တို့ကို စစ်ဆေးပေးပါမယ်။\n\n"

        "💡 <b>Movie Title ကို English လို "
        "ရိုက်ထည့်ပေးပါ။</b>"
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard,
    )


# =========================================================
# HELP
# =========================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "🎬 <b>Movie Search Bot အသုံးပြုပုံ</b>\n\n"
        "Movie ရှာရန် —\n"
        "<code>/interstellar</code>\n\n"
        "<code>/inception</code>\n\n"
        "Movie title ကို English လို ရိုက်ထည့်ပါ။",
        parse_mode="HTML",
    )


# =========================================================
# GENERIC MOVIE COMMAND
# =========================================================

async def movie_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message:
        return

    command_text = (
        update.message.text.strip()
    )

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

            safe_name = html.escape(
                movie_name
            )

            await searching_message.edit_text(
                f"❌ <b>{safe_name}</b> ကို "
                "မတွေ့ပါဘူး။\n\n"
                "Movie title ကို English လို "
                "ပြန်စမ်းကြည့်ပါ။",
                parse_mode="HTML",
            )

            return

        # ပထမဆုံး result 5 ခု
        movies = movies[:5]

        keyboard = []

        for index, movie in enumerate(
            movies
        ):

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

            try:
                rating = float(rating)
            except (
                TypeError,
                ValueError,
            ):
                rating = 0.0

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

        safe_search = html.escape(
            movie_name
        )

        text = (
            "🔎 <b>Search Results</b>\n\n"
            f"Search: <code>{safe_search}</code>\n\n"
            "မှန်ကန်တဲ့ Movie ကို ရွေးပါ 👇"
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

        await searching_message.edit_text(
            "⚠️ TMDB API နဲ့ ချိတ်ဆက်ရာမှာ "
            "ပြဿနာဖြစ်နေပါတယ်။"
        )

    except Exception:

        logger.exception(
            "Movie search error"
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

    except (
        IndexError,
        ValueError,
    ):

        await query.answer(
            "Invalid movie.",
            show_alert=True,
        )

        return

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
            else None
        )

        year_text = (
            year
            if year
            else "N/A"
        )

        rating = movie.get(
            "vote_average",
            0,
        )

        try:
            rating = float(rating)
        except (
            TypeError,
            ValueError,
        ):
            rating = 0.0

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

        # -----------------------------------------
        # Subtitle Checking
        # -----------------------------------------

        subtitle_message = (
            "🔎 <b>Subtitle စစ်ဆေးနေပါတယ်...</b>"
        )

        initial_text = (
            f"🎬 <b>{html.escape(title)}</b>\n\n"
            f"📅 Year: <b>{year_text}</b>\n"
            f"⭐ Rating: <b>{rating:.1f}/10</b>\n\n"
            "📝 <b>Overview</b>\n"
            f"{html.escape(overview)}\n\n"
            f"{subtitle_message}"
        )

        # Temporary keyboard
        loading_keyboard = (
            InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "⏳ Checking...",
                        callback_data="checking",
                    )
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
        )

        # -----------------------------------------
        # Subtitle check
        # -----------------------------------------

        mm_subtitle = await check_subtitle(
            movie_name=title,
            language="my",
            year=year,
        )

        en_subtitle = await check_subtitle(
            movie_name=title,
            language="en",
            year=year,
        )

        mm_text = (
            "✅ Available"
            if mm_subtitle
            else "❌ Not Found"
        )

        en_text = (
            "✅ Available"
            if en_subtitle
            else "❌ Not Found"
        )

        text = (
            f"🎬 <b>{html.escape(title)}</b>\n\n"

            f"📅 Year: <b>{year_text}</b>\n"

            f"⭐ Rating: "
            f"<b>{rating:.1f}/10</b>\n\n"

            "📝 <b>Overview</b>\n"
            f"{html.escape(overview)}\n\n"

            f"🇲🇲 Myanmar Subtitle: "
            f"<b>{mm_text}</b>\n"

            f"🇬🇧 English Subtitle: "
            f"<b>{en_text}</b>"
        )

        keyboard = []

        # Myanmar button only if available
        if mm_subtitle:

            keyboard.append([
                InlineKeyboardButton(
                    "🇲🇲 Myanmar",
                    callback_data=(
                        f"subtitle:mm:{movie_id}"
                    ),
                )
            ])

        # English button only if available
        if en_subtitle:

            keyboard.append([
                InlineKeyboardButton(
                    "🇬🇧 English",
                    callback_data=(
                        f"subtitle:en:{movie_id}"
                    ),
                )
            ])

        keyboard.append([
            InlineKeyboardButton(
                "👨‍💻 Contact Developer",
                url=(
                    "https://t.me/"
                    "superraizo7"
                ),
            )
        ])

        reply_markup = (
            InlineKeyboardMarkup(
                keyboard
            )
        )

        # -----------------------------------------
        # Poster
        # -----------------------------------------

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
                reply_markup=reply_markup,
            )

        else:

            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )

    except Exception:

        logger.exception(
            "Movie details error"
        )

        try:

            await query.edit_message_text(
                "⚠️ Movie information ရယူလို့ "
                "မရပါဘူး။"
            )

        except Exception:

            pass


# =========================================================
# SUBTITLE BUTTON
# =========================================================

async def subtitle_button(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    try:

        parts = query.data.split(":")

        language = parts[1]

        movie_id = int(parts[2])

    except (
        IndexError,
        ValueError,
    ):

        await query.answer(
            "Invalid subtitle request.",
            show_alert=True,
        )

        return

    try:

        movie = await get_movie_details(
            movie_id
        )

        title = movie.get(
            "title",
            "Unknown",
        )

        if language == "mm":

            language_name = (
                "🇲🇲 Myanmar Subtitle"
            )

            language_code = "my"

        else:

            language_name = (
                "🇬🇧 English Subtitle"
            )

            language_code = "en"

        release_date = movie.get(
            "release_date",
            "",
        )

        year = (
            release_date[:4]
            if release_date
            else None
        )

        await query.message.reply_text(
            "🔎 <b>Subtitle ရှာနေပါတယ်...</b>",
            parse_mode="HTML",
        )

        results = await search_opensubtitles(
            movie_name=title,
            language=language_code,
            year=year,
        )

        if results:

            text = (
                f"{language_name}\n\n"
                f"🎬 <b>{html.escape(title)}</b>\n\n"
                "✅ <b>Available</b>\n\n"
                f"Subtitle result "
                f"{len(results)} ခုတွေ့ပါတယ်။"
            )

        else:

            text = (
                f"{language_name}\n\n"
                f"🎬 <b>{html.escape(title)}</b>\n\n"
                "❌ <b>Not Found</b>\n\n"
                "ဒီ Movie အတွက် ဒီ language "
                "နဲ့ subtitle မတွေ့ပါ။"
            )

        await query.message.reply_text(
            text,
            parse_mode="HTML",
        )

    except Exception:

        logger.exception(
            "Subtitle button error"
        )

        await query.message.reply_text(
            "⚠️ Subtitle ရှာတဲ့အချိန် "
            "Error ဖြစ်သွားပါတယ်။"
        )


# =========================================================
# TEXT MESSAGE
# =========================================================

async def text_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    """
    Customer က / မပါဘဲ movie title
    ရိုက်ထည့်ရင်လည်း ရှာပေးနိုင်အောင်
    """

    if not update.message:
        return

    text = update.message.text

    if not text:
        return

    text = text.strip()

    if not text:
        return

    # Command မဟုတ်ရင် movie search
    if not text.startswith("/"):

        await movie_search_by_text(
            update,
            context,
            text,
        )


# =========================================================
# MOVIE SEARCH BY NORMAL TEXT
# =========================================================

async def movie_search_by_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    movie_name,
):

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

            safe_name = html.escape(
                movie_name
            )

            await searching_message.edit_text(
                f"❌ <b>{safe_name}</b> ကို "
                "မတွေ့ပါဘူး။",
                parse_mode="HTML",
            )

            return

        movies = movies[:5]

        keyboard = []

        for index, movie in enumerate(
            movies
        ):

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

            try:
                rating = float(rating)
            except (
                TypeError,
                ValueError,
            ):
                rating = 0.0

            keyboard.append([
                InlineKeyboardButton(
                    (
                        f"{index + 1}️⃣ "
                        f"{title} ({year}) "
                        f"⭐ {rating:.1f}"
                    ),
                    callback_data=(
                        f"movie:{movie_id}"
                    ),
                )
            ])

        safe_name = html.escape(
            movie_name
        )

        await searching_message.edit_text(
            (
                "🔎 <b>Search Results</b>\n\n"
                f"Search: <code>{safe_name}</code>\n\n"
                "မှန်ကန်တဲ့ Movie ကို ရွေးပါ 👇"
            ),
            parse_mode="HTML",
            reply_markup=(
                InlineKeyboardMarkup(
                    keyboard
                )
            ),
        )

    except Exception:

        logger.exception(
            "Normal text movie search error"
        )

        await searching_message.edit_text(
            "⚠️ Movie ရှာတဲ့အချိန် "
            "Error ဖြစ်သွားပါတယ်။"
        )


# =========================================================
# ERROR HANDLER
# =========================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.error(
        "Unhandled exception: %s",
        context.error,
        exc_info=context.error,
    )


# =========================================================
# MAIN
# =========================================================

def main():

    # -----------------------------------------
    # Environment variable validation
    # -----------------------------------------

    if not BOT_TOKEN:

        raise ValueError(
            "BOT_TOKEN မတွေ့ပါ။ "
            "Render Environment Variables "
            "မှာ BOT_TOKEN ထည့်ပါ။"
        )

    if not TMDB_TOKEN:

        raise ValueError(
            "TMDB_TOKEN မတွေ့ပါ။ "
            "Render Environment Variables "
            "မှာ TMDB_TOKEN ထည့်ပါ။"
        )

    if not OPENSUBTITLES_API_KEY:

        logger.warning(
            "OPENSUBTITLES_API_KEY မတွေ့ပါ။ "
            "Subtitle checking မအလုပ်လုပ်နိုင်ပါ။"
        )

    # -----------------------------------------
    # Application
    # -----------------------------------------

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # -----------------------------------------
    # Commands
    # -----------------------------------------

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

    # -----------------------------------------
    # Movie commands
    #
    # IMPORTANT:
    # CommandHandler(".*") မသုံးပါ။
    # အဲဒါက invalid bot command ဖြစ်ပါတယ်။
    #
    # Regex command name မရတဲ့အတွက်
    # MessageHandler နဲ့ "/" စတဲ့
    # message တွေကို movie command အဖြစ်
    # handle လုပ်ပါတယ်။
    # -----------------------------------------

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & filters.Regex(r"^/[A-Za-z0-9].*"),
            movie_command,
        )
    )

    # -----------------------------------------
    # Normal text movie search
    # -----------------------------------------

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            text_message,
        )
    )

    # -----------------------------------------
    # Movie result button
    # -----------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            movie_selected,
            pattern=r"^movie:",
        )
    )

    # -----------------------------------------
    # Subtitle button
    # -----------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            subtitle_button,
            pattern=r"^subtitle:",
        )
    )

    # -----------------------------------------
    # Error handler
    # -----------------------------------------

    application.add_error_handler(
        error_handler
    )

    # -----------------------------------------
    # Startup log
    # -----------------------------------------

    logger.info(
        "======================================"
    )

    logger.info(
        "🎬 MM Movie Search Bot Started"
    )

    logger.info(
        "TMDB: ENABLED"
    )

    logger.info(
        "OpenSubtitles: %s",
        (
            "ENABLED"
            if OPENSUBTITLES_API_KEY
            else "DISABLED"
        ),
    )

    logger.info(
        "======================================"
    )

    # -----------------------------------------
    # Run
    # -----------------------------------------

    application.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()
