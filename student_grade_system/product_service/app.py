"""
Lab 5 – Product Microservice (port 5001)
=========================================
Flask microservice độc lập quản lý danh mục sản phẩm.
Sử dụng SQLAlchemy + SQLite (database riêng, không chia sẻ với service khác).

Chạy:
    cd product_service
    python app.py

Test:
    curl http://127.0.0.1:5001/api/products
    curl http://127.0.0.1:5001/api/products/1
    curl "http://127.0.0.1:5001/api/products?q=Laptop"
"""

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# Mỗi microservice có database RIÊNG BIỆT
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "products.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# ── Model (Database Schema) ───────────────────────────────────────────────────

class Product(db.Model):
    __tablename__ = 'products'

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    price       = db.Column(db.Float, nullable=False)
    stock       = db.Column(db.Integer, nullable=False, default=0)
    is_active   = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id':          self.id,
            'name':        self.name,
            'description': self.description,
            'price':       self.price,
            'stock':       self.stock,
            'is_active':   self.is_active,
        }


# ── Khởi tạo DB + seed data ───────────────────────────────────────────────────

def init_db():
    with app.app_context():
        db.create_all()
        if Product.query.count() == 0:
            samples = [
                Product(name='Laptop X1',    description='Laptop hiệu năng cao.',       price=1500.00, stock=10),
                Product(name='Mouse Pro',    description='Chuột không dây ergonomic.',   price=50.00,   stock=50),
                Product(name='Keyboard K2',  description='Bàn phím cơ RGB.',             price=120.00,  stock=30),
                Product(name='Monitor 4K',   description='Màn hình 27 inch 4K IPS.',     price=450.00,  stock=15),
            ]
            db.session.add_all(samples)
            db.session.commit()
            print('[Product Service] Database khởi tạo với dữ liệu mẫu.')


# ── REST API Endpoints (Service Contract từ Lab 4) ────────────────────────────

@app.route('/api/products', methods=['GET'])
def list_products():
    """GET /api/products – Liệt kê và tìm kiếm sản phẩm."""
    query = request.args.get('q')
    products = Product.query.filter_by(is_active=True)
    if query:
        products = products.filter(Product.name.ilike(f'%{query}%'))
    return jsonify([p.to_dict() for p in products.all()]), 200


@app.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """GET /api/products/<id> – Xem chi tiết sản phẩm."""
    product = Product.query.get(product_id)
    if product and product.is_active:
        return jsonify(product.to_dict()), 200
    return jsonify({'message': 'Sản phẩm không tìm thấy hoặc không còn hoạt động.'}), 404


@app.route('/api/products', methods=['POST'])
def create_product():
    """POST /api/products – Thêm sản phẩm mới (Admin)."""
    data = request.json or {}
    name  = data.get('name', '').strip()
    price = data.get('price')
    stock = data.get('stock', 0)

    if not name:
        return jsonify({'error': 'Tên sản phẩm không được để trống.'}), 400
    if price is None or float(price) <= 0:
        return jsonify({'error': 'Giá sản phẩm phải lớn hơn 0.'}), 400

    product = Product(
        name=name,
        description=data.get('description', ''),
        price=float(price),
        stock=int(stock),
    )
    db.session.add(product)
    db.session.commit()
    return jsonify(product.to_dict()), 201


@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """PUT /api/products/<id> – Cập nhật sản phẩm (Admin)."""
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Không tìm thấy sản phẩm.'}), 404

    data = request.json or {}
    if 'name' in data:
        product.name = data['name']
    if 'description' in data:
        product.description = data['description']
    if 'price' in data:
        if float(data['price']) <= 0:
            return jsonify({'error': 'Giá phải lớn hơn 0.'}), 400
        product.price = float(data['price'])
    if 'stock' in data:
        if int(data['stock']) < 0:
            return jsonify({'error': 'Tồn kho không được âm.'}), 400
        product.stock = int(data['stock'])

    db.session.commit()
    return jsonify(product.to_dict()), 200


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """DELETE /api/products/<id> – Ẩn sản phẩm (soft delete, Admin)."""
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Không tìm thấy sản phẩm.'}), 404
    product.is_active = False
    db.session.commit()
    return jsonify({'message': f'Sản phẩm ID {product_id} đã bị xóa (ẩn).'}), 200


# ── Health check ──────────────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'service': 'product-service', 'status': 'ok'}), 200


if __name__ == '__main__':
    init_db()
    print('Product Microservice đang chạy tại http://127.0.0.1:5001')
    app.run(port=5001, debug=True)