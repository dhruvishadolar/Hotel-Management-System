# models.py

from app import db  # Import the db instance from app.py

class Room(db.Model):
    __tablename__ = 'room'
    __table_args__ = {'extend_existing': True}  # Allows redefinition if needed
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Available')

class Booking(db.Model):
    __tablename__ = 'booking'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(100), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    status = db.Column(db.String(20), default='Pending')
