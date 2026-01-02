# Vinyl Collection Manager

Personal tool to catalogue vinyl records using album cover photos.

Album covers are identified via an LLM (single images, bulk local files, or via a Telegram bot). Metadata and tracklists are enriched from Discogs and stored in Google Sheets. A small FastAPI web app provides a basic UI.

Designed for local development or VPS deployment behind an Nginx reverse proxy. Assumes a personal setup.

## Requirements

- Google Cloud service account (Sheets API)
- OpenAI API key
- Discogs API token
- Telegram account (for bot)
- Optional: VPS with Nginx / Nginx Proxy Manager

## Setup

1. Clone the repo  
   git clone https://github.com/peteD900/vinyl-recorder.git  
   cd vinyl-recorder

2. Create a Google Sheet with these headers (exact order):  
   image_name | process_date | source | success | artist | album_title | album_year | confidence | discogs_title | image_url | tracklist

3. Create a Google Cloud service account, enable Sheets API, download the JSON key, and base64-encode it:  
   base64 -w 0 your-service-account.json > service-account.b64

4. Share the Google Sheet with the service account email (Editor access)

5. Create a Telegram bot via @BotFather and save the token

6. Create a `.env` file:

   APP_ENV=test  
   BOT_TOKEN=prod_bot_token  
   BOT_TOKEN_TEST=test_bot_token  
   OPENAI_API_KEY=sk-...  
   OPENAI_MODEL=gpt-4o  
   DISCOGS_API_KEY=discogs_token  
   GOOGLE_SERVICE_ACCOUNT=base64_service_account_json  
   VINYL_SHEET_TEST=test_sheet_id  
   VINYL_SHEET_PROD=prod_sheet_id  

## Run Locally

Docker:  
docker-compose up  

Web UI: http://localhost:8001

Without Docker:  
uv sync  
uvicorn vinyl_recorder.web_app:app --reload --port 8001  
python vinyl_recorder/telegram_bot.py

## Production (VPS)

docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

Use Nginx / Nginx Proxy Manager to forward traffic to the web container (port 8000) and enable SSL.

## Usage

Telegram:
- Send an album cover photo to the bot
- Confirm identification
- Add to collection

Bulk (local files):
- Set image path in config
- Run: python scripts/run_bulk_identification.py

## Notes

- Only one Telegram bot instance can run at a time
- Google Sheets must be shared with the service account email
