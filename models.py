from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    """Admin user model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class License(db.Model):
    """
    License record model
    CRITICAL: serial_number must be EXACT match only - no partial matching
    """
    __tablename__ = 'licenses'
    
    id = db.Column(db.Integer, primary_key=True)
    
    serial_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    license_number = db.Column(db.String(100), unique=True, nullable=False)
    brand = db.Column(db.String(100))
    model = db.Column(db.String(100))
    license_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # =========================
    # Computed Properties
    # =========================

    @property
    def is_expired(self):
        return datetime.now().date() > self.expiry_date
    
    @property
    def status(self):
        return "Expired" if self.is_expired else "Active"

    # =========================
    # Helper / Query Methods
    # =========================

    @classmethod
    def find_by_exact_serial(cls, serial_number):
        """
        EXACT serial match (case-insensitive)
        Prevents BB vs bb duplication
        """
        return cls.query.filter(
            func.lower(cls.serial_number) == func.lower(serial_number)
        ).first()

    @classmethod
    def find_by_exact_license(cls, license_number):
        """
        EXACT license number match (case-insensitive)
        """
        return cls.query.filter(
            func.lower(cls.license_number) == func.lower(license_number)
        ).first()

    def __repr__(self):
        return f'<License {self.serial_number}>'
