const CHANNELS = {
  male: {
    key: 'male',
    label: '男频',
    title: '男频新书榜',
    lead: '强设定、升级线和爽点密度',
  },
  female: {
    key: 'female',
    label: '女频',
    title: '女频新书榜',
    lead: '情绪张力、关系线和题材包装',
  },
};

document.addEventListener('DOMContentLoaded', () => {
  const categoryList = document.getElementById('category-list');
  const waterfall = document.getElementById('books-waterfall');
  const updateDate = document.getElementById('update-date');
  const categoryTitle = document.getElementById('current-category-title');
  const sourceLine = document.getElementById('source-line');
  const signalSource = document.getElementById('signal-source');
  const aiContent = document.getElementById('ai-content');
  const featureBook = document.getElementById('feature-book');
  const categoryStats = document.getElementById('category-stats');
  const topStack = document.getElementById('top-stack');
  const sidebar = document.getElementById('sidebar');
  const menuBtn = document.getElementById('mobile-menu-btn');
  const overlay = document.getElementById('sidebar-overlay');
  const dateDisplay = document.getElementById('date-display');
  const dateInput = document.getElementById('date-input');
  const datePickerBtn = document.getElementById('date-picker-btn');
  const prevBtn = document.getElementById('date-prev');
  const nextBtn = document.getElementById('date-next');
  const presetBtns = document.querySelectorAll('.seg-btn[data-preset]');
  const trendLink = document.getElementById('trend-link');
  const topbarActions = document.querySelector('.topbar-actions');
  const cacheBuster = `v=${Math.floor(Date.now() / 600000)}`;
  const params = new URLSearchParams(location.search);
  const requestedChannel = params.get('channel');
  const currentChannel = CHANNELS[requestedChannel] ? requestedChannel : '';
  const requestedCategory = params.get('type') || params.get('category') || '';

  let data = null;
  let dates = [];
  let currentDateIndex = -1;
  let currentCategory = requestedCategory;

  const toast = document.createElement('div');
  toast.className = 'copy-toast';
  toast.textContent = '书本信息已复制';
  document.body.appendChild(toast);
  let toastTimer = null;

  const channelSwitch = document.createElement('div');
  channelSwitch.className = 'channel-switch';
  topbarActions.prepend(channelSwitch);

  if (currentChannel) document.body.dataset.channel = currentChannel;
  else document.body.classList.add('overview-mode');

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
    renderChannelSwitch();
    if (!currentChannel) {
      await initOverview();
      return;
    }
    await initChannel();
  }

  async function initOverview() {
    try {
      const reports = (await Promise.all(Object.keys(CHANNELS).map(async channel => {
        const latest = await fetchChannelJson(channel, 'latest_ranks.json').catch(() => null);
        return latest ? { channel, config: CHANNELS[channel], latest } : null;
      }))).filter(Boolean);

      if (!reports.length) {
        renderLoadError('暂无频道数据，请先运行采集任务。');
        return;
      }
      renderOverview(reports);
    } catch (error) {
      console.error(error);
      renderLoadError('频道总览加载失败，请稍后刷新。');
    }
  }

  async function initChannel() {
    try {
      const dateIndex = await fetchChannelJson(currentChannel, 'dates.json').catch(() => ({ dates: [] }));
      dates = (dateIndex.dates || []).slice().sort();
      data = await fetchChannelJson(currentChannel, 'latest_ranks.json');
      if (!dates.includes(data.date)) dates.push(data.date);
      dates = Array.from(new Set(dates)).sort();
      currentDateIndex = dates.indexOf(data.date);
      applyData(data);
    } catch (error) {
      console.error(error);
      renderLoadError('数据加载失败，请稍后刷新。');
    }
  }

  async function switchDate(index) {
    if (!currentChannel || index < 0 || index >= dates.length) return;
    currentDateIndex = index;
    const selected = dates[index];
    try {
      const latest = data && data.date === selected ? data : await fetchChannelJson(currentChannel, 'latest_ranks.json');
      if (selected === latest.date) {
        data = latest;
      } else {
        const raw = await fetchChannelJson(currentChannel, `raw/${selected}.json`);
        const trend = await fetchChannelJson(currentChannel, `trends/${selected}.json`).catch(() => ({ trends: {}, source: {} }));
        data = {
          channel: currentChannel,
          channel_label: CHANNELS[currentChannel].label,
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
    const channelConfig = CHANNELS[currentChannel];
    document.title = `番茄${channelConfig.label}新书榜 · 风向标`;
    updateDate.textContent = nextData.prev_date ? `${nextData.date} 对比 ${nextData.prev_date}` : nextData.date;
    dateDisplay.textContent = nextData.date;
    dateInput.min = dates[0] || '';
    dateInput.max = dates[dates.length - 1] || '';
    dateInput.value = nextData.date;
    prevBtn.disabled = currentDateIndex <= 0;
    nextBtn.disabled = currentDateIndex >= dates.length - 1;
    trendLink.href = `trend.html?channel=${encodeURIComponent(currentChannel)}`;
    trendLink.textContent = `${channelConfig.label}趋势`;
    updatePresetButtons();
    renderCategories();
    const hasRequested = currentCategory && nextData.categories.some(category => category.name === currentCategory);
    const fallbackCategory = nextData.categories[0] && nextData.categories[0].name;
    selectCategory(hasRequested ? currentCategory : fallbackCategory);
    const analysis = nextData.source && nextData.source.analysis ? nextData.source.analysis : '未知分析';
    sourceLine.textContent = `${channelConfig.title} · ${nextData.timezone || 'Asia/Shanghai'} · ${analysis}`;
    signalSource.textContent = `${channelConfig.label} · ${analysis}`;
  }

  function renderOverview(reports) {
    document.title = '番茄新书榜 · 双频道风向标';
    categoryTitle.textContent = '频道总览';
    updateDate.textContent = reports.map(item => `${item.config.label} ${item.latest.date}`).join(' · ');
    sourceLine.textContent = '男频和女频独立采集、独立分析，点击频道进入榜单。';
    signalSource.textContent = '双频道总览';
    dateDisplay.textContent = '总览';
    renderOverviewNav(reports);
    renderOverviewHero(reports);
    renderOverviewSignal(reports);
    renderOverviewBooks(reports);
  }

  function renderOverviewNav(reports) {
    categoryList.innerHTML = reports.map(item => {
      const categories = item.latest.categories || [];
      const bookCount = categories.reduce((sum, category) => sum + (category.books || []).length, 0);
      return `
        <li class="channel-nav-item" data-channel="${escapeAttr(item.channel)}">
          <span>${escapeHtml(item.config.title)}</span>
          <small>${bookCount}本</small>
          <em>${escapeHtml(item.latest.date)}</em>
        </li>
      `;
    }).join('');
    categoryList.querySelectorAll('.channel-nav-item').forEach(li => {
      li.addEventListener('click', () => {
        location.href = `index.html?channel=${encodeURIComponent(li.dataset.channel)}`;
      });
    });
  }

  function renderOverviewHero(reports) {
    const totalCategories = reports.reduce((sum, item) => sum + (item.latest.categories || []).length, 0);
    const totalBooks = reports.reduce((sum, item) => sum + countBooks(item.latest), 0);
    featureBook.innerHTML = `
      <div class="overview-cards">
        ${reports.map(renderChannelCard).join('')}
      </div>
    `;
    categoryStats.innerHTML = `
      <div class="stat-tile red"><strong>${reports.length}</strong><span>追踪频道</span></div>
      <div class="stat-tile blue"><strong>${totalCategories}</strong><span>分类赛道</span></div>
      <div class="stat-tile green"><strong>${totalBooks}</strong><span>上榜作品</span></div>
    `;
    topStack.innerHTML = `
      <div class="stack-heading"><span>频道入口</span><em>独立榜单 / 趋势 / 详情</em></div>
      ${reports.map(item => {
        const top = pickTopBooks(item.latest, 1)[0];
        const href = `index.html?channel=${encodeURIComponent(item.channel)}`;
        return `
          <a class="stack-book" href="${href}">
            <span class="stack-rank">${escapeHtml(item.config.label.slice(0, 1))}</span>
            <div class="stack-cover">${top && top.cover ? `<img src="${escapeAttr(top.cover)}" alt="${escapeAttr(top.title)}">` : '<div class="no-cover">无</div>'}</div>
            <div>
              <strong>${escapeHtml(item.config.title)}</strong>
              <small>${escapeHtml(top ? `${top.title} · ${top.reads || '未知'}` : item.config.lead)}</small>
              <div class="book-heat"><span style="width:80%"></span></div>
            </div>
          </a>
        `;
      }).join('')}
    `;
  }

  function renderChannelCard(item) {
    const categories = item.latest.categories || [];
    const topBooks = pickTopBooks(item.latest, 4);
    const themes = collectThemes(item.latest).slice(0, 6);
    const analysis = item.latest.source && item.latest.source.analysis ? item.latest.source.analysis : '未知分析';
    return `
      <a class="channel-card channel-card-${escapeAttr(item.channel)}" href="index.html?channel=${encodeURIComponent(item.channel)}">
        <div class="channel-card-main">
          <span class="panel-kicker">${escapeHtml(item.config.label)}频道</span>
          <h3>${escapeHtml(item.config.title)}</h3>
          <p>${escapeHtml(item.config.lead)}</p>
          <div class="channel-metrics">
            <span><strong>${categories.length}</strong><small>分类</small></span>
            <span><strong>${countBooks(item.latest)}</strong><small>作品</small></span>
            <span><strong>${escapeHtml(item.latest.date || '-')}</strong><small>日期</small></span>
          </div>
          <div class="tag-row">${themes.length ? themes.map(theme => `<span>${escapeHtml(theme)}</span>`).join('') : '<span>题材待观察</span>'}</div>
          <em>${escapeHtml(analysis)}</em>
        </div>
        <div class="channel-cover-wall">
          ${topBooks.map(book => `<div>${book.cover ? `<img src="${escapeAttr(book.cover)}" alt="${escapeAttr(book.title)}">` : '<span>暂无封面</span>'}</div>`).join('')}
        </div>
      </a>
    `;
  }

  function renderOverviewSignal(reports) {
    const lines = reports.map(item => {
      const period = item.latest.market_summary && item.latest.market_summary.periods && (
        item.latest.market_summary.periods['7'] || item.latest.market_summary.periods.all
      );
      const summary = period && period.summary ? period.summary : `${item.config.title}已有 ${countBooks(item.latest)} 本样本。`;
      return `**${item.config.label}**：${summary}`;
    });
    aiContent.innerHTML = renderMarkdown(lines.join('\n'));
  }

  function renderOverviewBooks(reports) {
    const cards = [];
    reports.forEach(item => {
      (item.latest.categories || []).slice(0, 6).forEach(category => {
        const top = category.books && category.books[0];
        cards.push({ item, category, top });
      });
    });
    waterfall.innerHTML = cards.length ? cards.map(({ item, category, top }) => {
      const themes = ((category.trend && category.trend.hot_themes) || category.hot_themes || []).slice(0, 4);
      const href = `index.html?channel=${encodeURIComponent(item.channel)}&type=${encodeURIComponent(category.name)}`;
      return `
        <a class="overview-category-card" href="${href}">
          <div class="overview-category-cover">${top && top.cover ? `<img src="${escapeAttr(top.cover)}" alt="${escapeAttr(top.title)}" loading="lazy">` : '<div class="no-cover">暂无封面</div>'}</div>
          <div>
            <span class="panel-kicker">${escapeHtml(item.config.label)} · ${escapeHtml(category.name)}</span>
            <h3>${escapeHtml(top ? top.title : category.name)}</h3>
            <p>${escapeHtml(top ? `${top.author || '未知'} · ${top.reads || '未知'}` : '暂无榜首')}</p>
            ${renderTags(themes)}
          </div>
        </a>
      `;
    }).join('') : '<div class="empty-state">暂无可展示分类。</div>';
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
      const top = category.books && category.books[0];
      li.innerHTML = `
        <span>${escapeHtml(category.name)}</span>
        <small>${escapeHtml(top && top.reads ? top.reads : `${(category.books || []).length}本`)}</small>
      `;
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
        history.replaceState(null, '', `?channel=${encodeURIComponent(currentChannel)}&type=${encodeURIComponent(category.name)}`);
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
    categoryTitle.textContent = `${CHANNELS[currentChannel].label} · ${name}`;
    document.querySelectorAll('#category-list li').forEach(li => li.classList.toggle('active', li.dataset.category === name));
    renderHero(category);
    renderTrend(category);
    renderBooks(category);
  }

  function renderHero(category) {
    const books = category.books || [];
    const top = books[0];
    const trend = category.trend || {};
    const hotThemes = (trend.hot_themes || category.hot_themes || []).slice(0, 6);
    const maxReads = Math.max(...books.map(book => parseReadsValue(book.reads)), 1);
    if (!top) {
      featureBook.innerHTML = '<div class="empty-state">该分类暂无榜首作品。</div>';
      categoryStats.innerHTML = '';
      topStack.innerHTML = '';
      return;
    }
    featureBook.innerHTML = `
      <a class="feature-cover" href="${bookHref(top)}">
        ${top.cover ? `<img src="${escapeAttr(top.cover)}" alt="${escapeAttr(top.title)}">` : '<div class="no-cover">暂无封面</div>'}
        <span class="feature-rank">#1</span>
      </a>
      <div class="feature-content">
        <div class="feature-label">${escapeHtml(CHANNELS[currentChannel].label)}榜首 · ${escapeHtml(category.name)}</div>
        <h3>${escapeHtml(top.title)}</h3>
        <div class="feature-meta"><span>${escapeHtml(top.author || '未知作者')}</span><strong>${escapeHtml(top.reads || '未知')}</strong></div>
        ${renderTags(extractTags(top).slice(0, 5))}
        <p>${escapeHtml(top.intro || '暂无简介')}</p>
        <div class="feature-heat"><span style="width:${heatWidth(top.reads, maxReads)}%"></span></div>
      </div>
    `;
    categoryStats.innerHTML = `
      <div class="stat-tile red"><strong>${books.length}</strong><span>上榜作品</span></div>
      <div class="stat-tile blue"><strong>${escapeHtml(top.reads || '未知')}</strong><span>榜首在读</span></div>
      <div class="stat-tile green"><strong>${hotThemes.length || '-'}</strong><span>热词信号</span></div>
    `;
    topStack.innerHTML = `
      <div class="stack-heading"><span>Top 5 快扫</span><em>${escapeHtml(hotThemes.slice(0, 3).join(' / ') || '首日观察')}</em></div>
      ${books.slice(1, 5).map((book, index) => renderStackBook(book, index + 2, maxReads)).join('')}
    `;
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
    const maxReads = Math.max(...books.map(book => parseReadsValue(book.reads)), 1);
    const changeMap = buildChangeMap(category.trend || {});
    const fragment = document.createDocumentFragment();
    books.forEach((book, index) => {
      const rank = index + 1;
      const card = document.createElement('a');
      card.className = 'book-card';
      card.href = bookHref(book);
      card.innerHTML = `
        <span class="book-rank ${rank <= 3 ? `rank-${rank}` : ''}">${rank}</span>
        ${changeBadge(book.title, changeMap)}
        <div class="book-cover">${book.cover ? `<img src="${escapeAttr(book.cover)}" alt="${escapeAttr(book.title)}" loading="lazy">` : '<div class="no-cover">暂无封面</div>'}</div>
        <div class="book-info">
          <h3 class="book-title" title="${escapeAttr(book.title)}">${escapeHtml(book.title)}</h3>
          <div class="book-meta"><span>${escapeHtml(book.author || '未知')}</span><span class="book-reads">${escapeHtml(book.reads || '未知')}</span></div>
          ${renderTags(extractTags(book).slice(0, 4))}
          <p class="book-intro">${escapeHtml(book.intro || '暂无简介')}</p>
          <div class="book-heat"><span style="width:${heatWidth(book.reads, maxReads)}%"></span></div>
          <button class="book-copy-btn" type="button">复制信息</button>
        </div>
      `;
      card.querySelector('.book-copy-btn').addEventListener('click', event => copyBook(event, book));
      fragment.appendChild(card);
    });
    waterfall.appendChild(fragment);
  }

  function renderChannelSwitch() {
    channelSwitch.innerHTML = `
      <a class="channel-link ${!currentChannel ? 'active' : ''}" href="index.html">总览</a>
      ${Object.values(CHANNELS).map(channel => (
        `<a class="channel-link ${currentChannel === channel.key ? 'active' : ''}" href="index.html?channel=${encodeURIComponent(channel.key)}">${escapeHtml(channel.label)}</a>`
      )).join('')}
    `;
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

  function renderStackBook(book, rank, maxReads) {
    return `
      <a class="stack-book" href="${bookHref(book)}">
        <span class="stack-rank">${rank}</span>
        <div class="stack-cover">${book.cover ? `<img src="${escapeAttr(book.cover)}" alt="${escapeAttr(book.title)}">` : '<div class="no-cover">无</div>'}</div>
        <div>
          <strong>${escapeHtml(book.title)}</strong>
          <small>${escapeHtml(book.author || '未知')} · ${escapeHtml(book.reads || '未知')}</small>
          <div class="book-heat"><span style="width:${heatWidth(book.reads, maxReads)}%"></span></div>
        </div>
      </a>
    `;
  }

  function bookHref(book) {
    const params = new URLSearchParams({ channel: currentChannel });
    const bookId = extractBookId(book.url);
    if (bookId) params.set('id', bookId);
    else params.set('title', book.title || '');
    return `book.html?${params.toString()}`;
  }

  function renderLoadError(message) {
    waterfall.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
    featureBook.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
    aiContent.textContent = message;
  }

  function countBooks(payload) {
    return (payload.categories || []).reduce((sum, category) => sum + (category.books || []).length, 0);
  }

  function pickTopBooks(payload, limit) {
    const books = [];
    (payload.categories || []).forEach(category => (category.books || []).slice(0, 2).forEach(book => books.push(book)));
    return books.sort((a, b) => parseReadsValue(b.reads) - parseReadsValue(a.reads)).slice(0, limit);
  }

  function collectThemes(payload) {
    const themes = [];
    (payload.categories || []).forEach(category => {
      const trendThemes = category.trend && category.trend.hot_themes ? category.trend.hot_themes : category.hot_themes || [];
      trendThemes.forEach(theme => themes.push(theme));
    });
    return Array.from(new Set(themes));
  }

  async function fetchChannelJson(channel, path) {
    const channelPath = `data/channels/${channel}/${path}?${cacheBuster}`;
    try {
      return await fetchJson(channelPath);
    } catch (error) {
      if (channel === 'male') return fetchJson(`data/${path}?${cacheBuster}`);
      throw error;
    }
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

function extractTags(book) {
  const text = `${book.title || ''} ${book.intro || ''}`;
  const bracketTags = Array.from(text.matchAll(/[【\[]([^】\]]{1,10})[】\]]/g))
    .map(match => match[1].trim())
    .filter(Boolean);
  if (bracketTags.length) return Array.from(new Set(bracketTags));
  const keywords = [
    '无敌', '系统', '穿越', '重生', '多女主', '单女主', '无女主', '爽文',
    '都市', '玄幻', '修仙', '末世', '种田', '领主', '高武', '悬疑', '抗战',
    '同人', '游戏', '古言', '现言', '甜宠', '宫斗', '宅斗', '快穿', '豪门',
    '总裁', '婚恋', '年代', '女强', '团宠', '虐渣', '萌宝', '娱乐圈', '民国',
  ];
  return keywords.filter(keyword => text.includes(keyword)).slice(0, 5);
}

function renderTags(tags) {
  if (!tags || !tags.length) return '<div class="tag-row"><span>题材待观察</span></div>';
  return `<div class="tag-row">${tags.map(tag => `<span>${escapeHtml(tag)}</span>`).join('')}</div>`;
}

function parseReadsValue(value) {
  const raw = String(value || '').replace('在读', '').replace('：', '').replace(':', '').replace(',', '').trim();
  const n = parseFloat(raw);
  if (Number.isNaN(n)) return 0;
  if (raw.includes('亿')) return n * 100000000;
  if (raw.includes('万')) return n * 10000;
  return n;
}

function heatWidth(value, maxReads) {
  const ratio = Math.max(0.08, Math.min(1, parseReadsValue(value) / Math.max(maxReads || 1, 1)));
  return Math.round(ratio * 100);
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
