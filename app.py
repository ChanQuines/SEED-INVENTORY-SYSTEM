from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///seeds_inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Seed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seed_id = db.Column(db.String(10), unique=True, nullable=False)  
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

def generate_seed_id():
    last_seed = Seed.query.order_by(Seed.id.desc()).first()
    if not last_seed:
        return "S001"
    else:
        last_id_num = int(last_seed.seed_id[1:])
        new_id = last_id_num + 1
        return f"S{new_id:03d}"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/add', methods=['GET', 'POST'])
def add_seed():
    if request.method == 'POST':
        seed_name = request.form['seed_name']
        seed_type = request.form['seed_type']
        quantity = int(request.form['quantity'])
        supplier = request.form['supplier']
        status = request.form['status']

        new_seed = Seed(
            seed_id=generate_seed_id(),
            seed_name=seed_name,
            seed_type=seed_type,
            quantity=quantity,
            supplier=supplier,
            status=status
        )
        db.session.add(new_seed)
        db.session.commit()
        return redirect('/report')
    return render_template('add.html')

@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update_seed(id):
    seed = Seed.query.get_or_404(id)

    if request.method == 'POST':
    
        seed.seed_type = request.form['seed_type']
        seed.quantity = int(request.form['quantity'])
        seed.supplier = request.form['supplier']
        seed.status = request.form['status']

        db.session.commit()
        return redirect(url_for('report'))

    return render_template('update.html', seed=seed)

@app.route('/delete/<int:id>')
def delete_seed(id):
    seed = Seed.query.get_or_404(id)
    db.session.delete(seed)
    db.session.commit()
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

    return render_template(
        'status.html',
        available_count=available_count,
        low_stock_count=low_stock_count,
        expired_count=expired_count
    )

if __name__ == '__main__':
    app.run(debug=True)
