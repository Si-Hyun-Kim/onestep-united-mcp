#!/usr/bin/env python3
"""
Suricata MCP Server - Suricata 전용 모니터링
- eve.json tail (실시간 모니터링)
- 파일 회전 대응
- LLM 룰 생성기와 연동 준비
"""

import os
import sys
import asyncio
import json
import io
import select
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

# MCP 모듈
try:
    from mcp.server.models import InitializationOptions
    from mcp.server import NotificationOptions, Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Resource, Tool, TextContent, ImageContent, EmbeddedResource
except ImportError:
    print("ERROR: mcp 모듈이 설치되지 않았습니다.", file=sys.stderr)
    print("설치: pip install mcp", file=sys.stderr)
    sys.exit(1)

# ================== 전역 상태 ==================
alert_history: list[dict] = []
blocked_ips: set[str] = set()

# 설정 로드
CONFIG_PATH = Path("config.json")
if CONFIG_PATH.exists():
    with open(CONFIG_PATH) as f:
        config = json.load(f)
else:
    config = {
        "suricata": {
            "eve_log_path": "/var/log/suricata/eve.json",
            "rules_path": "/etc/suricata/rules"
        },
        "mcp_server": {
            "backfill_lines": 50,
            "max_alerts": 1000
        }
    }

EVE_LOG_PATH = config["suricata"]["eve_log_path"]
RULES_PATH = config["suricata"]["rules_path"]
BACKFILL_LINES = config["mcp_server"]["backfill_lines"]
MAX_ALERTS = config["mcp_server"]["max_alerts"]

# ================== 안전 로깅 ==================
def log(*args, **kwargs):
    """stderr로만 로깅 (stdout은 MCP 통신용)"""
    print(*args, file=sys.stderr, **kwargs)

# ================== Suricata 모니터 ==================
class SuricataMonitor:
    """Suricata eve.json 실시간 tail 모니터 (비동기, 논블로킹 I/O)"""
    
    def __init__(self, eve_log_path: str = EVE_LOG_PATH, backfill_lines: int = BACKFILL_LINES):
        self.eve_log_path = Path(eve_log_path)
        self.backfill_lines = max(0, backfill_lines)
        self._fd: Optional[io.BufferedReader] = None  # <--- 타입 변경
        self._inode: Optional[int] = None
        self.running = False
        self._buffer = b""  # <--- 바이트 버퍼 추가

    async def start(self):
        """모니터링 시작"""
        self.running = True
        
        while not self.eve_log_path.exists():
            log(f"[MCP] Waiting for {self.eve_log_path}...")
            await asyncio.sleep(1)
        
        await self._open_file(initial=True)
        log(f"[MCP] Monitoring: {self.eve_log_path}")
        
        # 메인 루프
        while self.running:
            try:
                # 1. 파일이 열려있는지, 회전되었는지 먼저 확인
                await self._reopen_if_rotated()

                if not self._fd:
                    # 파일이 아직 (재)생성되지 않음
                    await asyncio.sleep(0.5)
                    continue

                # 2. select를 사용해 non-blocking으로 읽기 가능 여부 확인
                ready_to_read, _, _ = select.select([self._fd], [], [], 0.01) # 10ms 타임아웃

                if ready_to_read:
                    # 3. 읽을 데이터가 있음: 논블로킹 read()로 청크 읽기
                    data_chunk = self._fd.read(4096)
                    
                    if data_chunk:
                        # 4. 버퍼에 추가하고, 완성된 라인만 처리
                        self._buffer += data_chunk
                        self._drain_buffer()
                    else:
                        # 5. read()가 b"" (empty bytes) 반환 = EOF.
                        #    파일이 삭제/회전됨. 핸들러를 닫고 비워서 강제 재오픈.
                        log("[MCP] ⚠ EOF (log rotated/truncated), forcing reopen...")
                        self._fd.close()
                        self._fd = None
                        self._inode = None
                        await asyncio.sleep(0.1) # 새 파일 생성 대기
                else:
                    # 4. 읽을 데이터가 없으면 이벤트 루프에 제어권 반환
                    await asyncio.sleep(0.05) # 폴링 간격

            except PermissionError:
                log("[MCP] ❌ Permission denied reading eve.json")
                log("[MCP] 💡 Fix: sudo chmod 644 /var/log/suricata/eve.json")
                await asyncio.sleep(2)
            except FileNotFoundError:
                log("[MCP] ⚠ eve.json not found (rotating?). Retrying...")
                self._fd = None
                self._inode = None
                await asyncio.sleep(1)
            except Exception as e:
                log(f"[MCP] ❌ Error in monitor loop: {e}")
                import traceback
                log(traceback.format_exc()) # <--- 디버깅용 상세 에러 로그
                await asyncio.sleep(0.5)

    def _drain_buffer(self):
        """버퍼에서 완성된 라인을 찾아 처리"""
        # 마지막 줄바꿈 문자 위치 찾기
        last_newline = self._buffer.rfind(b"\n")
        if last_newline == -1:
            # 버퍼에 완성된 라인이 없음
            return

        # 완성된 라인들만 추출
        lines_to_process = self._buffer[:last_newline]
        # 나머지 (미완성 라인)는 버퍼에 남김
        self._buffer = self._buffer[last_newline + 1:]

        # 라인 처리
        for line_bytes in lines_to_process.splitlines():
            line_str = line_bytes.decode("utf-8", errors="ignore")
            self._consume_line(line_str)
            
    async def _open_file(self, initial=False):
        """파일 열기 (백필 처리 포함) - 바이너리 모드로 변경"""
        self._fd = open(self.eve_log_path, "rb") # <--- "r"이 아닌 "rb" (바이너리 읽기)
        stat = self.eve_log_path.stat()
        self._inode = stat.st_ino
        self._buffer = b"" # 버퍼 초기화
        
        if initial and self.backfill_lines > 0:
            # 최근 N줄 백필
            try:
                self._fd.seek(0, 2) # 끝으로
                size = self._fd.tell()
                block = 4096
                chunks = []
                
                # 역방향 읽기 (바이트 기준)
                while size > 0 and len(chunks) < 1024:
                    step = min(block, size)
                    size -= step
                    self._fd.seek(size)
                    data = self._fd.read(step) # <--- 바이트 읽기
                    chunks.append(data)
                    if data.count(b"\n") >= self.backfill_lines: # <--- 바이트 \n 카운트
                        break
                
                # 최근 N줄 추출 (바이트 기준)
                buf = b"".join(reversed(chunks))
                lines = buf.splitlines()[-self.backfill_lines:]
                for line_bytes in lines:
                    line_str = line_bytes.decode("utf-8", errors="ignore")
                    self._consume_line(line_str)
                
                log(f"[MCP] ✓ Backfilled {len(lines)} alerts")
            except Exception as e:
                log(f"[MCP] ⚠ Backfill failed: {e}")
            
            # 끝으로 이동
            self._fd.seek(0, 2)
        else:
            # tail -f 방식 (끝부터 시작)
            self._fd.seek(0, 2)
    
    async def _reopen_if_rotated(self):
        """로그 회전 감지 및 재오픈"""
        if not self._fd:
            await self._open_file()
            return
        
        try:
            stat = self.eve_log_path.stat()
        except FileNotFoundError:
            # 회전 직후
            self._fd.close()
            self._fd = None
            self._inode = None
            raise
        
        # inode 변경 = 파일 회전
        if self._inode is not None and stat.st_ino != self._inode:
            log("[MCP] 🔄 Log rotation detected, reopening...")
            try:
                self._fd.close()
            except Exception:
                pass
            await self._open_file()
    
    # [참고] _drain_new_lines 메서드는 더 이상 사용되지 않습니다.
    #      start 루프가 직접 read()와 _drain_buffer()를 호출합니다.

    def _consume_line(self, line: str):
        """라인 파싱 (기존과 동일)"""
        s = line.strip()
        if not s:
            return
        
        try:
            event = json.loads(s)
        except json.JSONDecodeError:
            return
        
        # [!!!] 진단용 로그: 이 로그는 터미널에 출력되어야 합니다.
        log(f"[MCP] Read event type: {event.get('event_type', 'unknown')}")

        if event.get("event_type") != "alert":
            return
        
        self._process_alert(event)
    
    def _process_alert(self, event: dict):
        """알림 처리 및 저장 (기존과 동일)"""
        alert = event.get("alert", {}) or {}
        
        info = {
            "timestamp": event.get("timestamp", ""),
            "flow_id": event.get("flow_id", 0),
            "src_ip": event.get("src_ip", ""),
            "dest_ip": event.get("dest_ip", ""),
            "src_port": event.get("src_port", 0),
            "dest_port": event.get("dest_port", 0),
            "proto": event.get("proto", ""),
            "category": alert.get("category", ""),
            "severity": alert.get("severity", 3),
            "signature": alert.get("signature", ""),
            "signature_id": alert.get("signature_id", 0),
            "action": alert.get("action", ""),
            "app_proto": event.get("app_proto", ""),
            "metadata": alert.get("metadata", {}),
        }
        
        alert_history.append(info)
        
        if len(alert_history) > MAX_ALERTS:
            del alert_history[:len(alert_history) - MAX_ALERTS]
        
        if info["severity"] <= 2:
            log(f"[ALERT] {info['severity']} | {info['src_ip']} → {info['dest_ip']} | {info['signature']}")

# ================== MCP 서버 ==================
server = Server("suricata-mcp-server")
monitor = SuricataMonitor()

@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    """제공 가능한 리소스 목록"""
    return [
        Resource(
            uri="suricata://alerts",
            name="Suricata Alerts",
            description="Recent security alerts from Suricata IDS",
            mimeType="application/json",
        ),
        Resource(
            uri="suricata://blocked_ips",
            name="Blocked IPs",
            description="List of blocked IP addresses",
            mimeType="application/json",
        ),
        Resource(
            uri="suricata://stats",
            name="Statistics",
            description="Alert statistics",
            mimeType="application/json",
        ),
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """리소스 읽기"""
    if uri == "suricata://alerts":
        return json.dumps({
            "total": len(alert_history),
            "alerts": alert_history[-100:]  # 최근 100개
        }, indent=2)
    
    if uri == "suricata://blocked_ips":
        return json.dumps({
            "total": len(blocked_ips),
            "ips": list(blocked_ips)
        }, indent=2)
    
    if uri == "suricata://stats":
        # 통계 계산
        total = len(alert_history)
        by_severity = {}
        by_category = {}
        top_sources = {}
        
        for a in alert_history:
            sev = a.get("severity", 3)
            by_severity[sev] = by_severity.get(sev, 0) + 1
            
            cat = a.get("category", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1
            
            src = a.get("src_ip", "unknown")
            top_sources[src] = top_sources.get(src, 0) + 1
        
        top_10 = dict(sorted(top_sources.items(), key=lambda x: x[1], reverse=True)[:10])
        
        return json.dumps({
            "total_alerts": total,
            "by_severity": by_severity,
            "by_category": by_category,
            "top_sources": top_10,
            "blocked_ips": len(blocked_ips)
        }, indent=2)
    
    raise ValueError(f"Unknown resource: {uri}")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """제공 가능한 도구 목록"""
    return [
        Tool(
            name="get_recent_alerts",
            description="Get recent security alerts from Suricata",
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {
                        "type": "number",
                        "description": "Number of alerts to retrieve",
                        "default": 10
                    },
                    "severity": {
                        "type": "number",
                        "description": "Filter by severity (1=high, 2=medium, 3=low)",
                        "minimum": 1,
                        "maximum": 3
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by category"
                    }
                },
            },
        ),
        Tool(
            name="search_alerts",
            description="Search alerts by IP address or signature",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "IP address or signature to search"
                    }
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_alert_stats",
            description="Get alert statistics",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="block_ip",
            description="Block an IP address using iptables",
            inputSchema={
                "type": "object",
                "properties": {
                    "ip": {
                        "type": "string",
                        "description": "IP address to block"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for blocking"
                    }
                },
                "required": ["ip"],
            },
        ),
        Tool(
            name="add_suricata_rule",
            description="Add a new Suricata rule (준비 중 - LLM 연동용)",
            inputSchema={
                "type": "object",
                "properties": {
                    "rule_content": {
                        "type": "string",
                        "description": "Suricata rule content"
                    },
                    "description": {
                        "type": "string",
                        "description": "Rule description"
                    }
                },
                "required": ["rule_content"],
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent | ImageContent | EmbeddedResource]:
    """도구 실행"""
    args = arguments or {}
    
    # 최근 알림 조회
    if name == "get_recent_alerts":
        count = int(args.get("count", 10))
        severity_filter = args.get("severity", None)
        category_filter = args.get("category", None)
        
        alerts = alert_history[-count:]
        
        # 필터링
        if severity_filter is not None:
            alerts = [a for a in alerts if a.get("severity") == int(severity_filter)]
        
        if category_filter:
            alerts = [a for a in alerts if a.get("category", "").lower() == category_filter.lower()]
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "count": len(alerts),
                "alerts": alerts
            }, indent=2)
        )]
    
    # 알림 검색
    if name == "search_alerts":
        query = str(args.get("query", "")).lower()
        results = []
        
        for a in alert_history:
            if (query in (a.get("src_ip", "") or "").lower() or
                query in (a.get("dest_ip", "") or "").lower() or
                query in (a.get("signature", "") or "").lower()):
                results.append(a)
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "query": query,
                "results": len(results),
                "alerts": results[-50:]  # 최근 50개
            }, indent=2)
        )]
    
    # 통계
    if name == "get_alert_stats":
        total = len(alert_history)
        by_severity = {}
        by_category = {}
        top_sources = {}
        
        for a in alert_history:
            sev = a.get("severity", 3)
            by_severity[sev] = by_severity.get(sev, 0) + 1
            
            cat = a.get("category", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1
            
            src = a.get("src_ip", "unknown")
            top_sources[src] = top_sources.get(src, 0) + 1
        
        top_10 = dict(sorted(top_sources.items(), key=lambda x: x[1], reverse=True)[:10])
        
        stats = {
            "total_alerts": total,
            "by_severity": by_severity,
            "by_category": by_category,
            "top_sources": top_10,
            "blocked_ips": len(blocked_ips)
        }
        
        return [TextContent(type="text", text=json.dumps(stats, indent=2))]
    
    # IP 차단
    if name == "block_ip":
        ip = args.get("ip")
        if not ip:
            raise ValueError("IP address required")
        
        reason = args.get("reason", "Security threat")
        is_ipv6 = ":" in ip
        cmd = ["sudo", "ip6tables" if is_ipv6 else "iptables", "-A", "INPUT", "-s", ip, "-j", "DROP"]
        
        try:
            import subprocess
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                blocked_ips.add(ip)
                log(f"[BLOCK] IP {ip} blocked: {reason}")
                
                # 로그 파일에도 기록
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "action": "BLOCK",
                    "ip": ip,
                    "reason": reason
                }
                
                log_dir = Path("logs/actions")
                log_dir.mkdir(parents=True, exist_ok=True)
                
                with open(log_dir / "blocks.log", "a") as f:
                    f.write(json.dumps(log_entry) + "\n")
                
                return [TextContent(
                    type="text",
                    text=f"✓ Successfully blocked {ip}\nReason: {reason}"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"✗ Failed to block {ip}\nError: {result.stderr}"
                )]
        except Exception as e:
            return [TextContent(type="text", text=f"✗ Error: {e}")]
    
    # Suricata 룰 추가 (준비 중)
    if name == "add_suricata_rule":
        rule_content = args.get("rule_content")
        description = args.get("description", "")
        
        # 🚧 준비 중: LLM 연동 후 구현
        return [TextContent(
            type="text",
            text=json.dumps({
                "status": "준비 중",
                "message": "LLM 연동 후 구현 예정",
                "received_rule": rule_content,
                "description": description,
                "target_path": RULES_PATH
            }, indent=2, ensure_ascii=False)
        )]
    
    raise ValueError(f"Unknown tool: {name}")

# ================== 엔트리 포인트 ==================
async def main():
    """메인 함수"""
    log("=" * 60)
    log("🛡️  Suricata MCP Server Starting...")
    log("=" * 60)
    log(f"📁 Eve Log: {EVE_LOG_PATH}")
    log(f"📁 Rules Path: {RULES_PATH}")
    log(f"🔄 Backfill: {BACKFILL_LINES} lines")
    log(f"💾 Max Alerts: {MAX_ALERTS}")
    log("=" * 60)
    
    # Suricata 모니터 시작 (백그라운드)
    monitor_task = asyncio.create_task(monitor.start())
    
    # MCP 서버 실행 (stdio)
    async with stdio_server() as (read_stream, write_stream):
        log("✓ Suricata MCP Server started (stdio)")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="suricata-mcp-server",
                server_version="2.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("\n🛑 Suricata MCP Server stopped by user")
    except Exception as e:
        log(f"❌ Fatal error: {e}")
        sys.exit(1)
