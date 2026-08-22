/* ============================================================
   RecoverAI Operator Dashboard — app.js
   Pure Vanilla JS — No external libraries
   ============================================================ */

'use strict';

/* ─── Config ─── */
const API_BASE = 'http://localhost:8000/api';
const STATS_REFRESH_MS  = 30_000;
const EVENTS_REFRESH_MS = 10_000;

/* ─── State ─── */
let isDemoMode      = false;
let currentTxnId    = '';
let lastResult      = null;
let auditLog        = [];          // all processed events
let recentEvents    = [];          // for the right-panel table
let statsInterval   = null;
let eventsInterval  = null;
let liveWs          = null;

/* ─── Action Labels (match backend TREATMENT_ACTIONS) ─── */
const ACTION_LABELS = {
  smart_retry:        '🔄 Smart Retry',
  smart_delay:        '⏳ Smart Delay',
  send_notification:  '🔔 Send Notification',
  silent_wait:        '🤫 Silent Wait',
  human_review:       '🧑 Human Review',
};

const ACTION_COLORS = {
  smart_retry:        '#818cf8',
  smart_delay:        '#93c5fd',
  send_notification:  '#fcd34d',
  silent_wait:        '#6ee7b7',
  human_review:       '#fca5a5',
};

const ERROR_SHORT = {
  insufficient_funds:   'Insuff. Funds',
  INSUFFICIENT_FUNDS:   'Insuff. Funds',
  bank_server_down:     'Bank Down',
  BANK_SERVER_DOWN:     'Bank Down',
  network_timeout:      'Timeout',
  NETWORK_TIMEOUT:      'Timeout',
  wrong_pin:            'Wrong PIN',
  WRONG_PIN:            'Wrong PIN',
  card_expired:         'Expired Card',
  CARD_EXPIRED:         'Expired Card',
  daily_limit_exceeded: 'Limit Exceeded',
  DAILY_LIMIT_EXCEEDED: 'Limit Exceeded',
  upi_not_linked:       'UPI Unlinked',
  UPI_NOT_LINKED:       'UPI Unlinked',
  fraud_suspected:      'Fraud',
  FRAUD_SUSPECTED:      'Fraud',
};

/* ─── DEMO DATA ─── */
const DEMO_STATS = {
  total_events:    1247,
  recovery_rate:   67.3,
  avg_risk_score:  58.2,
  pending_reviews: 14,
};

function randomChoice(arr) { return arr[Math.floor(Math.random() * arr.length)]; }
function randomInt(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }
function randomFloat(min, max, dp=1) { return parseFloat((Math.random() * (max - min) + min).toFixed(dp)); }

function generateDemoEvents(n = 8) {
  const errors  = Object.keys(ACTION_LABELS).map(() => randomChoice([
    'insufficient_funds','bank_server_down','network_timeout','wrong_pin',
    'card_expired','daily_limit_exceeded','upi_not_linked','fraud_suspected',
  ]));
  const errList  = ['insufficient_funds','bank_server_down','network_timeout','wrong_pin','card_expired','daily_limit_exceeded','upi_not_linked','fraud_suspected'];
  const actions  = Object.keys(ACTION_LABELS);
  const methods  = ['upi', 'card', 'netbanking'];
  const banks    = ['SBI', 'HDFC', 'ICICI', 'Axis', 'Kotak'];
  const statuses = ['recovered', 'failed', 'pending', 'recovered', 'recovered'];

  const now = Date.now();
  return Array.from({ length: n }, (_, i) => {
    const prob   = randomFloat(20, 95);
    const status = prob >= 60 ? 'recovered' : randomChoice(statuses);
    return {
      id:          `TXN-${Math.random().toString(36).substring(2,10).toUpperCase()}`,
      transaction_id: `TXN-${Math.random().toString(36).substring(2,10).toUpperCase()}`,
      timestamp:   new Date(now - i * randomInt(30000, 300000)).toISOString(),
      amount:      randomInt(199, 49999),
      payment_method: randomChoice(methods),
      bank:        randomChoice(banks),
      error_reason:   randomChoice(errList),
      customer_segment: randomChoice(['premium', 'regular', 'new']),
      risk_score:  randomInt(20, 90),
      recommended_action: randomChoice(actions),
      recovery_probability: prob / 100,
      guardrail_triggered: prob > 30 ? false : true,
      status,
    };
  });
}

function generateDemoResult(formData) {
  const actions  = Object.keys(ACTION_LABELS);
  const scores   = {};
  let   total    = 0;
  actions.forEach(a => { scores[a] = randomFloat(5, 95); total += scores[a]; });
  Object.keys(scores).forEach(k => scores[k] = +(scores[k] / total).toFixed(4));

  const best = Object.entries(scores).sort((a,b)=>b[1]-a[1])[0];
  return {
    recommended_action:   best[0],
    recovery_probability: randomFloat(0.40, 0.93, 4),
    guardrail_triggered:  (formData.risk_score || 0) >= 80,
    guardrail_reason:     (formData.risk_score || 0) >= 80 ? 'High risk score exceeds threshold' : null,
    all_action_scores:    scores,
    transaction_id:       formData.transaction_id,
    risk_score:           formData.risk_score || 42,
    status: 'success',
  };
}

/* ─── UUID Generator ─── */
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

function generateTxnId() {
  return 'TXN-' + generateUUID().toUpperCase().slice(0, 18);
}

function regenerateTxnId() {
  currentTxnId = generateTxnId();
  document.getElementById('txnIdText').textContent = currentTxnId;
}

/* ─── Clock ─── */
function startClock() {
  const el = document.getElementById('navTime');
  function tick() {
    const now = new Date();
    el.textContent = now.toLocaleTimeString('en-IN', { hour12: false });
  }
  tick();
  setInterval(tick, 1000);
}

/* ─── Risk Badge Color ─── */
function updateRiskBadge(val) {
  const badge = document.getElementById('riskBadge');
  badge.textContent = val;
  const v = parseInt(val);
  if (v < 30)      { badge.style.color = '#6ee7b7'; badge.style.background = 'rgba(16,185,129,0.15)'; }
  else if (v < 65) { badge.style.color = '#fcd34d'; badge.style.background = 'rgba(245,158,11,0.15)'; }
  else             { badge.style.color = '#fca5a5'; badge.style.background = 'rgba(239,68,68,0.15)'; }
}

/* ─── Animated Counter ─── */
function animateCounter(el, target, duration = 1200, suffix = '') {
  const start     = 0;
  const startTime = performance.now();
  const isFloat   = String(target).includes('.');

  function update(currentTime) {
    const elapsed  = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased    = 1 - Math.pow(1 - progress, 3);
    const current  = start + (target - start) * eased;
    el.textContent = (isFloat ? current.toFixed(1) : Math.floor(current).toLocaleString()) + suffix;
    if (progress < 1) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

/* ─── Toast ─── */
function showToast(message, type = 'info', duration = 4000) {
  const container = document.getElementById('toastContainer');
  const icons = { error: '❌', success: '✅', info: 'ℹ️', warning: '⚠️' };

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'toastOut 0.4s ease forwards';
    setTimeout(() => toast.remove(), 400);
  }, duration);
}

/* ─── API Fetch Wrapper ─── */
async function apiFetch(path, options = {}) {
  const token = localStorage.getItem('recoverai_token');
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });
  
  if (response.status === 401) {
    window.location.href = 'login.html';
    throw new Error('Unauthorized');
  }

  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return await response.json();
}

/* ─── SET DEMO MODE ─── */
function enableDemoMode() {
  if (!isDemoMode) {
    isDemoMode = true;
    document.getElementById('demoBanner').classList.add('show');
    document.getElementById('demoBannerForm').classList.add('show');
    showToast('Backend offline — showing demo mode', 'warning', 6000);
  }
}

function disableDemoMode() {
  isDemoMode = false;
  document.getElementById('demoBanner').classList.remove('show');
  document.getElementById('demoBannerForm').classList.remove('show');
}

/* ─── LOGOUT ─── */
function logout() {
  localStorage.removeItem('recoverai_token');
  window.location.href = 'login.html';
}

/* ─── LOAD STATS ─── */
async function loadStats(animate = false) {
  let stats;
  try {
    // Backend endpoint: GET /api/dashboard-stats
    const data = await apiFetch('/dashboard-stats');
    stats = data.data || data;
    if (isDemoMode) disableDemoMode();
  } catch {
    enableDemoMode();
    stats = DEMO_STATS;
  }

  const dur = animate ? 1500 : 0;
  animateCounter(document.getElementById('stat-events'), stats.total_events || 0, dur);
  animateCounter(document.getElementById('stat-rate'),   stats.recovery_rate || 0, dur, '%');
  animateCounter(document.getElementById('stat-risk'),   stats.avg_risk_score || 0, dur);
  animateCounter(document.getElementById('stat-pending'),stats.pending_reviews || 0, dur);
}

/* ─── FORMAT TIME ─── */
function fmtTime(isoStr) {
  const d = new Date(isoStr);
  return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
}

function fmtAmount(n) {
  return '₹' + Number(n).toLocaleString('en-IN');
}

/* ─── RENDER RECENT EVENTS TABLE ─── */
function renderRecentTable(events) {
  const tbody = document.getElementById('recentTableBody');
  if (!events || events.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-state"><div class="empty-icon">📡</div>No recent events</td></tr>`;
    return;
  }

  tbody.innerHTML = events.slice(0, 12).map(e => {
    const status    = e.status || 'pending';
    const rowClass  = status === 'recovered' ? 'row-success' : status === 'failed' ? 'row-danger' : '';
    const chipClass = { recovered:'chip-recovered', failed:'chip-failed', pending:'chip-pending', processing:'chip-processing' }[status] || 'chip-pending';
    const actionKey = e.recommended_action || e.action || '';
    const actionLabel = (ACTION_LABELS[actionKey] || actionKey).replace(/^\S+\s/, '');
    const prob = typeof e.recovery_probability === 'number' ? e.recovery_probability * 100 : null;

    return `
      <tr class="${rowClass}">
        <td>${fmtTime(e.timestamp)}</td>
        <td class="amount-display">${fmtAmount(e.amount)}</td>
        <td>${ERROR_SHORT[e.error_reason] || e.error_reason || '—'}</td>
        <td><span class="action-tag">${actionLabel || '—'}</span></td>
        <td class="prob-mini">${prob !== null ? prob.toFixed(1)+'%' : '—'}</td>
        <td><span class="status-chip ${chipClass}">${status}</span></td>
      </tr>`;
  }).join('');
}

/* ─── LOAD RECENT EVENTS ─── */
async function loadRecentEvents() {
  let events;
  try {
    // Backend endpoint: GET /api/recent-events
    const data = await apiFetch('/recent-events');
    events = data.data || data.events || data;
    if (isDemoMode) disableDemoMode();
  } catch {
    enableDemoMode();
    events = generateDemoEvents(10);
  }

  recentEvents = events;
  renderRecentTable(events);
  updateDonutChart(events);

  document.getElementById('recentRefreshLabel').textContent =
    'Updated ' + new Date().toLocaleTimeString('en-IN', { hour12: false });
}

/* ─── DONUT CHART (SVG) ─── */
function updateDonutChart(events) {
  const counts = {};
  events.forEach(e => {
    const key = e.recommended_action || e.action || 'UNKNOWN';
    counts[key] = (counts[key] || 0) + 1;
  });

  const total   = events.length;
  const entries = Object.entries(counts).sort((a,b)=>b[1]-a[1]).slice(0,5);
  const colors  = ['#818cf8', '#6ee7b7', '#fcd34d', '#93c5fd', '#fca5a5'];

  const R = 33, CX = 45, CY = 45, STROKE_W = 12;
  const circumference = 2 * Math.PI * R;

  let offset = 0;
  const svg = document.getElementById('donutSvg');
  svg.innerHTML = '';

  const bgCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  bgCircle.setAttribute('cx', CX); bgCircle.setAttribute('cy', CY);
  bgCircle.setAttribute('r', R);   bgCircle.setAttribute('fill', 'none');
  bgCircle.setAttribute('stroke', 'rgba(255,255,255,0.06)');
  bgCircle.setAttribute('stroke-width', STROKE_W);
  svg.appendChild(bgCircle);

  entries.forEach(([action, count], i) => {
    const pct  = count / total;
    const dash = pct * circumference;
    const gap  = circumference - dash;
    const color = ACTION_COLORS[action] || colors[i % colors.length];

    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('cx', CX); circle.setAttribute('cy', CY);
    circle.setAttribute('r', R);   circle.setAttribute('fill', 'none');
    circle.setAttribute('stroke', color);
    circle.setAttribute('stroke-width', STROKE_W);
    circle.setAttribute('stroke-linecap', 'butt');
    circle.setAttribute('stroke-dasharray', `${dash} ${gap}`);
    circle.setAttribute('stroke-dashoffset', -offset * circumference);
    circle.setAttribute('transform', `rotate(-90 ${CX} ${CY})`);
    circle.style.transition = 'stroke-dashoffset 0.8s ease';
    svg.appendChild(circle);

    offset += pct;
  });

  document.getElementById('donutTotal').textContent = total;

  const legend = document.getElementById('donutLegend');
  legend.innerHTML = entries.map(([action, count], i) => {
    const color = ACTION_COLORS[action] || colors[i % colors.length];
    const pct   = ((count / total) * 100).toFixed(0);
    const label = (ACTION_LABELS[action] || action).replace(/^\S+\s/, '');
    return `
      <div class="legend-item">
        <div class="legend-dot" style="background:${color};"></div>
        <span class="legend-name">${label}</span>
        <span class="legend-pct">${count} (${pct}%)</span>
      </div>`;
  }).join('');
}

/* ─── CIRCULAR PROGRESS ─── */
function setCircularProgress(pct) {
  const circle = document.getElementById('progCircle');
  const text   = document.getElementById('circleText');
  const circumference = 188.5;
  const offset = circumference * (1 - pct / 100);
  circle.style.strokeDashoffset = offset;

  if (pct >= 70)       circle.style.stroke = '#34d399';
  else if (pct >= 45)  circle.style.stroke = '#6366f1';
  else                 circle.style.stroke = '#f59e0b';

  const startVal = 0;
  const dur = 1000;
  const startTime = performance.now();
  function animate(now) {
    const prog = Math.min((now - startTime) / dur, 1);
    const eased = 1 - Math.pow(1-prog, 3);
    text.textContent = Math.round(startVal + (pct - startVal) * eased) + '%';
    if (prog < 1) requestAnimationFrame(animate);
  }
  requestAnimationFrame(animate);
}

/* ─── RENDER ACTION SCORES ─── */
function renderActionScores(scores) {
  const container = document.getElementById('actionScores');
  // scores values come as 0-1 from backend
  const entries = Object.entries(scores).sort((a,b)=>b[1]-a[1]);
  const maxVal  = Math.max(...entries.map(([,v]) => v), 0.001);

  container.innerHTML = entries.map(([action, score]) => {
    const label = ACTION_LABELS[action] || action;
    const color = ACTION_COLORS[action] || '#6366f1';
    const pct   = ((score / maxVal) * 100).toFixed(0);
    const displayPct = (score * 100).toFixed(1);
    return `
      <div class="score-bar-row">
        <span class="score-name">${label}</span>
        <div class="score-bar-track">
          <div class="score-bar-fill" style="width:0%; background: linear-gradient(90deg, ${color}80, ${color});"
               data-target="${pct}"></div>
        </div>
        <span class="score-pct">${displayPct}%</span>
      </div>`;
  }).join('');

  requestAnimationFrame(() => {
    container.querySelectorAll('.score-bar-fill').forEach(bar => {
      const target = bar.dataset.target;
      setTimeout(() => { bar.style.width = target + '%'; }, 50);
    });
  });
}

/* ─── SHOW RESULT ─── */
function showResult(result) {
  lastResult = result;
  const panel = document.getElementById('resultPanel');
  panel.classList.remove('visible');
  void panel.offsetWidth;

  const action = result.recommended_action;
  // recovery_probability: backend returns 0-1, display as %
  const probRaw = result.recovery_probability;
  const prob    = probRaw <= 1 ? probRaw * 100 : probRaw;

  // Action badge
  const badge = document.getElementById('resultActionBadge');
  badge.textContent = ACTION_LABELS[action] || action.replace(/_/g, ' ');
  badge.className   = `result-action-badge action-badge-${action}`;

  // Guardrail
  const gBadge = document.getElementById('guardrailBadge');
  const gIcon  = document.getElementById('guardrailIcon');
  const gText  = document.getElementById('guardrailText');
  if (!result.guardrail_triggered) {
    gBadge.className = 'guardrail-badge pass';
    gIcon.textContent = '✓'; gText.textContent = 'Guardrails Passed';
  } else {
    gBadge.className = 'guardrail-badge fail';
    gIcon.textContent = '⚠'; gText.textContent = result.guardrail_reason || 'Guardrail Triggered';
  }

  // Probability
  document.getElementById('probValue').textContent = prob.toFixed(1) + '%';
  document.getElementById('probContext').textContent =
    prob >= 70 ? '🟢 High confidence recovery' :
    prob >= 45 ? '🟡 Moderate confidence' :
                 '🔴 Low confidence — review carefully';

  // Scores
  if (result.all_action_scores) renderActionScores(result.all_action_scores);

  panel.classList.add('visible');
  setTimeout(() => { setCircularProgress(prob); }, 100);
}

/* ─── BUILD FULL PAYLOAD FROM FORM ─── */
function buildPayload() {
  const now = new Date();
  return {
    transaction_id:          currentTxnId,
    amount:                  parseFloat(document.getElementById('amount').value),
    payment_method:          document.getElementById('paymentMethod').value,   // already lowercase
    bank:                    document.getElementById('bank').value,
    error_reason:            document.getElementById('errorReason').value,      // already lowercase
    customer_id:             'CUST-' + currentTxnId.slice(-8),
    customer_segment:        document.getElementById('customerSegment').value,
    opt_out_notification:    false,
    device_type:             'mobile',
    channel:                 'app',
    region:                  'South',
    customer_age:            30,
    account_balance:         1000.0,
    customer_tenure_months:  24,
    previous_failed_attempts:parseInt(document.getElementById('prevFailed').value || 0),
    retry_count:             0,
    risk_score:              parseFloat(document.getElementById('riskScore').value),
    merchant_category:       'ecommerce',
    card_type:               'NA',
    hour_of_day:             now.getHours(),
    day_of_week:             now.getDay() === 0 ? 6 : now.getDay() - 1,  // 0=Mon..6=Sun
    is_weekend:              (now.getDay() === 0 || now.getDay() === 6) ? 1 : 0,
    time_since_last_failure_hr: 2.0,
    transaction_frequency_30d:  8,
    recovery_attempt_count:     0,
    notification_sent:          0,
  };
}

/* ─── FORM SUBMIT ─── */
document.getElementById('paymentForm').addEventListener('submit', async (e) => {
  e.preventDefault();

  const btn        = document.getElementById('analyzeBtn');
  const btnContent = document.getElementById('analyzeBtnContent');

  // Validate required visible fields
  const amount = document.getElementById('amount').value;
  const method = document.getElementById('paymentMethod').value;
  const bank   = document.getElementById('bank').value;
  const error  = document.getElementById('errorReason').value;
  const seg    = document.getElementById('customerSegment').value;

  if (!amount || !method || !bank || !error || !seg) {
    showToast('Please fill in all required fields', 'error');
    return;
  }

  const payload = buildPayload();

  btn.disabled   = true;
  btnContent.innerHTML = '<div class="spinner"></div> Analyzing…';

  let result;
  try {
    // Backend endpoint: POST /api/process-payment
    result = await apiFetch('/process-payment', {
      method:  'POST',
      body:    JSON.stringify(payload),
    });
    if (isDemoMode) disableDemoMode();
  } catch {
    enableDemoMode();
    await new Promise(r => setTimeout(r, 900));
    result = generateDemoResult(payload);
  }

  btn.disabled   = false;
  btnContent.innerHTML = '⚡ Analyze &amp; Get Recovery Action';

  showResult(result);
  showToast('Analysis complete — review the recommendation', 'success');

  // Add to recent events and audit log
  const probDisplay = result.recovery_probability <= 1 ? result.recovery_probability * 100 : result.recovery_probability;
  const event = {
    ...payload,
    ...result,
    recommended_action: result.recommended_action,
    recovery_probability: result.recovery_probability,
    timestamp: new Date().toISOString(),
    status: probDisplay >= 60 ? 'processing' : 'pending',
  };

  recentEvents.unshift(event);
  if (recentEvents.length > 20) recentEvents.pop();
  renderRecentTable(recentEvents);
  updateDonutChart(recentEvents);

  auditLog.unshift(event);
  renderAuditTable();

  setTimeout(regenerateTxnId, 500);
});

/* ─── APPROVE / REJECT ─── */
async function submitApproval(decision) {
  if (!lastResult) return;

  const payload = {
    transaction_id: lastResult.transaction_id,
    decision,
    notes: null,
  };
  const token = localStorage.getItem('recoverai_token');

  try {
    // Backend endpoint: POST /api/approve-action
    await apiFetch('/approve-action', { 
        method: 'POST', 
        headers: { 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(payload) 
    });
  } catch {
    // demo mode: silently succeed
  }

  if (decision === 'approve' && lastResult.recommended_action === 'send_notification') {
    showToast('Sending notification via Twilio/Sendgrid...', 'info', 3000);
    try {
        await apiFetch('/simulate-notification', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({
                transaction_id: lastResult.transaction_id,
                customer_id: lastResult.transaction_id.replace('TXN-', 'CUST-'),
                action: 'send_notification'
            })
        });
        showToast('✉️ Customer successfully notified!', 'success', 5000);
    } catch {
        showToast('✉️ Customer notified (Simulated)', 'success', 5000);
    }
  }

  const newStatus = decision === 'approve' ? 'recovered' : 'failed';
  const idx = recentEvents.findIndex(e => e.transaction_id === lastResult.transaction_id);
  if (idx !== -1) { recentEvents[idx].status = newStatus; renderRecentTable(recentEvents); updateDonutChart(recentEvents); }

  const aidx = auditLog.findIndex(e => e.transaction_id === lastResult.transaction_id);
  if (aidx !== -1) { auditLog[aidx].status = newStatus; renderAuditTable(); }

  showToast(
    decision === 'approve'
      ? `✅ Action approved — ${ACTION_LABELS[lastResult.recommended_action] || lastResult.recommended_action}`
      : '❌ Action rejected',
    decision === 'approve' ? 'success' : 'error'
  );

  document.getElementById('resultPanel').classList.remove('visible');
  lastResult = null;

  await loadStats(false);
}

/* ─── AUDIT TABLE ─── */
function renderAuditTable() {
  const tbody = document.getElementById('auditTableBody');
  document.getElementById('auditCount').textContent = `(${auditLog.length} events)`;

  if (auditLog.length === 0) {
    tbody.innerHTML = `<tr><td colspan="13" class="empty-state"><div class="empty-icon">📂</div>No events logged yet</td></tr>`;
    return;
  }

  tbody.innerHTML = auditLog.slice(0, 20).map((e, i) => {
    const status    = e.status || 'pending';
    const rowClass  = status === 'recovered' ? 'row-success' : status === 'failed' ? 'row-danger' : '';
    const chipClass = { recovered:'chip-recovered', failed:'chip-failed', pending:'chip-pending', processing:'chip-processing' }[status] || 'chip-pending';
    const action    = e.recommended_action || '—';
    const probRaw   = e.recovery_probability;
    const probPct   = probRaw != null ? (probRaw <= 1 ? probRaw * 100 : probRaw).toFixed(1) + '%' : '—';

    return `
      <tr class="${rowClass}">
        <td style="color:var(--text-muted);">${i + 1}</td>
        <td>${new Date(e.timestamp).toLocaleString('en-IN', { hour12: false })}</td>
        <td style="font-family:monospace; font-size:10px; color:var(--accent-light);">${e.transaction_id || '—'}</td>
        <td class="amount-display">${fmtAmount(e.amount)}</td>
        <td>${e.payment_method || '—'}</td>
        <td>${e.bank || '—'}</td>
        <td>${ERROR_SHORT[e.error_reason] || e.error_reason || '—'}</td>
        <td>${e.customer_segment || '—'}</td>
        <td style="color:${(e.risk_score||0) > 65 ? 'var(--danger-light)' : 'var(--text-secondary)'};">${e.risk_score || 0}</td>
        <td><span class="action-tag">${(ACTION_LABELS[action] || action).replace(/^\S+\s/, '')}</span></td>
        <td class="prob-mini">${probPct}</td>
        <td><span style="font-size:14px;">${e.guardrail_triggered ? '⚠️' : '✅'}</span></td>
        <td><span class="status-chip ${chipClass}">${status}</span></td>
      </tr>`;
  }).join('');
}

/* ─── EXPORT CSV ─── */
function exportCSV() {
  if (auditLog.length === 0) { showToast('No events to export', 'warning'); return; }

  const headers = ['#','Timestamp','Transaction ID','Amount','Method','Bank','Error','Segment','Risk Score','Action','Probability','Guardrail','Status'];
  const rows = auditLog.map((e, i) => {
    const probRaw = e.recovery_probability;
    const prob    = probRaw != null ? (probRaw <= 1 ? (probRaw * 100).toFixed(1) : probRaw.toFixed(1)) : '';
    return [
      i+1,
      new Date(e.timestamp).toLocaleString('en-IN'),
      e.transaction_id,
      e.amount,
      e.payment_method,
      e.bank,
      e.error_reason,
      e.customer_segment,
      e.risk_score,
      e.recommended_action,
      prob,
      e.guardrail_triggered ? 'Triggered' : 'Passed',
      e.status,
    ].map(v => `"${(v ?? '').toString().replace(/"/g,'""')}"`).join(',');
  });

  const csv  = [headers.join(','), ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `recover-ai-audit-${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('CSV exported successfully', 'success');
}

/* ─── LOAD DEMO EVENTS ON STARTUP ─── */
async function loadInitialEvents() {
  let events;
  try {
    const data = await apiFetch('/recent-events');
    events = data.data || data.events || data;
    disableDemoMode();
  } catch {
    enableDemoMode();
    events = generateDemoEvents(12);
  }
  recentEvents = events;
  renderRecentTable(events);
  updateDonutChart(events);
}

/* ─── AUTO-REFRESH ─── */
function startAutoRefresh() {
  statsInterval  = setInterval(() => loadStats(false),   STATS_REFRESH_MS);
  eventsInterval = setInterval(() => loadRecentEvents(), EVENTS_REFRESH_MS);
}

/* ─── LIVE FEED WEBSOCKET ─── */
function toggleLiveFeed(e) {
  const isEnabled = e.target.checked;
  const dot = document.getElementById('liveDot');
  const label = document.getElementById('recentRefreshLabel');
  
  if (isEnabled) {
    dot.style.display = 'block';
    label.textContent = 'Live Feed ON';
    
    // Connect to WebSocket
    const wsUrl = 'ws://localhost:8000/api/ws/live-events';
    liveWs = new WebSocket(wsUrl);
    
    liveWs.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        
        // Add to recent events and audit log
        recentEvents.unshift(payload);
        if (recentEvents.length > 20) recentEvents.pop();
        renderRecentTable(recentEvents);
        updateDonutChart(recentEvents);
        
        auditLog.unshift(payload);
        renderAuditTable();
        
        showToast('New live event received!', 'info', 2000);
      } catch (e) {
        console.error("Error parsing WS data", e);
      }
    };
    
    liveWs.onclose = () => {
      console.log('Live feed disconnected');
      if (document.getElementById('liveFeedToggle').checked) {
        showToast('Live feed connection lost. Reconnecting...', 'warning');
        setTimeout(() => toggleLiveFeed({ target: { checked: true } }), 3000);
      }
    };
  } else {
    dot.style.display = 'none';
    label.textContent = 'Offline';
    if (liveWs) {
      liveWs.close();
      liveWs = null;
    }
  }
}

/* ─── CSV BATCH UPLOAD ─── */
function openUploadModal() {
  document.getElementById('uploadModal').classList.remove('hidden');
}

function closeUploadModal() {
  document.getElementById('uploadModal').classList.add('hidden');
  document.getElementById('uploadProgress').classList.add('hidden');
}

document.addEventListener('DOMContentLoaded', () => {
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('csvFileInput');

  dropZone.addEventListener('click', () => fileInput.click());

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('border-primary', 'bg-primary/5');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('border-primary', 'bg-primary/5');
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('border-primary', 'bg-primary/5');
    if (e.dataTransfer.files.length) {
      handleCsvUpload(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
      handleCsvUpload(e.target.files[0]);
    }
  });
});

async function handleCsvUpload(file) {
  if (!file.name.endsWith('.csv')) {
    showToast('Please upload a valid CSV file.', 'error');
    return;
  }

  const formData = new FormData();
  formData.append('file', file);

  document.getElementById('uploadProgress').classList.remove('hidden');
  document.getElementById('uploadBar').style.width = '50%';
  document.getElementById('uploadPercent').textContent = 'Uploading...';

  try {
    const token = localStorage.getItem('recoverai_token');
    const response = await fetch(`${API_BASE}/upload-csv`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    });

    if (response.status === 401) {
      window.location.href = 'login.html';
      return;
    }

    if (!response.ok) throw new Error('Upload failed');
    
    const data = await response.json();
    document.getElementById('uploadBar').style.width = '100%';
    document.getElementById('uploadPercent').textContent = 'Done!';
    
    showToast(`Batch processed: ${data.processed} rows (${data.errors} errors)`, 'success', 5000);
    
    setTimeout(() => {
      closeUploadModal();
      loadStats(true);
      loadRecentEvents();
      // force reload audit logs
      window.location.reload(); 
    }, 1500);

  } catch (error) {
    console.error(error);
    showToast('Failed to process CSV file.', 'error');
    document.getElementById('uploadProgress').classList.add('hidden');
  }
}

/* ─── INIT ─── */
async function init() {
  if (!localStorage.getItem('recoverai_token')) {
    window.location.href = 'login.html';
    return;
  }

  startClock();
  regenerateTxnId();
  updateRiskBadge(document.getElementById('riskScore').value);

  document.getElementById('liveFeedToggle').addEventListener('change', toggleLiveFeed);

  await Promise.all([
    loadStats(true),
    loadInitialEvents(),
  ]);

  startAutoRefresh();
  renderAuditTable();
}

document.addEventListener('DOMContentLoaded', init);
