"""
Lab 6 – API Gateway (port 5000)
=================================
Điểm vào duy nhất cho toàn bộ client requests.
Thực hiện:
  1. Kiểm tra bảo mật (Token Validation)
  2. Kiểm tra phân quyền (Admin vs. User)
  3. Định tuyến (Routing) đến microservice phù hợp
  4. Xử lý lỗi khi backend service không phản hồi (503)

Tiên quyết:
    Product Service (product_service/app.py) phải đang chạy trên port 5001.

Chạy:
    cd api_gateway
    python gateway.py

Test:
    # Không có token → 401
    curl http://127.0.0.1:5000/api/products

    # Token user → 200
    curl -H "Authorization: Bearer valid-user-token" http://127.0.0.1:5000/api/products

    # Token user POST → 403 (chỉ admin)
    curl -X POST -H "Authorization: Bearer valid-user-token" http://127.0.0.1:5000/api/products

    # Token admin POST → chuyển tiếp đến Product Service
    curl -X POST -H "Authorization: Bearer valid-admin-token" \\
         -H "Content-Type: application/json" \\
         -d '{"name":"New Item","price":99.9,"stock":10}' \\
         http://127.0.0.1:5000/api/products
"""

from flask import Flask, request, jsonify, make_response
import requests as http_client

app = Flask(__name__)

# ── Cấu hình địa chỉ các backend services ────────────────────────────────────
SERVICE_REGISTRY = {
    'products': 'http://127.0.0.1:5001',
    'users':    'http://127.0.0.1:5002',   # chưa triển khai – placeholder
    'orders':   'http://127.0.0.1:5003',   # chưa triển khai – placeholder
}

GATEWAY_PORT = 5000

# Token hợp lệ (production: thay bằng JWT verification)
VALID_TOKENS = {
    'valid-admin-token': 'admin',
    'valid-user-token':  'user',
}


# ── Hàm bảo mật (Cross-Cutting Concern) ──────────────────────────────────────

def validate_token(auth_header: str):
    """Xác thực Bearer token. Trả về (is_valid, role, error_message)."""
    if not auth_header:
        return False, None, "Thiếu Authorization header."
    parts = auth_header.split("Bearer ")
    if len(parts) != 2 or not parts[1].strip():
        return False, None, "Định dạng Authorization header không hợp lệ."
    token = parts[1].strip()
    role = VALID_TOKENS.get(token)
    if role:
        return True, role, None
    return False, None, "Token không hợp lệ hoặc đã hết hạn."


def proxy_request(target_base_url: str):
    """Chuyển tiếp request đến backend service và trả về response."""
    # Xây dựng URL đích
    path = request.full_path  # bao gồm query string
    # Bỏ tiền tố "/api/products" để giữ nguyên path
    target_url = target_base_url + path

    # Lọc header Host để tránh xung đột
    headers = {k: v for k, v in request.headers if k.lower() != 'host'}

    try:
        response = http_client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            timeout=5,
        )
        gw_response = make_response(response.content, response.status_code)
        for key, value in response.headers.items():
            if key.lower() not in ('content-encoding', 'transfer-encoding', 'connection'):
                gw_response.headers[key] = value
        return gw_response

    except http_client.exceptions.ConnectionError:
        return jsonify({
            'error': 'Service Unavailable',
            'details': f'Backend service tại {target_base_url} không phản hồi.'
        }), 503
    except http_client.exceptions.Timeout:
        return jsonify({
            'error': 'Gateway Timeout',
            'details': 'Backend service không phản hồi trong thời gian cho phép.'
        }), 504
    except http_client.exceptions.RequestException as e:
        return jsonify({'error': 'Bad Gateway', 'details': str(e)}), 502


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/api/products', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/api/products/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def route_product_service(path):
    """Định tuyến tất cả /api/products/* đến Product Service."""
    auth_header = request.headers.get('Authorization', '')
    is_valid, role, error = validate_token(auth_header)

    # 1. Kiểm tra xác thực
    if not is_valid:
        return jsonify({'error': 'Unauthorized', 'details': error}), 401

    # 2. Kiểm tra phân quyền cho thao tác thay đổi dữ liệu
    if request.method in ('POST', 'PUT', 'DELETE') and role != 'admin':
        return jsonify({
            'error': 'Forbidden',
            'details': 'Chỉ Admin mới được phép thêm, sửa, xóa sản phẩm.'
        }), 403

    # 3. Định tuyến đến Product Service
    return proxy_request(SERVICE_REGISTRY['products'])


@app.route('/health', methods=['GET'])
def health():
    """Health check của Gateway."""
    return jsonify({'service': 'api-gateway', 'status': 'ok'}), 200


if __name__ == '__main__':
    print(f'API Gateway khởi động tại http://127.0.0.1:{GATEWAY_PORT}')
    print(f'Định tuyến /api/products → {SERVICE_REGISTRY["products"]}')
    app.run(port=GATEWAY_PORT, debug=True)