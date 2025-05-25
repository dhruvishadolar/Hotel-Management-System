# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import or_, and_

# ------------------ Flask App Config ------------------
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://hotem_management_2l4a_user:pnQB0C06cNyGohtSmV48zpgnRMwYyrht@dpg-d0pcu3muk2gs739gi0b0-a/hotem_management_2l4a'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'hotelmanagement'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ------------------ Models ------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Available')
    image = db.Column(db.String(255), nullable=False, default='default.jpg')
    features = db.Column(db.String(255), default='Free WiFi, TV, AC')
    facility = db.Column(db.String(255), default='Gym, Pool')
    guests = db.Column(db.Integer, default=2)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(100), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    checkin_date = db.Column(db.Date, nullable=False)
    checkout_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Pending')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    subject = db.Column(db.String(200))
    message = db.Column(db.Text)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------ Routes ------------------

@app.route('/')
def home():
    rooms = Room.query.all()
    return render_template('index.html', rooms=rooms)

@app.route('/rooms')
def rooms():
    rooms = Room.query.filter_by(status='Available').all()
    return render_template('rooms.html', rooms=rooms)

@app.route('/room/<int:room_id>')
def room_details(room_id):
    room = Room.query.get_or_404(room_id)
    return render_template('room_details.html', room=room)

@app.route('/facilities.html')
def facilities():
    return render_template('facilities.html')

@app.route('/about.html')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        msg = Message(
            name=request.form['name'],
            email=request.form['email'],
            subject=request.form['subject'],
            message=request.form['message']
        )
        db.session.add(msg)
        db.session.commit()
        flash("Your message has been sent!", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")

@app.route('/messages')
@login_required
def messages():
    if not current_user.is_admin:
        return "Access Denied", 403
    msgs = Message.query.all()
    return render_template("messages.html", messages=msgs)

@app.route('/book/<int:room_id>', methods=['GET', 'POST'])
def book(room_id):
    room = Room.query.get_or_404(room_id)
    checkin = request.args.get('checkin')
    checkout = request.args.get('checkout')
    if request.method == 'POST':
        try:
            checkin_date = datetime.strptime(checkin, '%Y-%m-%d').date()
            checkout_date = datetime.strptime(checkout, '%Y-%m-%d').date()
        except ValueError:
            return "Invalid date format", 400
        booking = Booking(
            customer_name=request.form['customer_name'],
            customer_email=request.form['customer_email'],
            room_id=room_id,
            checkin_date=checkin_date,
            checkout_date=checkout_date,
            status='Confirmed'
        )
        db.session.add(booking)
        db.session.commit()
        return render_template('booking_confirmation.html', booking=booking, room=room)
    return render_template('booking.html', room=room, checkin=checkin, checkout=checkout)

@app.route('/availability', methods=['POST'])
def check_availability():
    try:
        checkin = datetime.strptime(request.form.get('checkin'), '%Y-%m-%d').date()
        checkout = datetime.strptime(request.form.get('checkout'), '%Y-%m-%d').date()
    except ValueError:
        return "Invalid date format", 400

    if checkin >= checkout:
        return "Check-in date must be before check-out date", 400

    booked_rooms = db.session.query(Booking.room_id).filter(
        Booking.status == 'Confirmed',
        or_(
            and_(Booking.checkin_date <= checkin, Booking.checkout_date > checkin),
            and_(Booking.checkin_date < checkout, Booking.checkout_date >= checkout),
            and_(Booking.checkin_date >= checkin, Booking.checkout_date <= checkout)
        )
    ).subquery()

    available = Room.query.filter(Room.status == 'Available', ~Room.id.in_(booked_rooms)).all()
    return render_template('availability_results.html', rooms=available, checkin=checkin, checkout=checkout)

@app.route('/api/room/<int:room_id>')
def api_room_details(room_id):
    room = Room.query.get_or_404(room_id)
    return jsonify({
        'id': room.id,
        'name': room.name,
        'price': room.price,
        'status': room.status,
        'features': room.features,
        'facility': room.facility,
        'guests': room.guests
    })

@app.route('/api/rooms')
def get_rooms():
    rooms = Room.query.all()
    return jsonify([
        {
            'id': room.id,
            'name': room.name,
            'price': room.price,
            'status': room.status
        } for room in rooms
    ])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if request.form['password'] != request.form['confirm_password']:
            return render_template('register.html', error="Passwords do not match")
        if User.query.filter(
            (User.username == request.form['username']) | (User.email == request.form['email'])
        ).first():
            return render_template('register.html', error="Username or email already exists")
        new_user = User(
            username=request.form['username'],
            email=request.form['email']
        )
        new_user.set_password(request.form['password'])
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('home'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('home'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        return "Access Denied", 403
    return render_template('admin_dashboard.html', bookings=Booking.query.all(), rooms=Room.query.all())

@app.route('/admin/room/new', methods=['GET', 'POST'])
@login_required
def add_room():
    if not current_user.is_admin:
        return "Access Denied", 403
    if request.method == 'POST':
        new_room = Room(
            name=request.form['name'],
            price=request.form['price'],
            status=request.form.get('status', 'Available'),
            image=request.form.get('image', 'default.jpg')
        )
        db.session.add(new_room)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    return render_template('add_room.html')

@app.route('/admin/room/delete/<int:room_id>')
@login_required
def delete_room(room_id):
    if not current_user.is_admin:
        return "Access Denied", 403
    room = Room.query.get_or_404(room_id)
    db.session.delete(room)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/booking/update/<int:booking_id>/<string:status>')
@login_required
def update_booking(booking_id, status):
    if not current_user.is_admin:
        return "Access Denied", 403
    booking = Booking.query.get_or_404(booking_id)
    booking.status = status
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

# ------------------ Run App ------------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Room.query.first():
            db.session.add_all([
                Room(name="Single Bed Room", price=1000, image="single.jpg"),
                Room(name="Double Bed Room", price=1500, image="double.jpg"),
                Room(name="Family Bed Room", price=2500, image="family.jpg")
            ])
            db.session.commit()
        print("Database initialized")
    app.run(debug=True)
