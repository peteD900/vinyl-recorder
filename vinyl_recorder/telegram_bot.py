"""
Telegram bot for identifying and adding vinyl albums to collection.
"""

import base64
from datetime import datetime
import json

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from vinyl_recorder.config import Config
from vinyl_recorder.vinyl_cover_identifier import VinylIdentifier
from vinyl_recorder.album_enricher import AlbumEnricher
from vinyl_recorder.collection_tracker import CollectionTracker
from vinyl_recorder.database import AlbumRepository
from vinyl_recorder.album_recommender import AlbumRecommender

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Silence noisy third-party libraries (prevents token exposure)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Your app logger
logger = logging.getLogger(__name__)


class VinylBot:
    def __init__(
        self,
        repo: AlbumRepository,
        identifier: VinylIdentifier,
        enricher: AlbumEnricher,
        tracker: CollectionTracker,
        recommender: AlbumRecommender,
    ):
        self.repo = repo
        self.identifier = identifier
        self.enricher = enricher
        self.tracker = tracker
        self.recommender = recommender
        self.bot_token = Config.bot_token()
        self.pending_photos = {}  # {user_id: {image data and results}}

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        await update.message.reply_text(
            "🎵 *Vinyl Collection Bot* 🎵\n\n"
            "Send a photo of an album cover to identify it with an LLM.\n"
            "The album can then be added to your collection.\n\n"
            "Commands:\n"
            "/start - Show this message\n"
            "/recommend - Recommend albums with 'distance' similarity metric.\n",
            parse_mode="Markdown",
        )

    async def recommend_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """
        Starts the album recommendation flow.
        Sends inline buttons to choose recommendation distance.
        """

        keyboard = [
            [
                InlineKeyboardButton("🎯 Very close (2)", callback_data="distance:2"),
                InlineKeyboardButton("🙂 Close (4)", callback_data="distance:4"),
            ],
            [
                InlineKeyboardButton("😐 Balanced (6)", callback_data="distance:6"),
                InlineKeyboardButton("🤪 Adventurous (8)", callback_data="distance:8"),
            ],
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "How adventurous should the recommendations be?",
            reply_markup=reply_markup,
        )

    async def handle_recommend(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Handle recommendation distance selection."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id

        _, distance = query.data.split(":")
        distance = int(distance)

        await query.edit_message_text("🔍 Recommending albums.. please wait")

        logger.info(f"Recommending albums for user {user_id}")

        results = self.recommender.recommend_albums(
            taste_distance=distance, n_suggestions=5
        )

        albums = self.recommender.parse_albums(results)

        message = "Recommended Albums:\n\n"
        message += albums

        await query.edit_message_text(message)

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming photo - ask if user wants to identify."""
        user_id = update.effective_user.id

        # Get the largest photo size
        photo = update.message.photo[-1]

        # Download photo
        photo_file = await photo.get_file()
        photo_bytes = await photo_file.download_as_bytearray()

        # Convert to base64
        image_base64 = base64.b64encode(photo_bytes).decode("utf-8")

        # Generate image name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_name = f"telegram_{timestamp}.jpg"

        # Store temporarily
        self.pending_photos[user_id] = {
            "image_base64": image_base64,
            "image_name": image_name,
            "timestamp": datetime.now(),
        }

        # Create inline keyboard
        keyboard = [
            [
                InlineKeyboardButton("🎵 Yes, identify", callback_data="identify_yes"),
                InlineKeyboardButton("❌ No", callback_data="identify_no"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🎸 Got your album cover!\n\nShould I identify this album?",
            reply_markup=reply_markup,
        )

    async def handle_identify_yes(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """User clicked Yes - run identification and enrichment."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id

        # Check if we have pending photo
        if user_id not in self.pending_photos:
            await query.edit_message_text("❌ No pending photo. Please send a new one.")
            return

        pending = self.pending_photos[user_id]

        # Show processing message
        await query.edit_message_text("🔍 Identifying album... please wait")

        try:
            # Step 1: Identify with LLM
            logger.info(f"Identifying album for user {user_id}")
            vinyl_data = self.identifier.identify(image_base64=pending["image_base64"])

            if not vinyl_data.success:
                await query.edit_message_text(
                    "❌ Could not identify the album.\n"
                    "Try a clearer photo with better lighting?"
                )
                del self.pending_photos[user_id]
                return

            # Update message
            await query.edit_message_text(
                f"✓ Identified as {vinyl_data.artist} - {vinyl_data.album_title}\n"
                f"🔍 Looking up details..."
            )

            # Step 2: Check for duplicate
            if self.repo.is_duplicate(vinyl_data.artist, vinyl_data.album_title):
                await query.edit_message_text(
                    f"⚠️ *You already have this album!*\n\n"
                    f"Artist: {vinyl_data.artist}\n"
                    f"Album: {vinyl_data.album_title}",
                    parse_mode="Markdown",
                )
                del self.pending_photos[user_id]
                return

            # Step 3: Enrich with MusicBrainz + LLM
            logger.info(
                f"Enriching: {vinyl_data.artist} - {vinyl_data.album_title}"
            )
            enrichment_data = self.enricher.fetch_enrichment(
                artist=vinyl_data.artist,
                album=vinyl_data.album_title,
                album_year=vinyl_data.album_year,
            )

            # Store results
            pending["vinyl_data"] = vinyl_data
            pending["enrichment_data"] = enrichment_data

            # Format results message
            message = self.format_results_message(vinyl_data, enrichment_data)

            # Create confirmation keyboard
            keyboard = [
                [
                    InlineKeyboardButton(
                        "✅ Add to Collection", callback_data="confirm_add"
                    ),
                    InlineKeyboardButton("❌ Cancel", callback_data="confirm_cancel"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                message, reply_markup=reply_markup, parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Error identifying album: {e}")
            await query.edit_message_text(
                f"❌ Error during identification: {str(e)}\nPlease try again."
            )
            if user_id in self.pending_photos:
                del self.pending_photos[user_id]

    async def handle_identify_no(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """User clicked No - cancel identification."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id

        if user_id in self.pending_photos:
            del self.pending_photos[user_id]

        await query.edit_message_text("❌ Cancelled. Send another photo anytime!")

    async def handle_confirm_add(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """User confirmed - add to collection."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id

        if user_id not in self.pending_photos:
            await query.edit_message_text("❌ No pending album. Please start over.")
            return

        pending = self.pending_photos[user_id]
        vinyl_data = pending["vinyl_data"]
        enrichment_data = pending.get("enrichment_data")

        # Show processing message
        await query.edit_message_text("🔍 Adding to collection... please wait")

        try:
            # Add to tracker (this adds identification data to DB)
            logger.info(
                f"Adding to collection: {vinyl_data.artist} - {vinyl_data.album_title}"
            )
            self.tracker.add_result_telegram(
                image_name=pending["image_name"], result=vinyl_data
            )

            # If we have enrichment data, save it immediately
            if enrichment_data:
                album_row = self.repo.find_by_image_name(pending["image_name"])
                if album_row:
                    updates = {}
                    if enrichment_data.image_url:
                        updates["cover_image_url"] = enrichment_data.image_url
                    if enrichment_data.tracklist:
                        updates["tracklist"] = json.dumps(enrichment_data.tracklist)
                    if updates:
                        self.repo.update_album(album_row["id"], updates)

            # Success message
            success_msg = (
                f"✅ *Added to your collection!*\n\n"
                f"🎸 Artist: {vinyl_data.artist}\n"
                f"💿 Album: {vinyl_data.album_title}\n"
                f"📅 Year: {vinyl_data.album_year or 'Unknown'}\n"
            )

            if enrichment_data and enrichment_data.image_url:
                success_msg += f"\n[Album cover]({enrichment_data.image_url})"

            await query.edit_message_text(success_msg, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error adding to collection: {e}")
            await query.edit_message_text(
                f"❌ Error adding to collection: {str(e)}\n"
                "Please try again or add manually."
            )
        finally:
            # Clean up
            if user_id in self.pending_photos:
                del self.pending_photos[user_id]

    async def handle_confirm_cancel(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """User cancelled - discard results."""
        query = update.callback_query
        await query.answer()
        user_id = update.effective_user.id

        if user_id in self.pending_photos:
            del self.pending_photos[user_id]

        await query.edit_message_text("❌ Cancelled. Send another photo anytime!")

    def format_results_message(self, vinyl_data, enrichment_data):
        """Format identification results for display."""
        message = "🎸 *Found Album:*\n\n"
        message += f"🎤 Artist: {vinyl_data.artist}\n"
        message += f"💿 Album: {vinyl_data.album_title}\n"
        message += f"📅 Year: {vinyl_data.album_year or 'Unknown'}\n"
        message += f"✨ Confidence: {vinyl_data.confidence}\n"

        if enrichment_data and enrichment_data.tracklist:
            tracks = "Tracks:\n"
            for track in enrichment_data.tracklist:
                tracks += f"{track}\n"

            message += "\n📀 *Enrichment Info:*\n"
            message += tracks
        else:
            message += "\n⚠️ Could not find enrichment data\n"

        message += "\nAdd this to your collection?"

        return message

    async def post_init(self, application):
        """Set bot commands after initialization."""
        await application.bot.set_my_commands(
            [
                BotCommand("start", "Help / list commands"),
                BotCommand("recommend", "Recommend albums to buy"),
            ]
        )

    def start(self):
        """Start the bot."""
        logger.info("Starting Vinyl Bot...")

        # Create application
        application = Application.builder().token(self.bot_token).build()

        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("recommend", self.recommend_command))

        application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))

        # Callback handlers for buttons
        application.add_handler(
            CallbackQueryHandler(self.handle_identify_yes, pattern="^identify_yes$")
        )
        application.add_handler(
            CallbackQueryHandler(self.handle_identify_no, pattern="^identify_no$")
        )
        application.add_handler(
            CallbackQueryHandler(self.handle_confirm_add, pattern="^confirm_add$")
        )
        application.add_handler(
            CallbackQueryHandler(self.handle_confirm_cancel, pattern="^confirm_cancel$")
        )

        # Callback for recommender
        application.add_handler(
            CallbackQueryHandler(self.handle_recommend, pattern="^distance")
        )

        # list handlers with /
        application.post_init = self.post_init

        # Start polling
        logger.info("Bot is running... Press Ctrl+C to stop")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    # Initialize components
    repo = AlbumRepository()
    identifier = VinylIdentifier()
    enricher = AlbumEnricher(repo=repo)
    tracker = CollectionTracker(repo=repo, source="telegram")
    recommender = AlbumRecommender(repo=repo)

    # Start bot
    bot = VinylBot(
        repo=repo,
        identifier=identifier,
        enricher=enricher,
        tracker=tracker,
        recommender=recommender,
    )
    bot.start()
