"""
Web app to display and manage Katie's vinyl collection.
Includes public gallery and password-protected admin studio for AI identification,
recommendations, and collection management.
"""

from contextlib import asynccontextmanager
from datetime import datetime
import hashlib
import hmac
import json
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from vinyl_recorder.album_enricher import AlbumEnricher
from vinyl_recorder.album_recommender import AlbumRecommender
from vinyl_recorder.config import Config, get_logger
from vinyl_recorder.database import AlbumRepository
from vinyl_recorder.musicbrainz import CoverArtFetcher
from vinyl_recorder.vinyl_cover_identifier import VinylIdentifier

logger = get_logger()


# ==== PYDANTIC REQUEST SCHEMAS ==== #

class LoginRequest(BaseModel):
    password: str


class IdentifyRequest(BaseModel):
    image: str  # Base64 encoded image string (data URI or raw base64)


class AddAlbumRequest(BaseModel):
    artist: str
    album_title: str
    album_year: Optional[str] = ""
    cover_image_url: Optional[str] = ""
    tracklist: Optional[List[str]] = []
    confidence: Optional[str] = "high"
    force: Optional[bool] = False


class RecommendRequest(BaseModel):
    taste_distance: int = Field(default=5, ge=1, le=10)
    n_suggestions: int = Field(default=5, ge=1, le=10)


class ToBuyRequest(BaseModel):
    artist: str
    album_title: str
    album_year: Optional[str] = None
    notes: Optional[str] = None


# ==== AUTH HELPERS ==== #

def get_admin_token() -> str:
    """Generate deterministic session token for valid admin password."""
    return hmac.new(
        Config.SECRET_KEY.encode(),
        Config.ADMIN_PASSWORD.encode(),
        hashlib.sha256,
    ).hexdigest()


def is_admin(request: Request) -> bool:
    """Check if request has valid admin cookie or Bearer token."""
    cookie_token = request.cookies.get("admin_session")
    expected = get_admin_token()
    if cookie_token and hmac.compare_digest(cookie_token, expected):
        return True

    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth[7:].strip()
        if hmac.compare_digest(token, Config.ADMIN_PASSWORD) or hmac.compare_digest(token, expected):
            return True

    return False


def require_admin(request: Request):
    """Raise 401 if request is not authenticated as admin."""
    if not is_admin(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
        )


def parse_tracklist(album: dict) -> list:
    """Parse tracklist JSON string into a list, returning [] on failure."""
    raw = album.get("tracklist")
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return []


# ==== APP LIFECYCLE ==== #

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize repository and AI helper classes."""
    app.state.repo = AlbumRepository()
    try:
        app.state.identifier = VinylIdentifier()
    except Exception as e:
        logger.warning(f"Could not initialize VinylIdentifier at startup: {e}")
        app.state.identifier = None

    try:
        app.state.enricher = AlbumEnricher(repo=app.state.repo)
    except Exception as e:
        logger.warning(f"Could not initialize AlbumEnricher at startup: {e}")
        app.state.enricher = None

    try:
        app.state.recommender = AlbumRecommender(repo=app.state.repo)
    except Exception as e:
        logger.warning(f"Could not initialize AlbumRecommender at startup: {e}")
        app.state.recommender = None

    app.state.cover_fetcher = CoverArtFetcher()

    yield

    app.state.repo.close()


app = FastAPI(title="Katie's Vinyl Collection", lifespan=lifespan)
templates = Jinja2Templates(directory="vinyl_recorder/templates")


# ==== PUBLIC ROUTES ==== #

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Public page showing the entire collection."""
    repo = request.app.state.repo
    albums = repo.get_all_albums()

    for album in albums:
        album["tracklist"] = parse_tracklist(album)
        album["image_url"] = album.get("cover_image_url", "")

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "albums": albums,
            "total_count": len(albums),
            "is_admin": is_admin(request),
        },
    )


@app.get("/api/albums")
async def get_albums(request: Request):
    """API endpoint to get albums as JSON (public)."""
    repo = request.app.state.repo
    albums = repo.get_all_albums()

    for album in albums:
        album["tracklist"] = parse_tracklist(album)

    return {"albums": albums, "count": len(albums)}


@app.get("/api/to-buy")
async def get_to_buy(request: Request):
    """API endpoint to get the wishlist (public read)."""
    repo = request.app.state.repo
    items = repo.get_to_buy_list()
    return {"items": items, "count": len(items)}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# ==== AUTHENTICATION ROUTES ==== #

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page for admin studio."""
    if is_admin(request):
        return RedirectResponse(url="/admin", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(request=request, name="login.html", context={})


@app.post("/api/login")
async def login(payload: LoginRequest, response: Response):
    """Verify password and set 30-day session cookie."""
    if not hmac.compare_digest(payload.password, Config.ADMIN_PASSWORD):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )

    res = JSONResponse({"success": True, "message": "Logged in successfully"})
    res.set_cookie(
        key="admin_session",
        value=get_admin_token(),
        max_age=60 * 60 * 24 * 30,  # 30 days
        httponly=True,
        samesite="lax",
        secure=Config.APP_ENV == "prod",
    )
    return res


@app.post("/api/logout")
async def logout(response: Response):
    """Log out and clear session cookie."""
    res = JSONResponse({"success": True, "message": "Logged out"})
    res.delete_cookie(key="admin_session")
    return res


# ==== PROTECTED ADMIN ROUTES ==== #

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Admin studio for album photo upload, recommendations, and wishlist."""
    if not is_admin(request):
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    repo = request.app.state.repo
    albums = repo.get_all_albums()
    to_buy = repo.get_to_buy_list()

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "total_albums": len(albums),
            "total_to_buy": len(to_buy),
        },
    )


@app.post("/api/identify")
async def identify_album(payload: IdentifyRequest, request: Request):
    """
    AI Identification endpoint (Admin Only).
    Takes a base64 album cover photo, identifies with Claude,
    and enriches with MusicBrainz cover art and tracklist.
    """
    require_admin(request)

    identifier = request.app.state.identifier
    enricher = request.app.state.enricher
    repo = request.app.state.repo

    if not identifier:
        identifier = VinylIdentifier()
    if not enricher:
        enricher = AlbumEnricher(repo=repo)

    # Clean base64 string if data URI scheme was included
    image_data = payload.image
    if "," in image_data:
        image_data = image_data.split(",", 1)[1]

    try:
        vinyl_data = identifier.identify(image_base64=image_data)
    except Exception as e:
        logger.error(f"Error during AI identification: {e}")
        raise HTTPException(status_code=500, detail=f"Identification error: {str(e)}")

    if not vinyl_data.success:
        return {
            "success": False,
            "message": "Could not identify album cover. Try a clearer photo or enter details manually.",
        }

    is_duplicate = repo.is_duplicate(vinyl_data.artist, vinyl_data.album_title)

    # Enrich with MusicBrainz cover and LLM tracklist
    try:
        enrichment = enricher.fetch_enrichment(
            artist=vinyl_data.artist,
            album=vinyl_data.album_title,
            album_year=vinyl_data.album_year,
        )
        cover_image_url = enrichment.image_url
        tracklist = enrichment.tracklist
    except Exception as e:
        logger.warning(f"Enrichment error: {e}")
        cover_image_url = ""
        tracklist = []

    return {
        "success": True,
        "artist": vinyl_data.artist or "",
        "album_title": vinyl_data.album_title or "",
        "album_year": vinyl_data.album_year or "",
        "confidence": vinyl_data.confidence or "medium",
        "cover_image_url": cover_image_url,
        "tracklist": tracklist,
        "is_duplicate": is_duplicate,
    }


@app.post("/api/albums")
async def add_album(payload: AddAlbumRequest, request: Request):
    """Add a confirmed album to the collection database (Admin Only)."""
    require_admin(request)
    repo = request.app.state.repo

    artist = payload.artist.strip()
    album_title = payload.album_title.strip()

    # Prevent accidental duplicates unless user explicitly checked force
    if not payload.force and repo.is_duplicate(artist, album_title):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "success": False,
                "is_duplicate": True,
                "message": f"'{artist} - {album_title}' is already in your collection.",
            },
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    image_name = f"web_{timestamp}.jpg"

    album_data = {
        "image_name": image_name,
        "process_date": datetime.now().isoformat(timespec="seconds"),
        "source": "web",
        "success": 1,
        "artist": artist,
        "album_title": album_title,
        "album_year": payload.album_year.strip() if payload.album_year else "",
        "confidence": payload.confidence or "high",
        "cover_image_url": payload.cover_image_url or "",
        "tracklist": json.dumps(payload.tracklist) if payload.tracklist else "",
    }

    album_id = repo.add_album(album_data)

    # If album was on the to_buy list, remove it
    try:
        to_buy_items = repo.get_to_buy_list()
        for item in to_buy_items:
            if (
                item["artist"].lower() == artist.lower()
                and item["album_title"].lower() == album_title.lower()
            ):
                repo.remove_from_to_buy(item["id"])
    except Exception as e:
        logger.warning(f"Failed to check to_buy list cleanup: {e}")

    return {"success": True, "id": album_id, "message": "Album added to collection"}


@app.post("/api/deduplicate")
async def deduplicate(request: Request):
    """Find and remove redundant duplicate albums from the database (Admin Only)."""
    require_admin(request)
    repo = request.app.state.repo
    removed = repo.deduplicate_collection()
    return {
        "success": True,
        "count": len(removed),
        "removed": removed,
        "message": f"Removed {len(removed)} duplicate album(s).",
    }


@app.delete("/api/albums/{album_id}")
async def delete_album(album_id: int, request: Request):
    """Delete an album from the collection (Admin Only)."""
    require_admin(request)
    repo = request.app.state.repo
    repo.delete_album(album_id)
    return {"success": True, "message": f"Album {album_id} deleted"}


@app.post("/api/recommend")
async def recommend(payload: RecommendRequest, request: Request):
    """
    Get AI album recommendations based on existing collection (Admin Only).
    Also fetches cover art from MusicBrainz so cards look great.
    """
    require_admin(request)
    recommender = request.app.state.recommender
    repo = request.app.state.repo
    cover_fetcher = request.app.state.cover_fetcher

    if not recommender:
        recommender = AlbumRecommender(repo=repo)

    try:
        results = recommender.recommend_albums(
            taste_distance=payload.taste_distance,
            n_suggestions=payload.n_suggestions,
        )
    except Exception as e:
        logger.error(f"Error during recommendation: {e}")
        raise HTTPException(status_code=500, detail=f"Recommendation error: {str(e)}")

    output_albums = []
    for album in results.albums:
        cover_url = ""
        try:
            cover_url = cover_fetcher.fetch_cover_url(album.artist, album.album) or ""
        except Exception:
            pass

        output_albums.append({
            "artist": album.artist,
            "album": album.album,
            "cover_url": cover_url,
        })

    return {"success": True, "albums": output_albums}


@app.post("/api/to-buy")
async def add_to_buy_item(payload: ToBuyRequest, request: Request):
    """Add an item to the wishlist (Admin Only)."""
    require_admin(request)
    repo = request.app.state.repo

    if repo.is_on_buy_list(payload.artist, payload.album_title):
        return {"success": False, "message": "Already on your wishlist"}

    item_id = repo.add_to_buy(
        artist=payload.artist.strip(),
        album_title=payload.album_title.strip(),
        album_year=payload.album_year,
        notes=payload.notes,
    )
    return {"success": True, "id": item_id}


@app.delete("/api/to-buy/{item_id}")
async def remove_to_buy_item(item_id: int, request: Request):
    """Remove an item from the wishlist (Admin Only)."""
    require_admin(request)
    repo = request.app.state.repo
    repo.remove_from_to_buy(item_id)
    return {"success": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
