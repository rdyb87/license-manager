# config.py - Configuration

import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production-12345678'
    
    # Database - SQLite by default, PostgreSQL ready
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///metrology.db'
    
    # Disable modification tracking (performance)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # For production, set to True
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    
    # Upload settings (if needed later)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max


# Inside config.py
class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False  # Ensure this is explicitly False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    # In production, ensure SECRET_KEY is set via environment variable