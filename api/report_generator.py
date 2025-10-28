"""
보고서 생성기
PDF, HTML, JSON 형식으로 보안 보고서 생성
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, List
import json
import sys

sys.path.append('../mcp_server')
from log_collectors import SuricataCollector, HexStrikeCollector, LogAnalyzer

class ReportGenerator:
    """보안 보고서 생성기"""
    
    def __init__(self, reports_dir: str = "./reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        self.suricata_collector = SuricataCollector()
        self.hexstrike_collector = HexStrikeCollector()
    
    async def generate(self, report_data: Dict, format: str = "pdf") -> Path:
        """보고서 생성 메인 함수"""
        # 데이터 수집
        start_time = report_data['start_time']
        end_time = report_data['end_time']
        report_type = report_data.get('type', 'summary')
        
        # 로그 수집
        suricata_logs = await self.suricata_collector.get_logs_since(start_time)
        hexstrike_logs = await self.hexstrike_collector.get_logs_since(end_time)
        
        # 필터링 (기간 내)
        suricata_logs = [log for log in suricata_logs 
                         if start_time <= datetime.fromisoformat(log['timestamp']) <= end_time]
        hexstrike_logs = [log for log in hexstrike_logs 
                          if start_time <= datetime.fromisoformat(log['timestamp']) <= end_time]
        
        # 분석
        analysis_data = self._analyze_data(suricata_logs, hexstrike_logs)
        
        # 보고서 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == "pdf":
            return await self._generate_pdf(report_type, analysis_data, timestamp)
        elif format == "html":
            return await self._generate_html(report_type, analysis_data, timestamp)
        elif format == "json":
            return await self._generate_json(report_type, analysis_data, timestamp)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _analyze_data(self, suricata_logs: List, hexstrike_logs: List) -> Dict:
        """데이터 분석"""
        from collections import Counter
        
        # 기본 통계
        total_alerts = len(suricata_logs)
        total_attacks = len(hexstrike_logs)
        
        # 심각도 분포
        severity_dist = Counter(log.get('severity', 'low') for log in suricata_logs)
        
        # 상위 IP
        top_ips = Counter(log.get('src_ip') for log in suricata_logs).most_common(10)
        
        # 상위 시그니처
        top_signatures = Counter(log.get('signature') for log in suricata_logs).most_common(10)
        
        # 공격 유형
        attack_types = Counter(log.get('attack_type', 'Unknown') for log in hexstrike_logs)
        
        # 탐지 지표
        metrics = LogAnalyzer.calculate_metrics(suricata_logs, hexstrike_logs)
        
        # 시간대별 분포
        hourly_dist = self._calculate_hourly_distribution(suricata_logs)
        
        return {
            "summary": {
                "total_alerts": total_alerts,
                "total_attacks": total_attacks,
                "detection_rate": metrics['detection_rate'],
                "false_positives": metrics['false_positives'],
                "false_negatives": metrics['false_negatives']
            },
            "severity_distribution": dict(severity_dist),
            "top_ips": [{"ip": ip, "count": count} for ip, count in top_ips],
            "top_signatures": [{"signature": sig, "count": count} for sig, count in top_signatures],
            "attack_types": dict(attack_types),
            "hourly_distribution": hourly_dist,
            "metrics": metrics
        }
    
    def _calculate_hourly_distribution(self, logs: List) -> Dict:
        """시간대별 분포 계산"""
        from collections import defaultdict
        
        hourly = defaultdict(int)
        for log in logs:
            try:
                dt = datetime.fromisoformat(log['timestamp'])
                hour = dt.hour
                hourly[hour] += 1
            except:
                continue
        
        return {f"{h:02d}:00": hourly[h] for h in range(24)}
    
    async def _generate_pdf(self, report_type: str, data: Dict, timestamp: str) -> Path:
        """PDF 보고서 생성"""
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
            from reportlab.platypus import Image as RLImage
            
            filename = f"security_report_{timestamp}.pdf"
            filepath = self.reports_dir / filename
            
            doc = SimpleDocTemplate(str(filepath), pagesize=A4)
            story = []
            styles = getSampleStyleSheet()
            
            # 제목
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1a1a1a'),
                spaceAfter=30
            )
            
            story.append(Paragraph("🛡️ Security Analysis Report", title_style))
            story.append(Spacer(1, 0.2*inch))
            
            # 보고서 정보
            info_data = [
                ["Report Type:", report_type.upper()],
                ["Generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                ["Period:", "Custom Range"]
            ]
            
            info_table = Table(info_data, colWidths=[2*inch, 4*inch])
            info_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(info_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Executive Summary
            story.append(Paragraph("Executive Summary", styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))
            
            summary = data['summary']
            summary_text = f"""
            During the analysis period, the system detected <b>{summary['total_alerts']}</b> alerts 
            from Suricata IPS and <b>{summary['total_attacks']}</b> attacks from HexStrike AI. 
            The overall detection rate was <b>{summary['detection_rate']}%</b>, with 
            <b>{summary['false_positives']}</b> false positives and 
            <b>{summary['false_negatives']}</b> false negatives.
            """
            
            story.append(Paragraph(summary_text, styles['BodyText']))
            story.append(Spacer(1, 0.3*inch))
            
            # Statistics Table
            story.append(Paragraph("Key Statistics", styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))
            
            stats_data = [
                ["Metric", "Value"],
                ["Total Alerts", str(summary['total_alerts'])],
                ["Total Attacks", str(summary['total_attacks'])],
                ["Detection Rate", f"{summary['detection_rate']}%"],
                ["False Positives", str(summary['false_positives'])],
                ["False Negatives", str(summary['false_negatives'])]
            ]
            
            stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(stats_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Top Threats
            story.append(Paragraph("Top Threat Sources", styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))
            
            threat_data = [["Rank", "IP Address", "Alert Count"]]
            for i, threat in enumerate(data['top_ips'][:5], 1):
                threat_data.append([str(i), threat['ip'], str(threat['count'])])
            
            threat_table = Table(threat_data, colWidths=[1*inch, 2.5*inch, 1.5*inch])
            threat_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(threat_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Recommendations
            story.append(Paragraph("Recommendations", styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))
            
            recommendations = [
                "1. Review and block top threat IP addresses",
                "2. Update Suricata rules to improve detection rate",
                "3. Investigate false negatives to identify gaps",
                "4. Monitor attack patterns for emerging threats",
                "5. Conduct regular security audits"
            ]
            
            for rec in recommendations:
                story.append(Paragraph(rec, styles['BodyText']))
                story.append(Spacer(1, 0.05*inch))
            
            # Build PDF
            doc.build(story)
            
            return filepath
        
        except ImportError:
            # reportlab이 없으면 간단한 텍스트 파일로
            return await self._generate_text_report(report_type, data, timestamp)
    
    async def _generate_html(self, report_type: str, data: Dict, timestamp: str) -> Path:
        """HTML 보고서 생성"""
        filename = f"security_report_{timestamp}.html"
        filepath = self.reports_dir / filename
        
        summary = data['summary']
        
        html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Report - {timestamp}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #667eea;
            margin-top: 30px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-card h3 {{
            margin: 0;
            font-size: 2em;
        }}
        .stat-card p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #667eea;
            color: white;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        .footer {{
            margin-top: 40px;
            text-align: center;
            color: #999;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🛡️ Security Analysis Report</h1>
        <p><strong>Report Type:</strong> {report_type.upper()}</p>
        <p><strong>Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        
        <h2>Executive Summary</h2>
        <div class="stats">
            <div class="stat-card">
                <h3>{summary['total_alerts']}</h3>
                <p>Total Alerts</p>
            </div>
            <div class="stat-card">
                <h3>{summary['total_attacks']}</h3>
                <p>Total Attacks</p>
            </div>
            <div class="stat-card">
                <h3>{summary['detection_rate']}%</h3>
                <p>Detection Rate</p>
            </div>
            <div class="stat-card">
                <h3>{summary['false_positives']}</h3>
                <p>False Positives</p>
            </div>
        </div>
        
        <h2>Top Threat Sources</h2>
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>IP Address</th>
                    <th>Alert Count</th>
                </tr>
            </thead>
            <tbody>
                {''.join(f'<tr><td>{i}</td><td>{threat["ip"]}</td><td>{threat["count"]}</td></tr>' 
                         for i, threat in enumerate(data['top_ips'][:10], 1))}
            </tbody>
        </table>
        
        <h2>Top Attack Signatures</h2>
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Signature</th>
                    <th>Count</th>
                </tr>
            </thead>
            <tbody>
                {''.join(f'<tr><td>{i}</td><td>{sig["signature"]}</td><td>{sig["count"]}</td></tr>' 
                         for i, sig in enumerate(data['top_signatures'][:10], 1))}
            </tbody>
        </table>
        
        <h2>Recommendations</h2>
        <ol>
            <li>Review and block top threat IP addresses</li>
            <li>Update Suricata rules to improve detection rate</li>
            <li>Investigate false negatives to identify security gaps</li>
            <li>Monitor attack patterns for emerging threats</li>
            <li>Conduct regular security audits and penetration testing</li>
        </ol>
        
        <div class="footer">
            <p>Generated by AI Security Dashboard v1.0.0</p>
            <p>© 2025 Security Automation System</p>
        </div>
    </div>
</body>
</html>
        """
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
    
    async def _generate_json(self, report_type: str, data: Dict, timestamp: str) -> Path:
        """JSON 보고서 생성"""
        filename = f"security_report_{timestamp}.json"
        filepath = self.reports_dir / filename
        
        report_json = {
            "report_type": report_type,
            "generated_at": datetime.now().isoformat(),
            "data": data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_json, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    async def _generate_text_report(self, report_type: str, data: Dict, timestamp: str) -> Path:
        """텍스트 보고서 생성 (fallback)"""
        filename = f"security_report_{timestamp}.txt"
        filepath = self.reports_dir / filename
        
        summary = data['summary']
        
        content = f"""
╔══════════════════════════════════════════════════╗
║       SECURITY ANALYSIS REPORT                  ║
╚══════════════════════════════════════════════════╝

Report Type: {report_type.upper()}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXECUTIVE SUMMARY

Total Alerts:      {summary['total_alerts']}
Total Attacks:     {summary['total_attacks']}
Detection Rate:    {summary['detection_rate']}%
False Positives:   {summary['false_positives']}
False Negatives:   {summary['false_negatives']}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TOP THREAT SOURCES

{''.join(f'{i}. {threat["ip"]:20} - {threat["count"]} alerts\n' 
         for i, threat in enumerate(data['top_ips'][:10], 1))}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RECOMMENDATIONS

1. Review and block top threat IP addresses
2. Update Suricata rules to improve detection rate
3. Investigate false negatives to identify gaps
4. Monitor attack patterns for emerging threats
5. Conduct regular security audits

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generated by AI Security Dashboard v1.0.0
        """
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath