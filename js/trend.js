const CHANNELS = {
  male: { key: 'male', label: '男频', title: '男频新书榜' },
  female: { key: 'female', label: '女频', title: '女频新书榜' },
};

document.addEventListener('DOMContentLoaded', () => {
  const cacheBuster = `v=${Math.floor(Date.now() / 600000)}`;
  const params = new URLSearchParams(location.search);
  const requestedChannel = params.get('channel') || 'male';
  const currentChannel = CHANNELS[requestedChannel] ? requestedChannel : 'male';
  const channelConfig = CHANNELS[currentChannel];
  const categoryButtons = document.getElementById('trend-category-buttons');
  const subtitle = document.getElementById('trend-subtitle');
  const rangeButtons = document.querySelectorAll('.seg-btn[data-days]');
  const backLink = document.querySelector('.back-link');
  const els = {
    marketSummary: document.getElementById('market-summary'),
    marketSource: document.getElementById('market-source'),
    hotGenres: document.getElementById('hot-genre-list'),
    hotTypes: document.getElementById('hot-type-list'),
    hotThemes: document.getElementById('hot-theme-list'),
    reads: document.getElementById('reads-list'),
    risers: document.getElementById('risers-list'),
    newBooks: document.getElementById('new-books-list'),
    summaries: document.getElementById('summary-feed'),
  };
  let latest = null;
  let trendRows = [];
  let categories = [];
  let selectedCategory = '';
  let selectedDays = 7;

  document.body.dataset.channel = currentChannel;
  document.title = `类型风向标 · 番茄${channelConfig.label}新书榜`;
  backLink.href = `index.html?channel=${encodeURIComponent(currentChannel)}`;

  init();

  async function init() {
    try {
      const [datesData, latestData, marketData] = await Promise.all([
        fetchChannelJson('dates.json').catch(() => ({ dates: [] })),
        fetchChannelJson('latest_ranks.json'),
        fetchChannelJson('market_summary.json').catch(() => null),
      ]);
      latest = latestData;
      latest.market_summary = marketData || latest.market_summary || {};
      categories = (latest.categories || []).map(category => category.name);
      const dates = (datesData.dates || []).slice().sort();
      const rows = await Promise.all(dates.map(date => fetchChannelJson(`trends/${date}.json`).catch(() => null)));
      trendRows = rows.filter(Boolean).sort((a, b) => a.date.localeCompare(b.date));
      selectedCategory = params.get('type') || '';
      if (!categories.includes(selectedCategory)) selectedCategory = categories[0] || '';
      bindEvents();
      renderCategoryButtons();
      render();
    } catch (error) {
      console.error(error);
      renderEmpty('趋势数据加载失败。');
    }
  }

  function bindEvents() {
    rangeButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        rangeButtons.forEach(item => item.classList.remove('active'));
        btn.classList.add('active');
        selectedDays = btn.dataset.days === 'all' ? 'all' : Number(btn.dataset.days);
        render();
      });
    });
  }

  function renderCategoryButtons() {
    categoryButtons.innerHTML = categories.map(name => (
      `<button class="category-chip ${name === selectedCategory ? 'active' : ''}" type="button" data-type="${escapeAttr(name)}">${escapeHtml(name)}</button>`
    )).join('');
    categoryButtons.querySelectorAll('.category-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        selectedCategory = btn.dataset.type;
        history.replaceState(null, '', `?channel=${encodeURIComponent(currentChannel)}&type=${encodeURIComponent(selectedCategory)}`);
        renderCategoryButtons();
        render();
      });
    });
  }

  function render() {
    const rows = getWindowRows();
    const categoryRows = rows.map(row => ({
      date: row.date,
      trend: row.trends && row.trends[selectedCategory],
    })).filter(row => row.trend);

    if (!categoryRows.length) {
      renderEmpty(`${channelConfig.label} · ${selectedCategory || '当前分类'} 暂无趋势数据。`);
      return;
    }

    subtitle.textContent = `${channelConfig.title} · ${selectedCategory} · ${categoryRows[0].date} 至 ${categoryRows[categoryRows.length - 1].date}`;
    renderMarket(rows);
    renderList(els.reads, collectReads(categoryRows));
    renderList(els.risers, collectRisers(categoryRows));
    renderList(els.newBooks, collectNewBooks(categoryRows));
    renderSummaries(categoryRows);
  }

  function getWindowRows() {
    if (selectedDays === 'all') return trendRows;
    return trendRows.slice(-selectedDays);
  }

  function renderMarket(rows) {
    const key = selectedDays === 'all' ? 'all' : String(selectedDays);
    const period = latest.market_summary && latest.market_summary.periods && latest.market_summary.periods[key];
    const fallback = collectFallbackMarket(rows);
    const hotGenres = period && period.hot_genres && period.hot_genres.length ? period.hot_genres : fallback.hotGenres;
    const hotTypes = period && period.hot_types && period.hot_types.length ? period.hot_types : fallback.hotTypes;
    const hotThemes = period && period.hot_themes && period.hot_themes.length ? period.hot_themes : fallback.hotThemes;
    els.marketSummary.textContent = period ? period.summary : fallback.summary;
    els.marketSource.textContent = period ? `${channelConfig.label} · ${period.source || 'rule'} · ${period.period}` : `${channelConfig.label} · 规则统计`;
    els.hotGenres.innerHTML = renderHotRows(hotGenres, 'categories');
    els.hotTypes.innerHTML = renderHotRows(hotTypes, 'type');
    els.hotThemes.innerHTML = hotThemes.length ? hotThemes.slice(0, 16).map(item => `<span class="theme-chip">${escapeHtml(item.name)} <small>${item.count || item.category_count || ''}</small></span>`).join('') : '<p class="muted-line">暂无题材信号。</p>';
    els.hotTypes.querySelectorAll('.hot-row').forEach(row => {
      row.addEventListener('click', () => {
        if (categories.includes(row.dataset.type)) {
          selectedCategory = row.dataset.type;
          history.replaceState(null, '', `?channel=${encodeURIComponent(currentChannel)}&type=${encodeURIComponent(selectedCategory)}`);
          renderCategoryButtons();
          render();
        }
      });
    });
  }

  function renderHotRows(items, kind) {
    if (!items || !items.length) return '<p class="muted-line">暂无数据。</p>';
    return items.slice(0, 7).map((item, index) => {
      const value = formatReads(item.read_growth_total || 0);
      const detail = kind === 'categories' ? (item.categories || []).join(' / ') : `新增 ${item.new_count || 0} · 增长作品 ${item.read_count || 0}`;
      return `<button class="hot-row" type="button" data-type="${escapeAttr(item.name)}"><span>${index + 1}</span><div><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(detail)}</small></div><em>${value}</em></button>`;
    }).join('');
  }

  function collectFallbackMarket(rows) {
    const typeScores = new Map();
    const themes = new Map();
    rows.forEach(row => {
      Object.entries(row.trends || {}).forEach(([name, trend]) => {
        const item = typeScores.get(name) || { name, read_growth_total: 0, read_count: 0, new_count: 0 };
        (trend.reads_growth || []).forEach(g => {
          item.read_growth_total += parseReadsGrowth(g.growth);
          item.read_count += 1;
        });
        item.new_count += Number(trend.new_count || 0);
        (trend.hot_themes || []).forEach(theme => {
          const current = themes.get(theme) || { name: theme, count: 0 };
          current.count += 1;
          themes.set(theme, current);
        });
        typeScores.set(name, item);
      });
    });
    const hotTypes = Array.from(typeScores.values()).sort((a, b) => b.read_growth_total - a.read_growth_total);
    const hotThemes = Array.from(themes.values()).sort((a, b) => b.count - a.count);
    return {
      hotGenres: [],
      hotTypes,
      hotThemes,
      summary: hotTypes.length ? `当前窗口内 ${hotTypes.slice(0, 3).map(item => item.name).join('、')} 更活跃。` : '暂无足够数据判断热点。',
    };
  }

  function collectReads(rows) {
    const map = new Map();
    rows.forEach(row => (row.trend.reads_growth || []).forEach(item => {
      const current = map.get(item.title) || { title: item.title, score: 0, dates: [] };
      current.score += parseReadsGrowth(item.growth);
      current.dates.push(`${row.date} ${item.growth}`);
      map.set(item.title, current);
    }));
    return Array.from(map.values()).sort((a, b) => b.score - a.score).slice(0, 10).map(item => ({
      title: item.title,
      meta: item.dates.slice(-2).join(' / '),
      value: formatReads(item.score),
    }));
  }

  function collectRisers(rows) {
    const map = new Map();
    rows.forEach(row => (row.trend.top_risers || []).forEach(item => {
      const current = map.get(item.title) || { title: item.title, score: 0, dates: [] };
      current.score += parseChange(item.change);
      current.dates.push(`${row.date} ${item.change}`);
      map.set(item.title, current);
    }));
    return Array.from(map.values()).sort((a, b) => b.score - a.score).slice(0, 10).map(item => ({
      title: item.title,
      meta: item.dates.slice(-2).join(' / '),
      value: `+${item.score}`,
    }));
  }

  function collectNewBooks(rows) {
    const items = [];
    rows.slice().reverse().forEach(row => (row.trend.new_books || []).forEach(title => items.push({ title, meta: row.date, value: '新上榜' })));
    return items.slice(0, 12);
  }

  function renderList(container, items) {
    if (!items.length) {
      container.innerHTML = '<p class="muted-line">暂无明显信号。</p>';
      return;
    }
    const bookMap = buildLatestBookMap();
    container.innerHTML = items.map(item => {
      const book = bookMap.get(item.title) || {};
      return `<a class="compact-row" href="${bookHref(book, item.title)}"><div><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.meta)}</small></div><span>${escapeHtml(item.value)}</span></a>`;
    }).join('');
  }

  function renderSummaries(rows) {
    const summaries = rows.slice().reverse().filter(row => row.trend.summary_markdown || row.trend.summary).slice(0, 10);
    els.summaries.innerHTML = summaries.length ? summaries.map(row => `<article class="summary-item"><time>${escapeHtml(row.date)}</time><div>${renderMarkdown(row.trend.summary_markdown || row.trend.summary)}</div></article>`).join('') : '<p class="muted-line">暂无摘要。</p>';
  }

  function buildLatestBookMap() {
    const map = new Map();
    (latest.categories || []).forEach(category => (category.books || []).forEach(book => map.set(book.title, book)));
    return map;
  }

  function bookHref(book, fallbackTitle) {
    const query = new URLSearchParams({ channel: currentChannel });
    const bookId = extractBookId(book.url);
    if (bookId) query.set('id', bookId);
    else query.set('title', book.title || fallbackTitle || '');
    return `book.html?${query.toString()}`;
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
    subtitle.textContent = message;
    Object.values(els).forEach(el => { el.innerHTML = `<p class="muted-line">${escapeHtml(message)}</p>`; });
  }
});

function parseChange(value) { return Number(String(value || '0').replace('+', '')) || 0; }
function parseReadsGrowth(value) {
  const raw = String(value || '0').replace('+', '').replace(',', '').trim();
  const n = parseFloat(raw);
  if (Number.isNaN(n)) return 0;
  if (raw.includes('亿')) return n * 100000000;
  if (raw.includes('万')) return n * 10000;
  return n;
}
function formatReads(value) {
  if (Math.abs(value) >= 100000000) return `+${(value / 100000000).toFixed(1)}亿`;
  if (Math.abs(value) >= 10000) return `+${(value / 10000).toFixed(1)}万`;
  return `+${Math.round(value)}`;
}
function fetchJson(url) {
  return fetch(url).then(response => {
    if (!response.ok) throw new Error(`Failed to load ${url}`);
    return response.json();
  });
}
function renderMarkdown(text) {
  let html = escapeHtml(text || '');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/《(.+?)》/g, '<span class="book-mark">《$1》</span>');
  html = html.replace(/\n/g, '<br>');
  return html;
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
