document.addEventListener('DOMContentLoaded', () => {
  const categoryList = document.getElementById('category-list');
  const waterfall = document.getElementById('books-waterfall');
  const updateDate = document.getElementById('update-date');
  const categoryTitle = document.getElementById('current-category-title');
  const sourceLine = document.getElementById('source-line');
  const signalSource = document.getElementById('signal-source');
  const aiContent = document.getElementById('ai-content');
  const sidebar = document.getElementById('sidebar');
  const menuBtn = document.getElementById('mobile-menu-btn');
  const overlay = document.getElementById('sidebar-overlay');
  const dateDisplay = document.getElementById('date-display');
  const dateInput = document.getElementById('date-input');
  const datePickerBtn = document.getElementById('date-picker-btn');
  const prevBtn = document.getElementById('date-prev');
  const nextBtn = document.getElementById('date-next');
  const presetBtns = document.querySelectorAll('.seg-btn[data-preset]');
  const cacheBuster = `v=${Math.floor(Date.now() / 600000)}`;

  let data = null;
  let dates = [];
  let currentDateIndex = -1;
  let currentCategory = '';

  const toast = document.createElement('div');
  toast.className = 'copy-toast';
  toast.textContent = '书本信息已复制';
  document.body.appendChild(toast);
  let toastTimer = null;

  menuBtn.addEventListener('click', () => {
    sidebar.classList.add('open');
    overlay.classList.add('show');
  });
  overlay.addEventListener('click', closeSidebar);
  datePickerBtn.addEventListener('click', () => dateInput.showPicker ? dateInput.showPicker() : dateInput.click());
  prevBtn.addEventListener('click', () => switchDate(currentDateIndex - 1));
  nextBtn.addEventListener('click', () => switchDate(currentDateIndex + 1));
  dateInput.addEventListener('change', () => {
    const idx = dates.indexOf(dateInput.value);
    if (idx >= 0) switchDate(idx);
    else showToast(`${dateInput.value} 暂无数据`);
  });
  presetBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const preset = btn.dataset.preset;
      if (preset === 'latest') switchDate(dates.length - 1);
      if (preset === 'previous') switchDate(Math.max(0, dates.length - 2));
    });
  });

  init();

  async function init() {
    try {
      const dateIndex = await fetchJson(`data/dates.json?${cacheBuster}`).catch(() => ({ dates: [] }));
      dates = (dateIndex.dates || []).slice().sort();
      data = await fetchJson(`data/latest_ranks.json?${cacheBuster}`);
      if (!dates.includes(data.date)) dates.push(data.date);
      dates = Array.from(new Set(dates)).sort();
      currentDateIndex = dates.indexOf(data.date);
      applyData(data);
    } catch (error) {
      console.error(error);
      waterfall.innerHTML = '<div class="empty-state">数据加载失败，请稍后刷新。</div>';
    }
  }

  async function switchDate(index) {
    if (index < 0 || index >= dates.length) return;
    currentDateIndex = index;
    const selected = dates[index];
    try {
      if (index === dates.length - 1) {
        data = await fetchJson(`data/latest_ranks.json?${cacheBuster}`);
      } else {
        const raw = await fetchJson(`data/raw/${selected}.json?${cacheBuster}`);
        const trend = await fetchJson(`data/trends/${selected}.json?${cacheBuster}`).catch(() => ({ trends: {}, source: {} }));
        data = {
          date: raw.date,
          prev_date: trend.prev_date || '',
          timezone: raw.timezone,
          generated_at: raw.generated_at,
          source: trend.source || raw.source || {},
          categories: (raw.categories || []).map(category => ({
            name: category.name,
            trend: (trend.trends || {})[category.name] || {},
            books: category.books || [],
          })),
        };
      }
      applyData(data);
    } catch (error) {
      console.error(error);
      showToast(`${selected} 数据不可用`);
    }
  }

  function applyData(nextData) {
    updateDate.textContent = nextData.prev_date ? `${nextData.date} 对比 ${nextData.prev_date}` : nextData.date;
    dateDisplay.textContent = nextData.date;
    dateInput.min = dates[0] || '';
    dateInput.max = dates[dates.length - 1] || '';
    dateInput.value = nextData.date;
    prevBtn.disabled = currentDateIndex <= 0;
    nextBtn.disabled = currentDateIndex >= dates.length - 1;
    updatePresetButtons();
    renderCategories();
    const exists = currentCategory && nextData.categories.some(category => category.name === currentCategory);
    selectCategory(exists ? currentCategory : (nextData.categories[0] && nextData.categories[0].name));
    const analysis = nextData.source && nextData.source.analysis ? nextData.source.analysis : '未知分析';
    sourceLine.textContent = `${nextData.timezone || 'Asia/Shanghai'} · ${analysis}`;
    signalSource.textContent = analysis;
  }

  function updatePresetButtons() {
    presetBtns.forEach(btn => {
      const preset = btn.dataset.preset;
      const active = (preset === 'latest' && currentDateIndex === dates.length - 1)
        || (preset === 'previous' && currentDateIndex === dates.length - 2);
      btn.classList.toggle('active', active);
    });
  }

  function renderCategories() {
    categoryList.innerHTML = '';
    (data.categories || []).forEach((category, index) => {
      const li = document.createElement('li');
      li.dataset.category = category.name;
      li.innerHTML = `<span>${escapeHtml(category.name)}</span>`;
      const newCount = Number(category.trend && category.trend.new_count || 0);
      if (newCount > 0) {
        const badge = document.createElement('span');
        badge.className = 'cat-badge';
        badge.textContent = `+${newCount}`;
        li.appendChild(badge);
      }
      if ((!currentCategory && index === 0) || category.name === currentCategory) li.classList.add('active');
      li.addEventListener('click', () => {
        selectCategory(category.name);
        closeSidebar();
      });
      categoryList.appendChild(li);
    });
  }

  function selectCategory(name) {
    if (!name) return;
    currentCategory = name;
    const category = data.categories.find(item => item.name === name);
    if (!category) return;
    categoryTitle.textContent = name;
    document.querySelectorAll('#category-list li').forEach(li => li.classList.toggle('active', li.dataset.category === name));
    renderTrend(category);
    renderBooks(category);
  }

  function renderTrend(category) {
    const trend = category.trend || {};
    const summary = trend.summary_markdown || trend.summary || '暂无分析数据。';
    aiContent.innerHTML = renderMarkdown(summary);
  }

  function renderBooks(category) {
    waterfall.innerHTML = '';
    const books = category.books || [];
    if (!books.length) {
      waterfall.innerHTML = '<div class="empty-state">该分类暂无书籍。</div>';
      return;
    }
    const changeMap = buildChangeMap(category.trend || {});
    const fragment = document.createDocumentFragment();
    books.forEach((book, index) => {
      const rank = index + 1;
      const card = document.createElement('a');
      const bookId = extractBookId(book.url);
      card.className = 'book-card';
      card.href = bookId ? `book.html?id=${encodeURIComponent(bookId)}` : `book.html?title=${encodeURIComponent(book.title)}`;
      card.innerHTML = `
        <span class="book-rank ${rank <= 3 ? `rank-${rank}` : ''}">${rank}</span>
        ${changeBadge(book.title, changeMap)}
        <div class="book-cover">${book.cover ? `<img src="${escapeAttr(book.cover)}" alt="${escapeAttr(book.title)}" loading="lazy">` : '<div class="no-cover">暂无封面</div>'}</div>
        <div class="book-info">
          <h3 class="book-title" title="${escapeAttr(book.title)}">${escapeHtml(book.title)}</h3>
          <div class="book-meta"><span>${escapeHtml(book.author || '未知')}</span><span class="book-reads">${escapeHtml(book.reads || '未知')}</span></div>
          <p class="book-intro">${escapeHtml(book.intro || '暂无简介')}</p>
          <button class="book-copy-btn" type="button">复制信息</button>
        </div>
      `;
      card.querySelector('.book-copy-btn').addEventListener('click', event => copyBook(event, book));
      fragment.appendChild(card);
    });
    waterfall.appendChild(fragment);
  }

  function buildChangeMap(trend) {
    const map = new Map();
    (trend.new_books || []).forEach(title => map.set(title, 'new'));
    (trend.top_risers || []).forEach(item => map.set(item.title, item.change));
    (trend.top_fallers || []).forEach(item => map.set(item.title, item.change));
    return map;
  }

  function changeBadge(title, map) {
    const value = map.get(title);
    if (!value) return '';
    if (value === 'new') return '<span class="book-change new">NEW</span>';
    if (String(value).startsWith('+')) return `<span class="book-change up">↑${escapeHtml(value)}</span>`;
    if (String(value).startsWith('-')) return `<span class="book-change down">↓${escapeHtml(String(value).replace('-', ''))}</span>`;
    return '';
  }

  function copyBook(event, book) {
    event.preventDefault();
    event.stopPropagation();
    const text = `${book.title}\n作者：${book.author || '未知'}\n在读：${book.reads || '未知'}\n简介：${book.intro || '无'}\n链接：${book.url || '无'}`;
    copyText(text).then(() => {
      const btn = event.currentTarget;
      btn.classList.add('copied');
      btn.textContent = '已复制';
      showToast('书本信息已复制');
      setTimeout(() => {
        btn.classList.remove('copied');
        btn.textContent = '复制信息';
      }, 1400);
    });
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
  }

  function showToast(message) {
    toast.textContent = message;
    if (toastTimer) clearTimeout(toastTimer);
    toast.classList.add('show');
    toastTimer = setTimeout(() => toast.classList.remove('show'), 1800);
  }
});

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
