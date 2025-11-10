# dashboard/config.py
"""
Flask 설정
"""

import os
from datetime import timedelta

class Config:
    """Flask 설정 클래스"""
    
    # 기본 설정
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production-12345'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # FastAPI 백엔드 URL
    API_URL = os.environ.get('API_URL', 'http://localhost:8000')
    
    # 세션 설정
    SESSION_COOKIE_SECURE = False  # HTTPS에서는 True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    
    # MFA 설정
    MFA_ENABLED = os.environ.get('MFA_ENABLED', 'True').lower() == 'true'
    MFA_ISSUER_NAME = "Security Dashboard"
    
    # 대시보드 설정
    ITEMS_PER_PAGE = 50
    CHART_UPDATE_INTERVAL = 5  # 초
    MAX_LOGS_DISPLAY = 1000
    
    # 보고서 설정
    REPORT_FORMATS = ['pdf', 'html', 'json']
    REPORT_DIRECTORY = './reports'
    
    # 로깅 설정
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = './logs/dashboard/app.log'
    
    # 보안 설정
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_ATTEMPT_WINDOW = 300  # 5분
    
    # 알림 설정
    ENABLE_EMAIL_ALERTS = False
    ENABLE_SLACK_ALERTS = False
    
    @staticmethod
    def init_app(app):
        """앱 초기화"""
        # 로그 디렉토리 생성
        from pathlib import Path
        Path('./logs/dashboard').mkdir(parents=True, exist_ok=True)
        Path('./reports').mkdir(parents=True, exist_ok=True)


class DevelopmentConfig(Config):
    """개발 환경 설정"""
    DEBUG = True
    MFA_ENABLED = False  # 개발 시 MFA 비활성화


class ProductionConfig(Config):
    """프로덕션 환경 설정"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    MFA_ENABLED = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}