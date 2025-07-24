import datetime

from flask import Flask, request, jsonify
from sqlalchemy import func

from models import db, Product, Inventory, InventoryTransaction, Warehouse, Supplier
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

@app.route('/api/companies/<int:company_id>/alerts/low-stock', methods=['GET'])
def low_stock_alerts(company_id):
    cutoff_date = datetime.utcnow() - datetime.timedelta(days=30)

    # Get recent sales activity (last 30 days, negative qty = sale)
    recent_sales = (
        db.session.query(
            InventoryTransaction.product_id,
            InventoryTransaction.warehouse_id,
            func.sum(-InventoryTransaction.change_qty).label('total_sold'),
            (func.sum(-InventoryTransaction.change_qty) / 30.0).label('avg_daily_sold')
        )
        .filter(InventoryTransaction.change_qty < 0)
        .filter(InventoryTransaction.timestamp >= cutoff_date)
        .group_by(InventoryTransaction.product_id, InventoryTransaction.warehouse_id)
        .subquery()
    )

    inventory_with_sales = (
        db.session.query(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Product.sku,
            Product.threshold,
            Inventory.warehouse_id,
            Warehouse.name.label("warehouse_name"),
            Inventory.quantity.label("current_stock"),
            Supplier.id.label("supplier_id"),
            Supplier.name.label("supplier_name"),
            Supplier.contact_email,
            recent_sales.c.avg_daily_sold
        )
        .join(Inventory, Inventory.product_id == Product.id)
        .join(Warehouse, Warehouse.id == Inventory.warehouse_id)
        .join(Supplier, Supplier.id == Product.supplier_id)
        .join(recent_sales, (recent_sales.c.product_id == Product.id) & (recent_sales.c.warehouse_id == Inventory.warehouse_id))
        .filter(Warehouse.company_id == company_id)
        .filter(Inventory.quantity < Product.threshold)
        .all()
    )

    alerts = []
    for row in inventory_with_sales:
        avg_daily = row.avg_daily_sold or 1  # avoid division by zero
        days_until_stockout = max(1, int(row.current_stock / avg_daily))

        alerts.append({
            "product_id": row.product_id,
            "product_name": row.product_name,
            "sku": row.sku,
            "warehouse_id": row.warehouse_id,
            "warehouse_name": row.warehouse_name,
            "current_stock": row.current_stock,
            "threshold": row.threshold,
            "days_until_stockout": days_until_stockout,
            "supplier": {
                "id": row.supplier_id,
                "name": row.supplier_name,
                "contact_email": row.contact_email
            }
        })

    return jsonify({"alerts": alerts, "total_alerts": len(alerts)})


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)