"""Shared fixtures for vinyl_recorder tests."""

import os

# Set test environment before any vinyl_recorder imports
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("BOT_TOKEN_TEST", "test-bot-token")
