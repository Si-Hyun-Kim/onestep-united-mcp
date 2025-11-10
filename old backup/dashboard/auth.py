# dashboard/auth.py
"""
사용자 인증 및 MFA 관리
"""

from flask_login import UserMixin
import pyotp
import qrcode
import io
import base64

class User(UserMixin):
    """사용자 클래스"""
    
    def __init__(self, user_id, user_data):
        self.id = user_id
        self.data = user_data
        self.role = user_data.get('role', 'user')
    
    def has_mfa(self):
        return self.data.get('mfa_secret') is not None
    
    def is_admin(self):
        return self.role == 'admin'


class MFAManager:
    """MFA (Multi-Factor Authentication) 관리자"""
    
    def __init__(self, issuer_name="Security Dashboard"):
        self.issuer_name = issuer_name
    
    def generate_secret(self):
        """MFA 시크릿 생성"""
        return pyotp.random_base32()
    
    def generate_qr_uri(self, username, secret):
        """QR 코드 URI 생성"""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=username,
            issuer_name=self.issuer_name
        )
    
    def generate_qr_image(self, uri):
        """QR 코드 이미지 생성 (Base64)"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 이미지를 Base64로 변환
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode()
        
        return f"data:image/png;base64,{img_base64}"
    
    def verify_token(self, secret, token):
        """MFA 토큰 검증"""
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=1)
        except:
            return False
    
    def get_current_token(self, secret):
        """현재 토큰 생성 (테스트용)"""
        totp = pyotp.TOTP(secret)
        return totp.now()