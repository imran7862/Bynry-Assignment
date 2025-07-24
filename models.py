from flask_sqlalchemy import SQLAlchemy
from decimal import Decimal

db = SQLAlchemy()

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    sku = db.Column(db.String(64), unique=True, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)

class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)