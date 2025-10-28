# vulnerable_app/backend/server.py
"""
취약한 백엔드 서버 (5000번 포트)
HexStrike AI 공격 테스트용 - 의도적으로 취약점 포함
"""

from flask import Flask, request, jsonify, render_template_string
import sqlite3
import subprocess
import os

app = Flask(__name__)

# SQLite DB 초기화
def init_db():
    conn = sqlite3.connect('vulnerable.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT, password TEXT, email TEXT)''')
    c.execute("INSERT OR IGNORE INTO users VALUES (1, 'admin', 'admin123', 'admin@example.com')")
    c.execute("INSERT OR IGNORE INTO users VALUES (2, 'user', 'password', 'user@example.com')")
    conn.commit()
    conn.close()

init_db()

# ============================================
# 취약점 1: SQL Injection
# ============================================
@app.route('/api/login', methods=['POST'])
def login():
    """SQL Injection 취약점"""
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')
    
    # 위험: SQL Injection 취약
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    
    conn = sqlite3.connect('vulnerable.db')
    c = conn.cursor()
    
    try:
        c.execute(query)
        result = c.fetchone()
        conn.close()
        
        if result:
            return jsonify({
                "success": True,
                "message": "Login successful",
                "user": {
                    "id": result[0],
                    "username": result[1],
                    "email": result[3]
                }
            })
        else:
            return jsonify({"success": False, "message": "Invalid credentials"}), 401
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# 취약점 2: XSS (Cross-Site Scripting)
# ============================================
@app.route('/api/search', methods=['GET'])
def search():
    """XSS 취약점"""
    query = request.args.get('q', '')
    
    # 위험: 사용자 입력을 필터링 없이 HTML에 삽입
    html = f"""
    <html>
    <body>
        <h1>Search Results</h1>
        <p>You searched for: {query}</p>
        <p>No results found.</p>
    </body>
    </html>
    """
    
    return render_template_string(html)


# ============================================
# 취약점 3: Command Injection
# ============================================
@app.route('/api/ping', methods=['POST'])
def ping():
    """Command Injection 취약점"""
    data = request.get_json()
    host = data.get('host', '127.0.0.1')
    
    # 위험: 사용자 입력을 직접 쉘 명령어에 사용
    try:
        result = subprocess.check_output(f"ping -c 1 {host}", shell=True, text=True)
        return jsonify({"success": True, "result": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# 취약점 4: Path Traversal
# ============================================
@app.route('/api/file', methods=['GET'])
def get_file():
    """Path Traversal 취약점"""
    filename = request.args.get('name', 'default.txt')
    
    # 위험: 경로 검증 없이 파일 읽기
    try:
        with open(f"./files/{filename}", 'r') as f:
            content = f.read()
        return jsonify({"success": True, "content": content})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 404


# ============================================
# 취약점 5: Insecure Deserialization
# ============================================
@app.route('/api/deserialize', methods=['POST'])
def deserialize():
    """Insecure Deserialization 취약점"""
    import pickle
    
    data = request.data
    
    # 위험: 신뢰할 수 없는 데이터를 pickle로 역직렬화
    try:
        obj = pickle.loads(data)
        return jsonify({"success": True, "data": str(obj)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# 취약점 6: SSRF (Server-Side Request Forgery)
# ============================================
@app.route('/api/fetch', methods=['POST'])
def fetch_url():
    """SSRF 취약점"""
    import requests
    
    data = request.get_json()
    url = data.get('url', '')
    
    # 위험: 사용자가 제공한 URL로 요청
    try:
        response = requests.get(url, timeout=5)
        return jsonify({
            "success": True,
            "status_code": response.status_code,
            "content": response.text[:500]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# 취약점 7: Weak Authentication
# ============================================
@app.route('/api/admin', methods=['GET'])
def admin_panel():
    """약한 인증"""
    # 위험: 쉽게 추측 가능한 인증
    auth_token = request.headers.get('X-Auth-Token')
    
    if auth_token == 'admin123':  # 하드코딩된 토큰
        return jsonify({
            "success": True,
            "message": "Welcome admin!",
            "users": ["admin", "user1", "user2"]
        })
    else:
        return jsonify({"success": False, "message": "Unauthorized"}), 401


# ============================================
# 취약점 8: Information Disclosure
# ============================================
@app.route('/api/debug', methods=['GET'])
def debug_info():
    """정보 노출"""
    # 위험: 민감한 정보 노출
    return jsonify({
        "success": True,
        "debug_info": {
            "python_version": os.sys.version,
            "environment": dict(os.environ),
            "database": "vulnerable.db",
            "secret_key": "super-secret-key-12345"
        }
    })


# ============================================
# 정상 엔드포인트
# ============================================
@app.route('/')
def index():
    return jsonify({
        "service": "Vulnerable API Server",
        "version": "1.0.0",
        "warning": "⚠️  This server is intentionally vulnerable for testing purposes!",
        "endpoints": [
            "/api/login - SQL Injection",
            "/api/search - XSS",
            "/api/ping - Command Injection",
            "/api/file - Path Traversal",
            "/api/deserialize - Insecure Deserialization",
            "/api/fetch - SSRF",
            "/api/admin - Weak Authentication",
            "/api/debug - Information Disclosure"
        ]
    })

@app.route('/api/users', methods=['GET'])
def list_users():
    """정상적인 사용자 목록 (안전)"""
    conn = sqlite3.connect('vulnerable.db')
    c = conn.cursor()
    c.execute("SELECT id, username, email FROM users")
    users = [{"id": row[0], "username": row[1], "email": row[2]} for row in c.fetchall()]
    conn.close()
    
    return jsonify({"success": True, "users": users})


if __name__ == '__main__':
    print("⚠️  WARNING: This is a VULNERABLE server for testing only!")
    print("Do NOT expose this to the internet!")
    print("Starting on http://0.0.0.0:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=True)