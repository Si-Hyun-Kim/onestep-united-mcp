# dashboard/utils.py
"""
유틸리티 함수
"""

from datetime import datetime, timedelta
from functools import wraps
from flask import abort
from flask_login import current_user

def admin_required(f):
    """관리자 권한 필요"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def format_datetime(dt_str):
    """날짜/시간 포맷팅"""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return dt_str


def format_bytes(bytes_value):
    """바이트 포맷팅"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def severity_color(severity):
    """심각도 색상"""
    colors = {
        'critical': 'danger',
        'high': 'warning',
        'medium': 'info',
        'low': 'secondary'
    }
    return colors.get(severity, 'secondary')


def calculate_time_ago(timestamp_str):
    """시간 경과 계산"""
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now(timestamp.tzinfo)
        delta = now - timestamp
        
        if delta.days > 0:
            return f"{delta.days}일 전"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"{hours}시간 전"
        elif delta.seconds >= 60:
            minutes = delta.seconds // 60
            return f"{minutes}분 전"
        else:
            return "방금 전"
    except:
        return "알 수 없음"


def parse_suricata_rule(rule_str):
    """Suricata 룰 파싱"""
    import re
    
    try:
        # action 추출
        action_match = re.match(r'^\s*(alert|drop|reject|pass)', rule_str)
        action = action_match.group(1) if action_match else 'unknown'
        
        # msg 추출
        msg_match = re.search(r'msg:"([^"]+)"', rule_str)
        msg = msg_match.group(1) if msg_match else 'No message'
        
        # sid 추출
        sid_match = re.search(r'sid:(\d+)', rule_str)
        sid = int(sid_match.group(1)) if sid_match else 0
        
        return {
            'action': action,
            'message': msg,
            'sid': sid,
            'raw': rule_str
        }
    except:
        return {
            'action': 'unknown',
            'message': 'Parse error',
            'sid': 0,
            'raw': rule_str
        }


# Jinja2 필터 등록
def register_filters(app):
    """Jinja2 필터 등록"""
    app.jinja_env.filters['datetime'] = format_datetime
    app.jinja_env.filters['bytes'] = format_bytes
    app.jinja_env.filters['severity_color'] = severity_color
    app.jinja_env.filters['time_ago'] = calculate_time_ago