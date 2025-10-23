from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = "mysecretkey"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///seeds_inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Seed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
<<<<<<< HEAD
    seed_id = db.Column(db.String(10), unique=True, nullable=False)
=======
    seed_id = db.Column(db.String(10), unique=True, nullable=False)  
>>>>>>> 35c203209fd42e1ba8ce00b0f65b7f15acf12637
    seed_name = db.Column(db.String(100), nullable=False)
    seed_type = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    supplier = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Available')
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Seed {self.seed_name}>"

with app.app_context():
    db.create_all()

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "12345"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['user'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('report'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('report'))

def generate_seed_id():
    last_seed = Seed.query.order_by(Seed.id.desc()).first()
    if not last_seed:
        return "S001"
    else:
        last_id_num = int(last_seed.seed_id[1:])
        return f"S{last_id_num + 1:03d}"

@app.route('/')
def index():
    return redirect(url_for('report'))

@app.route('/add', methods=['GET', 'POST'])
def add_seed():
    if 'user' not in session:
        flash('You must be logged in to add a seed.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_seed = Seed(
            seed_id=generate_seed_id(),
            seed_name=request.form['seed_name'],
            seed_type=request.form['seed_type'],
            quantity=int(request.form['quantity']),
            supplier=request.form['supplier'],
            status=request.form['status']
        )
        db.session.add(new_seed)
        db.session.commit()
        flash('Seed added successfully!', 'success')
        return redirect(url_for('report'))
    return render_template('add.html')

@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update_seed(id):
    if 'user' not in session:
        flash('Only authorized users can update seeds.', 'warning')
        return redirect(url_for('login'))

    seed = Seed.query.get_or_404(id)
    if request.method == 'POST':
<<<<<<< HEAD
=======
    
>>>>>>> 35c203209fd42e1ba8ce00b0f65b7f15acf12637
        seed.seed_type = request.form['seed_type']
        seed.quantity = int(request.form['quantity'])
        seed.supplier = request.form['supplier']
        seed.status = request.form['status']
        db.session.commit()
        flash('Seed updated successfully!', 'success')
        return redirect(url_for('report'))
    return render_template('update.html', seed=seed)

@app.route('/delete/<int:id>')
def delete_seed(id):
    if 'user' not in session:
        flash('Only authorized users can delete seeds.', 'warning')
        return redirect(url_for('login'))

    seed = Seed.query.get_or_404(id)
    db.session.delete(seed)
    db.session.commit()
    flash('Seed deleted successfully!', 'success')
    return redirect(url_for('report'))

@app.route('/report')
def report():
    seeds = Seed.query.all()
    return render_template('report.html', seeds=seeds)

@app.route('/status')
def status_overview():
    available_count = Seed.query.filter_by(status='Available').count()
    low_stock_count = Seed.query.filter_by(status='Low Stock').count()
    expired_count = Seed.query.filter_by(status='Expired').count()
    return render_template('status.html',
                           available_count=available_count,
                           low_stock_count=low_stock_count,
                           expired_count=expired_count)

if __name__ == '__main__':
    app.run(debug=True)
