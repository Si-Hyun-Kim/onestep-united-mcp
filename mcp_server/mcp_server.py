#!/usr/bin/env python3
"""
FastMCP 기반 보안 로그 서버
Suricata IPS 및 HexStrike AI 로그 수집 및 관리
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from log_collectors import SuricataCollector, HexStrikeCollector
from rule_manager import SuricataRuleManager

class SecurityMCPServer:
    def __init__(self):
        self.server = Server("security-mcp-server")
        self.suricata_collector = SuricataCollector()
        self.hexstrike_collector = HexStrikeCollector()
        self.rule_manager = SuricataRuleManager()
        
        # 캐시
        self.cache = {
            'suricata_logs': [],
            'hexstrike_logs': [],
            'last_update': None
        }
        
        self._register_tools()
    
    def _register_tools(self):
        """MCP 도구 등록"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="get_suricata_logs",
                    description="Suricata IPS 로그 조회 (최근 N개)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "count": {
                                "type": "integer",
                                "description": "조회할 로그 개수",
                                "default": 50
                            },
                            "severity": {
                                "type": "string",
                                "description": "필터링할 심각도 (critical/high/medium/low)",
                                "default": "all"
                            }
                        }
                    }
                ),
                Tool(
                    name="get_hexstrike_logs",
                    description="HexStrike AI 공격 로그 조회",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "count": {
                                "type": "integer",
                                "description": "조회할 로그 개수",
                                "default": 50
                            },
                            "attack_type": {
                                "type": "string",
                                "description": "공격 유형 필터",
                                "default": "all"
                            }
                        }
                    }
                ),
                Tool(
                    name="compare_logs",
                    description="Suricata와 HexStrike 로그 비교 분석",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "time_window": {
                                "type": "integer",
                                "description": "분석 시간 범위 (분)",
                                "default": 60
                            }
                        }
                    }
                ),
                Tool(
                    name="get_active_rules",
                    description="현재 활성화된 Suricata 룰 조회",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "룰 카테고리 필터",
                                "default": "all"
                            }
                        }
                    }
                ),
                Tool(
                    name="add_suricata_rule",
                    description="Suricata 룰 추가",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "rule_content": {
                                "type": "string",
                                "description": "Suricata 룰 내용"
                            },
                            "description": {
                                "type": "string",
                                "description": "룰 설명"
                            },
                            "auto_reload": {
                                "type": "boolean",
                                "description": "자동 리로드 여부",
                                "default": True
                            }
                        },
                        "required": ["rule_content"]
                    }
                ),
                Tool(
                    name="block_ip",
                    description="IP 차단 (iptables)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ip": {
                                "type": "string",
                                "description": "차단할 IP 주소"
                            },
                            "reason": {
                                "type": "string",
                                "description": "차단 사유"
                            },
                            "duration": {
                                "type": "integer",
                                "description": "차단 기간 (분, 0=영구)",
                                "default": 0
                            }
                        },
                        "required": ["ip"]
                    }
                ),
                Tool(
                    name="get_statistics",
                    description="전체 통계 정보 조회",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "time_range": {
                                "type": "string",
                                "description": "시간 범위 (1h/24h/7d/30d)",
                                "default": "24h"
                            }
                        }
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[TextContent]:
            try:
                if name == "get_suricata_logs":
                    result = await self._get_suricata_logs(
                        arguments.get('count', 50),
                        arguments.get('severity', 'all')
                    )
                
                elif name == "get_hexstrike_logs":
                    result = await self._get_hexstrike_logs(
                        arguments.get('count', 50),
                        arguments.get('attack_type', 'all')
                    )
                
                elif name == "compare_logs":
                    result = await self._compare_logs(
                        arguments.get('time_window', 60)
                    )
                
                elif name == "get_active_rules":
                    result = await self._get_active_rules(
                        arguments.get('category', 'all')
                    )
                
                elif name == "add_suricata_rule":
                    result = await self._add_suricata_rule(
                        arguments['rule_content'],
                        arguments.get('description', ''),
                        arguments.get('auto_reload', True)
                    )
                
                elif name == "block_ip":
                    result = await self._block_ip(
                        arguments['ip'],
                        arguments.get('reason', 'Security threat'),
                        arguments.get('duration', 0)
                    )
                
                elif name == "get_statistics":
                    result = await self._get_statistics(
                        arguments.get('time_range', '24h')
                    )
                
                else:
                    result = {"error": f"Unknown tool: {name}"}
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, ensure_ascii=False, indent=2)
                )]
            
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, ensure_ascii=False)
                )]
    
    async def _get_suricata_logs(self, count: int, severity: str) -> Dict:
        """Suricata 로그 조회"""
        logs = await self.suricata_collector.get_recent_logs(count)
        
        if severity != 'all':
            logs = [log for log in logs if log.get('severity') == severity]
        
        return {
            "success": True,
            "count": len(logs),
            "logs": logs,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _get_hexstrike_logs(self, count: int, attack_type: str) -> Dict:
        """HexStrike 로그 조회"""
        logs = await self.hexstrike_collector.get_recent_logs(count)
        
        if attack_type != 'all':
            logs = [log for log in logs if log.get('attack_type') == attack_type]
        
        return {
            "success": True,
            "count": len(logs),
            "logs": logs,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _compare_logs(self, time_window: int) -> Dict:
        """로그 비교 분석"""
        cutoff_time = datetime.now() - timedelta(minutes=time_window)
        
        # Suricata 로그
        suricata_logs = await self.suricata_collector.get_logs_since(cutoff_time)
        
        # HexStrike 로그
        hexstrike_logs = await self.hexstrike_collector.get_logs_since(cutoff_time)
        
        # IP 기반 매칭
        comparison = self._match_logs_by_ip(suricata_logs, hexstrike_logs)
        
        return {
            "success": True,
            "time_window_minutes": time_window,
            "suricata_count": len(suricata_logs),
            "hexstrike_count": len(hexstrike_logs),
            "matched_attacks": comparison['matched'],
            "undetected_attacks": comparison['undetected'],
            "false_positives": comparison['false_positives'],
            "detection_rate": comparison['detection_rate']
        }
    
    def _match_logs_by_ip(self, suricata_logs: List, hexstrike_logs: List) -> Dict:
        """IP 기반 로그 매칭"""
        # HexStrike 공격 IP 추출
        attack_ips = {log['source_ip'] for log in hexstrike_logs}
        
        # Suricata 탐지 IP 추출
        detected_ips = {log['src_ip'] for log in suricata_logs}
        
        # 매칭
        matched = attack_ips & detected_ips
        undetected = attack_ips - detected_ips
        false_positives = detected_ips - attack_ips
        
        detection_rate = len(matched) / len(attack_ips) * 100 if attack_ips else 0
        
        return {
            "matched": list(matched),
            "undetected": list(undetected),
            "false_positives": list(false_positives),
            "detection_rate": round(detection_rate, 2)
        }
    
    async def _get_active_rules(self, category: str) -> Dict:
        """활성 룰 조회"""
        rules = await self.rule_manager.get_active_rules(category)
        
        return {
            "success": True,
            "category": category,
            "count": len(rules),
            "rules": rules
        }
    
    async def _add_suricata_rule(self, rule_content: str, description: str, auto_reload: bool) -> Dict:
        """Suricata 룰 추가"""
        result = await self.rule_manager.add_rule(
            rule_content,
            description,
            auto_reload
        )
        
        return result
    
    async def _block_ip(self, ip: str, reason: str, duration: int) -> Dict:
        """IP 차단"""
        import subprocess
        
        try:
            # iptables로 차단
            cmd = f"sudo iptables -A INPUT -s {ip} -j DROP"
            subprocess.run(cmd, shell=True, check=True)
            
            # 로그 기록
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "action": "BLOCK",
                "ip": ip,
                "reason": reason,
                "duration": duration
            }
            
            log_file = Path("./logs/actions/blocks.log")
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            return {
                "success": True,
                "message": f"IP {ip} blocked successfully",
                "reason": reason,
                "duration": duration
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_statistics(self, time_range: str) -> Dict:
        """통계 정보"""
        # 시간 범위 파싱
        range_map = {
            '1h': 60,
            '24h': 1440,
            '7d': 10080,
            '30d': 43200
        }
        minutes = range_map.get(time_range, 1440)
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        # 로그 수집
        suricata_logs = await self.suricata_collector.get_logs_since(cutoff_time)
        hexstrike_logs = await self.hexstrike_collector.get_logs_since(cutoff_time)
        
        # 통계 계산
        stats = {
            "time_range": time_range,
            "total_alerts": len(suricata_logs),
            "total_attacks": len(hexstrike_logs),
            "unique_source_ips": len(set(log['src_ip'] for log in suricata_logs)),
            "severity_distribution": self._calculate_severity_distribution(suricata_logs),
            "top_signatures": self._get_top_signatures(suricata_logs, 10),
            "attack_types": self._get_attack_types(hexstrike_logs),
            "hourly_distribution": self._calculate_hourly_distribution(suricata_logs)
        }
        
        return stats
    
    def _calculate_severity_distribution(self, logs: List) -> Dict:
        """심각도 분포 계산"""
        distribution = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for log in logs:
            severity = log.get('severity', 'low')
            if severity in distribution:
                distribution[severity] += 1
        return distribution
    
    def _get_top_signatures(self, logs: List, limit: int) -> List:
        """상위 시그니처"""
        from collections import Counter
        signatures = [log.get('alert', {}).get('signature', 'Unknown') for log in logs]
        top = Counter(signatures).most_common(limit)
        return [{"signature": sig, "count": count} for sig, count in top]
    
    def _get_attack_types(self, logs: List) -> Dict:
        """공격 유형 분포"""
        from collections import Counter
        attack_types = [log.get('attack_type', 'Unknown') for log in logs]
        distribution = Counter(attack_types)
        return dict(distribution)
    
    def _calculate_hourly_distribution(self, logs: List) -> List:
        """시간대별 분포"""
        from collections import defaultdict
        hourly = defaultdict(int)
        
        for log in logs:
            try:
                timestamp = datetime.fromisoformat(log.get('timestamp', ''))
                hour = timestamp.hour
                hourly[hour] += 1
            except:
                continue
        
        return [{"hour": h, "count": hourly[h]} for h in range(24)]

    async def run(self):
        """서버 실행"""
        async with stdio_server() as (read_stream, write_stream):
            print("🚀 Security MCP Server Started")
            print("📊 Collecting logs from Suricata and HexStrike...")
            await self.server.run(read_stream, write_stream)

async def main():
    server = SecurityMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())