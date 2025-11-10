"""
mcp/rule_manager.py
Suricata 룰 관리자
자동 생성된 룰 관리 및 적용
"""

import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import aiofiles
import re

class SuricataRuleManager:
    """Suricata 룰 관리"""
    
    def __init__(
        self,
        rules_dir: str = "/etc/suricata/rules",
        custom_rules_file: str = "./rules/custom/auto_generated.rules"
    ):
        self.rules_dir = Path(rules_dir)
        self.custom_rules_file = Path(custom_rules_file)
        self.custom_rules_file.parent.mkdir(parents=True, exist_ok=True)
        
        # SID 카운터 (자동 생성 룰용)
        self.sid_counter = 9000000
    
    async def get_active_rules(self, category: str = "all") -> List[Dict]:
        """활성화된 룰 조회"""
        rules = []
        
        # 모든 룰 파일 읽기
        if self.rules_dir.exists():
            for rule_file in self.rules_dir.glob("*.rules"):
                file_rules = await self._parse_rule_file(rule_file)
                rules.extend(file_rules)
        
        # 커스텀 룰 추가
        if self.custom_rules_file.exists():
            custom_rules = await self._parse_rule_file(self.custom_rules_file)
            rules.extend(custom_rules)
        
        # 카테고리 필터링
        if category != "all":
            rules = [r for r in rules if r['category'] == category]
        
        return rules
    
    async def _parse_rule_file(self, file_path: Path) -> List[Dict]:
        """룰 파일 파싱"""
        rules = []
        
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                
                for line in content.split('\n'):
                    line = line.strip()
                    
                    # 주석이나 빈 줄 건너뛰기
                    if not line or line.startswith('#'):
                        continue
                    
                    # 룰 파싱
                    rule_info = self._parse_rule_line(line)
                    if rule_info:
                        rule_info['file'] = file_path.name
                        rules.append(rule_info)
        
        except Exception as e:
            print(f"❌ Error parsing {file_path}: {e}")
        
        return rules
    
    def _parse_rule_line(self, line: str) -> Optional[Dict]:
        """개별 룰 라인 파싱"""
        try:
            # 기본 패턴 추출
            action_match = re.match(r'^\s*(alert|drop|reject|pass)', line)
            if not action_match:
                return None
            
            action = action_match.group(1)
            
            # msg 추출
            msg_match = re.search(r'msg:"([^"]+)"', line)
            msg = msg_match.group(1) if msg_match else "Unknown"
            
            # sid 추출
            sid_match = re.search(r'sid:(\d+)', line)
            sid = int(sid_match.group(1)) if sid_match else 0
            
            # classtype 추출
            classtype_match = re.search(r'classtype:([^;]+)', line)
            classtype = classtype_match.group(1).strip() if classtype_match else "unknown"
            
            return {
                "action": action,
                "message": msg,
                "sid": sid,
                "category": classtype,
                "rule": line
            }
        
        except Exception:
            return None
    
    async def add_rule(
        self,
        rule_content: str,
        description: str = "",
        auto_reload: bool = True
    ) -> Dict:
        """룰 추가"""
        try:
            # SID가 없으면 자동 생성
            if 'sid:' not in rule_content:
                sid = await self._get_next_sid()
                rule_content = rule_content.rstrip(')') + f'; sid:{sid}; rev:1;)'
            
            # 백업
            await self._backup_rules()
            
            # 룰 추가
            async with aiofiles.open(self.custom_rules_file, 'a') as f:
                if description:
                    await f.write(f"# {description}\n")
                await f.write(f"{rule_content}\n")
            
            # Suricata 리로드
            if auto_reload:
                reload_result = await self._reload_suricata()
                if not reload_result['success']:
                    return reload_result
            
            return {
                "success": True,
                "message": "Rule added successfully",
                "rule": rule_content,
                "reloaded": auto_reload
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_next_sid(self) -> int:
        """다음 SID 번호"""
        self.sid_counter += 1
        return self.sid_counter
    
    async def _backup_rules(self):
        """룰 백업"""
        if not self.custom_rules_file.exists():
            return
        
        backup_dir = Path("./rules/backup")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"auto_generated_{timestamp}.rules"
        
        async with aiofiles.open(self.custom_rules_file, 'r') as src:
            content = await src.read()
        
        async with aiofiles.open(backup_file, 'w') as dst:
            await dst.write(content)
    
    async def _reload_suricata(self) -> Dict:
        """Suricata 리로드"""
        try:
            # Suricata 룰 테스트
            test_cmd = "sudo suricata -T -c /etc/suricata/suricata.yaml"
            test_result = subprocess.run(
                test_cmd,
                shell=True,
                capture_output=True,
                text=True
            )
            
            if test_result.returncode != 0:
                return {
                    "success": False,
                    "error": "Rule validation failed",
                    "output": test_result.stderr
                }
            
            # Suricata 리로드
            reload_cmd = "sudo kill -USR2 $(pidof suricata)"
            subprocess.run(reload_cmd, shell=True, check=True)
            
            return {
                "success": True,
                "message": "Suricata reloaded successfully"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def remove_rule(self, sid: int) -> Dict:
        """룰 제거 (SID 기준)"""
        try:
            if not self.custom_rules_file.exists():
                return {
                    "success": False,
                    "error": "Custom rules file not found"
                }
            
            # 백업
            await self._backup_rules()
            
            # 파일 읽기
            async with aiofiles.open(self.custom_rules_file, 'r') as f:
                lines = await f.readlines()
            
            # SID에 해당하는 라인 제거
            filtered_lines = [
                line for line in lines
                if f'sid:{sid}' not in line or line.strip().startswith('#')
            ]
            
            # 파일 쓰기
            async with aiofiles.open(self.custom_rules_file, 'w') as f:
                await f.writelines(filtered_lines)
            
            # 리로드
            await self._reload_suricata()
            
            return {
                "success": True,
                "message": f"Rule with SID {sid} removed"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def validate_rule(self, rule_content: str) -> Dict:
        """룰 유효성 검증"""
        try:
            # 기본 문법 검사
            if not rule_content.strip():
                return {
                    "valid": False,
                    "error": "Empty rule"
                }
            
            # action 체크
            valid_actions = ['alert', 'drop', 'reject', 'pass']
            if not any(rule_content.startswith(action) for action in valid_actions):
                return {
                    "valid": False,
                    "error": "Invalid action (must be alert, drop, reject, or pass)"
                }
            
            # 필수 필드 체크
            required_fields = ['msg:', 'sid:', 'rev:']
            missing_fields = [field for field in required_fields if field not in rule_content]
            
            if missing_fields:
                return {
                    "valid": False,
                    "error": f"Missing required fields: {', '.join(missing_fields)}"
                }
            
            return {
                "valid": True,
                "message": "Rule syntax is valid"
            }
        
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }


class RuleTemplate:
    """룰 템플릿 생성기"""
    
    @staticmethod
    def create_ip_block_rule(ip: str, reason: str = "Suspicious activity") -> str:
        """IP 차단 룰"""
        return (
            f'drop ip {ip} any -> $HOME_NET any '
            f'(msg:"Auto-block: {reason}"; '
            f'threshold:type limit,track by_src,count 1,seconds 60; '
            f'classtype:attempted-admin; priority:1;)'
        )
    
    @staticmethod
    def create_port_scan_rule() -> str:
        """포트 스캔 탐지 룰"""
        return (
            'alert tcp $EXTERNAL_NET any -> $HOME_NET any '
            '(msg:"Auto-generated: Possible Port Scan"; '
            'flags:S; threshold:type threshold,track by_src,count 20,seconds 60; '
            'classtype:attempted-recon; priority:2;)'
        )
    
    @staticmethod
    def create_brute_force_rule(port: int) -> str:
        """브루트 포스 탐지 룰"""
        return (
            f'alert tcp $EXTERNAL_NET any -> $HOME_NET {port} '
            f'(msg:"Auto-generated: Brute Force Attempt on Port {port}"; '
            f'threshold:type both,track by_src,count 5,seconds 60; '
            f'classtype:attempted-admin; priority:1;)'
        )
    
    @staticmethod
    def create_sql_injection_rule() -> str:
        """SQL Injection 탐지 룰"""
        return (
            'alert tcp $EXTERNAL_NET any -> $HOME_NET $HTTP_PORTS '
            '(msg:"Auto-generated: Possible SQL Injection"; '
            'flow:to_server,established; '
            'content:"SELECT"; nocase; content:"FROM"; nocase; '
            'classtype:web-application-attack; priority:1;)'
        )
    
    @staticmethod
    def create_xss_rule() -> str:
        """XSS 탐지 룰"""
        return (
            'alert tcp $EXTERNAL_NET any -> $HOME_NET $HTTP_PORTS '
            '(msg:"Auto-generated: Possible XSS Attack"; '
            'flow:to_server,established; '
            'content:"<script"; nocase; '
            'classtype:web-application-attack; priority:2;)'
        )