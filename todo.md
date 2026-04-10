# todo

 - change collection tracker to use db: dont need this??
 - try running bulk upload script with test data
 - fun to make test db pre loaded?
 - update bot to use db

 # class info

  - llLLMClient: send requests to llm
  - VinylDatabase: db handler. Get all data, get discogs need, add new vinyl, add discog data
  - VinylIdentifier: takes in image, returns VinylIdentity = artist, album, year
  - DiscogsEnricher: takes in db. Search disogs specific aritst then add using db. Check all missing. Update all
  - 