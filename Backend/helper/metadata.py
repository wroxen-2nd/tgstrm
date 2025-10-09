import asyncio
import traceback
import PTN

from Backend.helper.imdb import get_detail, get_season, search_title
from Backend.helper.pyro import extract_tmdb_id
from themoviedb import aioTMDb
from Backend.config import Telegram
import Backend
from Backend.logger import LOGGER
from Backend.helper.encrypt import encode_string

DELAY = 2
tmdb = aioTMDb(key=Telegram.TMDB_API, language="en-US", region="US")


# ----------------- Helpers -----------------
def format_tmdb_image(path: str, size="w500", fallback="https://i.ibb.co/mrfTVzyW/Screenshot-20251006-232731.png") -> str:
    return f"https://image.tmdb.org/t/p/{size}{path}" if path else fallback


def format_imdb_images(imdb_id: str) -> dict:
    return {
        "poster": f"https://images.metahub.space/poster/small/{imdb_id}/img",
        "backdrop": f"https://images.metahub.space/background/medium/{imdb_id}/img",
        "logo": f"https://images.metahub.space/logo/medium/{imdb_id}/img",
    }


async def safe_imdb_search(title: str, type_: str) -> str | None:
    try:
        result = await search_title(query=title, type=type_)
        return result["id"] if result else None
    except Exception as e:
        LOGGER.warning(f"IMDb search failed for '{title}' [{type_}]: {e}")
        return None


async def safe_tmdb_search(title: str, type_: str, year=None):
    try:
        if type_ == "movie":
            results = await tmdb.search().movies(query=title, year=year) if year else await tmdb.search().movies(query=title)
        else:
            results = await tmdb.search().tv(query=title)
        return results[0] if results else None
    except Exception as e:
        LOGGER.error(f"TMDb search failed for '{title}' [{type_}]: {e}")
        return None


# ----------------- Main -----------------
async def metadata(filename: str, channel: int, msg_id) -> dict | None:
    try:
        parsed = PTN.parse(filename)
    except Exception as e:
        LOGGER.error(f"PTN parsing failed for {filename}: {e}\n{traceback.format_exc()}")
        return None

    # Skip combined/invalid files
    if "excess" in parsed and any("combined" in item.lower() for item in parsed["excess"]):
        LOGGER.info(f"Skipping {filename}: contains 'combined'")
        return None

    title, season, episode, year, quality = (
        parsed.get("title"),
        parsed.get("season"),
        parsed.get("episode"),
        parsed.get("year"),
        parsed.get("resolution"),
    )

    if not quality:
        LOGGER.warning(f"Skipping {filename}: No resolution (parsed={parsed})")
        return None
    if isinstance(season, list) or isinstance(episode, list):
        LOGGER.warning(f"Invalid season/episode format for {filename}: {parsed}")
        return None
    if season and not episode:
        LOGGER.warning(f"Missing episode in {filename}: {parsed}")
        return None

    # Extract TMDb ID hints
    default_id = None
    try:
        default_id = extract_tmdb_id(Backend.USE_DEFAULT_ID)
    except Exception:
        pass
    if not default_id:
        try:
            default_id = extract_tmdb_id(filename)
        except Exception:
            pass

    if not title:
        LOGGER.info(f"No title parsed from: {filename} (parsed={parsed})")
        return None

    data = {"chat_id": channel, "msg_id": msg_id}
    encoded_string = await encode_string(data)
    

    try:
        if season and episode:
            LOGGER.info(f"Fetching TV metadata: {title} S{season}E{episode}")
            return await fetch_tv_metadata(title, season, episode, encoded_string, year, quality, default_id)
        else:
            LOGGER.info(f"Fetching Movie metadata: {title} ({year})")
            return await fetch_movie_metadata(title, encoded_string, year, quality, default_id)
    except Exception as e:
        LOGGER.error(f"Error while fetching metadata for {filename}: {e}\n{traceback.format_exc()}")
        return None


# ----------------- TV -----------------
async def fetch_tv_metadata(title, season, episode, encoded_string, year=None, quality=None, default_id=None) -> dict | None:
    imdb_id = default_id if default_id and default_id.startswith("tt") else await safe_imdb_search(title, "tvSeries")
    tv_details, ep_details, use_tmdb = None, None, False

    if imdb_id:
        try:
            await asyncio.sleep(DELAY)
            tv_details = await get_detail(imdb_id=imdb_id)
            await asyncio.sleep(DELAY)
            ep_details = await get_season(imdb_id=imdb_id, season_id=season, episode_id=episode)
        except Exception as e:
            LOGGER.warning(f"IMDb TV fetch failed [{imdb_id}]: {e}")

    if not tv_details and not ep_details:
        use_tmdb = True
        tmdb_result = await safe_tmdb_search(title, "tv")
        if not tmdb_result:
            return None
        tv_id = tmdb_result.id
        tv_details = await tmdb.tv(tv_id).details()
        ep_details = await tmdb.episode(tv_id, season, episode).details()

    if use_tmdb:
        return {
            "tmdb_id": tv_details.id,
            "imdb_id": "",
            "title": tv_details.name,
            "year": tv_details.first_air_date.year if tv_details.first_air_date else 0,
            "rate": tv_details.vote_average or 0,
            "description": tv_details.overview or "",
            "poster": format_tmdb_image(tv_details.poster_path),
            "backdrop": format_tmdb_image(tv_details.backdrop_path, "original"),
            "logo": "",
            "genres": [g.name for g in (tv_details.genres or [])],
            "media_type": "tv",
            "season_number": season,
            "episode_number": episode,
            "episode_title": getattr(ep_details, "name", f"S{season}E{episode}"),
            "episode_backdrop": format_tmdb_image(getattr(ep_details, "still_path", None), "original"),
            "quality": quality,
            "encoded_string": encoded_string,
        }

    imdb_id = tv_details.get("id", "")
    images = format_imdb_images(imdb_id)
    return {
        "tmdb_id": imdb_id.replace("tt", ""),
        "imdb_id": imdb_id,
        "title": tv_details.get("title", title),
        "year": tv_details.get("releaseDetailed", {}).get("year", 0),
        "rate": tv_details.get("rating", {}).get("star", 0),
        "description": tv_details.get("plot", ""),
        "poster": images["poster"],
        "backdrop": images["backdrop"],
        "logo": images["logo"],
        "genres": tv_details.get("genre", []),
        "media_type": "tv",
        "season_number": season,
        "episode_number": episode,
        "episode_title": ep_details.get("title", f"S{season}E{episode}") if ep_details else f"S{season}E{episode}",
        "episode_backdrop": ep_details.get("image", "") if ep_details else "https://i.ibb.co/mrfTVzyW/Screenshot-20251006-232731.png",
        "quality": quality,
        "encoded_string": encoded_string,
    }


# ----------------- Movie -----------------
async def fetch_movie_metadata(title, encoded_string, year=None, quality=None, default_id=None) -> dict | None:
    imdb_id = default_id if default_id and default_id.startswith("tt") else await safe_imdb_search(f"{title} {year}" if year else title, "movie")
    movie_details, use_tmdb = None, False

    if imdb_id:
        try:
            movie_details = await get_detail(imdb_id=imdb_id)
        except Exception as e:
            LOGGER.warning(f"IMDb movie fetch failed [{title}]: {e}")

    if not movie_details:
        use_tmdb = True
        tmdb_result = await safe_tmdb_search(title, "movie", year)
        if not tmdb_result:
            return None
        movie_details = await tmdb.movie(tmdb_result.id).details()

    if use_tmdb:
        return {
            "tmdb_id": movie_details.id,
            "imdb_id": "",
            "title": movie_details.title,
            "year": movie_details.release_date.year if movie_details.release_date else 0,
            "rate": movie_details.vote_average or 0,
            "description": movie_details.overview or "",
            "poster": format_tmdb_image(movie_details.poster_path),
            "backdrop": format_tmdb_image(movie_details.backdrop_path, "original"),
            "logo": "",
            "media_type": "movie",
            "genres": [g.name for g in (movie_details.genres or [])],
            "quality": quality,
            "encoded_string": encoded_string,
        }

    imdb_id = movie_details.get("id", "")
    images = format_imdb_images(imdb_id)
    return {
        "tmdb_id": imdb_id.replace("tt", ""),
        "imdb_id": imdb_id,
        "title": movie_details.get("title", title),
        "year": movie_details.get("releaseDetailed", {}).get("year", 0),
        "rate": movie_details.get("rating", {}).get("star", 0),
        "description": movie_details.get("plot", ""),
        "poster": images["poster"],
        "backdrop": images["backdrop"],
        "logo": images["logo"],
        "media_type": "movie",
        "genres": movie_details.get("genre", []),
        "quality": quality,
        "encoded_string": encoded_string,
    }
