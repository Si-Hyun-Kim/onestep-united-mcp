# agent/rule_generator.py
"""
AI 기반 Suricata 룰 생성기
"""

import sys
sys.path.append('../mcp_server')
from rule_manager import RuleTemplate

class AIRuleGenerator:
    """AI 기반 룰 생성기"""
    
    def __init__(self, ollama_analyzer, rule_manager):
        self.ollama = ollama_analyzer
        self.rule_manager = rule_manager
    
    async def generate_rule(
        self,
        rule_type: str,
        reason: str,
        suggestion: Dict
    ) -> Optional[str]:
        """룰 생성"""
        
        # 템플릿 기반 룰 생성
        if rule_type == "block_ip":
            ip = suggestion.get('target_ip')
            if ip:
                return RuleTemplate.create_ip_block_rule(ip, reason)
        
        elif rule_type == "port_scan":
            return RuleTemplate.create_port_scan_rule()
        
        elif rule_type == "brute_force":
            port = suggestion.get('port', 22)
            return RuleTemplate.create_brute_force_rule(port)
        
        elif rule_type == "sql_injection":
            return RuleTemplate.create_sql_injection_rule()
        
        elif rule_type == "xss":
            return RuleTemplate.create_xss_rule()
        
        # AI 기반 커스텀 룰 생성
        else:
            return await self._generate_custom_rule(suggestion, reason)
    
    async def _generate_custom_rule(self, suggestion: Dict, reason: str) -> Optional[str]:
        """AI 기반 커스텀 룰 생성"""
        prompt = f"""
다음 정보를 바탕으로 Suricata 룰을 생성하세요:

이유: {reason}
우선순위: {suggestion.get('priority', 2)}
추가 정보: {suggestion}

Suricata 룰 형식:
- action (alert/drop) + 프로토콜 + 소스 + 목적지
- msg, classtype, sid, rev 포함
- 유효한 Suricata 문법 사용

예시:
alert tcp $EXTERNAL_NET any -> $HOME_NET 22 (msg:"SSH Brute Force"; threshold:type both,track by_src,count 5,seconds 60; classtype:attempted-admin; sid:9000001; rev:1;)

하나의 완전한 룰만 응답하세요.
"""
        
        try:
            response = await self.ollama.analyze(prompt)
            
            # 룰 추출 (alert 또는 drop으로 시작하는 라인)
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('alert') or line.startswith('drop'):
                    # 유효성 검증
                    validation = await self.rule_manager.validate_rule(line)
                    if validation['valid']:
                        return line
            
            return None
        
        except Exception as e:
            print(f"❌ Custom rule generation failed: {e}")
            return None
    
    async def optimize_existing_rule(self, rule: str) -> Optional[str]:
        """기존 룰 최적화"""
        prompt = f"""
다음 Suricata 룰을 분석하고 최적화하세요:

{rule}

개선 사항:
1. 성능 최적화 (불필요한 검사 제거)
2. 정확도 향상 (false positive 감소)
3. 가독성 개선

최적화된 룰만 응답하세요.
"""
        
        try:
            response = await self.ollama.analyze(prompt)
            
            # 최적화된 룰 추출
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('alert') or line.startswith('drop'):
                    validation = await self.rule_manager.validate_rule(line)
                    if validation['valid']:
                        return line
            
            return None
        
        except Exception:
            return None