"""
mcp/log_collectors.py
Suricata와 HexStrike 로그 수집기
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import aiofiles

class SuricataCollector:
    """Suricata IPS 로그 수집"""
    
    def __init__(self, log_path: str = "/var/log/suricata/eve.json"):
        self.log_path = Path(log_path)
        self.cache = []
        self.last_position = 0
    
    async def get_recent_logs(self, count: int = 50) -> List[Dict]:
        """최근 N개 로그 조회"""
        if not self.log_path.exists():
            print(f"⚠️  Suricata log not found: {self.log_path}")
            return self._generate_sample_logs(count)
        
        logs = []
        try:
            async with aiofiles.open(self.log_path, 'r') as f:
                lines = await f.readlines()
                
                # 최근 로그부터 역순으로
                for line in reversed(lines[-count:]):
                    try:
                        log = json.loads(line.strip())
                        if log.get('event_type') == 'alert':
                            logs.append(self._parse_suricata_log(log))
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            print(f"❌ Error reading Suricata logs: {e}")
            return self._generate_sample_logs(count)
        
        return logs[:count]
    
    async def get_logs_since(self, cutoff_time: datetime) -> List[Dict]:
        """특정 시간 이후 로그 조회"""
        if not self.log_path.exists():
            return []
        
        logs = []
        try:
            async with aiofiles.open(self.log_path, 'r') as f:
                async for line in f:
                    try:
                        log = json.loads(line.strip())
                        if log.get('event_type') != 'alert':
                            continue
                        
                        timestamp = datetime.fromisoformat(
                            log['timestamp'].replace('Z', '+00:00')
                        )
                        
                        if timestamp >= cutoff_time:
                            logs.append(self._parse_suricata_log(log))
                    
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        
        except Exception as e:
            print(f"❌ Error reading Suricata logs: {e}")
        
        return logs
    
    def _parse_suricata_log(self, log: Dict) -> Dict:
        """Suricata 로그 파싱"""
        alert = log.get('alert', {})
        
        # 심각도 매핑
        severity_map = {1: 'critical', 2: 'high', 3: 'medium'}
        severity = severity_map.get(alert.get('severity', 3), 'low')
        
        return {
            "timestamp": log.get('timestamp'),
            "src_ip": log.get('src_ip'),
            "dest_ip": log.get('dest_ip'),
            "src_port": log.get('src_port'),
            "dest_port": log.get('dest_port'),
            "protocol": log.get('proto'),
            "signature": alert.get('signature'),
            "signature_id": alert.get('signature_id'),
            "category": alert.get('category'),
            "severity": severity,
            "action": alert.get('action', 'alert'),
            "raw": log
        }
    
    def _generate_sample_logs(self, count: int) -> List[Dict]:
        """샘플 로그 생성 (테스트용)"""
        import random
        
        signatures = [
            "ET SCAN Potential SSH Scan",
            "ET WEB_SERVER SQL Injection Attempt",
            "ET EXPLOIT Possible Remote Code Execution",
            "ET MALWARE Trojan Activity",
            "ET POLICY External IP Lookup",
            "ET DOS Possible DDoS Attack"
        ]
        
        ips = [
            "203.0.113.10", "198.51.100.25", "192.0.2.50",
            "203.0.113.100", "198.51.100.200"
        ]
        
        logs = []
        for i in range(count):
            logs.append({
                "timestamp": datetime.now().isoformat(),
                "src_ip": random.choice(ips),
                "dest_ip": "10.0.0.1",
                "src_port": random.randint(1024, 65535),
                "dest_port": random.choice([22, 80, 443, 3306, 8080]),
                "protocol": "TCP",
                "signature": random.choice(signatures),
                "signature_id": random.randint(2000000, 2999999),
                "category": random.choice(["Attempted Admin", "Web Application Attack", "Trojan"]),
                "severity": random.choice(["critical", "high", "medium", "low"]),
                "action": "alert"
            })
        
        return logs


class HexStrikeCollector:
    """HexStrike AI 로그 수집"""
    
    def __init__(self, log_path: str = "./logs/hexstrike"):
        self.log_path = Path(log_path)
        self.log_path.mkdir(parents=True, exist_ok=True)
    
    async def get_recent_logs(self, count: int = 50) -> List[Dict]:
        """최근 N개 로그 조회"""
        logs = []
        
        # HexStrike 로그 파일들 읽기
        log_files = sorted(self.log_path.glob("*.json"), reverse=True)
        
        if not log_files:
            print(f"⚠️  HexStrike logs not found in: {self.log_path}")
            return self._generate_sample_logs(count)
        
        for log_file in log_files:
            if len(logs) >= count:
                break
            
            try:
                async with aiofiles.open(log_file, 'r') as f:
                    content = await f.read()
                    file_logs = json.loads(content)
                    
                    if isinstance(file_logs, list):
                        logs.extend(file_logs)
                    else:
                        logs.append(file_logs)
            
            except Exception as e:
                print(f"❌ Error reading {log_file}: {e}")
                continue
        
        return logs[:count]
    
    async def get_logs_since(self, cutoff_time: datetime) -> List[Dict]:
        """특정 시간 이후 로그 조회"""
        all_logs = await self.get_recent_logs(1000)
        
        filtered_logs = []
        for log in all_logs:
            try:
                timestamp = datetime.fromisoformat(log['timestamp'])
                if timestamp >= cutoff_time:
                    filtered_logs.append(log)
            except (KeyError, ValueError):
                continue
        
        return filtered_logs
    
    def _generate_sample_logs(self, count: int) -> List[Dict]:
        """샘플 로그 생성 (테스트용)"""
        import random
        
        attack_types = [
            "SQL Injection",
            "XSS",
            "Command Injection",
            "Path Traversal",
            "Authentication Bypass",
            "Brute Force",
            "DDoS"
        ]
        
        payloads = [
            "' OR '1'='1",
            "<script>alert('XSS')</script>",
            "; cat /etc/passwd",
            "../../../etc/passwd",
            "admin' --",
            "POST /login (multiple attempts)"
        ]
        
        logs = []
        for i in range(count):
            attack_type = random.choice(attack_types)
            logs.append({
                "timestamp": datetime.now().isoformat(),
                "attack_id": f"HEX-{random.randint(100000, 999999)}",
                "attack_type": attack_type,
                "source_ip": f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}",
                "target": "http://10.0.0.1:3000",
                "payload": random.choice(payloads),
                "success": random.choice([True, False]),
                "response_code": random.choice([200, 403, 500, 404]),
                "severity": random.choice(["critical", "high", "medium", "low"])
            })
        
        return logs


class LogAnalyzer:
    """로그 분석 유틸리티"""
    
    @staticmethod
    def correlate_by_ip(suricata_logs: List[Dict], hexstrike_logs: List[Dict]) -> Dict:
        """IP 기반 상관관계 분석"""
        correlation = {
            "matched_ips": [],
            "undetected_attacks": [],
            "potential_false_positives": []
        }
        
        # HexStrike 공격 IP
        attack_ips = {log['source_ip'] for log in hexstrike_logs}
        
        # Suricata 탐지 IP
        detected_ips = {log['src_ip'] for log in suricata_logs}
        
        # 매칭
        correlation['matched_ips'] = list(attack_ips & detected_ips)
        correlation['undetected_attacks'] = list(attack_ips - detected_ips)
        correlation['potential_false_positives'] = list(detected_ips - attack_ips)
        
        return correlation
    
    @staticmethod
    def calculate_metrics(suricata_logs: List[Dict], hexstrike_logs: List[Dict]) -> Dict:
        """성능 지표 계산"""
        total_attacks = len(hexstrike_logs)
        if total_attacks == 0:
            return {
                "detection_rate": 0,
                "false_positive_rate": 0,
                "accuracy": 0
            }
        
        # 탐지된 공격
        attack_ips = {log['source_ip'] for log in hexstrike_logs}
        detected_ips = {log['src_ip'] for log in suricata_logs}
        
        true_positives = len(attack_ips & detected_ips)
        false_negatives = len(attack_ips - detected_ips)
        false_positives = len(detected_ips - attack_ips)
        
        detection_rate = (true_positives / total_attacks) * 100
        false_positive_rate = (false_positives / len(suricata_logs)) * 100 if suricata_logs else 0
        accuracy = (true_positives / (true_positives + false_positives + false_negatives)) * 100
        
        return {
            "detection_rate": round(detection_rate, 2),
            "false_positive_rate": round(false_positive_rate, 2),
            "accuracy": round(accuracy, 2),
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives
        }