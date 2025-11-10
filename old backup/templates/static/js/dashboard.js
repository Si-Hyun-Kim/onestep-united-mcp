// dashboard/static/js/dashboard.js
// 대시보드 JavaScript

// 전역 변수
let realtimeUpdateInterval = null;
let charts = {};

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    startRealtimeUpdates();
});

// 대시보드 초기화
function initializeDashboard() {
    console.log('Dashboard initialized');
    
    // 툴팁 초기화
    initializeTooltips();
    
    // 이벤트 리스너
    attachEventListeners();
}

// 툴팁 초기화
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// 이벤트 리스너 연결
function attachEventListeners() {
    // 새로고침 버튼
    const refreshButtons = document.querySelectorAll('.btn-refresh');
    refreshButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            refreshData();
        });
    });
    
    // 필터 변경
    const filterSelects = document.querySelectorAll('.filter-select');
    filterSelects.forEach(select => {
        select.addEventListener('change', function() {
            applyFilters();
        });
    });
}

// 실시간 업데이트 시작
function startRealtimeUpdates() {
    // 5초마다 업데이트
    realtimeUpdateInterval = setInterval(() => {
        updateRealtimeStats();
    }, 5000);
}

// 실시간 통계 업데이트
async function updateRealtimeStats() {
    try {
        const response = await fetch('/api/realtime/stats');
        const data = await response.json();
        
        if (data.success !== false) {
            updateStatCards(data);
        }
    } catch (error) {
        console.error('Failed to update realtime stats:', error);
    }
}

// 통계 카드 업데이트
function updateStatCards(data) {
    // 총 알림
    const alertsEl = document.querySelector('[data-stat="total-alerts"]');
    if (alertsEl && data.total_alerts_24h !== undefined) {
        animateValue(alertsEl, parseInt(alertsEl.textContent), data.total_alerts_24h, 500);
    }
    
    // 총 공격
    const attacksEl = document.querySelector('[data-stat="total-attacks"]');
    if (attacksEl && data.total_attacks_24h !== undefined) {
        animateValue(attacksEl, parseInt(attacksEl.textContent), data.total_attacks_24h, 500);
    }
    
    // 탐지율
    const detectionEl = document.querySelector('[data-stat="detection-rate"]');
    if (detectionEl && data.detection_rate !== undefined) {
        detectionEl.textContent = data.detection_rate + '%';
    }
}

// 숫자 애니메이션
function animateValue(element, start, end, duration) {
    const range = end - start;
    const increment = range / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
            current = end;
            clearInterval(timer);
        }
        element.textContent = Math.round(current);
    }, 16);
}

// 데이터 새로고침
function refreshData() {
    showSpinner();
    
    setTimeout(() => {
        location.reload();
    }, 500);
}

// 상위 위협 새로고침
async function refreshTopThreats() {
    showSpinner();
    
    try {
        const response = await fetch('/api/stats/top-threats?limit=10');
        const data = await response.json();
        
        if (data.threats) {
            updateTopThreatsTable(data.threats);
        }
    } catch (error) {
        console.error('Failed to refresh top threats:', error);
        showAlert('Failed to refresh data', 'error');
    } finally {
        hideSpinner();
    }
}

// 상위 위협 테이블 업데이트
function updateTopThreatsTable(threats) {
    const tbody = document.getElementById('topThreatsTable');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    threats.forEach((threat, index) => {
        const row = `
            <tr>
                <td>${index + 1}</td>
                <td><code>${threat.ip}</code></td>
                <td>${threat.count}</td>
                <td><span class="badge bg-danger">${threat.severity_score}</span></td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="blockIP('${threat.ip}')">
                        <i class="bi bi-shield-x"></i> 차단
                    </button>
                </td>
            </tr>
        `;
        tbody.innerHTML += row;
    });
}

// IP 차단
async function blockIP(ip) {
    if (!confirm(`${ip}를 차단하시겠습니까?`)) {
        return;
    }
    
    showSpinner();
    
    try {
        const response = await fetch('/api/block-ip', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ip: ip,
                reason: 'Manual block from dashboard'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert(`IP ${ip} 차단 성공`, 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showAlert(`차단 실패: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Block IP error:', error);
        showAlert('차단 요청 실패', 'error');
    } finally {
        hideSpinner();
    }
}

// IP 차단 해제
async function unblockIP(ip) {
    if (!confirm(`${ip} 차단을 해제하시겠습니까?`)) {
        return;
    }
    
    showSpinner();
    
    try {
        const response = await fetch('/api/unblock-ip', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ip: ip})
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert(`IP ${ip} 차단 해제 성공`, 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showAlert(`차단 해제 실패: ${data.error}`, 'error');
        }
    } catch (error) {
        console.error('Unblock IP error:', error);
        showAlert('차단 해제 요청 실패', 'error');
    } finally {
        hideSpinner();
    }
}

// 스피너 표시
function showSpinner() {
    const spinner = `
        <div class="spinner-overlay">
            <div class="spinner-border text-light" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `;
    
    if (!document.querySelector('.spinner-overlay')) {
        document.body.insertAdjacentHTML('beforeend', spinner);
    }
}

// 스피너 숨김
function hideSpinner() {
    const spinner = document.querySelector('.spinner-overlay');
    if (spinner) {
        spinner.remove();
    }
}

// 알림 표시
function showAlert(message, type = 'info') {
    const alertClass = type === 'error' ? 'danger' : type;
    const alert = `
        <div class="alert alert-${alertClass} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3" 
             style="z-index: 10000; min-width: 300px;" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', alert);
    
    // 3초 후 자동 제거
    setTimeout(() => {
        const alertEl = document.querySelector('.alert');
        if (alertEl) {
            alertEl.remove();
        }
    }, 3000);
}

// 필터 적용
function applyFilters() {
    const form = document.getElementById('filterForm');
    if (form) {
        form.submit();
    }
}

// 로그 상세 모달
function showLogDetail(logData) {
    const modal = new bootstrap.Modal(document.getElementById('logDetailModal'));
    const content = document.getElementById('logDetailContent');
    
    if (content) {
        content.innerHTML = `<pre>${JSON.stringify(logData, null, 2)}</pre>`;
    }
    
    modal.show();
}

// 시간 포맷팅
function formatTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('ko-KR', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// 바이트 포맷팅
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 페이지 언로드 시 정리
window.addEventListener('beforeunload', function() {
    if (realtimeUpdateInterval) {
        clearInterval(realtimeUpdateInterval);
    }
});