from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='agent')

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False)
    passport = db.Column(db.String(20), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    vehicles = db.relationship('Vehicle', backref='client', lazy=True)

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    vin = db.Column(db.String(17), unique=True, nullable=False)
    reg_number = db.Column(db.String(20), unique=True, nullable=False)
    engine_power = db.Column(db.Integer)  # в лошадиных силах

class Policy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), unique=True, nullable=False)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    cost = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='active')
    notes = db.Column(db.Text)  # Для причины отмены и других примечаний
    vehicle = db.relationship('Vehicle', backref='policies')
