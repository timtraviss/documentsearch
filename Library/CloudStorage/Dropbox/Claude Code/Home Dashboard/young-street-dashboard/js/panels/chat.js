export function initChat() {
  const drawer   = document.getElementById('chat-drawer');
  const scrim    = document.getElementById('chat-scrim');
  const openBtn  = document.getElementById('btn-chat');
  const closeBtn = document.getElementById('chat-close');
  const messages = document.getElementById('chat-messages');
  const input    = document.getElementById('chat-input');
  const sendBtn  = document.getElementById('chat-send');

  // In-memory conversation history (session only)
  const history = [];

  function open() {
    drawer.classList.add('open');
    scrim.classList.add('open');
    openBtn.classList.add('active');
    input.focus();
  }

  function close() {
    drawer.classList.remove('open');
    scrim.classList.remove('open');
    openBtn.classList.remove('active');
  }

  openBtn.addEventListener('click', () =>
    drawer.classList.contains('open') ? close() : open()
  );
  closeBtn.addEventListener('click', close);
  scrim.addEventListener('click', close);
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') close();
  });

  sendBtn.addEventListener('click', submit);
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); }
  });

  async function submit() {
    const text = input.value.trim();
    if (!text) return;
    input.value = '';

    appendUser(text);
    const thinking = appendThinking();
    scrollBottom();

    try {
      const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text, messages: history }),
      });
      const data = await res.json();
      thinking.remove();

      if (data.error) {
        appendError(data.error);
      } else {
        appendAI(data.answer, data.sources || []);
        history.push({ role: 'user',      content: text });
        history.push({ role: 'assistant', content: data.answer });
      }
    } catch (err) {
      thinking.remove();
      appendError('Connection error — is the Flask server running?');
    }

    scrollBottom();
  }

  function appendUser(text) {
    const div = document.createElement('div');
    div.className = 'chat-msg';
    div.innerHTML = `
      <div class="chat-msg-user">
        <span class="chat-prompt">❯</span>
        <span>${escHtml(text)}</span>
      </div>`;
    messages.appendChild(div);
  }

  function appendThinking() {
    const div = document.createElement('div');
    div.className = 'chat-msg chat-msg-thinking';
    div.innerHTML = `
      <div class="chat-dots">
        <span></span><span></span><span></span>
      </div>
      searching documents…`;
    messages.appendChild(div);
    return div;
  }

  function appendAI(text, sources) {
    const div = document.createElement('div');
    div.className = 'chat-msg';

    // Render answer: replace leading "- " or "• " list items with → bullets
    const rendered = text
      .split('\n')
      .map(line => {
        if (/^\s*[-•]\s/.test(line)) {
          return `<span class="chat-bullet">→</span> ${escHtml(line.replace(/^\s*[-•]\s*/, ''))}`;
        }
        return escHtml(line);
      })
      .join('\n');

    let html = `<div class="chat-msg-ai">${rendered}</div>`;

    if (sources.length > 0) {
      const srcLine = sources
        .map(s => escHtml(s.name || s.filename))
        .join(' · ');
      html += `<div class="chat-msg-source">─ ${srcLine}</div>`;
    }

    div.innerHTML = html;
    messages.appendChild(div);
  }

  function appendError(msg) {
    const div = document.createElement('div');
    div.className = 'chat-msg';
    div.innerHTML = `<div class="chat-msg-ai" style="opacity:.5">${escHtml(msg)}</div>`;
    messages.appendChild(div);
  }

  function scrollBottom() {
    messages.scrollTop = messages.scrollHeight;
  }

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
}
