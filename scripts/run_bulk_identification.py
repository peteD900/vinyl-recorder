"""
Bulk identification and enrichment of local album images.
Run with: python scripts/run_bulk_identification.py
"""

from pathlib import Path
from pyprojroot import here
from vinyl_recorder.collection_tracker import CollectionTracker
from vinyl_recorder.vinyl_cover_identifier import VinylIdentifier
from vinyl_recorder.discogs import DiscogEnricher
from vinyl_recorder.ghseets import GoogleSheeter
from vinyl_recorder.config import get_logger

logger = get_logger()


def main():
    # Configuration
    LOCAL_WD = here()
    IMAGES_DIR = LOCAL_WD / "data/all_images"

    logger.info("Starting bulk identification and enrichment")
    logger.info(f"Images directory: {IMAGES_DIR}")

    # Initialize components
    sheeter = GoogleSheeter()
    tracker = CollectionTracker(sheeter=sheeter, images_path=IMAGES_DIR, source="local")
    identifier = VinylIdentifier()
    enricher = DiscogEnricher(sheeter=sheeter)

    # Step 1: Identification
    logger.info("Step 1: Identifying albums...")
    pending_list = tracker.get_pending_images()

    if len(pending_list) == 0:
        logger.info("No new images to process")
    else:
        logger.info(f"Found {len(pending_list)} images to identify")

        for i, image_path in enumerate(pending_list, 1):
            logger.info(f"[{i}/{len(pending_list)}] Processing: {image_path.name}")
            try:
                result = identifier.identify_image(image_path=image_path)
                tracker.add_result_local(image_path=image_path, result=result)
                logger.info(f"  ✓ Identified: {result.artist} - {result.album_title}")
            except Exception as e:
                logger.error(f"  ✗ Failed to identify {image_path.name}: {e}")

    # Step 2: Enrichment
    logger.info("\nStep 2: Enriching with Discogs data...")
    enricher.enrich_all_pending()

    logger.info(f"\n✓ Process complete!")
    logger.info(f"  Identified: {len(pending_list)} albums")


if __name__ == "__main__":
    main()
