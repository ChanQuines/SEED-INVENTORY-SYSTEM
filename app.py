from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps

# Initialize Flask App
app = Flask(__name__)
app.secret_key = "mysecretkey"

# Configure SQLite Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///seeds_inventory_v4.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# --- Database Models ---

class Seed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seed_id = db.Column(db.String(10), unique=True, nullable=False)
    seed_name = db.Column(db.String(100), nullable=False)
    seed_type = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    supplier = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Available')
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    seed_image_b64 = db.Column(db.Text, nullable=True)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(10), default='Staff')


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('transactions', lazy=True))
    transaction_type = db.Column(db.String(10), nullable=False)  # 'Add' or 'Withdraw'
    seed_name = db.Column(db.String(100), nullable=False)
    seed_type = db.Column(db.String(100))
    quantity = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255))
    status = db.Column(db.String(20), default='Pending')  # 'Pending', 'Approved', 'Denied'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    seed_image_b64 = db.Column(db.Text, nullable=True)


# Create database tables and initial Admin user
with app.app_context():
    # db.drop_all() # Commented out for safety during development, use only for clean reset
    db.create_all()

    # Create default users if they don't exist
    if not User.query.filter_by(username='admin').first():
        admin_user = User(username='admin', password='123', role='Admin')
        db.session.add(admin_user)
    if not User.query.filter_by(username='staff1').first():
        staff_user = User(username='staff1', password='123', role='Staff')
        db.session.add(staff_user)
    db.session.commit()


# --- Utility Functions & Decorators ---

def generate_seed_id():
    """Generates a unique Seed ID like S001, S002, etc."""
    last_seed = Seed.query.order_by(Seed.id.desc()).first()
    if not last_seed or not last_seed.seed_id or not last_seed.seed_id.startswith('S'):
        return "S001"
    try:
        last_id_num = int(last_seed.seed_id[1:])
        return f"S{last_id_num + 1:03d}"
    except ValueError:
        return "S001"


def is_admin():
    """Checks if the logged-in user is an Admin."""
    return session.get('role') == 'Admin'


def login_required(f):
    """Decorator to ensure user is logged in."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('You must be logged in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Decorator to ensure user is an Admin."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin():
            flash('Admin access required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function


@app.context_processor
def inject_global_data():
    """Injects global data like current year and pending approvals count."""
    current_year = datetime.utcnow().year
    pending_count = 0
    if 'user_id' in session and session.get('role') == 'Admin':
        pending_count = Transaction.query.filter_by(status='Pending').count()
    return {
        'now': datetime.now,
        'current_year': current_year,
        'pending_approvals_count': pending_count
    }


# --- Routes ---

@app.route('/')
def index():
    if session.get('role') == 'Staff':
        return redirect(url_for('staff_transactions'))
    return redirect(url_for('report'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username, password=password).first()

        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash(f'Login successful! Welcome, {user.role}.', 'success')
            if user.role == 'Staff':
                return redirect(url_for('staff_transactions'))
            return redirect(url_for('report'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# --- Staff Routes ---

@app.route('/staff/transactions')
@login_required
def staff_transactions():
    if is_admin():
        # Admin sees Pending Transactions (for approval)
        transactions = Transaction.query.filter_by(status='Pending').order_by(Transaction.created_at.asc()).all()
        return render_template('admin_transactions.html', transactions=transactions)
    else:
        # Staff sees their own transaction history
        user_id = session.get('user_id')
        transactions = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.created_at.desc()).all()
        return render_template('staff_transactions.html', transactions=transactions)


@app.route('/staff/request', methods=['GET', 'POST'])
@login_required
def submit_request():
    if is_admin():
        flash('Admins perform direct actions, not requests.', 'warning')
        return redirect(url_for('report'))

    if request.method == 'POST':
        try:
            quantity = int(request.form['quantity'])
            image_b64 = request.form.get('seed_image_base64')
            transaction_type = request.form['transaction_type']

            if quantity <= 0:
                flash('Quantity must be greater than zero.', 'danger')
                return redirect(url_for('submit_request'))

            new_request = Transaction(
                user_id=session.get('user_id'),
                transaction_type=transaction_type,
                seed_name=request.form['seed_name'].strip(),
                seed_type=request.form.get('seed_type').strip() if request.form.get('seed_type') else 'Unknown',
                quantity=quantity,
                reason=request.form.get('reason', '').strip(),
                status='Pending',
                seed_image_b64=image_b64
            )
            db.session.add(new_request)
            db.session.commit()
            flash('Your request has been submitted for admin approval!', 'success')
            return redirect(url_for('staff_transactions'))
        except ValueError:
            flash('Quantity must be a valid whole number.', 'danger')
        except Exception as e:
            db.session.rollback()
            print(f"Server-side error submitting request: {e}")
            flash(f'An unexpected error occurred: {e}', 'danger')

    return render_template('submit_request.html')


# --- Admin Routes ---

@app.route('/admin/archive')
@admin_required
def admin_archive():
    transactions = Transaction.query.order_by(Transaction.created_at.desc()).all()
    return render_template('admin_archive.html', transactions=transactions)


@app.route('/admin/users', methods=['GET', 'POST'])
@admin_required
def user_management():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            username = request.form['username'].strip()
            password = request.form['password']
            role = request.form.get('role', 'Staff')
            if User.query.filter_by(username=username).first():
                flash(f'User "{username}" already exists.', 'danger')
            else:
                new_user = User(username=username, password=password, role=role)
                db.session.add(new_user)
                db.session.commit()
                flash(f'User "{username}" ({role}) created successfully.', 'success')

        elif action == 'delete':
            user_id_to_delete = request.form['user_id']
            user_to_delete = User.query.get(user_id_to_delete)
            if user_to_delete and user_to_delete.role != 'Admin' and user_to_delete.id != session.get('user_id'):
                db.session.delete(user_to_delete)
                db.session.commit()
                flash(f'User "{user_to_delete.username}" deleted.', 'success')
            else:
                flash('Cannot delete that user (either an Admin or yourself).', 'danger')

    users = User.query.all()
    return render_template('admin_users.html', users=users)


@app.route('/admin/approve/<int:transaction_id>')
@admin_required
def approve_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.status != 'Pending':
        flash('Transaction is not pending.', 'warning')
        return redirect(url_for('staff_transactions'))

    try:
        seed_name_clean = transaction.seed_name.strip()

        if transaction.transaction_type == 'Add':
            seed = Seed.query.filter_by(seed_name=seed_name_clean).first()
            if seed:
                seed.quantity += transaction.quantity
                if transaction.seed_image_b64:
                    seed.seed_image_b64 = transaction.seed_image_b64
                if seed.quantity > 0:
                    seed.status = 'Available'
                flash(f'Inventory updated: Added {transaction.quantity} to existing {seed_name_clean}.', 'success')

            else:
                seed = Seed(
                    seed_id=generate_seed_id(),
                    seed_name=seed_name_clean,
                    seed_type=(transaction.seed_type or 'Unknown').strip(),
                    quantity=transaction.quantity,
                    supplier=transaction.user.username,
                    status='Available',
                    seed_image_b64=transaction.seed_image_b64
                )
                db.session.add(seed)
                flash(f'New seed {seed_name_clean} added to inventory.', 'success')

        elif transaction.transaction_type == 'Withdraw':
            seed = Seed.query.filter_by(seed_name=seed_name_clean).first()
            if seed and seed.quantity >= transaction.quantity:
                seed.quantity -= transaction.quantity
                if seed.quantity == 0:
                    seed.status = 'Out of Stock'
                elif seed.quantity < 5:
                    seed.status = 'Low Stock'
                flash(f'Inventory updated: Withdrew {transaction.quantity} of {seed_name_clean}.', 'success')

            elif seed and seed.quantity < transaction.quantity:
                flash(
                    f'Denial: Insufficient stock for "{seed_name_clean}" (Needed: {transaction.quantity}, Available: {seed.quantity})',
                    'danger')
                transaction.status = 'Denied'
                db.session.commit()
                return redirect(url_for('staff_transactions'))
            else:
                flash(f'Denial: Seed "{seed_name_clean}" not found in inventory.', 'danger')
                transaction.status = 'Denied'
                db.session.commit()
                return redirect(url_for('staff_transactions'))

        transaction.status = 'Approved'
        db.session.commit()
        if not flash:
            flash(f'{transaction.transaction_type} request for {seed_name_clean} approved and inventory updated!',
                  'success')


    except Exception as e:
        db.session.rollback()
        print(f"Server-side error during approval: {e}")
        flash(f'Error processing approval: {e}', 'danger')

    return redirect(url_for('staff_transactions'))


@app.route('/admin/deny/<int:transaction_id>')
@admin_required
def deny_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.status != 'Pending':
        flash('Transaction is not pending.', 'warning')
    else:
        transaction.status = 'Denied'
        db.session.commit()
        flash(f'{transaction.transaction_type} request for {transaction.seed_name} denied.', 'info')

    return redirect(url_for('staff_transactions'))


# --- General Routes (Inventory Report & Dashboard) ---

@app.route('/report')
def report():
    seeds = Seed.query.order_by(Seed.seed_name).all()
    user_role = session.get('role', 'Guest')
    return render_template('report.html', seeds=seeds, user_role=user_role)


@app.route('/status_overview')
@login_required
def status_overview():
    # 1. Fetch KPI Metrics (Counts)
    total_seeds_in_inventory = Seed.query.count()
    low_stock_count = Seed.query.filter_by(status='Low Stock').count()
    total_quantity = db.session.query(db.func.sum(Seed.quantity)).scalar() or 0

    # 2. Fetch Data for Dashboard Cards
    pending_transactions = Transaction.query.filter_by(status='Pending').order_by(Transaction.created_at.asc()).all()
    pending_count = len(pending_transactions)

    recent_activity = Transaction.query.filter(Transaction.status.in_(['Approved', 'Denied'])).order_by(
        Transaction.created_at.desc()).limit(10).all()

    return render_template('status_overview.html',
                           total_quantity=total_quantity,
                           pending_count=pending_count,
                           low_stock_count=low_stock_count,
                           total_seeds_in_inventory=total_seeds_in_inventory,

                           pending_transactions=pending_transactions,
                           recent_activity=recent_activity,
                           user_role=session.get('role'))


if __name__ == '__main__':
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    with app.app_context():
        db.create_all()
    app.run(debug=True)