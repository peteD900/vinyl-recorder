"""Shared fixtures for vinyl_recorder tests."""

import os
import pytest

# Set test environment before any vinyl_recorder imports
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("GOOGLE_SERVICE_ACCOUNT", "dGVzdA==")  # base64("test")
os.environ.setdefault("VINYL_SHEET_TEST", "test-sheet-id")
os.environ.setdefault("BOT_TOKEN_TEST", "test-bot-token")
os.environ.setdefault("DISCOGS_API_KEY", "test-discogs-key")
