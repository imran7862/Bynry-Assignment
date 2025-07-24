from flask import Flask, request, jsonify
from models import db, Product, Inventory
from decimal import Decimal

app = Flask(__name__)
app.config.from_pyfile('config.py')
db.init_app(app)

@app.route('/api/products', methods=['POST'])
def create_product():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON body"}), 400

    required_fields = ['name', 'sku']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"'{field}' is required"}), 400

    if Product.query.filter_by(sku=data['sku']).first():
        return jsonify({"error": "SKU already exists"}), 400

    try:
        price = Decimal(str(data.get('price', '0.00')))
    except:
        return jsonify({"error": "Invalid price format"}), 400

    product = Product(name=data['name'], sku=data['sku'], price=price)
    db.session.add(product)
    try:
        db.session.flush()
    except:
        db.session.rollback()
        return jsonify({"error": "Product insert failed"}), 500

    warehouse_id = data.get('warehouse_id')
    initial_qty = data.get('initial_quantity')
    if warehouse_id is not None and initial_qty is not None:
        try:
            qty = int(initial_qty)
        except ValueError:
            return jsonify({"error": "Quantity must be an integer"}), 400
        inventory = Inventory(product_id=product.id, warehouse_id=warehouse_id, quantity=qty)
        db.session.add(inventory)

    try:
        db.session.commit()
    except:
        db.session.rollback()
        return jsonify({"error": "Transaction failed"}), 500

    return jsonify({"message": "Product created", "product_id": product.id}), 201

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)