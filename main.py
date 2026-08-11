import os
import logging
import threading
from html import escape
from http.server import HTTPServer, BaseHTTPRequestHandler

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
    ContextTypes,
    MessageHandler,
    filters,
)


# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    "",
).strip()

TMDB_TOKEN = os.getenv(
    "TMDB_TOKEN",
    "",
).strip()

OPENSUBTITLES_API_KEY = os.getenv(
    "OPENSUBTITLES_API_KEY",
    "",
).strip()


TMDB_BASE_URL = (
    "https://api.themoviedb.org/3"
)

TMDB_IMAGE_URL = (
    "https://image.tmdb.org/t/p/w500"
)

OPENSUBTITLES_BASE_URL = (
    "https://api.opensubtitles.com/api/v1"
)


DEVELOPER_USERNAME = "superraizo7"

DEVELOPER_URL = (
    "https://t.me/superraizo7"
)


# Render PORT
DEFAULT_PORT = 10000


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
# RENDER HEALTH SERVER
# =========================================================

class HealthHandler(
    BaseHTTPRequestHandler
):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; "
            "charset=utf-8",
        )

        self.end_headers()

        self.wfile.write(
            b"MM Movie Search Bot is running!"
        )

    def do_HEAD(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; "
            "charset=utf-8",
        )

        self.end_headers()

    def log_message(
        self,
        format,
        *args,
    ):
        return


def start_web_server():

    port = int(
        os.environ.get(
            "PORT",
            DEFAULT_PORT,
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
        "Render health server started "
        "on port %s",
        port,
    )

    server.serve_forever()


# =========================================================
# COMMON HTTP CLIENT
# =========================================================

async def http_get_json(
    url,
    headers=None,
    params=None,
    timeout=20,
):

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
    ) as client:

        response = await client.get(
            url,
            headers=headers,
            params=params,
        )

        response.raise_for_status()

        return response.json()


# =========================================================
# TMDB API
# =========================================================

async def tmdb_request(
    endpoint,
    params=None,
):

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

    return await http_get_json(
        f"{TMDB_BASE_URL}{endpoint}",
        headers=headers,
        params=params,
    )


# =========================================================
# TMDB SEARCH
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
        params=params,
    )

    return data.get(
        "results",
        [],
    )


# =========================================================
# TMDB MOVIE DETAILS
# =========================================================

async def get_movie_details(
    movie_id,
):

    params = {
        "language": "en-US",
    }

    return await tmdb_request(
        f"/movie/{movie_id}",
        params=params,
    )


# =========================================================
# TMDB WATCH PROVIDERS
# =========================================================

async def get_watch_providers(
    movie_id,
):

    return await tmdb_request(
        f"/movie/{movie_id}/watch/providers"
    )


async def get_movie_watch_links(
    movie_id,
):

    data = await get_watch_providers(
        movie_id
    )

    results = data.get(
        "results",
        {},
    )

    # -----------------------------------------------------
    # Myanmar
    # -----------------------------------------------------

    country_data = results.get(
        "MM"
    )

    country_code = "MM"

    # -----------------------------------------------------
    # Fallback to US
    # -----------------------------------------------------

    if not country_data:

        country_data = results.get(
            "US"
        )

        country_code = "US"

    # -----------------------------------------------------
    # No provider
    # -----------------------------------------------------

    if not country_data:

        return {
            "country": None,
            "link": None,
            "flatrate": [],
            "rent": [],
            "buy": [],
        }

    return {
        "country": country_code,

        "link": country_data.get(
            "link"
        ),

        "flatrate": country_data.get(
            "flatrate",
            [],
        ),

        "rent": country_data.get(
            "rent",
            [],
        ),

        "buy": country_data.get(
            "buy",
            [],
        ),
    }


# =========================================================
# OPENSUBTITLES API
# =========================================================

async def search_opensubtitles(
    movie_title,
    year=None,
    language="en",
):

    if not OPENSUBTITLES_API_KEY:

        logger.warning(
            "OPENSUBTITLES_API_KEY "
            "is not configured."
        )

        return []

    headers = {

        "Api-Key":
            OPENSUBTITLES_API_KEY,

        "User-Agent":
            "MM-Movie-Search-Bot v1.0",

        "Accept":
            "application/json",
    }

    params = {

        "query":
            movie_title,

        "languages":
            language,

        "page":
            1,

        "per_page":
            10,
    }

    if year:

        params["year"] = year

    try:

        data = await http_get_json(
            (
                f"{OPENSUBTITLES_BASE_URL}"
                "/subtitles"
            ),
            headers=headers,
            params=params,
            timeout=20,
        )

        return data.get(
            "data",
            [],
        )

    except httpx.HTTPStatusError as error:

        logger.error(
            "OpenSubtitles HTTP error: %s",
            error,
        )

        return []

    except Exception:

        logger.exception(
            "OpenSubtitles error"
        )

        return []


# =========================================================
# CHECK SUBTITLE
# =========================================================

async def check_subtitle(
    movie_title,
    year,
    language,
):

    results = await search_opensubtitles(
        movie_title=movie_title,
        year=year,
        language=language,
    )

    if not results:

        return False, None

    return True, results[0]


# =========================================================
# SUBTITLE STATUS
# =========================================================

async def get_subtitle_status(
    movie_title,
    year,
):

    mm_found, mm_result = (
        await check_subtitle(
            movie_title,
            year,
            "my",
        )
    )

    en_found, en_result = (
        await check_subtitle(
            movie_title,
            year,
            "en",
        )
    )

    return {

        "mm_found":
            mm_found,

        "mm_result":
            mm_result,

        "en_found":
            en_found,

        "en_result":
            en_result,
    }


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
                url=DEVELOPER_URL,
            )
        ]
    ])

    text = (

        "🎬 "
        "<b>Welcome to "
        "MM Movie Search Bot!</b>"
        "\n\n"

        "ကြည့်လိုသော Movie ကို "
        "အောက်ပါပုံစံအတိုင်း "
        "ရိုက်ထည့်ပြီး "
        "ရှာဖွေနိုင်ပါတယ် 👇"
        "\n\n"

        "📌 <b>အသုံးပြုပုံ</b>"
        "\n\n"

        "ဥပမာ —\n"

        "<code>/interstellar</code>"
        "\n\n"

        "<code>/inception</code>"
        "\n\n"

        "<code>/avatar</code>"
        "\n\n"

        "🔎 Bot က Movie ကို "
        "အလိုအလျောက်ရှာပြီး —"
        "\n\n"

        "🎬 Movie Title\n"
        "🖼️ Poster\n"
        "📅 Release Year\n"
        "⭐ Rating\n"
        "📝 Overview\n"
        "🇲🇲 Myanmar Subtitle\n"
        "🇬🇧 English Subtitle\n"
        "🎬 Official Watch Provider\n\n"

        "တို့ကို ပြသပေးပါမယ်။"
        "\n\n"

        "💡 <b>Movie Title ကို "
        "English လို "
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

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "👨‍💻 Contact Developer",
                url=DEVELOPER_URL,
            )
        ]
    ])

    text = (

        "🎬 "
        "<b>MM Movie Search Bot</b>"
        "\n\n"

        "Movie ရှာရန် —\n"

        "<code>/movie name</code>"
        "\n\n"

        "ဥပမာ —\n"

        "<code>/interstellar</code>\n"
        "<code>/inception</code>\n"
        "<code>/avatar</code>\n\n"

        "Movie ကိုရွေးပြီးနောက် "
        "Subtitle availability နှင့် "
        "Official Watch Provider "
        "များကို စစ်ဆေးနိုင်ပါတယ်။"
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

    if not update.message:
        return

    command_text = (
        update.message.text or ""
    ).strip()

    if not command_text.startswith(
        "/"
    ):
        return

    movie_name = (
        command_text[1:]
        .strip()
    )

    if not movie_name:

        await update.message.reply_text(
            (
                "❌ Movie name "
                "ထည့်ပေးပါ။\n\n"
                "ဥပမာ:\n"
                "<code>/interstellar</code>"
            ),
            parse_mode="HTML",
        )

        return

    blocked_commands = {
        "start",
        "help",
    }

    if (
        movie_name.lower()
        in blocked_commands
    ):
        return

    searching_message = (
        await update.message.reply_text(
            "🔎 "
            "<b>Movie ရှာနေပါတယ်...</b>",
            parse_mode="HTML",
        )
    )

    try:

        movies = await search_movies(
            movie_name
        )

        if not movies:

            await searching_message.edit_text(
                (
                    f"❌ "
                    f"<b>{escape(movie_name)}</b> "
                    "ကို မတွေ့ပါဘူး။\n\n"

                    "Movie title ကို "
                    "English လို "
                    "ပြန်စမ်းကြည့်ပါ။"
                ),
                parse_mode="HTML",
            )

            return

        # First 5 results
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

                f"{title} "

                f"({year}) "

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

            "🔎 <b>Search Results</b>"
            "\n\n"

            f"Search: "
            f"<code>"
            f"{escape(movie_name)}"
            f"</code>"
            "\n\n"

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

        await searching_message.edit_text(
            "⚠️ TMDB API နဲ့ "
            "ချိတ်ဆက်ရာမှာ "
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
# WATCH PROVIDER BUTTON BUILDER
# =========================================================

def build_watch_provider_buttons(
    watch_data,
):

    rows = []

    provider_types = [
        (
            "flatrate",
            "📺 Stream",
        ),
        (
            "rent",
            "💳 Rent",
        ),
        (
            "buy",
            "🛒 Buy",
        ),
    ]

    added_provider_ids = set()

    for provider_type, label in (
        provider_types
    ):

        providers = watch_data.get(
            provider_type,
            [],
        )

        for provider in providers:

            provider_id = provider.get(
                "provider_id"
            )

            provider_name = provider.get(
                "provider_name",
                "Provider",
            )

            logo_path = provider.get(
                "logo_path"
            )

            # Avoid duplicate provider
            if provider_id in (
                added_provider_ids
            ):
                continue

            if provider_id is not None:

                added_provider_ids.add(
                    provider_id
                )

            link = watch_data.get(
                "link"
            )

            if not link:
                continue

            button_text = (
                f"{label}: "
                f"{provider_name}"
            )

            rows.append([
                InlineKeyboardButton(
                    button_text,
                    url=link,
                )
            ])

    return rows


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

    except Exception:

        await query.message.reply_text(
            "⚠️ Invalid movie selection."
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

        # =================================================
        # SUBTITLE
        # =================================================

        subtitle_status = (
            await get_subtitle_status(
                title,
                year,
            )
        )

        mm_found = subtitle_status[
            "mm_found"
        ]

        en_found = subtitle_status[
            "en_found"
        ]

        mm_status = (

            "✅ Available"

            if mm_found

            else "❌ Not Found"
        )

        en_status = (

            "✅ Available"

            if en_found

            else "❌ Not Found"
        )

        # =================================================
        # WATCH PROVIDERS
        # =================================================

        watch_data = (
            await get_movie_watch_links(
                movie_id
            )
        )

        provider_rows = (
            build_watch_provider_buttons(
                watch_data
            )
        )

        watch_country = (
            watch_data.get(
                "country"
            )
        )

        # =================================================
        # TEXT
        # =================================================

        text = (

            f"🎬 "
            f"<b>{escape(title)}</b>"
            "\n\n"

            f"📅 Year: "
            f"<b>{escape(year)}</b>"
            "\n"

            f"⭐ Rating: "
            f"<b>{rating:.1f}/10</b>"
            "\n\n"

            "📝 <b>Overview</b>"
            "\n"

            f"{escape(overview)}"
            "\n\n"

            f"🇲🇲 Myanmar Subtitle: "
            f"<b>{mm_status}</b>"
            "\n"

            f"🇬🇧 English Subtitle: "
            f"<b>{en_status}</b>"
        )

        # =================================================
        # KEYBOARD
        # =================================================

        keyboard_rows = []

        # -------------------------------------------------
        # Subtitle buttons
        # -------------------------------------------------

        if mm_found:

            keyboard_rows.append([
                InlineKeyboardButton(
                    "🇲🇲 Myanmar Subtitle",
                    callback_data=(
                        f"subtitle:mm:"
                        f"{movie_id}"
                    ),
                )
            ])

        if en_found:

            keyboard_rows.append([
                InlineKeyboardButton(
                    "🇬🇧 English Subtitle",
                    callback_data=(
                        f"subtitle:en:"
                        f"{movie_id}"
                    ),
                )
            ])

        # -------------------------------------------------
        # Watch providers
        # -------------------------------------------------

        if provider_rows:

            text += (
                "\n\n"
                "🎬 <b>Where to Watch</b>"
            )

            if watch_country:

                text += (
                    f"\n🌍 Region: "
                    f"<b>{watch_country}</b>"
                )

            keyboard_rows.extend(
                provider_rows
            )

        else:

            text += (
                "\n\n"
                "🎬 <b>Where to Watch</b>"
                "\n"
                "❌ ဒီ Region မှာ "
                "official provider မတွေ့ပါ။"
            )

        # -------------------------------------------------
        # Check Again
        # -------------------------------------------------

        keyboard_rows.append([
            InlineKeyboardButton(
                "🔄 Check Again",
                callback_data=(
                    f"check:{movie_id}"
                ),
            )
        ])

        # -------------------------------------------------
        # Developer
        # -------------------------------------------------

        keyboard_rows.append([
            InlineKeyboardButton(
                "👨‍💻 Contact Developer",
                url=DEVELOPER_URL,
            )
        ])

        keyboard = InlineKeyboardMarkup(
            keyboard_rows
        )

        # =================================================
        # SEND POSTER
        # =================================================

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

    except Exception:

        logger.exception(
            "Movie details error"
        )

        try:

            await query.edit_message_text(
                "⚠️ Movie information "
                "ရယူလို့ မရပါဘူး။"
            )

        except Exception:

            await query.message.reply_text(
                "⚠️ Movie information "
                "ရယူလို့ မရပါဘူး။"
            )


# =========================================================
# CHECK AGAIN
# =========================================================

async def check_again(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer(
        "Information ပြန်စစ်နေပါတယ်..."
    )

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

        # -------------------------------------------------
        # Subtitle
        # -------------------------------------------------

        status = (
            await get_subtitle_status(
                title,
                year,
            )
        )

        mm_found = status[
            "mm_found"
        ]

        en_found = status[
            "en_found"
        ]

        mm_status = (

            "✅ Available"

            if mm_found

            else "❌ Not Found"
        )

        en_status = (

            "✅ Available"

            if en_found

            else "❌ Not Found"
        )

        # -------------------------------------------------
        # Watch providers
        # -------------------------------------------------

        watch_data = (
            await get_movie_watch_links(
                movie_id
            )
        )

        provider_rows = (
            build_watch_provider_buttons(
                watch_data
            )
        )

        watch_country = (
            watch_data.get(
                "country"
            )
        )

        # -------------------------------------------------
        # Text
        # -------------------------------------------------

        text = (

            f"🎬 "
            f"<b>{escape(title)}</b>"
            "\n\n"

            f"📅 Year: "
            f"<b>{escape(year)}</b>"
            "\n"

            f"⭐ Rating: "
            f"<b>{rating:.1f}/10</b>"
            "\n\n"

            "📝 <b>Overview</b>"
            "\n"

            f"{escape(overview)}"
            "\n\n"

            f"🇲🇲 Myanmar Subtitle: "
            f"<b>{mm_status}</b>"
            "\n"

            f"🇬🇧 English Subtitle: "
            f"<b>{en_status}</b>"
        )

        keyboard_rows = []

        # -------------------------------------------------
        # Subtitle
        # -------------------------------------------------

        if mm_found:

            keyboard_rows.append([
                InlineKeyboardButton(
                    "🇲🇲 Myanmar Subtitle",
                    callback_data=(
                        f"subtitle:mm:"
                        f"{movie_id}"
                    ),
                )
            ])

        if en_found:

            keyboard_rows.append([
                InlineKeyboardButton(
                    "🇬🇧 English Subtitle",
                    callback_data=(
                        f"subtitle:en:"
                        f"{movie_id}"
                    ),
                )
            ])

        # -------------------------------------------------
        # Providers
        # -------------------------------------------------

        if provider_rows:

            text += (
                "\n\n"
                "🎬 <b>Where to Watch</b>"
            )

            if watch_country:

                text += (
                    f"\n🌍 Region: "
                    f"<b>{watch_country}</b>"
                )

            keyboard_rows.extend(
                provider_rows
            )

        else:

            text += (
                "\n\n"
                "🎬 <b>Where to Watch</b>"
                "\n"
                "❌ ဒီ Region မှာ "
                "official provider မတွေ့ပါ။"
            )

        # -------------------------------------------------
        # Check again
        # -------------------------------------------------

        keyboard_rows.append([
            InlineKeyboardButton(
                "🔄 Check Again",
                callback_data=(
                    f"check:{movie_id}"
                ),
            )
        ])

        # -------------------------------------------------
        # Developer
        # -------------------------------------------------

        keyboard_rows.append([
            InlineKeyboardButton(
                "👨‍💻 Contact Developer",
                url=DEVELOPER_URL,
            )
        ])

        keyboard = InlineKeyboardMarkup(
            keyboard_rows
        )

        # -------------------------------------------------
        # Caption edit
        # -------------------------------------------------

        if query.message.photo:

            await query.edit_message_caption(
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
            "Check again error"
        )

        await query.message.reply_text(
            "⚠️ Information ပြန်စစ်တဲ့အချိန် "
            "Error ဖြစ်သွားပါတယ်။"
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

    try:

        parts = query.data.split(":")

        language = parts[1]

        movie_id = int(
            parts[2]
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

        # -------------------------------------------------
        # Myanmar
        # -------------------------------------------------

        if language == "mm":

            found, result = (
                await check_subtitle(
                    title,
                    year,
                    "my",
                )
            )

            language_name = (
                "🇲🇲 Myanmar Subtitle"
            )

        # -------------------------------------------------
        # English
        # -------------------------------------------------

        else:

            found, result = (
                await check_subtitle(
                    title,
                    year,
                    "en",
                )
            )

            language_name = (
                "🇬🇧 English Subtitle"
            )

        # -------------------------------------------------
        # Not found
        # -------------------------------------------------

        if not found:

            await query.message.reply_text(
                (
                    f"{language_name}"
                    "\n\n"

                    "❌ <b>Not Found</b>"
                    "\n\n"

                    "OpenSubtitles မှာ "
                    "ဒီ Movie အတွက် "
                    "subtitle မတွေ့ပါ။"
                ),
                parse_mode="HTML",
            )

            return

        # -------------------------------------------------
        # Metadata
        # -------------------------------------------------

        attributes = (

            result.get(
                "attributes",
                {},
            )

            if result

            else {}
        )

        feature_details = (
            attributes.get(
                "feature_details",
                {},
            )
        )

        movie_title = (
            feature_details.get(
                "movie_name",
                title,
            )
        )

        release_year = (
            feature_details.get(
                "year",
                year,
            )
        )

        download_count = (
            attributes.get(
                "download_count",
                0,
            )
        )

        subtitle_text = (

            f"{language_name}"
            "\n\n"

            "✅ <b>Available</b>"
            "\n\n"

            f"🎬 Movie: "
            f"<b>"
            f"{escape(str(movie_title))}"
            f"</b>"
            "\n"

            f"📅 Year: "
            f"<b>"
            f"{escape(str(release_year))}"
            f"</b>"
            "\n"

            f"⬇️ Downloads: "
            f"<b>{download_count}</b>"
            "\n\n"

            "ℹ️ Subtitle availability ကို "
            "OpenSubtitles database မှ "
            "စစ်ဆေးထားပါတယ်။"
        )

        await query.message.reply_text(
            subtitle_text,
            parse_mode="HTML",
        )

    except Exception:

        logger.exception(
            "Subtitle button error"
        )

        await query.message.reply_text(
            "⚠️ Subtitle information "
            "ရယူတဲ့အချိန် "
            "Error ဖြစ်သွားပါတယ်။"
        )


# =========================================================
# UNKNOWN TEXT
# =========================================================

async def unknown_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not update.message:

        return

    text = (
        update.message.text or ""
    ).strip()

    if not text:

        return

    await update.message.reply_text(
        (
            "🎬 Movie ရှာရန်\n\n"

            "Movie title ကို "
            "ဒီလိုရိုက်ပါ 👇"
            "\n\n"

            "<code>/interstellar</code>\n"
            "<code>/inception</code>\n"
            "<code>/avatar</code>\n\n"

            "💡 Movie name တစ်ခုချင်းစီကို "
            "code ထဲ ကြိုထည့်ထားစရာ "
            "မလိုပါဘူး။"
        ),
        parse_mode="HTML",
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
    )


# =========================================================
# MAIN
# =========================================================

def main():

    # -----------------------------------------------------
    # Environment checks
    # -----------------------------------------------------

    if not BOT_TOKEN:

        raise ValueError(
            "BOT_TOKEN မတွေ့ပါ။ "
            "Render Environment Variables "
            "ကိုစစ်ပါ။"
        )

    if not TMDB_TOKEN:

        raise ValueError(
            "TMDB_TOKEN မတွေ့ပါ။ "
            "Render Environment Variables "
            "ကိုစစ်ပါ။"
        )

    if not OPENSUBTITLES_API_KEY:

        logger.warning(
            "OPENSUBTITLES_API_KEY "
            "မတွေ့ပါ။ "
            "Subtitle checking disabled."
        )

    # -----------------------------------------------------
    # Render Health Server
    # -----------------------------------------------------

    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True,
    )

    web_thread.start()

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
    # Arbitrary movie commands
    #
    # /interstellar
    # /avatar
    # /inception
    #
    # Movie names do NOT need to be
    # hard-coded.
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.COMMAND,
            movie_command,
        )
    )

    # -----------------------------------------------------
    # Movie selection
    # -----------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            movie_selected,
            pattern=r"^movie:",
        )
    )

    # -----------------------------------------------------
    # Subtitle
    # -----------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            subtitle_button,
            pattern=r"^subtitle:",
        )
    )

    # -----------------------------------------------------
    # Check again
    # -----------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            check_again,
            pattern=r"^check:",
        )
    )

    # -----------------------------------------------------
    # Normal text
    # -----------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            unknown_text,
        )
    )

    # -----------------------------------------------------
    # Error handler
    # -----------------------------------------------------

    application.add_error_handler(
        error_handler
    )

    # -----------------------------------------------------
    # Startup logs
    # -----------------------------------------------------

    logger.info(
        "========================================"
    )

    logger.info(
        "🎬 MM Movie Search Bot Started"
    )

    logger.info(
        "TMDB: Connected"
    )

    logger.info(
        "Watch Providers: Enabled"
    )

    logger.info(
        "OpenSubtitles: %s",
        (
            "Configured"
            if OPENSUBTITLES_API_KEY
            else "Not configured"
        ),
    )

    logger.info(
        "Render health server: Enabled"
    )

    logger.info(
        "========================================"
    )

    # -----------------------------------------------------
    # Telegram polling
    # -----------------------------------------------------

    application.run_polling(
        drop_pending_updates=True
    )


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()
