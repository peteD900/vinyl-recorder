"""Tests for Config environment switching and validation."""

import os
import pytest
from vinyl_recorder.config import Config


class TestConfigEnvSwitching:
    def test_db_path_prod(self):
        original = Config.APP_ENV
        try:
            Config.APP_ENV = "prod"
            assert str(Config.db_path()).endswith("vinyl_collection.db")
        finally:
            Config.APP_ENV = original

    def test_db_path_test(self):
        original = Config.APP_ENV
        try:
            Config.APP_ENV = "test"
            assert str(Config.db_path()).endswith("vinyl_collection_test.db")
        finally:
            Config.APP_ENV = original

    def test_db_path_invalid_env(self):
        original = Config.APP_ENV
        try:
            Config.APP_ENV = "invalid"
            with pytest.raises(ValueError, match="APP_ENV must be"):
                Config.db_path()
        finally:
            Config.APP_ENV = original

    def test_bot_token_prod(self):
        original = Config.APP_ENV
        try:
            Config.APP_ENV = "prod"
            Config.BOT_TOKEN = "prod-token"
            assert Config.bot_token() == "prod-token"
        finally:
            Config.APP_ENV = original

    def test_bot_token_test(self):
        original = Config.APP_ENV
        try:
            Config.APP_ENV = "test"
            Config.BOT_TOKEN_TEST = "test-token"
            assert Config.bot_token() == "test-token"
        finally:
            Config.APP_ENV = original

    def test_bot_token_invalid_env(self):
        original = Config.APP_ENV
        try:
            Config.APP_ENV = None
            with pytest.raises(ValueError, match="APP_ENV must be"):
                Config.bot_token()
        finally:
            Config.APP_ENV = original

    def test_local_image_dir_invalid_env(self):
        original = Config.APP_ENV
        try:
            Config.APP_ENV = "staging"
            with pytest.raises(ValueError, match="APP_ENV must be"):
                Config.local_image_dir()
        finally:
            Config.APP_ENV = original


class TestConfigValidation:
    def test_validate_passes_with_required_vars(self):
        originals = (Config.APP_ENV, Config.ANTHROPIC_API_KEY)
        try:
            Config.APP_ENV = "test"
            Config.ANTHROPIC_API_KEY = "key"
            Config.validate()  # Should not raise
        finally:
            Config.APP_ENV, Config.ANTHROPIC_API_KEY = originals

    def test_validate_fails_missing_app_env(self):
        originals = (Config.APP_ENV, Config.ANTHROPIC_API_KEY)
        try:
            Config.APP_ENV = None
            Config.ANTHROPIC_API_KEY = "key"
            with pytest.raises(EnvironmentError, match="APP_ENV"):
                Config.validate()
        finally:
            Config.APP_ENV, Config.ANTHROPIC_API_KEY = originals

    def test_validate_reports_all_missing(self):
        originals = (Config.APP_ENV, Config.ANTHROPIC_API_KEY)
        try:
            Config.APP_ENV = None
            Config.ANTHROPIC_API_KEY = None
            with pytest.raises(EnvironmentError, match="APP_ENV.*ANTHROPIC_API_KEY"):
                Config.validate()
        finally:
            Config.APP_ENV, Config.ANTHROPIC_API_KEY = originals
