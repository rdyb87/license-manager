# config.py - Configuration for Flask + SQLAlchemy + PostgreSQL (Render)

import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration"""
    # Secret key (set in Render environment variables for production)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production-12345678'

    # Database URI
    DATABASE_URL = os.environ.get('DATABASE_URL')

    if DATABASE_URL:
        # Force SQLAlchemy to use psycopg v3 driver
        if DATABASE_URL.startswith("postgresql://"):
            SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")
        else:
            SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Local fallback SQLite for dev
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, 'licenses.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session settings
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB


class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class ProductionConfig(Config):
    DEBUG = False
    # Make sure SECRET_KEY is set in Render environment variables
