# to use
 - need google sheet with correct headers
  - add headers
 - need google service account and convert json to b64:

 base64 -w 0 python-projects-482809-a127ebd5b3d9.json > service-account.b64 

Copy the long string unquoted into .env

Following this need to add a folder in PERSONAL google drive e.g. python.
Then this needs sharing with the google account email looks like:
 dave-python@python-projects-11111.iam.gserviceaccount.com 

 - need telegram bot
  - add setup 
 - need discogs account and api toke
 - need openai account and api key
 - if want test mode (optional) need two keys for bot and two google sheets

 - need .env file with:


 # For switching google sheets
#APP_ENV=prod        
APP_ENV=test        

# TELEGRAM
BOT_TOKEN =
BOT_TOKEN_TEST = 

# LLM
OPENAI_API_KEY = 

# DISCOGS
DISCOGS_API_KEY = 

# GSHEETS
GOOGLE_SERVICE_ACCOUNT = 
VINYL_SHEET_TEST = 
VINYL_SHEET_PROD = 

git clone
docker compose up --build 
need -d?

      
# nginx setup

- subdomain from cloudflare
 - nginx reverse proxy port 8000 cotainer-name:port subdom.dom with ssl