#!/usr/bin/env python3
"""
dashboard/app.py
Flask 웹 대시보드 (SPA - Single Page Application)
UI 재구성 버전 (v3 - 버그 수정 및 차트 추가)
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user, AnonymousUserMixin
import requests
import os

# Flask 앱 생성
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production-12345')
app.config['API_URL'] = os.environ.get('API_URL', 'http://localhost:8000') # <-- 실제 API 서버 주소
app.config['MFA_ENABLED'] = False
app.config['ITEMS_PER_PAGE'] = 50
app.config['REPORT_DIR'] = os.path.join(app.root_path, 'generated_reports') # 보고서 저장 경로 (예시)

# LoginManager 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class AnonymousUser(AnonymousUserMixin):
    def has_mfa(self):
        return False

login_manager.anonymous_user = AnonymousUser

# 간단한 사용자 클래스
class User(UserMixin):
    def __init__(self, user_id, user_data=None):
        self.id = user_id
        self.data = user_data or {}
        self.role = self.data.get('role', 'user')
    
    def has_mfa(self):
        return app.config['MFA_ENABLED'] and self.data.get('mfa_enabled', False)
    
    def is_admin(self):
        return self.role == 'admin'

# 사용자 데이터 (실제로는 DB 사용)
USERS = {
    'admin': {
        'password': 'admin', # script.js와 일치
        'role': 'admin',
        'mfa_secret': 'BASE32SECRETCODE',
        'mfa_enabled': False, # 테스트를 위해 False로 둠
    }
}

@login_manager.user_loader
def load_user(user_id):
    if user_id in USERS:
        return User(user_id, USERS[user_id])
    return None

# API 헬퍼 함수
def api_request(endpoint, method='GET', data=None):
    url = f"{app.config['API_URL']}{endpoint}"
    try:
        if method == 'GET':
            response = requests.get(url, timeout=5)
        elif method == 'POST':
            response = requests.post(url, json=data, timeout=5)
        elif method == 'DELETE':
            response = requests.delete(url, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 204: # DELETE 성공 (No Content)
             return {"success": True}
        else:
            # API가 404 등을 반환할 때 JSON이 아닐 수 있음
            try:
                error_json = response.json()
            except requests.exceptions.JSONDecodeError:
                error_json = {"error": response.text}
            print(f"API Error Response: {error_json}")
            return {"error": f"API error: {response.status_code}", "detail": error_json}
            
    except Exception as e:
        print(f"API Request Exception: {e}")
        return {"error": str(e)}

# --- 인증 라우트 (AJAX 처리) ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if username in USERS and USERS[username]['password'] == password:
            user = User(username, USERS[username])
            
            if user.has_mfa():
                session['mfa_user_id'] = user.id
                return jsonify({"success": True, "mfa_required": True})
            else:
                login_user(user)
                return jsonify({"success": True, "mfa_required": False})
        
        return jsonify({"success": False, "error": "Invalid credentials"}), 401
    
    return render_template('login.html')

@app.route('/verify-mfa-ajax', methods=['POST'])
def verify_mfa_ajax():
    if 'mfa_user_id' not in session:
        return jsonify({"success": False, "error": "Session expired"}), 400
    
    username = session['mfa_user_id']
    user_data = USERS.get(username)
    data = request.get_json()
    code = data.get('code')

    if not user_data or not code:
        return jsonify({"success": False, "error": "Invalid request"}), 400

    # (테스트용) 123456 하드코딩 (pyotp 권장)
    if code == '123456':
        user = User(username, user_data)
        login_user(user)
        session.pop('mfa_user_id', None)
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Invalid verification code"}), 401

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- 메인 대시보드 ---

@app.route('/')
@app.route('/dashboard')
@login_required
def index():
    """메인 SPA 셸(Shell) 렌더링"""
    return render_template('index.html')

# --- 데이터 제공 API 엔드포인트 ---

@app.route('/api/get-stats')
@login_required
def get_stats():
    """대시보드 통계 데이터 (원형 차트 데이터 포함)"""
    stats = api_request('/api/stats/overview')
    rules_data = api_request('/api/rules/active?category=all')
    
    stats_summary = stats if stats and 'error' not in stats else {}
    rules_list = rules_data.get('rules', []) if rules_data else []
    
    stats_summary['active_rules_count'] = len(rules_list)
    stats_summary['ai_rules_count'] = len([r for r in rules_list if 'auto_generated' in r.get('file', '')])
    stats_summary['drop_rules_count'] = len([r for r in rules_list if r.get('action') == 'drop'])
    
    # (중요) 원형 차트를 위해 /api/stats/overview가 이 'severity_distribution'을 반환해야 함
    # 만약 반환하지 않는다면, 여기서 임시 데이터를 제공하거나 API 서버를 수정해야 함
    if 'severity_distribution' not in stats_summary:
        stats_summary['severity_distribution'] = {
            "critical": stats_summary.get("critical_alerts_24h", 1), # 예시 데이터
            "high": stats_summary.get("total_alerts_24h", 10) // 2,
            "medium": stats_summary.get("total_alerts_24h", 10) // 3,
            "low": stats_summary.get("total_alerts_24h", 10) // 4
        }
    
    return jsonify(stats_summary)

@app.route('/api/get-timeline')
@login_required
def get_timeline():
    """대시보드 타임라인 차트 데이터"""
    hours = request.args.get('hours', 24, type=int)
    timeline = api_request(f'/api/stats/timeline?hours={hours}')
    # (API가 에러 반환 시 임시 데이터 제공)
    if not timeline or 'error' in timeline:
        timeline = {"timeline": [
            {"time": "00:00", "count": 0}, {"time": "04:00", "count": 0}, 
            {"time": "08:00", "count": 0}, {"time": "12:00", "count": 0},
            {"time": "16:00", "count": 0}, {"time": "20:00", "count": 0}
        ]}
    return jsonify(timeline)

@app.route('/api/get-recent-alerts')
@login_required
def get_recent_alerts():
    """대시보드 최근 알림 (상위 5개)"""
    data = api_request('/api/logs/suricata?count=5')
    return jsonify(data if data and 'error' not in data else {'logs': []})

@app.route('/api/get-alerts')
@login_required
def get_alerts():
    """알림 페이지 데이터 (필터링 포함)"""
    count = request.args.get('count', 50, type=int)
    severity = request.args.get('severity', 'all')
    
    endpoint = f'/api/logs/suricata?count={count}'
    if severity != 'all':
        endpoint += f'&severity={severity}'
    
    data = api_request(endpoint)
    return jsonify(data if data and 'error' not in data else {'logs': []})

@app.route('/api/get-rules')
@login_required
def get_rules():
    """룰 관리 페이지 데이터 (API 서버에서 가져오도록 수정)"""
    
    # API 서버에 활성 룰 요청
    # /api/get-stats에서 사용하던 엔드포인트와 동일하게 맞춥니다.
    data = api_request('/api/rules/active?category=all') 
    
    # API가 에러를 반환하거나 데이터가 없는 경우
    if not data or 'error' in data:
        print(f"API Error in /api/get-rules: {data.get('error')}")
        return jsonify({'rules': [], 'total': 0})
    
    # API 응답 형식이 {"rules": [...], "total": N} 형태일 것
    return jsonify(data)

@app.route('/api/rules/<int:sid>', methods=['DELETE'])
@login_required
def delete_rule(sid):
    """룰 삭제 (auto_generated 룰만)"""
    # result = api_request(f'/api/rules/delete/{sid}', 'DELETE') # 실제 API 호출
    print(f"Simulating delete rule: {sid}")
    result = {"success": True, "message": f"Rule {sid} deleted"}
    return jsonify(result)

@app.route('/api/get-reports')
@login_required
def get_reports():
    """보고서 목록"""
    data = api_request('/api/reports/list')
    # (API가 에러 반환 시 임시 데이터 제공)
    if not data or 'error' in data:
        data = {"reports": [
            {"filename": "simulated_report_1.pdf", "size": 12345, "created_at": "2025-11-10T10:00:00Z"},
            {"filename": "simulated_report_2.pdf", "size": 67890, "created_at": "2025-11-09T14:30:00Z"}
        ]}
    return jsonify(data)

@app.route('/api/generate-report', methods=['POST'])
@login_required
def generate_report():
    """보고서 생성"""
    data = request.get_json()
    result = api_request('/api/reports/generate', 'POST', data)
    return jsonify(result if result and 'error' not in result else {"success": False, "error": result.get('error', 'Unknown error')})

@app.route('/api/reports/download/<path:filename>')
@login_required
def download_report(filename):
    """보고서 다운로드"""
    if not os.path.exists(app.config['REPORT_DIR']):
        os.makedirs(app.config['REPORT_DIR'])
    
    # (시뮬레이션을 위해 임시 파일 생성)
    dummy_path = os.path.join(app.config['REPORT_DIR'], filename)
    if not os.path.exists(dummy_path):
        with open(dummy_path, 'w') as f:
            f.write(f"This is a test report for {filename}")
            
    return send_from_directory(app.config['REPORT_DIR'], filename, as_attachment=True)

@app.route('/api/reports/delete/<path:filename>', methods=['DELETE'])
@login_required
def delete_report(filename):
    """보고서 삭제"""
    # result = api_request(f'/api/reports/delete/{filename}', 'DELETE') # 실제 API 호출
    print(f"Simulating delete report: {filename}")
    file_path = os.path.join(app.config['REPORT_DIR'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    result = {"success": True, "message": f"Report {filename} deleted"}
    return jsonify(result)

@app.route('/api/get-comparison')
@login_required
def get_comparison():
    """Red vs Blue 비교 분석 (비활성화)"""
    return jsonify({
        'disabled': True,
        'message': 'HexStrike AI 기능은 현재 준비 중입니다. Ollama 모델 선택 후 활성화 예정입니다.',
        'defense_events': [],
        'attack_events': [],
        'analysis': { 'attempted': [], 'blocked': [] }
    })

@app.route('/api/block-ip', methods=['POST'])
@login_required
def block_ip_route():
    """IP 차단"""
    data = request.get_json()
    # result = api_request('/api/action/block-ip', 'POST', data) # 실제 API 호출
    print(f"Simulating block IP: {data.get('ip')}")
    result = {"success": True, "message": f"IP {data.get('ip')} blocked (simulated)"}
    return jsonify(result)

# --- 에러 핸들러 ---
@app.errorhandler(404)
def page_not_found(e):
    if request.path.startswith('/api/'):
        return jsonify(error="Not Found"), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    if request.path.startswith('/api/'):
        return jsonify(error="Internal Server Error"), 500
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)