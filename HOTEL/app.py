# -*- coding: utf-8 -*-
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import or_, and_
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, flash, redirect, url_for
import sqlite3

conn = sqlite3.connect("database.db")
c = conn.cursor()

#Insert sample rooms
c.execute("INSERT INTO rooms (name, price) VALUES ('Deluxe Room', 3000)")
c.execute("INSERT INTO rooms (name, price) VALUES ('Standard Room', 2000)")
c.execute("INSERT INTO rooms (name, price) VALUES ('Suite Room', 5000)")

conn.commit()
conn.close()

print("Test rooms added successfully!")

# Create and configure the Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://hotem_management_2l4a_user:pnQB0C06cNyGohtSmV48zpgnRMwYyrht@dpg-d0pcu3muk2gs739gi0b0-a/hotem_management_2l4a'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'hotelmanagement'  # Replace with a strong secret key

# Initialize the database with the app
db = SQLAlchemy(app)

# Ensure the database and table exist
def create_tables():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    
    #Create 'rooms' table
    c.execute('''CREATE TABLE IF NOT EXISTS rooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    price INTEGER NOT NULL
                )''')
    
    conn.commit()
    conn.close()

# Call function at startup to ensure tables exist
create_tables()

@app.route("/messages")
def messages():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM messages")
    messages = c.fetchall()
    conn.close()
    return render_template("messages.html", messages=messages)



# Define your models
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

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(100), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    checkin_date = db.Column(db.Date, nullable=False)
    checkout_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Pending')

# Initialize Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes

# Home route: Redirect to /rooms
@app.route('/')
def home():
    rooms_list = Room.query.all()  # Fetch all rooms
    print("Rooms fetched:", rooms_list)  #  Debugging step

    return render_template('index.html', rooms=rooms_list)  # Pass rooms to template




# Rooms route � renders rooms.html from the templates folder
@app.route('/rooms', methods=['GET'])
def rooms():
    rooms_list = Room.query.filter_by(status='Available').all()
    return render_template('rooms.html', rooms=rooms_list)

@app.route('/facilities.html')
def facilities():
    return render_template('facilities.html')

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        subject = request.form["subject"]
        message = request.form["message"]

        # Store message in database
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO messages (name, email, subject, message) VALUES (?, ?, ?, ?)", 
                  (name, email, subject, message))
        conn.commit()
        conn.close()

        flash("Your message has been sent successfully!", "success")
        return redirect(url_for("contact"))  # Redirect to prevent form resubmission

    return render_template("contact.html")

@app.route('/about.html')
def about():
    return render_template('about.html')


# Booking route
@app.route('/book/<int:room_id>', methods=['GET', 'POST'])
def book(room_id):
    room = Room.query.get_or_404(room_id)
    checkin = request.args.get('checkin')
    checkout = request.args.get('checkout')
    if request.method == 'POST':
        customer_name = request.form.get('customer_name')
        customer_email = request.form.get('customer_email')
        try:
            checkin_date = datetime.strptime(checkin, '%Y-%m-%d').date()
            checkout_date = datetime.strptime(checkout, '%Y-%m-%d').date()
        except ValueError:
            return "Invalid date format", 400

        new_booking = Booking(
            customer_name=customer_name,
            customer_email=customer_email,
            room_id=room_id,
            checkin_date=checkin_date,
            checkout_date=checkout_date,
            status='Confirmed'
        )
        db.session.add(new_booking)
        db.session.commit()
        return render_template('booking_confirmation.html', booking=new_booking, room=room)
    return render_template('booking.html', room=room, checkin=checkin, checkout=checkout)

# API endpoint for room details
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

@app.route('/room/<int:room_id>')
def room_details(room_id):
    room = Room.query.get_or_404(room_id)
    return render_template('room_details.html', room=room)


# Availability route to filter rooms based on check-in/check-out
@app.route('/availability', methods=['POST'])
def check_availability():
    checkin = request.form.get('checkin')
    checkout = request.form.get('checkout')
    try:
        checkin_date = datetime.strptime(checkin, '%Y-%m-%d').date()
        checkout_date = datetime.strptime(checkout, '%Y-%m-%d').date()
    except ValueError:
        return "Invalid date format", 400

    if checkin_date >= checkout_date:
        return "Check-in date must be before check-out date", 400

    booked_room_ids = db.session.query(Booking.room_id).filter(
        Booking.status == 'Confirmed',
        or_(
            and_(Booking.checkin_date <= checkin_date, Booking.checkout_date > checkin_date),
            and_(Booking.checkin_date < checkout_date, Booking.checkout_date >= checkout_date),
            and_(Booking.checkin_date >= checkin_date, Booking.checkout_date <= checkout_date)
        )
    ).subquery()

    available_rooms = Room.query.filter(
        Room.status.ilike('available'),
        ~Room.id.in_(booked_room_ids)
    ).all()

    return render_template('availability_results.html', rooms=available_rooms, checkin=checkin, checkout=checkout)

# API endpoint to get all rooms (if needed)
@app.route('/api/room.html')
def get_rooms():
    rooms_list = Room.query.all()
    return jsonify([
        {
            'id': room.id,
            'name': room.name,
            'price': room.price,
            'status': room.status
        } for room in rooms_list
    ])

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Optionally, verify that password and confirm_password match
        if password != confirm_password:
            error = "Passwords do not match."
            return render_template('register.html', error=error)
        
        if User.query.filter((User.username == username) | (User.email == email)).first():
            error = "Username or email already exists."
            return render_template('register.html', error=error)
        
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('home'))
    return render_template('register.html')


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')  # Retrieve email
        password = request.form.get('password')
        user_obj = User.query.filter_by(email=email).first()  # Query by email
        if user_obj and user_obj.check_password(password):
            login_user(user_obj)
            return redirect(url_for('home'))
        else:
            error = "Invalid email or password."
            return render_template('login.html', error=error)
    return render_template('login.html')


#logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# Admin dashboard
@app.route('/admin')
@login_required
def admin_dashboard():
    bookings = Booking.query.all()
    rooms_list = Room.query.all()
    return render_template('admin_dashboard.html', bookings=bookings, rooms=rooms_list)

# Add new room (admin)
@app.route('/admin/room/new', methods=['GET', 'POST'])
@login_required
def add_room():
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        status = request.form.get('status', 'Available')
        
        new_room = Room(name=name, price=float(price), status=status)
        db.session.add(new_room)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    
    return render_template('add_room.html')

# Edit room (admin)
@app.route("/admin/edit_room/<int:room_id>", methods=["GET", "POST"])
def edit_room(room_id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]

        c.execute("UPDATE rooms SET name = ?, price = ? WHERE id = ?", (name, price, room_id))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_dashboard"))  # Redirect to admin panel

    # Fetch the room details
    c.execute("SELECT * FROM rooms WHERE id = ?", (room_id,))
    room = c.fetchone()
    conn.close()

    if not room:
        return "Room not found", 404

    return render_template("edit_room.html", room=room)# Delete room (admin)


@app.route('/admin/room/delete/<int:room_id>')
@login_required
def delete_room(room_id):
    room_obj = Room.query.get_or_404(room_id)
    db.session.delete(room_obj)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

# Update booking status (admin)
@app.route('/admin/booking/update/<int:booking_id>/<string:status>')
@login_required
def update_booking(booking_id, status):
    booking_obj = Booking.query.get_or_404(booking_id)
    booking_obj.status = status
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

# Test route
@app.route('/test/<int:room_id>')
def test_room(room_id):
    room_obj = Room.query.get_or_404(room_id)
    return render_template('test_room.html', room=room_obj)

if __name__ == '__main__':
    with app.app_context():  #  Ensures database operations run inside Flask context
        db.create_all()  #  Create tables if they don�t exist

        #  Add sample rooms only if the database is empty
        if not Room.query.first():  
            db.session.add(Room(name="Single Bed Room", price=1000, image="single.jpg"))
            db.session.add(Room(name="Double Bed Room", price=1500, image="double.jpg"))
            db.session.add(Room(name="Family Bed Room", price=2500, image="family.jpg"))
            db.session.commit()
        print("Rooms added to database!")

    app.run(debug=True)  # Start Flask app

