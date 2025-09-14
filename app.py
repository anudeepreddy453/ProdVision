import sys
import os
import threading
import time
import random

# Check Python version compatibility
if sys.version_info < (3, 7):
    print("❌ Python 3.7.0 or higher is required")
    print(f"Current version: {sys.version}")
    print("Please install Python 3.7.0 from https://www.python.org/downloads/")
    sys.exit(1)
elif sys.version_info >= (3, 8):
    print(f"⚠️  Python {sys.version_info.major}.{sys.version_info.minor} detected")
    print("This application is optimized for Python 3.7.0")
    print("Some features may not work as expected with newer versions")

from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
from datetime import datetime, timedelta
import bcrypt
from flask_cors import CORS
from sharepoint_sqlite_adapter import ProductionEntryManagerWorking as ProductionEntryManager
from config import SECRET_KEY, DEBUG, HOST, PORT, SHAREPOINT_URL

app = Flask(__name__)

# Enable CORS for credentials
CORS(app, supports_credentials=True)

# Configuration
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './flask_session'  # Explicitly set session directory
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'prodvision:'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

# Initialize extensions
Session(app)

# Initialize SharePoint SQLite database manager
entry_manager = ProductionEntryManager(SHAREPOINT_URL)

# Session cleanup functions
def cleanup_expired_session_files():
    """Clean up expired and orphaned session files"""
    try:
        session_dir = app.config['SESSION_FILE_DIR']
        if not os.path.exists(session_dir):
            return 0
        
        current_time = time.time()
        session_lifetime_seconds = app.config['PERMANENT_SESSION_LIFETIME'].total_seconds()
        deleted_count = 0
        
        for filename in os.listdir(session_dir):
            file_path = os.path.join(session_dir, filename)
            
            # Skip directories
            if not os.path.isfile(file_path):
                continue
            
            # Get file modification time
            file_mtime = os.path.getmtime(file_path)
            file_age = current_time - file_mtime
            
            # Delete if file is older than session lifetime
            if file_age > session_lifetime_seconds:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    print(f"Deleted expired session file: {filename}")
                except OSError as e:
                    print(f"Error deleting session file {filename}: {e}")
        
        if deleted_count > 0:
            print(f"Session cleanup completed: {deleted_count} files deleted")
        
        return deleted_count
    except Exception as e:
        print(f"Session cleanup error: {e}")
        return 0

def delete_current_session_file():
    """Delete the current user's session file immediately"""
    try:
        # Get the current session ID
        session_id = session.get('_id')
        if not session_id:
            # Try to get session ID from Flask-Session's internal storage
            session_id = getattr(session, '_id', None)
        
        if session_id:
            # Remove the session key prefix if present
            session_key = app.config['SESSION_KEY_PREFIX'] + session_id
            session_file_path = os.path.join(app.config['SESSION_FILE_DIR'], session_key)
            
            if os.path.exists(session_file_path):
                os.remove(session_file_path)
                print(f"Immediately deleted session file: {session_key}")
                return True
        return False
    except Exception as e:
        print(f"Error deleting current session file: {e}")
        return False

def check_and_cleanup_expired_sessions():
    """Check for expired sessions and clean them immediately"""
    try:
        session_dir = app.config['SESSION_FILE_DIR']
        if not os.path.exists(session_dir):
            return 0
        
        current_time = time.time()
        session_lifetime_seconds = app.config['PERMANENT_SESSION_LIFETIME'].total_seconds()
        deleted_count = 0
        
        for filename in os.listdir(session_dir):
            file_path = os.path.join(session_dir, filename)
            
            if not os.path.isfile(file_path):
                continue
            
            # Check if file is expired
            file_mtime = os.path.getmtime(file_path)
            file_age = current_time - file_mtime
            
            if file_age > session_lifetime_seconds:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    print(f"Immediately deleted expired session file: {filename}")
                except OSError as e:
                    print(f"Error deleting expired session file {filename}: {e}")
        
        return deleted_count
    except Exception as e:
        print(f"Error in immediate session cleanup: {e}")
        return 0

def periodic_session_cleanup():
    """Run session cleanup every 30 minutes"""
    while True:
        time.sleep(1800)  # 30 minutes
        cleanup_expired_session_files()

def get_session_stats():
    """Get session file statistics"""
    try:
        session_dir = app.config['SESSION_FILE_DIR']
        if not os.path.exists(session_dir):
            return {'total_files': 0, 'total_size': 0}
        
        total_files = 0
        total_size = 0
        
        for filename in os.listdir(session_dir):
            file_path = os.path.join(session_dir, filename)
            if os.path.isfile(file_path):
                total_files += 1
                total_size += os.path.getsize(file_path)
        
        return {
            'total_files': total_files,
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2)
        }
    except Exception as e:
        print(f"Error getting session stats: {e}")
        return {'total_files': 0, 'total_size': 0}

# Helper functions for data validation and conversion
def validate_entry_data(data):
    """Validate production entry data based on application type"""
    application_name = data.get('application_name', '')
    
    # Common required fields for all applications
    common_required_fields = ['date', 'application_name']
    
    # Define required fields based on application type
    if application_name == 'XVA':
        # XVA-specific required fields (only date and application_name are required)
        required_fields = common_required_fields
    else:
        # CVAR (ALL/NYQ) required fields: require either single-time fields or arrays
        required_fields = common_required_fields + ['prc_mail_text', 'prc_mail_status']
    
    # Check required fields (allow arrays for multiple items)
    for field in required_fields:
        # If arrays are provided, skip single-field requirement
        if field not in data or not data[field]:
            # allow presence of arrays: 'issues', 'prbs', 'hiims' as alternatives
            if field in ('prc_mail_text', 'prc_mail_status'):
                # Accept if prbs/hiims arrays or issues array present
                if any(isinstance(data.get(k), list) and len(data.get(k)) > 0 for k in ('issues', 'prbs', 'hiims')):
                    continue
            return False, f'Missing required field: {field}'
    
    # Validate status values based on application type
    if application_name == 'XVA':
        # XVA-specific validation
        if data.get('valo_status') and data['valo_status'] not in ['Red', 'Yellow', 'Green']:
            return False, 'Invalid VALO status'
        if data.get('sensi_status') and data['sensi_status'] not in ['Red', 'Yellow', 'Green']:
            return False, 'Invalid SENSI status'
        if data.get('cf_ra_status') and data['cf_ra_status'] not in ['Red', 'Yellow', 'Green']:
            return False, 'Invalid CF RA status'
        if data.get('quality_legacy') and data['quality_legacy'] not in ['Red', 'Yellow', 'Green']:
            return False, 'Invalid quality legacy status'
        if data.get('quality_target') and data['quality_target'] not in ['Red', 'Yellow', 'Green']:
            return False, 'Invalid quality target status'
        # Skip CVAR-specific validation for XVA entries
    else:
        # CVAR-specific validation - validate single fields or arrays
        if data.get('prc_mail_status') and data['prc_mail_status'] not in ['Red', 'Yellow', 'Green']:
            return False, 'Invalid PRC mail status'
        if data.get('cp_alerts_status') and data['cp_alerts_status'] not in ['Red', 'Yellow', 'Green']:
            return False, 'Invalid CP alerts status'
        if data.get('quality_status') and data['quality_status'] not in ['Red', 'Yellow', 'Green']:
            return False, 'Invalid quality status'

        # Validate PRBs array if present
        if 'prbs' in data and isinstance(data['prbs'], list):
            for prb in data['prbs']:
                if 'prb_id_number' in prb and prb['prb_id_number'] is not None:
                    try:
                        int(prb['prb_id_number'])
                    except Exception:
                        return False, 'Invalid PRB id number'
                if prb.get('prb_id_status') and prb['prb_id_status'] not in ['active', 'closed']:
                    return False, 'Invalid PRB ID status in array'

        # Validate HIIMs array if present
        if 'hiims' in data and isinstance(data['hiims'], list):
            for hiim in data['hiims']:
                if 'hiim_id_number' in hiim and hiim['hiim_id_number'] is not None:
                    try:
                        int(hiim['hiim_id_number'])
                    except Exception:
                        return False, 'Invalid HIIM id number'
                if hiim.get('hiim_id_status') and hiim['hiim_id_status'] not in ['active', 'closed']:
                    return False, 'Invalid HIIM ID status in array'
    
    # Common validation for all applications
    if data.get('prb_id_status') and data['prb_id_status'] not in ['active', 'closed']:
        return False, 'Invalid PRB ID status'
    if data.get('hiim_id_status') and data['hiim_id_status'] not in ['active', 'closed']:
        return False, 'Invalid HIIM ID status'
    
    return True, None

def convert_date_string(date_str):
    """Convert date string to datetime object"""
    if isinstance(date_str, str):
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    return date_str

# Authentication helper functions
def is_authenticated():
    # Check for expired sessions and clean them immediately
    check_and_cleanup_expired_sessions()
    
    return 'authenticated' in session and session['authenticated'] == True

def require_auth(f):
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Before request handler for session cleanup
@app.before_request
def cleanup_expired_sessions_before_request():
    """Clean up expired sessions before each request (occasionally)"""
    # Only run cleanup occasionally to avoid performance impact
    if random.random() < 0.1:  # 10% chance
        check_and_cleanup_expired_sessions()

# Routes
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/favicon.ico')
def favicon():
    """Favicon route to prevent 404 errors"""
    return '', 204

@app.route('/api/entries')
def get_entries():
    """Get production entries with optional filtering"""
    try:
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        application = request.args.get('application')
        quality_status = request.args.get('quality_status')
        prb_only = request.args.get('prb_only', 'false').lower() == 'true'
        hiim_only = request.args.get('hiim_only', 'false').lower() == 'true'
        
        # Get all entries from SharePoint SQLite database
        all_entries = entry_manager.get_all_entries()
        
        # Apply filters
        filtered_entries = []
        for entry in all_entries:
            # Date filters
            if start_date:
                entry_date = convert_date_string(entry.get('date', ''))
                if entry_date < datetime.strptime(start_date, '%Y-%m-%d').date():
                    continue
            if end_date:
                entry_date = convert_date_string(entry.get('date', ''))
                if entry_date > datetime.strptime(end_date, '%Y-%m-%d').date():
                    continue
            
            # Application filter
            if application:
                if application.lower() not in entry.get('application_name', '').lower():
                    continue
            
            # Quality status filter
            if quality_status:
                if entry.get('quality_status') != quality_status:
                    continue
            
            # PRB only filter
            if prb_only:
                # Accept legacy single field or new prbs array
                if not entry.get('prb_id_number') and not (isinstance(entry.get('prbs'), list) and len(entry.get('prbs')) > 0):
                    continue
            
            # HIIM only filter
            if hiim_only:
                # Accept legacy single field or new hiims array
                if not entry.get('hiim_id_number') and not (isinstance(entry.get('hiims'), list) and len(entry.get('hiims')) > 0):
                    continue
            
            filtered_entries.append(entry)
        
        # Sort by date descending, then by created_at descending
        filtered_entries.sort(key=lambda x: (
            convert_date_string(x.get('date', '1900-01-01')),
            x.get('created_at', '1900-01-01T00:00:00')
        ), reverse=True)
        
        return jsonify(filtered_entries)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/entries/<int:entry_id>')
def get_entry(entry_id):
    """Get a specific production entry by ID"""
    try:
        entry = entry_manager.get_entry_by_id(entry_id)
        if entry:
            return jsonify(entry)
        else:
            return jsonify({'error': 'Entry not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/entries', methods=['POST'])
@require_auth
def create_entry():
    """Create a new production entry"""
    try:
        data = request.get_json()
        
        # Validate data
        is_valid, error_msg = validate_entry_data(data)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        # Check if entry already exists for this date and application
        entry_date = convert_date_string(data['date'])
        all_entries = entry_manager.get_all_entries()
        
        for existing_entry in all_entries:
            if (existing_entry.get('date') == data['date'] and 
                existing_entry.get('application_name') == data['application_name']):
                return jsonify({'error': f'An entry already exists for {data["application_name"]} on {data["date"]}'}), 400
        
        # Create new entry
        entry = entry_manager.create_entry(data)
        
        if entry:
            return jsonify(entry), 201
        else:
            return jsonify({'error': 'Failed to create entry'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/entries/<int:entry_id>', methods=['PUT'])
@require_auth
def update_entry(entry_id):
    """Update an existing production entry"""
    try:
        data = request.get_json()
        print(f"API update_entry called for id={entry_id} with data:", data)
        
        # Get existing entry
        existing_entry = entry_manager.get_entry_by_id(entry_id)
        if not existing_entry:
            return jsonify({'error': 'Entry not found'}), 404
        
        # Check for duplicate entry if date or application is being changed
        if 'date' in data or 'application_name' in data:
            new_date = data.get('date', existing_entry.get('date'))
            new_application = data.get('application_name', existing_entry.get('application_name'))
            
            # Check if another entry exists for this date and application (excluding current entry)
            all_entries = entry_manager.get_all_entries()
            for entry in all_entries:
                if (entry.get('id') != entry_id and 
                    entry.get('date') == new_date and 
                    entry.get('application_name') == new_application):
                    return jsonify({'error': f'An entry already exists for {new_application} on {new_date}'}), 400
        
        # Validate entry data using the updated validation function
        # Allow partial updates by merging with existing entry for validation
        merged_data = dict(existing_entry)
        merged_data.update(data)
        is_valid, error_message = validate_entry_data(merged_data)
        if not is_valid:
            return jsonify({'error': error_message}), 400
        
        # Update entry
        updated_entry = entry_manager.update_entry(entry_id, data)
        
        if updated_entry:
            return jsonify(updated_entry)
        else:
            return jsonify({'error': 'Failed to update entry'}), 500
    except Exception as e:
        print('Exception in API update_entry:', e)
        return jsonify({'error': str(e)}), 500

@app.route('/api/entries/<int:entry_id>', methods=['DELETE'])
@require_auth
def delete_entry(entry_id):
    """Delete a production entry"""
    try:
        success = entry_manager.delete_entry(entry_id)
        if success:
            return jsonify({'message': 'Entry deleted successfully'})
        else:
            return jsonify({'error': 'Entry not found or failed to delete'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """Get aggregated statistics for charts"""
    try:
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        application = request.args.get('application')
        quality_status = request.args.get('quality_status')
        prb_only = request.args.get('prb_only')
        hiim_only = request.args.get('hiim_only')
        
        # Get monthly and yearly filters
        years = request.args.getlist('year')
        months = request.args.getlist('month')
        
        # Get all entries from SharePoint SQLite database
        all_entries = entry_manager.get_all_entries()
        
        # Apply filters
        entries = []
        for entry in all_entries:
            # Date range filters
            if start_date:
                entry_date = convert_date_string(entry.get('date', ''))
                if entry_date < datetime.strptime(start_date, '%Y-%m-%d').date():
                    continue
            if end_date:
                entry_date = convert_date_string(entry.get('date', ''))
                if entry_date > datetime.strptime(end_date, '%Y-%m-%d').date():
                    continue
            
            # Monthly and yearly filters
            if years or months:
                entry_date = convert_date_string(entry.get('date', ''))
                entry_year = str(entry_date.year)
                entry_month = str(entry_date.month)
                
                if years and entry_year not in years:
                    continue
                if months and entry_month not in months:
                    continue
            
            # Other filters
            if application and application.lower() not in entry.get('application_name', '').lower():
                continue
            if quality_status and entry.get('quality_status') != quality_status:
                continue
            if prb_only == 'true' and not entry.get('prb_id_number'):
                continue
            if hiim_only == 'true' and not entry.get('hiim_id_number'):
                continue
            
            entries.append(entry)
        
        # Calculate statistics
        total_entries = len(entries)
        quality_counts = {'Red': 0, 'Yellow': 0, 'Green': 0}
        punctuality_counts = {'Red': 0, 'Yellow': 0, 'Green': 0}
        prb_counts = {'active': 0, 'closed': 0}
        hiim_counts = {'active': 0, 'closed': 0}
        app_counts = {}
        
        # Monthly breakdown for comparison charts
        monthly_quality = {}
        monthly_punctuality = {}
        monthly_prb = {}
        monthly_hiim = {}
        
        # First, initialize all selected months with zero data
        if years or months:
            selected_months = set()
            
            # Generate all possible month-year combinations from selected years and months
            if years and months:
                # Both years and months are selected - use combinations
                for year in years:
                    for month in months:
                        month_key = f"{year}-{int(month):02d}"
                        month_name = datetime(int(year), int(month), 1).strftime('%B %Y')
                        selected_months.add((month_key, month_name))
            elif years:
                # Only years selected - include all months for those years
                for year in years:
                    for month in range(1, 13):
                        month_key = f"{year}-{month:02d}"
                        month_name = datetime(int(year), month, 1).strftime('%B %Y')
                        selected_months.add((month_key, month_name))
            elif months:
                # Only months selected - include those months for all years in the data
                # Get year range from the entries
                if entries:
                    years_in_data = set(convert_date_string(entry.get('date', '1900-01-01')).year for entry in entries)
                    for year in years_in_data:
                        for month in months:
                            month_key = f"{year}-{int(month):02d}"
                            month_name = datetime(int(year), int(month), 1).strftime('%B %Y')
                            selected_months.add((month_key, month_name))
            
            # Initialize all selected months with zero data
            for month_key, month_name in selected_months:
                monthly_quality[month_key] = {
                    'month_name': month_name,
                    'Red': 0, 'Yellow': 0, 'Green': 0
                }
                monthly_punctuality[month_key] = {
                    'month_name': month_name,
                    'Red': 0, 'Yellow': 0, 'Green': 0
                }
                monthly_prb[month_key] = {
                    'month_name': month_name,
                    'active': 0, 'closed': 0
                }
                monthly_hiim[month_key] = {
                    'month_name': month_name,
                    'active': 0, 'closed': 0
                }
        
        for entry in entries:
            # Get month-year key for grouping
            entry_date = convert_date_string(entry.get('date', '1900-01-01'))
            month_key = f"{entry_date.year}-{entry_date.month:02d}"
            month_name = entry_date.strftime('%B %Y')
            
            # Initialize monthly data if not exists (for cases where no year/month filters are applied)
            if month_key not in monthly_quality:
                monthly_quality[month_key] = {
                    'month_name': month_name,
                    'Red': 0, 'Yellow': 0, 'Green': 0
                }
            if month_key not in monthly_punctuality:
                monthly_punctuality[month_key] = {
                    'month_name': month_name,
                    'Red': 0, 'Yellow': 0, 'Green': 0
                }
            if month_key not in monthly_prb:
                monthly_prb[month_key] = {
                    'month_name': month_name,
                    'active': 0, 'closed': 0
                }
            if month_key not in monthly_hiim:
                monthly_hiim[month_key] = {
                    'month_name': month_name,
                    'active': 0, 'closed': 0
                }
            
            # Quality counts
            quality_status = entry.get('quality_status')
            if quality_status:
                quality_counts[quality_status] += 1
                monthly_quality[month_key][quality_status] += 1
            
            # Calculate punctuality based only on PRC Mail status
            prc_mail_status = entry.get('prc_mail_status')
            if prc_mail_status:
                # Map old status values to new color scheme
                if prc_mail_status in ['Red', 'red']:
                    punctuality_counts['Red'] += 1
                    monthly_punctuality[month_key]['Red'] += 1
                elif prc_mail_status in ['Yellow', 'yellow', 'warning']:
                    punctuality_counts['Yellow'] += 1
                    monthly_punctuality[month_key]['Yellow'] += 1
                elif prc_mail_status in ['Green', 'green', 'on-time']:
                    punctuality_counts['Green'] += 1
                    monthly_punctuality[month_key]['Green'] += 1
                elif prc_mail_status in ['late']:
                    punctuality_counts['Red'] += 1
                    monthly_punctuality[month_key]['Red'] += 1
                else:
                    # For any other status, count as Yellow
                    punctuality_counts['Yellow'] += 1
                    monthly_punctuality[month_key]['Yellow'] += 1
            
            # Count PRB statuses
            prb_id_status = entry.get('prb_id_status')
            if prb_id_status:
                prb_counts[prb_id_status] += 1
                monthly_prb[month_key][prb_id_status] += 1
            
            # Count HIIM statuses
            hiim_id_status = entry.get('hiim_id_status')
            if hiim_id_status:
                hiim_counts[hiim_id_status] += 1
                monthly_hiim[month_key][hiim_id_status] += 1
            
            application_name = entry.get('application_name', 'Unknown')
            app_counts[application_name] = app_counts.get(application_name, 0) + 1
        
        # Convert monthly data to sorted list
        monthly_quality_list = sorted(monthly_quality.items(), key=lambda x: x[0])
        monthly_punctuality_list = sorted(monthly_punctuality.items(), key=lambda x: x[0])
        monthly_prb_list = sorted(monthly_prb.items(), key=lambda x: x[0])
        monthly_hiim_list = sorted(monthly_hiim.items(), key=lambda x: x[0])
        
        return jsonify({
            'total_entries': total_entries,
            'quality_distribution': quality_counts,
            'punctuality_distribution': punctuality_counts,
            'prb_distribution': prb_counts,
            'hiim_distribution': hiim_counts,
            'application_distribution': app_counts,
            'monthly_quality': monthly_quality_list,
            'monthly_punctuality': monthly_punctuality_list,
            'monthly_prb': monthly_prb_list,
            'monthly_hiim': monthly_hiim_list
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate user"""
    try:
        data = request.get_json()
        password = data.get('password', '')
        
        # Get stored password hash from settings
        stored_hash = entry_manager.get_setting('admin_password')
        if not stored_hash:
            return jsonify({'error': 'Authentication not configured'}), 500
        
        # Check password
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            session['authenticated'] = True
            session.permanent = True
            return jsonify({'message': 'Authentication successful'})
        else:
            return jsonify({'error': 'Invalid password'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout user"""
    # Delete session file immediately on logout
    delete_current_session_file()
    
    # Clear session data
    session.pop('authenticated', None)
    session.clear()
    
    return jsonify({'message': 'Logged out successfully'})

@app.route('/api/auth/status')
def auth_status():
    """Check authentication status"""
    return jsonify({'authenticated': is_authenticated()})

@app.route('/api/admin/cleanup-sessions', methods=['POST'])
@require_auth
def manual_cleanup_sessions():
    """Manually clean up expired session files"""
    try:
        deleted_count = check_and_cleanup_expired_sessions()
        return jsonify({
            'message': f'Successfully cleaned up {deleted_count} expired session files'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/session-stats')
@require_auth
def session_file_stats():
    """Get session file statistics"""
    try:
        stats = get_session_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/xva/stats')
def get_xva_stats():
    """Get XVA-specific statistics for charts and tables"""
    try:
        # Get filter parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        years = request.args.getlist('year')
        months = request.args.getlist('month')
        
        # Get all entries from SharePoint SQLite database and filter for XVA only
        all_entries = entry_manager.get_all_entries()
        
        # Apply filters for XVA entries only
        entries = []
        for entry in all_entries:
            # Only XVA entries
            if entry.get('application_name') != 'XVA':
                continue
            
            # Date range filters
            if start_date:
                entry_date = convert_date_string(entry.get('date', ''))
                if entry_date < datetime.strptime(start_date, '%Y-%m-%d').date():
                    continue
            if end_date:
                entry_date = convert_date_string(entry.get('date', ''))
                if entry_date > datetime.strptime(end_date, '%Y-%m-%d').date():
                    continue
            
            # Monthly and yearly filters
            if years or months:
                entry_date = convert_date_string(entry.get('date', ''))
                entry_year = str(entry_date.year)
                entry_month = str(entry_date.month)
                
                if years and entry_year not in years:
                    continue
                if months and entry_month not in months:
                    continue
            
            entries.append(entry)
        
        # Calculate XVA-specific statistics
        monthly_red_counts = {}
        root_cause_analysis = {}
        
        # Initialize monthly data for all selected months
        if years or months:
            from datetime import datetime
            selected_months = set()
            
            if years and months:
                for year in years:
                    for month in months:
                        month_key = f"{year}-{int(month):02d}"
                        month_name = datetime(int(year), int(month), 1).strftime('%B %Y')
                        selected_months.add((month_key, month_name))
            elif years:
                for year in years:
                    for month in range(1, 13):
                        month_key = f"{year}-{month:02d}"
                        month_name = datetime(int(year), month, 1).strftime('%B %Y')
                        selected_months.add((month_key, month_name))
            elif months:
                if entries:
                    years_in_data = set(entry.date.year for entry in entries)
                    for year in years_in_data:
                        for month in months:
                            month_key = f"{year}-{int(month):02d}"
                            month_name = datetime(int(year), int(month), 1).strftime('%B %Y')
                            selected_months.add((month_key, month_name))
            
            # Initialize all selected months with zero data
            for month_key, month_name in selected_months:
                monthly_red_counts[month_key] = {
                    'month_name': month_name,
                    'valo_red': 0,
                    'sensi_red': 0,
                    'cf_ra_red': 0,
                    'total_red': 0
                }
        
        for entry in entries:
            # Get month-year key for grouping
            entry_date = convert_date_string(entry.get('date', '1900-01-01'))
            month_key = f"{entry_date.year}-{entry_date.month:02d}"
            month_name = entry_date.strftime('%B %Y')
            
            # Initialize monthly data if not exists
            if month_key not in monthly_red_counts:
                monthly_red_counts[month_key] = {
                    'month_name': month_name,
                    'valo_red': 0,
                    'sensi_red': 0,
                    'cf_ra_red': 0,
                    'total_red': 0
                }
            
            # Check if entry is a red card (punctuality OR quality is red)
            is_red_card = False
            
            # Check punctuality statuses for red
            if (entry.get('valo_status') == 'Red' or 
                entry.get('sensi_status') == 'Red' or 
                entry.get('cf_ra_status') == 'Red'):
                is_red_card = True
            
            # Check quality status for red
            if (entry.get('quality_legacy') == 'Red' or 
                entry.get('quality_target') == 'Red'):
                is_red_card = True
            
            if is_red_card:
                # Count red occurrences by category
                if entry.get('valo_status') == 'Red':
                    monthly_red_counts[month_key]['valo_red'] += 1
                
                if entry.get('sensi_status') == 'Red':
                    monthly_red_counts[month_key]['sensi_red'] += 1
                
                if entry.get('cf_ra_status') == 'Red':
                    monthly_red_counts[month_key]['cf_ra_red'] += 1
                
                # Increment total red count for this month
                monthly_red_counts[month_key]['total_red'] += 1
                
                # Root cause analysis
                root_cause_app = entry.get('root_cause_application') or 'Unknown'
                root_cause_type = entry.get('root_cause_type') or 'Unknown'
                
                key = f"{root_cause_app}|{root_cause_type}"
                if key not in root_cause_analysis:
                    root_cause_analysis[key] = {
                        'root_cause_application': root_cause_app,
                        'root_cause_type': root_cause_type,
                        'count': 0
                    }
                root_cause_analysis[key]['count'] += 1
        
        # Convert monthly data to sorted list
        monthly_red_counts_list = sorted(monthly_red_counts.items(), key=lambda x: x[0])
        
        # Convert root cause analysis to list and calculate grand total
        root_cause_list = list(root_cause_analysis.values())
        grand_total = sum(item['count'] for item in root_cause_list)
        
        return jsonify({
            'monthly_red_counts': monthly_red_counts_list,
            'root_cause_analysis': root_cause_list,
            'grand_total': grand_total
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Initialize database and create default admin password
def initialize_database():
    """Initialize SharePoint SQLite database with default settings"""
    try:
        # Ensure database tables exist
        entry_manager._ensure_datasets_exist()
        
        # Create default admin password if not exists
        admin_password = entry_manager.get_setting('admin_password')
        if not admin_password:
            # Default password is 'admin123' - should be changed in production
            hashed_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
            entry_manager.set_setting('admin_password', hashed_password.decode('utf-8'))
        
        # Clean up any existing expired session files on startup
        cleanup_expired_session_files()
        
    except Exception as e:
        raise

if __name__ == '__main__':
    with app.app_context():
        initialize_database()
    
    # Start session cleanup thread
    cleanup_thread = threading.Thread(target=periodic_session_cleanup, daemon=True)
    cleanup_thread.start()
    
    print("Starting ProdVision Dashboard...")
    print(f"Access the dashboard at: http://{HOST}:{PORT}")
    print("Default admin password: admin123")
    print("Session cleanup: Enabled (runs every 30 minutes)")
    print("Press Ctrl+C to stop the server")
    app.run(debug=DEBUG, host=HOST, port=PORT)
