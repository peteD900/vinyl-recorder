"""
Simple web app to display vinyl collection.
Run locally: uvicorn vinyl_recorder.web_app:app --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import json
from vinyl_recorder.database import AlbumRepository
from vinyl_recorder.config import get_logger

logger = get_logger()


def parse_tracklist(album: dict) -> list:
    """Parse tracklist JSON string into a list, returning [] on failure."""
    raw = album.get("tracklist")
    if not raw:
        return []
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and clean up the database connection."""
    app.state.repo = AlbumRepository()
    yield
    app.state.repo.close()


app = FastAPI(title="Katie's Vinyl Collection", lifespan=lifespan)

# Setup templates
templates = Jinja2Templates(directory="vinyl_recorder/templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main page showing the collection."""
    repo = request.app.state.repo
    albums = repo.get_all_albums()

    for album in albums:
        album["tracklist"] = parse_tracklist(album)
        # Map cover_image_url to image_url for template compatibility
        album["image_url"] = album.get("cover_image_url", "")

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"albums": albums, "total_count": len(albums)},
    )


@app.get("/api/albums")
async def get_albums(request: Request):
    """API endpoint to get albums as JSON."""
    repo = request.app.state.repo
    albums = repo.get_all_albums()

    for album in albums:
        album["tracklist"] = parse_tracklist(album)

    return {"albums": albums, "count": len(albums)}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
