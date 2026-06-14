const CHANNELS = {
  male: { key: 'male', label: '男频', title: '男频新书榜' },
  female: { key: 'female', label: '女频', title: '女频新书榜' },
};

document.addEventListener('DOMContentLoaded', () => {
  const detail = document.getElementById('book-detail');
  const cacheBuster = `v=${Math.floor(Date.now() / 600000)}`;
  const maxDays = 30;
  const params = new URLSearchParams(location.search);
  const requestedChannel = params.get('channel') || 'male';
  const currentChannel = CHANNELS[requestedChannel] ? requestedChannel : 'male';
  const channelConfig = CHANNELS[currentChannel];
  const backLink = document.querySelector('.back-link');
  const trendLink = document.querySelector('.book-topbar .text-btn');
  const toast = document.createElement('div');
  toast.className = 'copy-toast';
  toast.textContent = '书本信息已复制';
  document.body.appendChild(toast);

  document.body.dataset.channel = currentChannel;
  document.title = `作品详情 · 番茄${channelConfig.label}新书榜`;
  backLink.href = `index.html?channel=${encodeURIComponent(currentChannel)}`;
  trendLink.href = `trend.html?channel=${encodeURIComponent(currentChannel)}`;

  init();

  async function init() {
    const bookId = params.get('id');
    const title = params.get('title');
    if (!bookId && !title) {
      renderEmpty('缺少作品 ID。');
      return;
    }
    try {
      const dateIndex = await fetchChannelJson('dates.json');
      const dates = (dateIndex.dates || []).slice().sort().slice(-maxDays);
      const snapshots = await Promise.all(dates.map(date => fetchChannelJson(`raw/${date}.json`).catch(() => null)));
      const records = collectRecords(bookId, title, dates, snapshots);
      if (!records.length) {
        renderEmpty(`最近 30 天${channelConfig.label}榜单中没有找到这本书。`);
        return;
      }
      renderBook(records);
    } catch (error) {
      console.error(error);
      renderEmpty('作品详情加载失败。');
    }
  }

  function collectRecords(bookId, title, dates, snapshots) {
    const records = [];
    snapshots.forEach((snapshot, snapshotIndex) => {
      if (!snapshot || !snapshot.categories) return;
      snapshot.categories.forEach(category => {
        (category.books || []).forEach((book, index) => {
          if (bookId && extractBookId(book.url) !== bookId) return;
          if (!bookId && book.title !== title) return;
          records.push({
            date: dates[snapshotIndex],
            category: category.name,
            rank: index + 1,
            readsLabel: book.reads || '未知',
            readsValue: parseReads(book.reads),
            book,
          });
        });
      });
    });
    return records.sort((a, b) => a.date.localeCompare(b.date));
  }

  function renderBook(records) {
    const latest = records[records.length - 1];
    const book = latest.book;
    const chartRecords = compactByDate(records).filter(item => item.readsValue > 0);
    const maxReads = Math.max(...records.map(item => item.readsValue || 0), 0);
    detail.innerHTML = `
      <section class="book-detail-hero">
        <div class="detail-cover">${book.cover ? `<img src="${escapeAttr(book.cover)}" alt="${escapeAttr(book.title)}">` : '<div class="no-cover">暂无封面</div>'}</div>
        <div class="detail-main">
          <span class="panel-kicker">${escapeHtml(channelConfig.label)} · ${escapeHtml(latest.category)} · 第 ${latest.rank} 名</span>
          <h1>${escapeHtml(book.title)}</h1>
          <p class="detail-author">作者：${escapeHtml(book.author || '未知')}</p>
          <div class="detail-stats">
            <span><strong>${escapeHtml(latest.readsLabel)}</strong><small>当前在读</small></span>
            <span><strong>${escapeHtml(formatPlainReads(maxReads))}</strong><small>近30日峰值</small></span>
            <span><strong>${records.length}</strong><small>上榜记录</small></span>
          </div>
          <p class="detail-intro">${escapeHtml(book.intro || '暂无简介')}</p>
          <div class="detail-actions">
            <button class="book-copy-btn detail-copy-btn" type="button">复制信息</button>
            ${book.url ? `<a class="source-link-btn" href="${escapeAttr(book.url)}" target="_blank" rel="noopener noreferrer">打开番茄原文</a>` : ''}
          </div>
        </div>
      </section>
      <section class="book-detail-grid">
        <article class="detail-panel">
          <span class="panel-kicker">阅读趋势</span>
          <h2>最近 30 天在读变化</h2>
          ${renderChart(chartRecords)}
        </article>
        <article class="detail-panel">
          <span class="panel-kicker">上榜记录</span>
          <h2>最近出现</h2>
          <div class="history-list">${records.slice().reverse().slice(0, 12).map(renderHistory).join('')}</div>
        </article>
      </section>
    `;
    detail.querySelector('.detail-copy-btn').addEventListener('click', () => {
      copyText(`${book.title}\n作者：${book.author || '未知'}\n在读：${latest.readsLabel}\n简介：${book.intro || '无'}\n链接：${book.url || '无'}`).then(() => {
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 1600);
      });
    });
  }

  function renderChart(records) {
    if (!records.length) return '<p class="muted-line">暂无可用趋势。</p>';
    const width = 760;
    const height = 280;
    const pad = { left: 56, right: 20, top: 20, bottom: 42 };
    const innerW = width - pad.left - pad.right;
    const innerH = height - pad.top - pad.bottom;
    const max = niceMax(Math.max(...records.map(item => item.readsValue), 1));
    const points = records.map((item, index) => {
      const x = records.length > 1 ? pad.left + (innerW / (records.length - 1)) * index : pad.left + innerW / 2;
      const y = pad.top + innerH - (item.readsValue / max) * innerH;
      return { x, y, item };
    });
    const poly = points.map(point => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(' ');
    const ticks = [0, max / 2, max];
    return `<div class="chart-wrap"><svg class="reads-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="阅读趋势">
      ${ticks.map(tick => {
        const y = pad.top + innerH - (tick / max) * innerH;
        return `<line class="chart-grid" x1="${pad.left}" y1="${y}" x2="${width - pad.right}" y2="${y}"></line><text class="chart-label" x="${pad.left - 10}" y="${y + 4}" text-anchor="end">${formatPlainReads(tick)}</text>`;
      }).join('')}
      <line class="chart-axis" x1="${pad.left}" y1="${height - pad.bottom}" x2="${width - pad.right}" y2="${height - pad.bottom}"></line>
      <polyline class="chart-line" points="${poly}"></polyline>
      ${points.map((point, index) => `<circle class="chart-point" cx="${point.x}" cy="${point.y}" r="4"><title>${point.item.date} ${point.item.readsLabel}</title></circle>${index % Math.ceil(points.length / 6 || 1) === 0 ? `<text class="chart-label" x="${point.x}" y="${height - 14}" text-anchor="middle">${point.item.date.slice(5)}</text>` : ''}`).join('')}
    </svg></div>`;
  }

  function renderHistory(record) {
    return `<div class="history-row"><time>${escapeHtml(record.date)}</time><strong>${escapeHtml(record.category)} · 第 ${record.rank} 名</strong><span>${escapeHtml(record.readsLabel)}</span></div>`;
  }

  function compactByDate(records) {
    const map = new Map();
    records.forEach(record => {
      const current = map.get(record.date);
      if (!current || record.readsValue >= current.readsValue) map.set(record.date, record);
    });
    return Array.from(map.values()).sort((a, b) => a.date.localeCompare(b.date));
  }

  async function fetchChannelJson(path) {
    const channelPath = `data/channels/${currentChannel}/${path}?${cacheBuster}`;
    try {
      return await fetchJson(channelPath);
    } catch (error) {
      if (currentChannel === 'male') return fetchJson(`data/${path}?${cacheBuster}`);
      throw error;
    }
  }

  function renderEmpty(message) {
    detail.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
  }
});

function parseReads(value) {
  const raw = String(value || '').replace('在读', '').replace('：', '').replace(':', '').replace(',', '').trim();
  const n = parseFloat(raw);
  if (Number.isNaN(n)) return 0;
  if (raw.includes('亿')) return n * 100000000;
  if (raw.includes('万')) return n * 10000;
  return n;
}
function formatPlainReads(value) {
  if (Math.abs(value) >= 100000000) return `${(value / 100000000).toFixed(1)}亿`;
  if (Math.abs(value) >= 10000) return `${(value / 10000).toFixed(1)}万`;
  return `${Math.round(value)}`;
}
function niceMax(value) {
  const raw = Math.max(1, Number(value || 1));
  const magnitude = 10 ** Math.floor(Math.log10(raw));
  const step = raw / magnitude > 5 ? magnitude : magnitude / 2;
  return Math.ceil(raw / step) * step;
}
function fetchJson(url) {
  return fetch(url).then(response => {
    if (!response.ok) throw new Error(`Failed to load ${url}`);
    return response.json();
  });
}
function copyText(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    return navigator.clipboard.writeText(text).catch(() => fallbackCopyText(text));
  }
  return fallbackCopyText(text);
}
function fallbackCopyText(text) {
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  document.execCommand('copy');
  document.body.removeChild(ta);
  return Promise.resolve();
}
function extractBookId(url) {
  const match = String(url || '').match(/\/page\/(\d+)/);
  return match ? match[1] : '';
}
function escapeHtml(value) {
  return String(value || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function escapeAttr(value) {
  return escapeHtml(value).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
