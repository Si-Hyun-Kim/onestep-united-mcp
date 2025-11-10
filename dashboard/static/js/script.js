// Global variables
let charts = {}; // 차트 객체 저장
// (Bootstrap 모달 인스턴스 저장)
let ruleModal, logModal;

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    applyTheme(getTheme());
    setupEventListeners();

    if (document.getElementById('dashboard')) {
        // Bootstrap 모달 초기화
        const ruleModalEl = document.getElementById('ruleDetailModal');
        if(ruleModalEl) ruleModal = new bootstrap.Modal(ruleModalEl);
        
        const logModalEl = document.getElementById('logDetailModal');
        if(logModalEl) logModal = new bootstrap.Modal(logModalEl);

        initializeDashboard();
    }
});

// Setup event listeners
function setupEventListeners() {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    // MFA inputs
    document.querySelectorAll('.mfa-input').forEach((input, index) => {
        input.addEventListener('input', function(e) {
            if (e.target.value) {
                if (index < 5) {
                    document.querySelectorAll('.mfa-input')[index + 1].focus();
                } else {
                    verifyMFA();
                }
            }
        });
        
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Backspace' && !e.target.value && index > 0) {
                document.querySelectorAll('.mfa-input')[index - 1].focus();
            }
        });
    });
    
    // Navigation tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            switchPage(this.dataset.page);
        });
    });
    
    // Chart time range buttons
    document.querySelectorAll('.chart-option').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.chart-option').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            updateChart(this.dataset.range);
        });
    });

    const themeBtn = document.getElementById('themeToggle');
    if (themeBtn) {
        themeBtn.addEventListener('click', toggleTheme);
    }

    const logo = document.querySelector('.logo');
    if (logo) {
        logo.addEventListener('click', () => {
            logo.classList.add('clicked');
            setTimeout(() => logo.classList.remove('clicked'), 600);
        });
    }
}

// --- AJAX (Fetch) Helper ---
async function apiFetch(url, options = {}) {
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        // DELETE는 204 No Content를 반환할 수 있음
        if (response.status === 204) {
            return { success: true };
        }
        return await response.json();
    } catch (error) {
        console.error('API Fetch Error:', error);
        showToast(error.message, 'error');
        return null;
    }
}

// --- 인증 ---
async function handleLogin(e) {
    e.preventDefault();
    // ... (이전과 동일) ...
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const btn = document.getElementById('btnLogin');
    btn.disabled = true;
    btn.textContent = 'Signing In...';

    const data = await apiFetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });

    if (data) {
        if (data.success) {
            if (data.mfa_required) {
                document.getElementById('mfaContainer').style.display = 'block';
                document.querySelectorAll('.mfa-input')[0].focus();
                showToast('Enter verification code', 'success');
                btn.textContent = 'Verify Code';
                btn.disabled = false;
            } else {
                showToast('Login successful!', 'success');
                window.location.href = '/dashboard';
            }
        }
    } else {
        btn.disabled = false;
        btn.textContent = 'Sign In';
    }
}

// MFA verification (AJAX)
async function verifyMFA() {
    const code = Array.from(document.querySelectorAll('.mfa-input'))
        .map(input => input.value)
        .join('');
    
    if (code.length !== 6) return; // 6자리 모두 입력되었을 때만 실행

    const data = await apiFetch('/verify-mfa-ajax', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code })
    });

    if (data && data.success) {
        showToast('Verification successful!', 'success');
        window.location.href = '/dashboard'; // 대시보드로 리디렉션
    } else {
        // 인증 실패 (apiFetch가 오류 처리)
        document.querySelectorAll('.mfa-input').forEach(input => input.value = '');
        document.querySelectorAll('.mfa-input')[0].focus();
    }
}

// Initialize dashboard (데이터 로드 시작)
function initializeDashboard() {
    updateStats();
    initializeCharts();
    loadRecentAlerts(); // 최근 알림 로드
    
    // Auto-update (필요 시)
    // setInterval(updateStats, 10000); // 10초마다 통계 업데이트
}

// Update dashboard stats (API 호출)
async function updateStats() {
    const data = await apiFetch('/api/get-stats');
    if (!data) return;
    
    // Overview 통계
    document.getElementById('totalAlerts').textContent = data.total_alerts_24h?.toLocaleString() || '0';
    document.getElementById('blockedAttacks').textContent = data.blocked_attacks_24h?.toLocaleString() || '0';
    document.getElementById('criticalThreats').textContent = data.critical_alerts_24h?.toLocaleString() || '0';
    document.getElementById('activeRules').textContent = data.active_rules_count?.toLocaleString() || '0';

    // Rules 페이지 통계 (미리 로드)
    const rulesTotal = document.getElementById('rulesTotal');
    if(rulesTotal) rulesTotal.textContent = data.active_rules_count?.toLocaleString() || '0';
    
    const rulesAI = document.getElementById('rulesAI');
    if(rulesAI) rulesAI.textContent = data.ai_rules_count?.toLocaleString() || '0';
    
    const rulesDrop = document.getElementById('rulesDrop');
    if(rulesDrop) rulesDrop.textContent = data.drop_rules_count?.toLocaleString() || '0';
}

// Initialize charts (API 호출)
async function initializeCharts() {
    if (charts.attack) charts.attack.destroy();
    
    const timelineData = await apiFetch('/api/get-timeline?hours=24');
    const ctx1 = document.getElementById('attackChart').getContext('2d');
    
    const labels = timelineData?.timeline?.map(d => d.time) || [];
    const counts = timelineData?.timeline?.map(d => d.count) || [];

    charts.attack = new Chart(ctx1, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Attacks',
                data: counts,
                borderColor: cssVar('--accent-blue'),
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: getChartOptions()
    });
}

// Load recent alerts (API 호출)
async function loadRecentAlerts() {
    const tbody = document.getElementById('recentAlertsTable');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="5"><div class="spinner"></div></td></tr>';
    
    const data = await apiFetch('/api/get-recent-alerts');
    const alerts = data?.logs || [];
    
    if (alerts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5">No recent alerts found.</td></tr>';
        return;
    }
    
    tbody.innerHTML = alerts.map(alert => `
        <tr>
            <td>${new Date(alert.timestamp).toLocaleTimeString()}</td>
            <td>${alert.src_ip || 'N/A'}</td>
            <td>${alert.signature || 'N/A'}</td>
            <td><span class="severity-badge severity-${alert.severity}">${alert.severity?.toUpperCase()}</span></td>
            <td>
                <button class="action-btn" onclick="showLogDetail(event, ${JSON.stringify(alert)})"><i class="bi bi-eye"></i> View</button>
                <button class="action-btn" onclick="blockIP(event, '${alert.src_ip}')"><i class="bi bi-shield-x"></i> Block</button>
            </td>
        </tr>
    `).join('');
}

// Load FULL alerts (API 호출)
async function loadAlerts() {
    const tbody = document.getElementById('alertsTable');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="6"><div class="spinner"></div></td></tr>';

    const severity = document.getElementById('severityFilter').value;
    const count = document.getElementById('countFilter').value;

    const data = await apiFetch(`/api/get-alerts?severity=${severity}&count=${count}`);
    const alerts = data?.logs || [];

    if (alerts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6">No alerts found matching criteria.</td></tr>';
        return;
    }

    tbody.innerHTML = alerts.map(alert => `
        <tr>
            <td>${new Date(alert.timestamp).toLocaleString()}</td>
            <td>${alert.src_ip || 'N/A'}</td>
            <td>${alert.dest_ip || 'N/A'}</td>
            <td>${alert.signature || 'N/A'}</td>
            <td><span class="severity-badge severity-${alert.severity}">${alert.severity?.toUpperCase()}</span></td>
            <td>
                <button class="action-btn" onclick="showLogDetail(event, ${JSON.stringify(alert)})"><i class="bi bi-eye"></i> View</button>
                <button class="action-btn" onclick="blockIP(event, '${alert.src_ip}')"><i class="bi bi-shield-x"></i> Block</button>
            </td>
        </tr>
    `).join('');
}

// Load IPS rules (API 호출)
async function loadRules() {
    const tbody = document.getElementById('rulesTable');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="6"><div class="spinner"></div></td></tr>';

    const category = document.getElementById('ruleCategoryFilter').value;
    const data = await apiFetch(`/api/get-rules?category=${category}`);
    const rules = data?.rules || [];
    
    // (룰 통계도 여기서 업데이트 가능)
    updateStats();

    if (rules.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6">No rules found matching criteria.</td></tr>';
        return;
    }

    tbody.innerHTML = rules.map(rule => {
        const isAuto = rule.file && rule.file.includes('auto_generated');
        return `
        <tr>
            <td><code>${rule.sid}</code></td>
            <td>
                <span class="severity-badge severity-${rule.action === 'drop' ? 'critical' : 'high'}">
                    ${rule.action?.toUpperCase()}
                </span>
            </td>
            <td>${rule.message || rule.msg}</td>
            <td>${rule.category || 'N/A'}</td>
            <td>
                ${rule.file ? `<small>${rule.file}</small>` : ''}
                ${isAuto ? '<span class="severity-badge severity-low" style="margin-left: 5px;">AI</span>' : ''}
            </td>
            <td>
                <button class="action-btn" onclick='showRuleDetail(event, ${JSON.stringify(rule)})'>
                    <i class="bi bi-eye"></i>
                </button>
                ${isAuto ? `
                <button class="action-btn" onclick="deleteRule(event, ${rule.sid})">
                    <i class="bi bi-trash"></i>
                </button>` : ''}
            </td>
        </tr>
    `}).join('');
}

// Load reports (API 호출)
async function loadReports() {
    const tbody = document.getElementById('reportsTable');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="4"><div class="spinner"></div></td></tr>';
    
    const data = await apiFetch('/api/get-reports');
    const reports = data?.reports || [];
    
    if (reports.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 2rem;">No reports generated.</td></tr>';
        return;
    }
    
    tbody.innerHTML = reports.map(report => `
        <tr>
            <td><i class="bi bi-file-earmark-pdf" style="color:var(--accent-red);"></i> ${report.filename}</td>
            <td>${report.size ? (report.size / 1024).toFixed(1) + ' KB' : 'N/A'}</td>
            <td>${new Date(report.created || report.created_at).toLocaleString()}</td>
            <td>
                <a href="/api/reports/download/${report.filename}" class="action-btn" download>
                    <i class="bi bi-download"></i> Download
                </a>
                <button class="action-btn" onclick="deleteReport(event, '${report.filename}')">
                    <i class="bi bi-trash"></i> Delete
                </button>
            </td>
        </tr>
    `).join('');
}

// Load comparison timeline (API 호출)
async function loadComparison() {
    const container = document.getElementById('comparison-content');
    if (!container) return;
    container.innerHTML = '<div class="spinner"></div>';
    
    const data = await apiFetch('/api/get-comparison');
    if (!data) return;

    if (data.disabled) {
        container.innerHTML = `
            <div class="comparison-container">
                <div class="comparison-side" style="text-align: center;">
                    <i class="bi bi-exclamation-triangle" style="font-size: 3rem; color: var(--accent-yellow);"></i>
                    <h2 class="comparison-title">${data.message || 'Comparison is disabled.'}</h2>
                </div>
            </div>`;
        return;
    }
    
    // (데이터 구조는 app.py의 '/api/get-comparison' 응답을 따름)
    const defenseEvents = data.defense_events || [];
    const attackEvents = data.attack_events || [];
    const analysis = data.analysis || { attempted: [], blocked: [] };

    defenseTimeline.innerHTML = defenseEvents.length ? defenseEvents.map(event => `
        <div class="timeline-event">
            <div class="timeline-time">${new Date(event.time).toLocaleTimeString()}</div>
            <div class="timeline-content">${event.event}</div>
        </div>
    `).join('') : '<p>No defense events.</p>';
    
    attackTimeline.innerHTML = attackEvents.length ? attackEvents.map(event => `
        <div class="timeline-event" style="border-left-color: var(--accent-red);">
            <div class="timeline-time">${new Date(event.time).toLocaleTimeString()}</div>
            <div class="timeline-content">${event.event}</div>
        </div>
    `).join('') : '<p>No attack events.</p>';

    // Comparison Chart
    if (charts.comparison) charts.comparison.destroy();
    charts.comparison = new Chart(ctx2.getContext('2d'), {
        type: 'bar',
        data: {
            labels: analysis.labels || ['SQLi', 'XSS', 'DDoS'],
            datasets: [{
                label: 'Attempted',
                data: analysis.attempted || [0, 0, 0],
                backgroundColor: cssVar('--accent-red')
            }, {
                label: 'Blocked',
                data: analysis.blocked || [0, 0, 0],
                backgroundColor: cssVar('--accent-green')
            }]
        },
        options: getChartOptions()
    });
}

function loadGenerateReportPage() {
    // 페이지 로드 시 날짜/시간 기본값 설정
    try {
        const now = new Date();
        const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        
        // YYYY-MM-DDTHH:MM
        document.getElementById('reportEnd').value = formatDateTimeLocal(now);
        document.getElementById('reportStart').value = formatDateTimeLocal(yesterday);
    } catch(e) {
        console.warn("Failed to set default report times.", e);
    }
}

// --- Helper functions ---

// 페이지 전환
function switchPage(page) {
    const activePage = document.querySelector('.page.active');
    if (activePage && activePage.id === `page-${page}`) return;

    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.page === page);
    });
    
    document.querySelectorAll('.page').forEach(p => {
        p.classList.toggle('active', p.id === `page-${page}`);
    });
    
    // 페이지별 1회성 로드
    if (page === 'alerts' && !document.getElementById('alertsTable').hasChildNodes()) {
        loadAlerts();
    } else if (page === 'rules' && !document.getElementById('rulesTable').hasChildNodes()) {
        loadRules();
    } else if (page === 'reports' && !document.getElementById('reportsTable').hasChildNodes()) {
        loadReports();
    } else if (page === 'comparison' && !document.getElementById('comparison-content').hasChildNodes()) {
        loadComparison();
    } else if (page === 'generate_report') {
        loadGenerateReportPage(); // 날짜/시간 설정을 위해 매번 호출
    }
}

// 차트 업데이트 (시간 범위 변경)
async function updateChart(range) {
    let hours = 24;
    switch(range) {
        case '24h': hours = 24; break;
        case '7d': hours = 168; break;
        case '30d': hours = 720; break;
    }
    
    const timelineData = await apiFetch(`/api/get-timeline?hours=${hours}`);
    if (charts.attack && timelineData?.timeline) {
        charts.attack.data.labels = timelineData.timeline.map(d => d.time);
        charts.attack.data.datasets[0].data = timelineData.timeline.map(d => d.count);
        charts.attack.update();
    }
}

// IP 차단 (API 호출)
async function blockIP(event, ip) {
    event.stopPropagation(); // (이벤트 버블링 방지)
    if (!ip || ip === 'N/A') {
        showToast('Invalid IP address', 'error');
        return;
    }
    if (confirm(`Are you sure you want to block IP: ${ip}?`)) {
        const data = await apiFetch('/api/block-ip', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ip: ip, reason: 'Manual block from dashboard' })
        });
        
        if (data && data.success) {
            showToast(`IP ${ip} blocked successfully`, 'success');
            // 테이블 새로고침
            if (document.getElementById('page-alerts').classList.contains('active')) loadAlerts();
            if (document.getElementById('page-overview').classList.contains('active')) loadRecentAlerts();
        }
    }
}

// 룰 삭제
async function deleteRule(event, sid) {
    event.stopPropagation();
    if (confirm(`Are you sure you want to delete AI rule SID ${sid}?`)) {
        const data = await apiFetch(`/api/rules/${sid}`, { method: 'DELETE' });
        if (data && data.success) {
            showToast(`Rule ${sid} deleted successfully`, 'success');
            loadRules(); // 룰 목록 새로고침
        }
    }
}

// 룰 토글 (API 호출)
async function toggleRule(ruleId) {
    const data = await apiFetch('/api/toggle-rule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rule_id: ruleId })
    });

    if (data && data.success) {
        showToast(`Rule ${ruleId} toggled (simulated)`, 'success');
        loadRules(); // 룰 목록 새로고침
    }
}

// 보고서 생성 (API 호출)
async function generateReport() {
    // ... (이전과 동일) ...
    const type = document.getElementById('reportType').value;
    const startDate = document.getElementById('reportStart').value;
    const endDate = document.getElementById('reportEnd').value;
    const format = document.getElementById('reportFormat').value;
    
    if (!startDate || !endDate) {
        showToast('Please select date range', 'error');
        return;
    }
    
    showToast('Generating report...', 'success');
    
    const data = await apiFetch('/api/generate-report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            report_type: type,
            start_time: startDate,
            end_time: endDate,
            format: format
        })
    });
    
    if (data && data.success) {
        showToast('Report generated successfully', 'success');
        switchPage('reports'); // 리포트 목록 페이지로 이동
        loadReports(); // 리포트 목록 새로고침
    }
}

// 보고서 삭제
async function deleteReport(event, filename) {
    event.stopPropagation();
    if (confirm(`Are you sure you want to delete report: ${filename}?`)) {
        const data = await apiFetch(`/api/reports/delete/${filename}`, { method: 'DELETE' });
        if (data && data.success) {
            showToast(`Report ${filename} deleted`, 'success');
            loadReports(); // 보고서 목록 새로고침
        }
    }
}

function downloadReport(filename) {
    // TODO: Flask에 /api/reports/download/<filename> 같은 엔드포인트 필요
    showToast(`Downloading ${filename}... (Not Implemented)`, 'success');
    // window.open(`/api/reports/download/${filename}`);
}

function addNewRule() {
    showToast('Rule editor (Not Implemented)', 'success');
}

// --- 유틸리티 ---
function formatDateTimeLocal(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
}

// Toast 알림
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');
    
    toast.className = `toast show toast-${type}`;
    toastMessage.textContent = message;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// (로그아웃은 단순 링크로 변경됨)

// === 테마 유틸 ===
function getTheme() {
  const saved = localStorage.getItem('theme');
  if (saved === 'light' || saved === 'dark') return saved;
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  return prefersDark ? 'dark' : 'light';
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  const toggleBtn = document.getElementById('themeToggle');
  if (toggleBtn) toggleBtn.textContent = theme === 'dark' ? '🌙' : '☀️';
  refreshChartTheme();
}

function toggleTheme() {
  const next = (getTheme() === 'dark') ? 'light' : 'dark';
  localStorage.setItem('theme', next);
  applyTheme(next);
}

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// 차트 옵션 (테마 적용)
function getChartOptions() {
    const text = cssVar('--text-secondary') || '#94a3b8';
  const grid = cssVar('--border') || '#2a3142';
  
  return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
          legend: { labels: { color: text } }
      },
      scales: {
          x: { grid: { color: grid }, ticks: { color: text } },
          y: { grid: { color: grid }, ticks: { color: text } }
      }
  };
}

// 차트 테마 갱신
function refreshChartTheme() {
  const options = getChartOptions();
  for (const chartName in charts) {
      if(charts[chartName]) {
          charts[chartName].options.plugins.legend.labels.color = options.plugins.legend.labels.color;
          charts[chartName].options.scales.x.ticks.color = options.scales.x.ticks.color;
          charts[chartName].options.scales.y.ticks.color = options.scales.y.ticks.color;
          charts[chartName].options.scales.x.grid.color = options.scales.x.grid.color;
          charts[chartName].options.scales.y.grid.color = options.scales.y.grid.color;
          charts[chartName].update('none');
      }
  }
}