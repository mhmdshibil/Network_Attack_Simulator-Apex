# backend/app/core/config.py
# This file is intended to serve as a centralized configuration hub for the application. It is the
# ideal place to store environment-specific settings, sensitive credentials, and other configurable
# parameters that may change between different deployment environments (e.g., development, staging,
# and production).
#
# By centralizing configuration here, you can:
#   - Avoid hardcoding values directly in the application logic.
#   - Easily manage different settings for various environments.
#   - Improve security by loading sensitive data (like API keys or database passwords) from
#     environment variables or a secure vault, rather than committing them to version control.
#
# Example usage:
#
# from pydantic import BaseSettings
#
# class Settings(BaseSettings):
#     API_KEY: str
#     DATABASE_URL: str
#
#     class Config:
#         env_file = ".env"
#
# settings = Settings()
