// Global variables
let charts = {
    attack: null,
    severityPie: null // 원형 차트 객체 추가
};
// Bootstrap 모달 인스턴스 저장
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
            updateChart(this.dataset.range); // 라인 차트만 업데이트
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
            // 로고 클릭 시 Overview로 이동
            switchPage('overview');
        });
    }

    // 신규: 모바일 네비게이션 버튼
    const btnMobileNav = document.getElementById('btnMobileNav');
    if (btnMobileNav) {
        btnMobileNav.addEventListener('click', () => {
            document.getElementById('main-nav').classList.toggle('active');
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
        showToast(error.message || 'Network error', 'error');
        return null;
    }
}

// --- 인증 ---
async function handleLogin(e) {
    e.preventDefault();
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
                window.location.href = '/dashboard'; // 대시보드로 리디렉션
            }
        }
    } else {
        // apiFetch가 null을 반환 (오류 토스트는 apiFetch가 이미 띄움)
        btn.disabled = false;
        btn.textContent = 'Sign In';
    }
}

async function verifyMFA() {
    const code = Array.from(document.querySelectorAll('.mfa-input'))
        .map(input => input.value)
        .join('');
    
    if (code.length !== 6) return;

    const data = await apiFetch('/verify-mfa-ajax', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code })
    });

    if (data && data.success) {
        showToast('Verification successful!', 'success');
        window.location.href = '/dashboard';
    } else {
        // apiFetch가 오류 토스트 띄움
        document.querySelectorAll('.mfa-input').forEach(input => input.value = '');
        document.querySelectorAll('.mfa-input')[0].focus();
    }
}

// --- 대시보드 초기화 ---
function initializeDashboard() {
    // 3가지 핵심 데이터 로드
    updateStats(); // 통계 + 원형 차트 로드
    updateChart('24h'); // 라인 차트 로드
    loadRecentAlerts();
    
    // 페이지에 data-loaded 속성 추가 (버그 수정용)
    document.querySelectorAll('.page').forEach(page => {
        page.dataset.loaded = "false";
    });
    // Overview 페이지는 지금 로드했으므로 true
    document.getElementById('page-overview').dataset.loaded = "true";
}

// --- 데이터 로딩 함수 (페이지별) ---

async function updateStats() {
    const data = await apiFetch('/api/get-stats');
    if (!data) {
        // API 실패 시
        document.getElementById('totalAlerts').textContent = 'Error';
        document.getElementById('blockedAttacks').textContent = 'Error';
        document.getElementById('criticalThreats').textContent = 'Error';
        document.getElementById('activeRules').textContent = 'Error';
        return;
    }
    
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

    // 신규: 원형 차트 그리기
    const severityData = data.severity_distribution || {};
    const pieCtx = document.getElementById('severityPieChart');
    if (pieCtx) {
        if (charts.severityPie) charts.severityPie.destroy();
        charts.severityPie = new Chart(pieCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['Critical', 'High', 'Medium', 'Low'],
                datasets: [{
                    data: [
                        severityData.critical || 0,
                        severityData.high || 0,
                        severityData.medium || 0,
                        severityData.low || 0
                    ],
                    backgroundColor: [
                        cssVar('--accent-red'),
                        cssVar('--accent-yellow'),
                        cssVar('--accent-blue'),
                        cssVar('--text-secondary')
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { 
                            color: cssVar('--text-secondary'),
                            padding: 10
                        }
                    }
                }
            }
        });
    }
}

// 라인 차트 업데이트 (데이터 분리)
async function updateChart(range) {
    let hours = 24;
    switch(range) {
        case '24h': hours = 24; break;
        case '7d': hours = 168; break;
        case '30d': hours = 720; break;
    }
    
    const timelineData = await apiFetch(`/api/get-timeline?hours=${hours}`);
    if (!timelineData) return; // API 실패 시 중단

    const labels = timelineData?.timeline?.map(d => d.time) || [];
    const counts = timelineData?.timeline?.map(d => d.count) || [];
    
    const ctx1 = document.getElementById('attackChart');
    if (!ctx1) return;

    if (charts.attack) {
        // 데이터만 업데이트
        charts.attack.data.labels = labels;
        charts.attack.data.datasets[0].data = counts;
        charts.attack.update();
    } else {
        // 최초 생성
        charts.attack = new Chart(ctx1.getContext('2d'), {
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
            options: getChartOptions() // (getChartOptions는 맨 아래 유틸리티에 있음)
        });
    }
}


async function loadRecentAlerts() {
    const tbody = document.getElementById('recentAlertsTable');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="5"><div class="spinner"></div></td></tr>';
    
    const data = await apiFetch('/api/get-recent-alerts');
    const alerts = data?.logs || [];
    
    if (alerts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding: 1rem;">No recent alerts found.</td></tr>';
    } else {
        tbody.innerHTML = alerts.map(alert => `
            <tr>
                <td>${new Date(alert.timestamp).toLocaleTimeString()}</td>
                <td>${alert.src_ip || 'N/A'}</td>
                <td>${alert.signature || 'N/A'}</td>
                <td><span class="severity-badge severity-${alert.severity}">${alert.severity?.toUpperCase()}</span></td>
                <td>
                    <button class="action-btn" onclick="showLogDetail(event, ${JSON.stringify(alert)})" title="View Detail"><i class="bi bi-eye"></i></button>
                    <button class="action-btn" onclick="blockIP(event, '${alert.src_ip}')" title="Block IP"><i class="bi bi-shield-x"></i></button>
                </td>
            </tr>
        `).join('');
    }
}

async function loadAlerts() {
    const tbody = document.getElementById('alertsTableBody'); // ID 수정됨
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="6"><div class="spinner"></div></td></tr>';

    const severity = document.getElementById('severityFilter').value;
    const count = document.getElementById('countFilter').value;

    const data = await apiFetch(`/api/get-alerts?severity=${severity}&count=${count}`);
    const alerts = data?.logs || [];

    if (alerts.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 2rem;">No alerts found matching criteria.</td></tr>';
    } else {
        tbody.innerHTML = alerts.map(alert => `
            <tr>
                <td>${new Date(alert.timestamp).toLocaleString()}</td>
                <td>${alert.src_ip || 'N/A'}</td>
                <td>${alert.dest_ip || 'N/A'}</td>
                <td>${alert.signature || 'N/A'}</td>
                <td><span class="severity-badge severity-${alert.severity}">${alert.severity?.toUpperCase()}</span></td>
                <td>
                    <button class="action-btn" onclick="showLogDetail(event, ${JSON.stringify(alert)})" title="View Detail"><i class="bi bi-eye"></i></button>
                    <button class="action-btn" onclick="blockIP(event, '${alert.src_ip}')" title="Block IP"><i class="bi bi-shield-x"></i></button>
                </td>
            </tr>
        `).join('');
    }
}

async function loadRules() {
    const tbody = document.getElementById('rulesTableBody'); // ID 수정됨
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="6"><div class="spinner"></div></td></tr>';

    const category = document.getElementById('ruleCategoryFilter').value;
    const data = await apiFetch(`/api/get-rules?category=${category}`);
    const rules = data?.rules || [];
    
    // 룰 통계도 업데이트
    updateStats();

    if (rules.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 2rem;">No rules found matching criteria.</td></tr>';
    } else {
        tbody.innerHTML = rules.map(rule => {
            const isAuto = rule.file && rule.file.includes('auto_generated');
            return `
            <tr>
                <td><code>${rule.sid}</code></td>
                <td>
                    <span class="severity-badge severity-${rule.action === 'drop' ? 'critical' : 'high'}">
                        ${rule.action?.toUpperCase() || 'ALERT'}
                    </span>
                </td>
                <td>${rule.message || rule.msg}</td>
                <td>${rule.category || 'N/A'}</td>
                <td>
                    ${rule.file ? `<small>${rule.file}</small>` : ''}
                    ${isAuto ? '<span class="severity-badge severity-low" style="margin-left: 5px;">AI</span>' : ''}
                </td>
                <td>
                    <button class="action-btn" onclick='showRuleDetail(event, ${JSON.stringify(rule)})' title="View Rule Detail">
                        <i class="bi bi-eye"></i>
                    </button>
                    ${isAuto ? `
                    <button class="action-btn" onclick="deleteRule(event, ${rule.sid})" title="Delete AI Rule">
                        <i class="bi bi-trash"></i>
                    </button>` : ''}
                </td>
            </tr>
        `}).join('');
    }
}

async function searchRules() {
    const query = document.getElementById('ruleSearchInput').value;
    
    if (!query.trim()) {
        loadRules(); // 검색어 없으면 전체 로드
        return;
    }
    
    const tbody = document.getElementById('rulesTableBody');
    tbody.innerHTML = '<tr><td colspan="6"><div class="spinner"></div></td></tr>';
    
    const data = await apiFetch(`/api/rules/search?query=${encodeURIComponent(query)}`);
    const rules = data?.results || [];
    
    if (rules.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 2rem;">검색 결과 없음</td></tr>';
    } else {
        tbody.innerHTML = rules.map(rule => `
            <tr>
                <td><code>${rule.sid}</code></td>
                <td><span class="severity-badge severity-${rule.action === 'drop' ? 'critical' : 'high'}">${rule.action?.toUpperCase()}</span></td>
                <td>${rule.message}</td>
                <td>${rule.category}</td>
                <td><small>${rule.file}</small></td>
                <td>
                    <button class="action-btn" onclick='showRuleDetail(event, ${JSON.stringify(rule)})'>
                        <i class="bi bi-eye"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    }
}

async function loadReports() {
    const tbody = document.getElementById('reportsTableBody'); // ID 수정됨
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="4"><div class="spinner"></div></td></tr>';
    
    const data = await apiFetch('/api/get-reports');
    const reports = data?.reports || [];
    
    if (reports.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 2rem;">No reports generated.</td></tr>';
    } else {
        tbody.innerHTML = reports.map(report => `
            <tr>
                <td><i class="bi bi-file-earmark-pdf" style="color:var(--accent-red); margin-right: 5px;"></i> ${report.filename}</td>
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
}

async function loadComparison() {
    const container = document.getElementById('comparisonContainer'); // ID 수정됨
    if (!container) return;
    container.innerHTML = '<div class="spinner"></div>';
    
    const data = await apiFetch('/api/get-comparison');
    if (!data) return;

    if (data.disabled) {
        container.innerHTML = `
            <div class="comparison-container" style="padding: 2rem; text-align: center; display: block;">
                <i class="bi bi-exclamation-triangle" style="font-size: 3rem; color: var(--accent-yellow);"></i>
                <h2 class="comparison-title" style="justify-content: center; margin-top: 1rem;">${data.message || 'Comparison is disabled.'}</h2>
            </div>`;
    } else {
        // (정상 로드 로직)
        container.innerHTML = `
        <div class="comparison-container">
            <div class="comparison-side">
                <h2 class="comparison-title">
                    <span class="side-indicator side-defense"></span>
                    Defense (Suricata IPS)
                </h2>
                <div class="timeline" id="defenseTimeline">
                    ${data.defense_events.map(event => `
                        <div class="timeline-event">
                            <div class="timeline-time">${new Date(event.time).toLocaleTimeString()}</div>
                            <div class="timeline-content">${event.event}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
            <div class="comparison-side">
                <h2 class="comparison-title">
                    <span class="side-indicator side-attack"></span>
                    Attack (HexStrike AI)
                </h2>
                <div class="timeline" id="attackTimeline">
                    ${data.attack_events.map(event => `
                        <div class="timeline-event" style="border-left-color: var(--accent-red);">
                            <div class="timeline-time">${new Date(event.time).toLocaleTimeString()}</div>
                            <div class="timeline-content">${event.event}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
        <div class="chart-container">
            <div class="chart-header">
                <h2 class="chart-title">Attack Success Rate Analysis</h2>
            </div>
            <canvas id="comparisonChart"></canvas>
        </div>
        `;
        // (차트 그리기)
        const ctx2 = document.getElementById('comparisonChart');
        if (ctx2) {
            if(charts.comparison) charts.comparison.destroy();
            charts.comparison = new Chart(ctx2.getContext('2d'), {
                 type: 'bar',
                 data: {
                     labels: data.analysis.labels || [],
                     datasets: [{
                         label: 'Attempted',
                         data: data.analysis.attempted || [],
                         backgroundColor: cssVar('--accent-red')
                     }, {
                         label: 'Blocked',
                         data: data.analysis.blocked || [],
                         backgroundColor: cssVar('--accent-green')
                     }]
                 },
                 options: getChartOptions()
             });
        }
    }
}

function loadGenerateReportPage() {
    // 페이지 로드 시 날짜/시간 기본값 설정
    try {
        const now = new Date();
        const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        
        document.getElementById('reportEnd').value = formatDateTimeLocal(now);
        document.getElementById('reportStart').value = formatDateTimeLocal(yesterday);
    } catch(e) {
        console.warn("Failed to set default report times.", e);
    }
}


// --- 상호작용 함수 ---

function switchPage(page) {
    const activePage = document.querySelector('.page.active');
    if (activePage && activePage.id === `page-${page}`) return;

    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.page === page);
    });
    
    document.querySelectorAll('.page').forEach(p => {
        p.classList.toggle('active', p.id === `page-${page}`);
    });
    
    // 모바일 탭 클릭 시 메뉴 닫기
    document.getElementById('main-nav').classList.remove('active');

    // *** 버그 수정: data-loaded 속성으로 1회성 로드 검사 ***
    const pageElement = document.getElementById(`page-${page}`);
    if (pageElement.dataset.loaded === "false") {
        if (page === 'alerts') {
            loadAlerts();
        } else if (page === 'rules') {
            loadRules();
        } else if (page === 'reports') {
            loadReports();
        } else if (page === 'comparison') {
            loadComparison();
        } else if (page === 'generate_report') {
            loadGenerateReportPage();
        }
        
        // (주의) generate_report는 매번 날짜가 초기화되어야 하므로 플래그를 설정하지 않음
        if (page !== 'generate_report') {
            pageElement.dataset.loaded = "true";
        }
    }
}

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
            if (document.getElementById('page-alerts').classList.contains('active')) {
                loadAlerts();
            } else {
                // 다른 페이지에 있더라도 alerts 페이지의 로드 플래그를 리셋
                document.getElementById('page-alerts').dataset.loaded = "false";
            }
            // 최근 알림은 항상 새로고침
            loadRecentAlerts();
        }
    }
}

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

async function generateReport() {
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
        document.getElementById('page-reports').dataset.loaded = "false"; // 보고서 목록 새로고침 강제
        loadReports();
    }
}

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

// --- 모달 표시 ---
function showLogDetail(event, logData) {
    event.stopPropagation();
    const content = document.getElementById('logDetailContent');
    if(content) {
        content.innerHTML = `<pre>${JSON.stringify(logData, null, 2)}</pre>`;
    }
    if(logModal) logModal.show();
}

function showRuleDetail(event, ruleData) {
    event.stopPropagation();
    const content = document.getElementById('ruleDetailContent');
    if(content) {
        content.innerHTML = `<pre>${ruleData.rule || JSON.stringify(ruleData, null, 2)}</pre>`;
    }
    if(ruleModal) ruleModal.show();
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

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');
    
    toast.className = `toast show toast-${type}`;
    toastMessage.textContent = message;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

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

function getChartOptions() {
    const text = cssVar('--text-secondary') || '#94a3b8';
    const grid = cssVar('--border') || '#2a3142';
    
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { 
                display: false, // 라인 차트 범례 숨김
                labels: { color: text } 
            }
        },
        scales: {
            x: { 
                grid: { color: grid }, 
                ticks: { color: text } 
            },
            y: { 
                grid: { color: grid }, 
                ticks: { color: text } 
            }
        }
    };
}

function refreshChartTheme() {
    const options = getChartOptions();
    
    for (const chartName in charts) {
        if(charts[chartName]) {
            const chart = charts[chartName];
            // 차트 타입에 따라 옵션 적용
            if (chart.config.type === 'doughnut') {
                chart.options.plugins.legend.labels.color = cssVar('--text-secondary');
            } else if (chart.config.type === 'line' || chart.config.type === 'bar') {
                chart.options.plugins.legend.labels.color = options.plugins.legend.labels.color;
                chart.options.scales.x.ticks.color = options.scales.x.ticks.color;
                chart.options.scales.y.ticks.color = options.scales.y.ticks.color;
                chart.options.scales.x.grid.color = options.scales.x.grid.color;
                chart.options.scales.y.grid.color = options.scales.y.grid.color;
            }
            chart.update('none');
        }
    }
}