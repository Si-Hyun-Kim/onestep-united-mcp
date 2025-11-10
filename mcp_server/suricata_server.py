#!/usr/bin/env python3
"""
Suricata MCP Server - 데이터 공유 버전
- eve.json 실시간 모니터링
- 알림 데이터를 data/alerts.json에 저장 (FastAPI와 공유)
- 생성된 룰을 data/rules.json에 저장
- Ollama 자동 룰 생성
"""

import os
import sys
import asyncio
import json
import io
from pathlib import Path
from typing import Optional
from datetime import datetime
import subprocess

try:
    import httpx
except ImportError:
    print("ERROR: httpx 설치 필요 (pip install httpx)", file=sys.stderr)
    sys.exit(1)

# ================== 전역 상태 ==================
alert_history: list[dict] = []
generated_rules: list[dict] = []
processed_alerts: set[int] = set()

# 데이터 파일 경로
DATA_DIR = Path("data")
ALERTS_FILE = DATA_DIR / "alerts.json"
RULES_FILE = DATA_DIR / "rules.json"

# 설정
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
            "max_alerts": 1000,
            "auto_generate_rules": True,
            "severity_threshold": 2
        },
        "ollama": {
            "enabled": True,
            "base_url": "http://localhost:11434",
            "model": "llama3.2:latest"
        }
    }

EVE_LOG_PATH = config["suricata"]["eve_log_path"]
RULES_PATH = config["suricata"]["rules_path"]
BACKFILL_LINES = config["mcp_server"]["backfill_lines"]
MAX_ALERTS = config["mcp_server"]["max_alerts"]
AUTO_GENERATE = config["mcp_server"].get("auto_generate_rules", True)
SEVERITY_THRESHOLD = config["mcp_server"].get("severity_threshold", 2)

OLLAMA_ENABLED = config["ollama"]["enabled"]
OLLAMA_BASE_URL = config["ollama"]["base_url"]
OLLAMA_MODEL = config["ollama"]["model"]

# 데이터 디렉토리 생성
DATA_DIR.mkdir(exist_ok=True)

# ================== 로깅 ==================
def log(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# ================== 데이터 공유 함수 ==================
def save_alerts():
    """알림 데이터를 JSON 파일로 저장"""
    try:
        with open(ALERTS_FILE, "w") as f:
            json.dump({
                "total": len(alert_history),
                "alerts": alert_history[-1000:]  # 최근 1000개만
            }, f, indent=2)
    except Exception as e:
        log(f"[Data] ❌ 알림 저장 실패: {e}")

def save_rules():
    """생성된 룰을 JSON 파일로 저장"""
    try:
        with open(RULES_FILE, "w") as f:
            json.dump({
                "total": len(generated_rules),
                "rules": generated_rules
            }, f, indent=2)
    except Exception as e:
        log(f"[Data] ❌ 룰 저장 실패: {e}")

# ================== Ollama 클라이언트 ==================
class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_MODEL):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def generate_rule(self, alert_data: dict) -> Optional[str]:
        if not OLLAMA_ENABLED:
            return None
        
        prompt = self._build_prompt(alert_data)
        
        try:
            log(f"[Ollama] 🤖 LLM 룰 생성: {alert_data['signature'][:50]}...")
            
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                rule = self._extract_rule(result.get("response", ""))
                if rule:
                    log(f"[Ollama] ✓ 룰 생성 완료")
                return rule
            else:
                log(f"[Ollama] ❌ HTTP 오류: {response.status_code}")
                return None
                
        except httpx.TimeoutException:
            log(f"[Ollama] ❌ 타임아웃")
            return None
        except httpx.ConnectError:
            log(f"[Ollama] ❌ 연결 실패")
            return None
        except Exception as e:
            log(f"[Ollama] ❌ 예외: {e}")
            return None
    
    def _build_prompt(self, alert_data: dict) -> str:
        return f"""You are a Suricata IDS rule generator. Create a detection rule for this alert.

ALERT:
- Source IP: {alert_data.get('src_ip')}
- Destination IP: {alert_data.get('dest_ip')}
- Protocol: {alert_data.get('proto')}
- Signature: {alert_data.get('signature')}
- Category: {alert_data.get('category')}
- Severity: {alert_data.get('severity')}

REQUIREMENTS:
1. Output ONLY the Suricata rule (one line)
2. Format: alert [protocol] any any -> any any (msg:"..."; content:"..."; classtype:...; sid:9XXXXXX; rev:1;)
3. Use SID 9000000-9999999
4. Choose appropriate classtype
5. No explanations, only the rule

Generate rule:"""
    
    def _extract_rule(self, response: str) -> Optional[str]:
        lines = response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('```'):
                continue
            if (line.startswith(('alert', 'drop', 'reject', 'pass')) and 
                'sid:' in line and 'msg:' in line):
                if not line.endswith(';'):
                    line += ';'
                return line
        return None
    
    async def close(self):
        await self.client.aclose()

# ================== 룰 관리자 ==================
class RuleManager:
    def __init__(self, rules_path: str = RULES_PATH):
        self.rules_path = Path(rules_path)
        self.auto_rules_file = self.rules_path / "auto_generated.rules"
    
    async def add_rule(self, rule: str, alert_info: dict) -> bool:
        try:
            self.rules_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(self.auto_rules_file, "a") as f:
                f.write(f"\n# Generated: {timestamp}\n")
                f.write(f"# Alert: {alert_info.get('signature', 'Unknown')}\n")
                f.write(f"# Severity: {alert_info.get('severity')}\n")
                f.write(f"{rule}\n")
            
            # 생성 기록 저장
            generated_rules.append({
                "rule": rule,
                "alert": alert_info.get('signature', 'Unknown'),
                "severity": alert_info.get('severity'),
                "timestamp": timestamp,
                "file": "auto_generated.rules"
            })
            
            # JSON 파일에 저장 (FastAPI와 공유)
            save_rules()
            
            log(f"[Rules] ✓ 룰 추가: {self.auto_rules_file}")
            
            await self._reload_suricata()
            
            return True
            
        except PermissionError:
            log(f"[Rules] ❌ 권한 거부")
            return False
        except Exception as e:
            log(f"[Rules] ❌ 실패: {e}")
            return False
    
    async def _reload_suricata(self):
        try:
            log("[Rules] 🔄 Suricata 재시작...")
            result = subprocess.run(
                ["sudo", "systemctl", "reload", "suricata"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                log("[Rules] ✓ 재시작 완료")
            else:
                log(f"[Rules] ⚠ 재시작 실패: {result.stderr}")
        except Exception as e:
            log(f"[Rules] ❌ 예외: {e}")

# ================== Suricata 모니터 ==================
class SuricataMonitor:
    def __init__(self, eve_log_path: str = EVE_LOG_PATH, backfill_lines: int = BACKFILL_LINES):
        self.eve_log_path = Path(eve_log_path)
        self.backfill_lines = max(0, backfill_lines)
        self._fd: Optional[io.BufferedReader] = None
        self._inode: Optional[int] = None
        self.running = False
        self._buffer = b""
        self.ollama = OllamaClient()
        self.rule_manager = RuleManager()
        self._save_counter = 0

    async def start(self):
        self.running = True
        
        while not self.eve_log_path.exists():
            log(f"[MCP] eve.json 대기: {self.eve_log_path}...")
            await asyncio.sleep(1)
        
        await self._open_file(initial=True)
        log(f"[MCP] ✓ 모니터링 시작: {self.eve_log_path}")
        
        if AUTO_GENERATE and OLLAMA_ENABLED:
            log(f"[MCP] 🤖 자동 룰 생성 활성화 (심각도 <= {SEVERITY_THRESHOLD})")
        
        while self.running:
            try:
                await self._reopen_if_rotated()

                if not self._fd:
                    await asyncio.sleep(0.5)
                    continue

                current_pos = self._fd.tell()
                stat_result = os.fstat(self._fd.fileno())
                
                if stat_result.st_size > current_pos:
                    data_chunk = self._fd.read(stat_result.st_size - current_pos)
                    if data_chunk:
                        self._buffer += data_chunk
                        await self._drain_buffer()
                
                elif stat_result.st_size < current_pos:
                    log("[MCP] ⚠ 로그 트렁케이트")
                    self._fd.seek(stat_result.st_size)
                    self._buffer = b""
                
                await asyncio.sleep(0.1)

            except PermissionError:
                log("[MCP] ❌ 권한 거부")
                await asyncio.sleep(2)
            except FileNotFoundError:
                log("[MCP] ⚠ 파일 없음")
                if self._fd:
                    try: self._fd.close()
                    except: pass
                self._fd = None
                self._inode = None
                await asyncio.sleep(1)
            except Exception as e:
                log(f"[MCP] ❌ 오류: {e}")
                await asyncio.sleep(0.5)

    async def _drain_buffer(self):
        last_newline = self._buffer.rfind(b"\n")
        if last_newline == -1:
            return

        lines_to_process = self._buffer[:last_newline]
        self._buffer = self._buffer[last_newline + 1:]

        for line_bytes in lines_to_process.splitlines():
            line_str = line_bytes.decode("utf-8", errors="ignore")
            await self._consume_line(line_str)
            
    async def _open_file(self, initial=False):
        log(f"[MCP] 파일 열기: {self.eve_log_path}...")
        self._fd = open(self.eve_log_path, "rb")
        stat = self.eve_log_path.stat()
        self._inode = stat.st_ino
        self._buffer = b""
        
        if initial and self.backfill_lines > 0:
            try:
                self._fd.seek(0, 2)
                size = self._fd.tell()
                block = 4096
                chunks = []
                
                while size > 0 and len(chunks) < 1024:
                    step = min(block, size)
                    size -= step
                    self._fd.seek(size)
                    data = self._fd.read(step)
                    chunks.append(data)
                    if data.count(b"\n") >= self.backfill_lines:
                        break
                
                buf = b"".join(reversed(chunks))
                lines = buf.splitlines()[-self.backfill_lines:]
                for line_bytes in lines:
                    line_str = line_bytes.decode("utf-8", errors="ignore")
                    await self._consume_line(line_str)
                
                log(f"[MCP] ✓ 백필: {len(lines)}개")
            except Exception as e:
                log(f"[MCP] ⚠ 백필 실패: {e}")
            
            self._fd.seek(0, 2)
        else:
            self._fd.seek(0, 2)
    
    async def _reopen_if_rotated(self):
        if not self._fd:
            await self._open_file()
            return
        
        try:
            path_stat = self.eve_log_path.stat()
        except FileNotFoundError:
            log("[MCP] 🔄 파일 사라짐")
            self._fd.close()
            self._fd = None
            self._inode = None
            raise
        
        if self._inode is not None and path_stat.st_ino != self._inode:
            log("[MCP] 🔄 로그 회전")
            self._fd.close()
            self._fd = None
            await self._open_file()

    async def _consume_line(self, line: str):
        s = line.strip()
        if not s:
            return
        
        try:
            event = json.loads(s)
        except json.JSONDecodeError:
            return
        
        if event.get("event_type") != "alert":
            return
        
        await self._process_alert(event)
    
    async def _process_alert(self, event: dict):
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
        }
        
        alert_history.append(info)
        
        if len(alert_history) > MAX_ALERTS:
            del alert_history[:len(alert_history) - MAX_ALERTS]
        
        # 10개마다 파일 저장
        self._save_counter += 1
        if self._save_counter >= 10:
            save_alerts()
            self._save_counter = 0
        
        severity = info["severity"]
        
        if severity <= 2:
            log(f"[ALERT] 심각도 {severity} | {info['src_ip']} → {info['dest_ip']} | {info['signature']}")
        
        # 자동 룰 생성
        if AUTO_GENERATE and OLLAMA_ENABLED and severity <= SEVERITY_THRESHOLD:
            signature_id = info["signature_id"]
            
            if signature_id not in processed_alerts:
                processed_alerts.add(signature_id)
                
                log(f"[MCP] 🎯 자동 룰 생성: {info['signature']}")
                
                rule = await self.ollama.generate_rule(info)
                
                if rule:
                    success = await self.rule_manager.add_rule(rule, info)
                    if success:
                        log(f"[MCP] ✅ 룰 생성 & 추가 완료!")
    
    async def stop(self):
        self.running = False
        save_alerts()  # 종료 시 마지막 저장
        save_rules()
        if self._fd:
            try:
                self._fd.close()
            except:
                pass
        await self.ollama.close()

# ================== 메인 ==================
async def main():
    log("=" * 60)
    log("🛡️  Suricata MCP Server (데이터 공유)")
    log("=" * 60)
    log(f"📁 Eve Log: {EVE_LOG_PATH}")
    log(f"📁 Rules Path: {RULES_PATH}")
    log(f"💾 Alerts File: {ALERTS_FILE}")
    log(f"💾 Rules File: {RULES_FILE}")
    log(f"🤖 Ollama: {'Enabled' if OLLAMA_ENABLED else 'Disabled'}")
    if OLLAMA_ENABLED:
        log(f"   Model: {OLLAMA_MODEL}")
    log(f"⚡ Auto Gen: {'Enabled' if AUTO_GENERATE else 'Disabled'}")
    log("=" * 60)
    
    monitor = SuricataMonitor()
    
    try:
        await monitor.start()
    except KeyboardInterrupt:
        log("\n🛑 중지...")
        await monitor.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("\n🛑 종료")