#!/usr/bin/env python3
"""
AI 기반 보안 에이전트
Ollama Qwen3를 사용한 로그 분석 및 자동 룰 생성
"""

import asyncio
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from ollama_analyzer import OllamaAnalyzer
from rule_generator import AIRuleGenerator
import sys
sys.path.append('../mcp_server')
from log_collectors import SuricataCollector, HexStrikeCollector, LogAnalyzer
from rule_manager import SuricataRuleManager

class SecurityAgent:
    """AI 기반 보안 자동화 에이전트"""
    
    def __init__(self, config_path: str = "./config.yaml"):
        # 설정 로드
        self.config = self._load_config(config_path)
        
        # 컴포넌트 초기화
        self.suricata_collector = SuricataCollector(
            self.config['suricata']['log_path']
        )
        self.hexstrike_collector = HexStrikeCollector(
            self.config['hexstrike']['log_path']
        )
        self.rule_manager = SuricataRuleManager(
            self.config['suricata']['rules_path'],
            self.config['suricata']['custom_rules_path']
        )
        
        # AI 분석기
        self.ollama_analyzer = OllamaAnalyzer(
            host=self.config['ollama']['host'],
            model=self.config['ollama']['model']
        )
        
        # 룰 생성기
        self.rule_generator = AIRuleGenerator(
            self.ollama_analyzer,
            self.rule_manager
        )
        
        # 상태
        self.is_running = False
        self.blocked_ips = set()
        
        # 로그 디렉토리
        self.log_dir = Path("./logs/agent")
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_config(self, config_path: str) -> Dict:
        """설정 파일 로드"""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return self._default_config()
    
    def _default_config(self) -> Dict:
        """기본 설정"""
        return {
            'agent': {
                'name': 'SecurityAgent',
                'check_interval': 30
            },
            'ollama': {
                'host': 'http://localhost:11434',
                'model': 'qwen2.5:7b',
                'temperature': 0.3,
                'max_tokens': 2000
            },
            'suricata': {
                'log_path': '/var/log/suricata/eve.json',
                'rules_path': '/etc/suricata/rules',
                'custom_rules_path': './rules/custom/auto_generated.rules'
            },
            'hexstrike': {
                'log_path': './logs/hexstrike'
            },
            'detection': {
                'alert_threshold': 5,
                'time_window': 300,
                'severity_weights': {
                    'critical': 10,
                    'high': 5,
                    'medium': 2,
                    'low': 1
                }
            },
            'auto_response': {
                'enabled': True,
                'block_threshold': 20,
                'whitelist': ['127.0.0.1', 'localhost']
            }
        }
    
    async def start(self):
        """에이전트 시작"""
        print("╔════════════════════════════════════════════════╗")
        print("║  🤖 AI Security Agent Starting...           ║")
        print("╚════════════════════════════════════════════════╝")
        print()
        print(f"⚙️  Agent: {self.config['agent']['name']}")
        print(f"⚙️  AI Model: {self.config['ollama']['model']}")
        print(f"⚙️  Check Interval: {self.config['agent']['check_interval']}s")
        print(f"⚙️  Auto Response: {self.config['auto_response']['enabled']}")
        print()
        
        # Ollama 연결 확인
        if not await self.ollama_analyzer.check_connection():
            print("❌ Ollama 서버에 연결할 수 없습니다!")
            print("   ollama serve 명령으로 Ollama를 시작하세요.")
            return
        
        print("✅ Ollama 연결 성공")
        print()
        
        self.is_running = True
        
        try:
            while self.is_running:
                await self._analysis_cycle()
                await asyncio.sleep(self.config['agent']['check_interval'])
        
        except KeyboardInterrupt:
            print("\n🛑 Agent stopping...")
            self.is_running = False
    
    async def _analysis_cycle(self):
        """분석 사이클"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] 🔍 Starting analysis cycle...")
        
        try:
            # 1. 로그 수집
            print("  📊 Collecting logs...")
            suricata_logs = await self.suricata_collector.get_recent_logs(100)
            hexstrike_logs = await self.hexstrike_collector.get_recent_logs(50)
            
            print(f"     Suricata: {len(suricata_logs)} alerts")
            print(f"     HexStrike: {len(hexstrike_logs)} attacks")
            
            if not suricata_logs and not hexstrike_logs:
                print("  ℹ️  No new logs to analyze")
                return
            
            # 2. AI 분석
            print("  🧠 Analyzing with AI...")
            analysis_result = await self._ai_analysis(suricata_logs, hexstrike_logs)
            
            # 3. 위협 탐지
            threats = self._detect_threats(suricata_logs)
            
            if threats:
                print(f"  🚨 Detected {len(threats)} threats")
                
                for threat in threats:
                    print(f"\n  ⚠️  Threat: {threat['ip']}")
                    print(f"     Score: {threat['score']}")
                    print(f"     Reason: {threat['reason']}")
                    
                    # 자동 대응
                    if self.config['auto_response']['enabled']:
                        await self._auto_respond(threat)
            
            # 4. 룰 생성 (AI 추천)
            if analysis_result.get('should_create_rules', False):
                print("\n  📝 AI recommends creating new rules...")
                await self._generate_rules(analysis_result)
            
            # 5. Red vs Blue 비교
            if hexstrike_logs:
                metrics = LogAnalyzer.calculate_metrics(suricata_logs, hexstrike_logs)
                print(f"\n  📈 Detection Metrics:")
                print(f"     Detection Rate: {metrics['detection_rate']}%")
                print(f"     False Positives: {metrics['false_positives']}")
                print(f"     False Negatives: {metrics['false_negatives']}")
        
        except Exception as e:
            print(f"  ❌ Error during analysis: {e}")
            self._log_error(str(e))
    
    async def _ai_analysis(self, suricata_logs: List[Dict], hexstrike_logs: List[Dict]) -> Dict:
        """AI 기반 로그 분석"""
        # 로그 요약
        log_summary = {
            "suricata": {
                "total": len(suricata_logs),
                "by_severity": self._group_by_severity(suricata_logs),
                "top_ips": self._get_top_ips(suricata_logs, 5),
                "top_signatures": self._get_top_signatures(suricata_logs, 5)
            },
            "hexstrike": {
                "total": len(hexstrike_logs),
                "by_attack_type": self._group_by_attack_type(hexstrike_logs),
                "success_rate": self._calculate_success_rate(hexstrike_logs)
            }
        }
        
        # AI에게 분석 요청
        prompt = self._create_analysis_prompt(log_summary)
        
        try:
            ai_response = await self.ollama_analyzer.analyze(prompt)
            
            # AI 응답 파싱
            return self._parse_ai_response(ai_response)
        
        except Exception as e:
            print(f"  ⚠️  AI analysis failed: {e}")
            return {
                "should_create_rules": False,
                "recommendations": []
            }
    
    def _create_analysis_prompt(self, log_summary: Dict) -> str:
        """AI 분석 프롬프트 생성"""
        return f"""
당신은 보안 전문가 AI입니다. 다음 로그를 분석하고 권장 사항을 제시하세요.

# Suricata IPS 로그
- 총 알림: {log_summary['suricata']['total']}
- 심각도별:
  * Critical: {log_summary['suricata']['by_severity'].get('critical', 0)}
  * High: {log_summary['suricata']['by_severity'].get('high', 0)}
  * Medium: {log_summary['suricata']['by_severity'].get('medium', 0)}
  * Low: {log_summary['suricata']['by_severity'].get('low', 0)}

- 상위 공격 IP: {', '.join(log_summary['suricata']['top_ips'])}
- 상위 시그니처: {', '.join(log_summary['suricata']['top_signatures'])}

# HexStrike 공격 로그
- 총 공격: {log_summary['hexstrike']['total']}
- 공격 유형별: {json.dumps(log_summary['hexstrike']['by_attack_type'], ensure_ascii=False)}
- 성공률: {log_summary['hexstrike']['success_rate']}%

다음 형식으로 JSON 응답을 제공하세요:
{{
  "threat_level": "low|medium|high|critical",
  "should_create_rules": true|false,
  "recommended_actions": ["action1", "action2", ...],
  "rule_suggestions": [
    {{
      "type": "block_ip|port_scan|brute_force|sql_injection|xss",
      "reason": "이유 설명",
      "priority": 1-3
    }}
  ],
  "analysis_summary": "종합 분석 결과"
}}
"""
    
    def _parse_ai_response(self, ai_response: str) -> Dict:
        """AI 응답 파싱"""
        try:
            # JSON 추출
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = ai_response[json_start:json_end]
                return json.loads(json_str)
            
            return {
                "should_create_rules": False,
                "recommendations": []
            }
        
        except Exception:
            return {
                "should_create_rules": False,
                "recommendations": []
            }
    
    def _detect_threats(self, logs: List[Dict]) -> List[Dict]:
        """규칙 기반 위협 탐지"""
        from collections import defaultdict
        
        ip_stats = defaultdict(lambda: {
            'count': 0,
            'score': 0,
            'signatures': set(),
            'severities': []
        })
        
        # 로그 집계
        for log in logs:
            ip = log['src_ip']
            
            if ip in self.config['auto_response']['whitelist']:
                continue
            
            ip_stats[ip]['count'] += 1
            ip_stats[ip]['signatures'].add(log['signature'])
            ip_stats[ip]['severities'].append(log['severity'])
            
            # 심각도 가중치
            weight = self.config['detection']['severity_weights'].get(
                log['severity'], 1
            )
            ip_stats[ip]['score'] += weight
        
        # 위협 판단
        threats = []
        threshold = self.config['detection']['alert_threshold']
        block_threshold = self.config['auto_response']['block_threshold']
        
        for ip, stats in ip_stats.items():
            if stats['count'] >= threshold or stats['score'] >= block_threshold:
                threats.append({
                    'ip': ip,
                    'count': stats['count'],
                    'score': stats['score'],
                    'signatures': list(stats['signatures']),
                    'reason': self._determine_threat_reason(stats)
                })
        
        return threats
    
    def _determine_threat_reason(self, stats: Dict) -> str:
        """위협 사유 결정"""
        if stats['count'] >= 10:
            return f"High alert count ({stats['count']})"
        elif stats['score'] >= 30:
            return f"High threat score ({stats['score']})"
        elif len(stats['signatures']) >= 3:
            return f"Multiple attack types ({len(stats['signatures'])})"
        else:
            return "Suspicious activity"
    
    async def _auto_respond(self, threat: Dict):
        """자동 대응"""
        ip = threat['ip']
        
        if ip in self.blocked_ips:
            print(f"     ℹ️  Already blocked")
            return
        
        print(f"     🔒 Auto-blocking...")
        
        try:
            # IP 차단
            import subprocess
            cmd = f"sudo iptables -A INPUT -s {ip} -j DROP"
            subprocess.run(cmd, shell=True, check=True)
            
            self.blocked_ips.add(ip)
            
            # 로그 기록
            self._log_action('BLOCK', ip, threat)
            
            print(f"     ✅ Blocked successfully")
        
        except Exception as e:
            print(f"     ❌ Block failed: {e}")
    
    async def _generate_rules(self, analysis_result: Dict):
        """AI 추천 기반 룰 생성"""
        suggestions = analysis_result.get('rule_suggestions', [])
        
        for suggestion in suggestions:
            rule_type = suggestion['type']
            reason = suggestion['reason']
            
            print(f"     Creating {rule_type} rule...")
            
            rule_content = await self.rule_generator.generate_rule(
                rule_type,
                reason,
                suggestion
            )
            
            if rule_content:
                result = await self.rule_manager.add_rule(
                    rule_content,
                    f"AI-generated: {reason}",
                    auto_reload=True
                )
                
                if result['success']:
                    print(f"     ✅ Rule created successfully")
                else:
                    print(f"     ❌ Failed: {result.get('error')}")
    
    def _log_action(self, action: str, ip: str, details: Dict):
        """액션 로그 기록"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "ip": ip,
            "details": details
        }
        
        log_file = self.log_dir / "actions.log"
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def _log_error(self, error: str):
        """에러 로그"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "error": error
        }
        
        log_file = self.log_dir / "errors.log"
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    # 유틸리티 메서드들
    def _group_by_severity(self, logs: List[Dict]) -> Dict:
        from collections import Counter
        severities = [log['severity'] for log in logs]
        return dict(Counter(severities))
    
    def _get_top_ips(self, logs: List[Dict], limit: int) -> List[str]:
        from collections import Counter
        ips = [log['src_ip'] for log in logs]
        return [ip for ip, _ in Counter(ips).most_common(limit)]
    
    def _get_top_signatures(self, logs: List[Dict], limit: int) -> List[str]:
        from collections import Counter
        sigs = [log['signature'] for log in logs]
        return [sig for sig, _ in Counter(sigs).most_common(limit)]
    
    def _group_by_attack_type(self, logs: List[Dict]) -> Dict:
        from collections import Counter
        types = [log.get('attack_type', 'Unknown') for log in logs]
        return dict(Counter(types))
    
    def _calculate_success_rate(self, logs: List[Dict]) -> float:
        if not logs:
            return 0.0
        successful = sum(1 for log in logs if log.get('success', False))
        return round((successful / len(logs)) * 100, 2)


async def main():
    agent = SecurityAgent()
    await agent.start()

if __name__ == "__main__":
    asyncio.run(main())