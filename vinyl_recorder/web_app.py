"""
Simple web app to display vinyl collection.
Run locally: uvicorn vinyl_recorder.web_app:app --reload
"""

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import json
from vinyl_recorder.ghseets import GoogleSheeter
from vinyl_recorder.config import get_logger

logger = get_logger()

app = FastAPI(title="Katie's Vinyl Collection")

# Setup templates
templates = Jinja2Templates(directory="vinyl_recorder/templates")

# Initialize sheeter
sheeter = GoogleSheeter()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main page showing the collection."""
    # Get data from sheet
    df = sheeter.refresh_df()

    # Sort by artist (default)
    df = df.sort_values("artist", key=lambda x: x.str.lower())

    # Convert to list of dicts for template
    albums = df.to_dict("records")

    # Parse tracklist JSON strings
    for album in albums:
        if album.get("tracklist"):
            try:
                album["tracklist"] = json.loads(album["tracklist"])
            except:
                album["tracklist"] = []
        else:
            album["tracklist"] = []

    return templates.TemplateResponse(
        "index.html", {"request": request, "albums": albums, "total_count": len(albums)}
    )


@app.get("/api/albums")
async def get_albums():
    """API endpoint to get albums as JSON (for future use)."""
    df = sheeter.refresh_df()
    albums = df.to_dict("records")

    for album in albums:
        if album.get("tracklist"):
            try:
                album["tracklist"] = json.loads(album["tracklist"])
            except:
                album["tracklist"] = []

    return {"albums": albums, "count": len(albums)}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
