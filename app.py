from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from datetime import datetime, timedelta
from config import DevelopmentConfig
from models import db, User, License
from sqlalchemy import or_
import os

# Create Flask app
app = Flask(__name__, instance_relative_config=True)
app.config.from_object(DevelopmentConfig)

# Ensure instance folder exists (SQLite db will be here)
try:
    os.makedirs(app.instance_path, exist_ok=True)
except OSError:
    pass

# Force session settings for local testing
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db.init_app(app)
with app.app_context():
    db.create_all()

# ============================================================================
# Authentication Decorator
# ============================================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(f"DEBUG: Session contents: {dict(session)}") # This prints to your terminal
        if 'user_id' not in session:
            print("DEBUG: user_id not found in session, redirecting to login")
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# Public Routes - No Authentication Required
# ============================================================================

@app.route('/')
def index():
    """Landing page - redirect to scan"""
    return redirect(url_for('scan'))


@app.route('/scan')
def scan():
    """Public barcode scanning page"""
    return render_template('public/scan.html')


@app.route('/api/validate', methods=['POST'])
def validate_serial():
    """
    API endpoint to validate serial number
    
    CRITICAL: Uses EXACT match only via find_by_exact_serial()
    """
    data = request.get_json()
    serial_number = data.get('serial_number', '').strip()
    
    if not serial_number:
        return jsonify({
            'success': False,
            'error': 'Serial number is required'
        }), 400
    
    # CRITICAL: Use exact match method only
    license_record = License.find_by_exact_serial(serial_number)
    
    if license_record:
        return jsonify({
            'success': True,
            'found': True,
            'data': {
                'serial_number': license_record.serial_number,
                'license_number': license_record.license_number,
                'brand': license_record.brand,
                'model': license_record.model,
                'license_date': license_record.license_date.strftime('%Y-%m-%d'),
                'expiry_date': license_record.expiry_date.strftime('%Y-%m-%d'),
                'status': license_record.status,
                'is_expired': license_record.is_expired
            }
        })
    else:
        return jsonify({
            'success': True,
            'found': False,
            'message': 'No license record found for this serial number'
        })


# ============================================================================
# Admin Authentication Routes
# ============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    # If already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session.clear()  # Clear any existing session data
            session['user_id'] = user.id
            session['username'] = user.username
            session.permanent = True  # Make session permanent
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('admin/login.html')


@app.route('/debug/session')
def debug_session():
    """Debug route to check session"""
    return jsonify({
        'session_data': dict(session),
        'user_id_in_session': 'user_id' in session,
        'secret_key_set': bool(app.config['SECRET_KEY']),
        'secret_key_length': len(app.config['SECRET_KEY'])
    })


@app.route('/logout')
def logout():
    """Logout admin user"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))
    
# ============================================================================
# Admin Routes - Authentication Required
# ============================================================================

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard with license list"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    
    query = License.query
    
    # Search functionality (exact or contains for admin convenience)
    if search:
        query = query.filter(
            or_(
                License.serial_number.ilike(f"%{search}%"),
                License.license_number.ilike(f"%{search}%"),
                License.brand.ilike(f"%{search}%")
        )
)
    
    licenses = query.order_by(License.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/dashboard.html', licenses=licenses, search=search)

@app.route('/admin/licenses/add', methods=['GET', 'POST'])
@login_required
def add_license():
    if request.method == 'POST':
        serial_number = request.form.get('serial_number', '').strip().upper()
        license_number = request.form.get('license_number', '').strip().upper()
        brand = request.form.get('brand', '').strip()
        model = request.form.get('model', '').strip()
        license_date_str = request.form.get('license_date')
        expiry_date_str = request.form.get('expiry_date')
        notes = request.form.get('notes', '').strip()

        # Required fields
        if not serial_number or not license_number:
            flash('Serial number and license number are required.', 'danger')
            return render_template('admin/add_license.html')

        # Uniqueness checks
        if License.find_by_exact_serial(serial_number):
            flash('Serial number already exists!', 'danger')
            return render_template('admin/add_license.html')

        if License.find_by_exact_license(license_number):
            flash('License number already exists!', 'danger')
            return render_template('admin/add_license.html')

        # Parse dates (HTML date input = YYYY-MM-DD)
        try:
            license_date = datetime.strptime(license_date_str, '%Y-%m-%d').date()
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            flash('Invalid date format.', 'danger')
            return render_template('admin/add_license.html')

        new_license = License(
            serial_number=serial_number,
            license_number=license_number,
            brand=brand or None,
            model=model or None,
            license_date=license_date,
            expiry_date=expiry_date,
            notes=notes or None
        )

        try:
            db.session.add(new_license)
            db.session.commit()
            flash('License added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Database error: duplicate data detected.', 'danger')

    return render_template('admin/add_license.html')

@app.route('/admin/licenses/edit/<int:license_id>', methods=['GET', 'POST'])
@login_required
def edit_license(license_id):
    license_record = License.query.get_or_404(license_id)

    if request.method == 'POST':
        serial_number = request.form.get('serial_number', '').strip().upper()
        license_number = request.form.get('license_number', '').strip().upper()
        brand = request.form.get('brand', '').strip()
        model = request.form.get('model', '').strip()
        license_date_str = request.form.get('license_date')
        expiry_date_str = request.form.get('expiry_date')
        notes = request.form.get('notes', '').strip()

        # Serial uniqueness (exclude self)
        if serial_number != license_record.serial_number:
            existing = License.find_by_exact_serial(serial_number)
            if existing and existing.id != license_record.id:
                flash('Serial number already exists!', 'danger')
                return render_template('admin/edit_license.html', license=license_record)

        # License number uniqueness (exclude self)
        if license_number != license_record.license_number:
            existing = License.find_by_exact_license(license_number)
            if existing and existing.id != license_record.id:
                flash('License number already exists!', 'danger')
                return render_template('admin/edit_license.html', license=license_record)

        # Parse dates
        try:
            license_record.license_date = datetime.strptime(license_date_str, '%Y-%m-%d').date()
            license_record.expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            flash('Invalid date format.', 'danger')
            return render_template('admin/edit_license.html', license=license_record)

        license_record.serial_number = serial_number
        license_record.license_number = license_number
        license_record.brand = brand or None
        license_record.model = model or None
        license_record.notes = notes or None

        try:
            db.session.commit()
            flash('License updated successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception:
            db.session.rollback()
            flash('Database error: duplicate data detected.', 'danger')

    return render_template('admin/edit_license.html', license=license_record)

@app.route('/admin/licenses/delete/<int:license_id>', methods=['POST'])
@login_required
def delete_license(license_id):
    """Delete license record"""
    license_record = License.query.get_or_404(license_id)
    
    try:
        db.session.delete(license_record)
        db.session.commit()
        flash('License deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting license: {str(e)}', 'danger')
    
    return redirect(url_for('admin_dashboard'))
    
@app.route('/admin/api/check-duplicate', methods=['POST'])
@login_required
def check_duplicate():
    data = request.get_json()

    serial_number = data.get('serial_number', '').strip()
    license_number = data.get('license_number', '').strip()
    exclude_id = data.get('exclude_id')  # for edit page

    response = {
        'serial_exists': False,
        'license_exists': False
    }

    if serial_number:
        existing = License.find_by_exact_serial(serial_number)
        if existing and str(existing.id) != str(exclude_id):
            response['serial_exists'] = True

    if license_number:
        existing = License.find_by_exact_license(license_number)
        if existing and str(existing.id) != str(exclude_id):
            response['license_exists'] = True

    return jsonify(response)
    
# ============================================================================
# Database Initialization
# ============================================================================

@app.route('/init_db_temp')
def init_db_temp():
    try:
        db.create_all()
        return "✅ Database tables created successfully!"
    except Exception as e:
        return f"❌ Error creating tables: {str(e)}"


@app.cli.command()
def init_db():
    """Initialize the database"""
    db.create_all()
    print('Database initialized.')


@app.route('/create_admin_temp')
def create_admin_temp():
    from models import User

    username = 'admin'
    password = 'admin123'  # Change this to a strong password

    if User.query.filter_by(username=username).first():
        return "⚠️ Admin already exists"

    admin = User(username=username)
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    return f"✅ Admin '{username}' created!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    with app.app_context():
        db.create_all()
    app.run(debug=True, host="0.0.0.0", port=port)