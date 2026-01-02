# VPS (Production) - Without Helper Script:
# Start
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Stop
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# Rebuild and restart
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build