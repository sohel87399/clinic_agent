/* Closira AI Agent — Frontend JS */

const API = '';  // same origin

// ── State ─────────────────────────────────────────────────────────────────────
let sessionId = null;
let isWaiting  = false;

// ── DOM refs ──────────────────────────────────────────────────────────────────
const messagesInner   = document.getElementById('messagesInner');
const messageInput    = document.getElementById('messageInput');
const sendBtn         = document.getElementById('sendBtn');
const typingIndicator = document.getElementById('typingIndicator');
const inputArea       = document.getElementById('inputArea');
const statusBadge     = document.getElementById('statusBadge');
const stageBadge      = document.getElementById('stageBadge');
const sessionIdDisplay= document.getElementById('sessionIdDisplay');
const headerStatus    = document.getElementById('headerStatus');
const summaryOverlay  = document.getElementById('summaryOverlay');
const summaryBody     = document.getElementById('summaryBody');
const newChatBtn      = document.getElementById('newChatBtn');
const newChatSummaryBtn = document.getElementById('newChatSummaryBtn');
const closeSummaryBtn = document.getElementById('closeSummaryBtn');
const endSessionBtn   = document.getElementById('endSessionBtn');

// ── Init ──────────────────────────────────────────────────────────────────────
async function initSession() {
  clearMessages();
  const res  = await fetch(`${API}/api/session/new`, { method: 'POST' });
  const data = await res.json();
  sessionId  = data.session_id;
  sessionIdDisplay.textContent = sessionId.slice(0, 8);
  appendMessage('aria', data.message, data.stage, null);
  updateStageUI(data.stage, false);
}

// ── Send message ──────────────────────────────────────────────────────────────
async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text || isWaiting || !sessionId) return;

  appendMessage('user', text);
  messageInput.value = '';
  autoResize();
  setWaiting(true);

  try {
    const res  = await fetch(`${API}/api/message`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message: text }),
    });
    const data = await res.json();

    setWaiting(false);
    appendMessage('aria', data.message, data.stage, data.metadata, data.escalated);
    updateStageUI(data.stage, data.escalated);

    if (data.session_ended || data.escalated) {
      disableInput(data.escalated ? 'escalated' : 'ended');
    }

    if (data.session_ended && data.summary) {
      setTimeout(() => showSummary(data.summary), 800);
    }

  } catch (err) {
    setWaiting(false);
    appendMessage('aria', '⚠️ Something went wrong. Please try again.', 'FAQ_ANSWERING', null);
  }
}

// ── Append message ────────────────────────────────────────────────────────────
function appendMessage(role, text, stage = null, metadata = null, escalated = false) {
  const row = document.createElement('div');
  row.className = `msg-row ${role}`;

  const avatar = document.createElement('div');
  avatar.className = `msg-avatar ${role}`;
  avatar.textContent = role === 'aria' ? 'A' : 'U';

  const content = document.createElement('div');
  content.className = 'msg-content';

  // Stage pill (aria only)
  if (role === 'aria' && stage) {
    const pill = document.createElement('div');
    const stageKey = stage.toLowerCase().replace('_', '');
    pill.className = `stage-pill ${stageKey}`;
    pill.textContent = stageLabel(stage);
    content.appendChild(pill);
  }

  // Bubble
  const bubble = document.createElement('div');
  bubble.className = `msg-bubble ${role}`;
  if (escalated) bubble.classList.add('escalated');
  if (stage === 'ENDED' || stage === 'SUMMARY') bubble.classList.add('summary-bubble');
  bubble.textContent = text;
  content.appendChild(bubble);

  // Confidence bar (aria FAQ only)
  if (role === 'aria' && metadata && metadata.confidence !== undefined) {
    const conf = metadata.confidence;
    const bar  = document.createElement('div');
    bar.className = 'confidence-bar';
    const color = conf >= 0.8 ? '#10B981' : conf >= 0.6 ? '#F59E0B' : '#EF4444';
    bar.innerHTML = `
      <span class="conf-label">Confidence</span>
      <div class="conf-track"><div class="conf-fill" style="width:${conf*100}%;background:${color}"></div></div>
      <span class="conf-value">${Math.round(conf*100)}%</span>`;
    content.appendChild(bar);
  }

  // Timestamp
  const time = document.createElement('div');
  time.className = 'msg-time';
  time.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  content.appendChild(time);

  row.appendChild(avatar);
  row.appendChild(content);
  messagesInner.appendChild(row);
  scrollToBottom();
}

function appendSystemMsg(text) {
  const div = document.createElement('div');
  div.className = 'system-msg';
  div.innerHTML = `<span>${text}</span>`;
  messagesInner.appendChild(div);
  scrollToBottom();
}

// ── Stage label ───────────────────────────────────────────────────────────────
function stageLabel(stage) {
  const map = {
    FAQ_ANSWERING:      '💬 FAQ',
    LEAD_QUALIFICATION: '✅ Qualifying',
    SUMMARY:            '📋 Summary',
    ESCALATED:          '🚨 Escalated',
    ENDED:              '✅ Ended',
  };
  return map[stage] || stage;
}

// ── Update sidebar UI ─────────────────────────────────────────────────────────
function updateStageUI(stage, escalated) {
  const stageMap = {
    FAQ_ANSWERING:      'FAQ',
    LEAD_QUALIFICATION: 'Qualifying',
    SUMMARY:            'Summary',
    ESCALATED:          'Escalated',
    ENDED:              'Ended',
  };

  stageBadge.textContent = stageMap[stage] || stage;

  if (escalated || stage === 'ESCALATED') {
    statusBadge.textContent = 'Escalated';
    statusBadge.className   = 'status-badge escalated';
    headerStatus.textContent = 'Escalated — Human handoff';
  } else if (stage === 'ENDED') {
    statusBadge.textContent = 'Ended';
    statusBadge.className   = 'status-badge ended';
    headerStatus.textContent = 'Session ended';
  } else {
    statusBadge.textContent = 'Active';
    statusBadge.className   = 'status-badge';
    headerStatus.textContent = `Online · ${stageMap[stage] || stage} Stage`;
  }

  // System message on stage transition
  if (stage === 'LEAD_QUALIFICATION') {
    appendSystemMsg('Moving to lead qualification');
  } else if (stage === 'SUMMARY' || stage === 'ENDED') {
    appendSystemMsg('Session complete');
  } else if (stage === 'ESCALATED') {
    appendSystemMsg('Session escalated to human agent');
  }
}

// ── Waiting state ─────────────────────────────────────────────────────────────
function setWaiting(val) {
  isWaiting = val;
  sendBtn.disabled = val;
  typingIndicator.style.display = val ? 'flex' : 'none';
  if (val) scrollToBottom();
}

// ── Disable input ─────────────────────────────────────────────────────────────
function disableInput(reason) {
  inputArea.style.opacity = '0.5';
  inputArea.style.pointerEvents = 'none';
  messageInput.placeholder = reason === 'escalated'
    ? 'Session escalated — please contact us directly'
    : 'Session ended — start a new conversation';
}

// ── Show summary panel ────────────────────────────────────────────────────────
function showSummary(summary) {
  summaryBody.innerHTML = '';

  // Customer intent
  if (summary.customer_intent) {
    summaryBody.appendChild(summaryCard('Customer Intent', summary.customer_intent));
  }

  // Details collected
  if (summary.details_collected) {
    const d = summary.details_collected;
    const rows = [
      ['Name',             d.name],
      ['Interested In',    d.interested_service],
      ['Prior Experience', d.prior_experience],
      ['Booking Intent',   d.booking_intent],
    ].filter(([, v]) => v && v !== 'null');

    if (rows.length) {
      const card = document.createElement('div');
      card.className = 'summary-card';
      card.innerHTML = `<div class="summary-card-title">Details Collected</div>`;
      rows.forEach(([k, v]) => {
        card.innerHTML += `
          <div class="summary-detail-row">
            <span class="summary-detail-key">${k}</span>
            <span class="summary-detail-value">${v}</span>
          </div>`;
      });
      summaryBody.appendChild(card);
    }
  }

  // Lead score
  if (summary.details_collected?.booking_intent || summary.lead_score) {
    const score = summary.lead_score || deriveScore(summary);
    if (score) {
      const card = document.createElement('div');
      card.className = 'summary-card';
      card.innerHTML = `
        <div class="summary-card-title">Lead Score</div>
        <div class="lead-score ${score}">
          ${{ hot: '🔥', warm: '😊', cold: '❄️' }[score] || ''} ${score.toUpperCase()}
        </div>`;
      summaryBody.appendChild(card);
    }
  }

  // SOP gaps
  if (summary.sop_gaps && summary.sop_gaps.length > 0) {
    const card = document.createElement('div');
    card.className = 'summary-card';
    card.innerHTML = `<div class="summary-card-title">SOP Gaps</div>`;
    summary.sop_gaps.forEach(gap => {
      card.innerHTML += `<div class="summary-card-value" style="padding:3px 0">• ${gap}</div>`;
    });
    summaryBody.appendChild(card);
  }

  // Escalation
  if (summary.escalated) {
    const card = document.createElement('div');
    card.className = 'summary-card';
    card.style.borderColor = '#FECACA';
    card.innerHTML = `
      <div class="summary-card-title" style="color:#EF4444">Escalation</div>
      <div class="summary-card-value">${summary.escalation_reason || 'Escalated to human agent'}</div>`;
    summaryBody.appendChild(card);
  }

  // Recommended action
  if (summary.recommended_next_action) {
    const card = document.createElement('div');
    card.className = 'next-action-card';
    card.innerHTML = `
      <div class="next-action-label">Recommended Next Action</div>
      <div class="next-action-value">${summary.recommended_next_action}</div>`;
    summaryBody.appendChild(card);
  }

  summaryOverlay.style.display = 'flex';
}

function summaryCard(title, value) {
  const card = document.createElement('div');
  card.className = 'summary-card';
  card.innerHTML = `
    <div class="summary-card-title">${title}</div>
    <div class="summary-card-value">${value}</div>`;
  return card;
}

function deriveScore(summary) {
  const intent = (summary.details_collected?.booking_intent || '').toLowerCase();
  if (intent.includes('week') || intent.includes('soon') || intent.includes('asap')) return 'hot';
  if (intent.includes('month') || intent.includes('exploring')) return 'warm';
  if (intent) return 'cold';
  return null;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function scrollToBottom() {
  const c = document.getElementById('messagesContainer');
  setTimeout(() => c.scrollTop = c.scrollHeight, 50);
}

function clearMessages() {
  messagesInner.innerHTML = '';
  inputArea.style.opacity = '';
  inputArea.style.pointerEvents = '';
  messageInput.placeholder = 'Type your message...';
  updateStageUI('FAQ_ANSWERING', false);
}

function autoResize() {
  messageInput.style.height = 'auto';
  messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
}

// ── Event listeners ───────────────────────────────────────────────────────────
sendBtn.addEventListener('click', sendMessage);

messageInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

messageInput.addEventListener('input', autoResize);

document.querySelectorAll('.quick-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    if (isWaiting) return;
    messageInput.value = btn.dataset.msg;
    sendMessage();
  });
});

newChatBtn.addEventListener('click', () => {
  summaryOverlay.style.display = 'none';
  initSession();
});

newChatSummaryBtn.addEventListener('click', () => {
  summaryOverlay.style.display = 'none';
  initSession();
});

closeSummaryBtn.addEventListener('click', () => {
  summaryOverlay.style.display = 'none';
});

endSessionBtn.addEventListener('click', async () => {
  if (!sessionId || isWaiting) return;
  setWaiting(true);
  try {
    const res  = await fetch(`${API}/api/session/${sessionId}/end`, { method: 'POST' });
    const data = await res.json();
    setWaiting(false);
    appendMessage('aria', data.message, 'ENDED', null);
    updateStageUI('ENDED', false);
    disableInput('ended');
    if (data.summary) setTimeout(() => showSummary(data.summary), 600);
  } catch {
    setWaiting(false);
  }
});

// ── Start ─────────────────────────────────────────────────────────────────────
initSession();
