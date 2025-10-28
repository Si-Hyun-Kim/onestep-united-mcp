"""
Flask 웹 대시보드
SIEM 스타일 보안 모니터링 대시보드
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps
import requests
from datetime import datetime, timedelta
import pyotp
import qrcode
import io
import base64
from config import Config
from auth import User, MFAManager

# Flask 앱 생성
app = Flask(__name__)
app.config.from_object(Config)

# LoginManager 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# MFA 관리자
mfa_manager = MFAManager()

# 사용자 데이터 (실제로는 DB 사용)
USERS = {
    'admin': {
        'password': 'admin123',  # 실제로는 해시화된 비밀번호
        'mfa_secret': None,
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
            
            # MFA 활성화 여부 확인
            if app.config['MFA_ENABLED'] and USERS[username].get('mfa_secret'):
                session['pending_mfa'] = username
                return redirect(url_for('verify_mfa'))
            
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid credentials', 'error')
    
    return render_template('login.html')


@app.route('/verify-mfa', methods=['GET', 'POST'])
def verify_mfa():
    """MFA 검증"""
    if 'pending_mfa' not in session:
        return redirect(url_for('login'))
    
    username = session['pending_mfa']
    
    if request.method == 'POST':
        code = request.form.get('code')
        secret = USERS[username]['mfa_secret']
        
        if mfa_manager.verify_token(secret, code):
            user = User(username, USERS[username])
            login_user(user)
            session.pop('pending_mfa', None)
            return redirect(url_for('dashboard'))
        
        flash('Invalid MFA code', 'error')
    
    return render_template('verify_mfa.html')


@app.route('/setup-mfa')
@login_required
def setup_mfa():
    """MFA 설정"""
    if USERS[current_user.id].get('mfa_secret'):
        flash('MFA already enabled', 'info')
        return redirect(url_for('dashboard'))
    
    # 새 시크릿 생성
    secret = pyotp.random_base32()
    USERS[current_user.id]['mfa_secret'] = secret
    
    # QR 코드 생성
    qr_uri = mfa_manager.generate_qr_uri(current_user.id, secret)
    qr_img = mfa_manager.generate_qr_image(qr_uri)
    
    return render_template('setup_mfa.html', qr_image=qr_img, secret=secret)


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
    # 전체 통계 조회
    stats = api_request('/api/stats/overview')
    timeline = api_request('/api/stats/timeline?hours=24')
    top_threats = api_request('/api/stats/top-threats?limit=10')
    
    return render_template(
        'dashboard.html',
        stats=stats,
        timeline=timeline,
        top_threats=top_threats
    )


@app.route('/logs')
@login_required
def logs():
    """로그 목록"""
    # 필터 파라미터
    source = request.args.get('source', 'suricata')
    count = int(request.args.get('count', 50))
    severity = request.args.get('severity', 'all')
    page = int(request.args.get('page', 1))
    
    # 로그 조회
    if source == 'suricata':
        endpoint = f'/api/logs/suricata/recent?count={count}'
        if severity != 'all':
            endpoint += f'&severity={severity}'
        logs_data = api_request(endpoint)
    elif source == 'hexstrike':
        logs_data = api_request(f'/api/logs/hexstrike/recent?count={count}')
    else:
        logs_data = {"logs": []}
    
    # 페이지네이션
    items_per_page = app.config['ITEMS_PER_PAGE']
    logs = logs_data.get('logs', [])
    total_pages = (len(logs) + items_per_page - 1) // items_per_page
    
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page
    page_logs = logs[start_idx:end_idx]
    
    return render_template(
        'logs.html',
        logs=page_logs,
        source=source,
        severity=severity,
        page=page,
        total_pages=total_pages
    )


@app.route('/logs/search')
@login_required
def logs_search():
    """로그 검색"""
    query = request.args.get('q', '')
    source = request.args.get('source', 'all')
    
    if not query:
        flash('Please enter a search query', 'warning')
        return redirect(url_for('logs'))
    
    # 검색 실행
    results = api_request(f'/api/logs/search?query={query}&source={source}')
    
    return render_template(
        'logs_search.html',
        query=query,
        results=results.get('results', []),
        count=results.get('count', 0)
    )


@app.route('/rules')
@login_required
def rules():
    """룰 관리"""
    category = request.args.get('category', 'all')
    
    # 활성 룰 조회
    rules_data = api_request(f'/api/rules/active?category={category}')
    
    return render_template(
        'rules.html',
        rules=rules_data.get('rules', []),
        category=category
    )


@app.route('/rules/add', methods=['GET', 'POST'])
@login_required
def add_rule():
    """룰 추가"""
    if request.method == 'POST':
        rule_content = request.form.get('rule_content')
        description = request.form.get('description', '')
        
        # 룰 추가
        result = api_request('/api/rules/add', 'POST', {
            'rule_content': rule_content,
            'description': description,
            'auto_reload': True
        })
        
        if result.get('success'):
            flash('Rule added successfully', 'success')
            return redirect(url_for('rules'))
        else:
            flash(f"Error: {result.get('error')}", 'error')
    
    return render_template('add_rule.html')


@app.route('/analysis/comparison')
@login_required
def comparison():
    """Red vs Blue 비교 분석"""
    time_window = int(request.args.get('time_window', 60))
    
    # 비교 분석 데이터
    analysis_data = api_request(f'/api/analysis/compare?time_window={time_window}')
    
    return render_template(
        'comparison.html',
        analysis=analysis_data,
        time_window=time_window
    )


@app.route('/reports')
@login_required
def reports():
    """보고서"""
    # 생성된 보고서 목록
    reports_data = api_request('/api/reports/list')
    
    return render_template(
        'reports.html',
        reports=reports_data.get('reports', [])
    )


@app.route('/reports/generate', methods=['GET', 'POST'])
@login_required
def generate_report():
    """보고서 생성"""
    if request.method == 'POST':
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        report_type = request.form.get('report_type', 'summary')
        format = request.form.get('format', 'pdf')
        
        # 보고서 생성 요청
        result = api_request('/api/reports/generate', 'POST', {
            'start_time': start_time,
            'end_time': end_time,
            'report_type': report_type,
            'format': format
        })
        
        if result.get('success'):
            flash('Report generated successfully', 'success')
            return redirect(url_for('reports'))
        else:
            flash(f"Error: {result.get('error')}", 'error')
    
    return render_template('generate_report.html')


@app.route('/settings')
@login_required
def settings():
    """설정"""
    return render_template('settings.html')


# API 엔드포인트 (AJAX용)
@app.route('/api/realtime/stats')
@login_required
def realtime_stats():
    """실시간 통계 (AJAX)"""
    stats = api_request('/api/stats/overview')
    return jsonify(stats)


@app.route('/api/block-ip', methods=['POST'])
@login_required
def block_ip():
    """IP 차단 (AJAX)"""
    data = request.get_json()
    ip = data.get('ip')
    reason = data.get('reason', 'Blocked from dashboard')
    
    result = api_request('/api/action/block-ip', 'POST', {
        'ip': ip,
        'reason': reason
    })
    
    return jsonify(result)


@app.route('/api/unblock-ip', methods=['POST'])
@login_required
def unblock_ip():
    """IP 차단 해제 (AJAX)"""
    data = request.get_json()
    ip = data.get('ip')
    
    result = api_request('/api/action/unblock-ip', 'POST', {'ip': ip})
    
    return jsonify(result)


# 에러 핸들러
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=True
    )