
"""
Ollama 기반 AI 분석기
Qwen3 모델을 사용한 로그 분석
"""

import ollama
from typing import Dict, Optional

class OllamaAnalyzer:
    """Ollama AI 분석기"""
    
    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "qwen2.5:7b",
        temperature: float = 0.3,
        max_tokens: int = 2000
    ):
        self.host = host
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Ollama 클라이언트 설정
        ollama._client._base_url = host
    
    async def check_connection(self) -> bool:
        """Ollama 연결 확인"""
        try:
            models = ollama.list()
            available_models = [m['name'] for m in models['models']]
            
            if self.model not in available_models:
                print(f"⚠️  Model {self.model} not found!")
                print(f"   Available models: {', '.join(available_models)}")
                print(f"   Run: ollama pull {self.model}")
                return False
            
            return True
        
        except Exception as e:
            print(f"❌ Ollama connection failed: {e}")
            return False
    
    async def analyze(self, prompt: str) -> str:
        """AI 분석 실행"""
        try:
            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        'role': 'system',
                        'content': (
                            '당신은 사이버 보안 전문가입니다. '
                            '로그를 분석하고 위협을 탐지하며, '
                            '효과적인 방어 규칙을 제안합니다. '
                            '항상 JSON 형식으로 응답하세요.'
                        )
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                options={
                    'temperature': self.temperature,
                    'num_predict': self.max_tokens
                }
            )
            
            return response['message']['content']
        
        except Exception as e:
            raise Exception(f"Ollama analysis failed: {e}")
    
    async def analyze_attack_pattern(self, logs: list) -> Dict:
        """공격 패턴 분석"""
        prompt = f"""
다음 로그에서 공격 패턴을 분석하세요:

{logs[:10]}  # 샘플만 전송

다음 형식으로 JSON 응답:
{{
  "attack_type": "brute_force|port_scan|sql_injection|xss|dos|etc",
  "severity": "low|medium|high|critical",
  "confidence": 0-100,
  "indicators": ["indicator1", "indicator2"],
  "recommended_action": "block|monitor|alert"
}}
"""
        
        response = await self.analyze(prompt)
        return self._parse_json_response(response)
    
    async def generate_rule_description(self, attack_info: Dict) -> str:
        """룰 설명 생성"""
        prompt = f"""
다음 공격 정보를 바탕으로 Suricata 룰에 대한 간단한 설명을 생성하세요:

공격 유형: {attack_info.get('type')}
심각도: {attack_info.get('severity')}
이유: {attack_info.get('reason')}

한 문장으로 작성하세요.
"""
        
        response = await self.analyze(prompt)
        return response.strip()
    
    async def suggest_mitigation(self, threat: Dict) -> Dict:
        """완화 조치 제안"""
        prompt = f"""
다음 위협에 대한 완화 조치를 제안하세요:

IP: {threat.get('ip')}
위협 점수: {threat.get('score')}
공격 시그니처: {', '.join(threat.get('signatures', []))}

JSON 형식으로 응답:
{{
  "immediate_actions": ["action1", "action2"],
  "long_term_actions": ["action1", "action2"],
  "monitoring_points": ["point1", "point2"]
}}
"""
        
        response = await self.analyze(prompt)
        return self._parse_json_response(response)
    
    def _parse_json_response(self, response: str) -> Dict:
        """JSON 응답 파싱"""
        import json
        
        try:
            # JSON 부분만 추출
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
            
            return {}
        
        except Exception:
            return {}