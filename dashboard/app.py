#!/usr/bin/env python3
"""
Flask 웹 대시보드
SIEM 스타일 보안 모니터링 대시보드
HexStrike 비활성화 버전 (향후 사용 대비)
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps
import requests
from datetime import datetime, timedelta
import os
from pathlib import Path

# Flask 앱 생성
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production-12345')
app.config['API_URL'] = os.environ.get('API_URL', 'http://localhost:8000')
app.config['MFA_ENABLED'] = False  # 개발 환경에서는 MFA 비활성화
app.config['ITEMS_PER_PAGE'] = 50

# LoginManager 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 간단한 사용자 클래스
class User(UserMixin):
    def __init__(self, user_id, user_data=None):
        self.id = user_id
        self.data = user_data or {}
        self.role = self.data.get('role', 'user')
    
    def has_mfa(self):
        return False  # MFA 비활성화
    
    def is_admin(self):
        return self.role == 'admin'

# 사용자 데이터 (실제로는 DB 사용)
USERS = {
    'admin': {
        'password': 'admin123',
        'role': 'admin'
    }
}

@login_manager.user_loader
def load_user(user_id):
    if user_id in USERS:
        return User(user_id, USERS[user_id])
    return None

# API 헬퍼 함수
def api_request(endpoint, method='GET', data=None):
    """FastAPI 백엔드 요청"""
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
        else:
            return {"error": f"API error: {response.status_code}"}
    except Exception as e:
        print(f"API Error: {e}")
        return {"error": str(e)}

# 인증 라우트
@app.route('/login', methods=['GET', 'POST'])
def login():
    """로그인"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in USERS and USERS[username]['password'] == password:
            user = User(username, USERS[username])
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('잘못된 사용자 이름 또는 비밀번호', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """로그아웃"""
    logout_user()
    return redirect(url_for('login'))

# 대시보드 라우트
@app.route('/')
@login_required
def index():
    """메인"""
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    """메인 대시보드"""
    stats = api_request('/api/stats/overview')
    timeline = api_request('/api/stats/timeline?hours=24')
    top_threats = api_request('/api/stats/top-threats?limit=10')
    
    return render_template(
        'dashboard.html',
        stats=stats if stats and 'error' not in stats else {},
        timeline=timeline if timeline and 'error' not in timeline else {'timeline': []},
        top_threats=top_threats if top_threats and 'error' not in top_threats else {'threats': []}
    )

@app.route('/logs')
@login_required
def logs():
    """로그 목록"""
    count = int(request.args.get('count', 50))
    severity = request.args.get('severity', 'all')
    page = int(request.args.get('page', 1))
    
    # Suricata 로그만 조회
    endpoint = f'/api/logs/suricata?count={count}'
    if severity != 'all':
        endpoint += f'&severity={severity}'
    
    logs_data = api_request(endpoint)
    
    # 페이지네이션
    items_per_page = app.config['ITEMS_PER_PAGE']
    logs = logs_data.get('logs', []) if logs_data and 'error' not in logs_data else []
    total_pages = max(1, (len(logs) + items_per_page - 1) // items_per_page)
    
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_logs = logs[start_idx:end_idx]
    
    return render_template(
        'logs.html',
        logs=page_logs,
        source='suricata',
        severity=severity,
        page=page,
        total_pages=total_pages,
        count=count
    )

@app.route('/logs/search')
@login_required
def logs_search():
    """로그 검색"""
    query = request.args.get('q', '')
    
    if not query:
        flash('검색어를 입력하세요', 'warning')
        return redirect(url_for('logs'))
    
    results = api_request(f'/api/logs/search?query={query}')
    
    return render_template(
        'logs.html',
        logs=results.get('results', []) if results else [],
        source='suricata',
        severity='all',
        page=1,
        total_pages=1,
        search_query=query
    )

@app.route('/rules')
@login_required
def rules():
    """룰 관리"""
    category = request.args.get('category', 'all')
    rules_data = api_request(f'/api/rules/active?category={category}')
    
    return render_template(
        'rules.html',
        rules=rules_data.get('rules', []) if rules_data else [],
        category=category
    )

@app.route('/reports')
@login_required
def reports():
    """보고서"""
    reports_data = api_request('/api/reports/list')
    
    return render_template(
        'reports.html',
        reports=reports_data.get('reports', []) if reports_data else []
    )

@app.route('/reports/generate', methods=['GET', 'POST'])
@login_required
def generate_report():
    """보고서 생성"""
    if request.method == 'POST':
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        report_type = request.form.get('report_type', 'summary')
        format_type = request.form.get('format', 'pdf')
        
        result = api_request('/api/reports/generate', 'POST', {
            'start_time': start_time,
            'end_time': end_time,
            'report_type': report_type,
            'format': format_type
        })
        
        if result and result.get('success'):
            flash('보고서가 생성되었습니다', 'success')
            return redirect(url_for('reports'))
        else:
            flash(f"오류: {result.get('error', '알 수 없는 오류')}", 'error')
    
    return render_template('generate_report.html')

# 🚧 HexStrike 비활성화 (향후 사용 대비)
@app.route('/comparison')
@login_required
def comparison():
    """Red vs Blue 비교 분석 (비활성화)"""
    flash('HexStrike AI 기능은 현재 준비 중입니다. Ollama 모델 선택 후 활성화 예정입니다.', 'info')
    return render_template(
        'comparison.html',
        analysis={
            'hexstrike_count': 0,
            'suricata_count': 0,
            'detection_rate': 0,
            'matched_attacks': [],
            'undetected_attacks': [],
            'false_positives': []
        },
        time_window=60,
        disabled=True
    )

# API 엔드포인트 (AJAX용)
@app.route('/api/realtime/stats')
@login_required
def realtime_stats():
    """실시간 통계"""
    stats = api_request('/api/stats/overview')
    return jsonify(stats if stats else {})

@app.route('/api/block-ip', methods=['POST'])
@login_required
def block_ip_route():
    """IP 차단"""
    data = request.get_json()
    ip = data.get('ip')
    reason = data.get('reason', 'Blocked from dashboard')
    
    result = api_request('/api/action/block-ip', 'POST', {
        'ip': ip,
        'reason': reason
    })
    
    return jsonify(result if result else {'success': False, 'error': 'API 요청 실패'})

# 에러 핸들러
@app.errorhandler(404)
def not_found(e):
    return "<h1>404 - Page Not Found</h1>", 404

@app.errorhandler(500)
def server_error(e):
    return "<h1>500 - Internal Server Error</h1>", 500

# Jinja2 필터
@app.template_filter('datetime')
def format_datetime(dt_str):
    try:
        dt = datetime.fromisoformat(str(dt_str).replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return str(dt_str)

@app.template_filter('severity_color')
def severity_color(severity):
    colors = {
        1: 'danger', 2: 'warning', 3: 'info',
        'critical': 'danger', 'high': 'warning',
        'medium': 'info', 'low': 'secondary'
    }
    return colors.get(severity, 'secondary')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
