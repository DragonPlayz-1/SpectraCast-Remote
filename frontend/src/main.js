import './styles.css';
import brandMark from './assets/spectracast-mark.svg';

const demoMode = new URLSearchParams(window.location.search).get('demo') === '1';
const appRoot = document.querySelector('#app');
const API_TIMEOUT = 2200;

const iconPaths = {
  activity: '<path d="M3 12h3l2.2-6 3.6 12 2.2-6H21"/>',
  apps: '<rect x="3" y="3" width="7" height="7" rx="1.2"/><rect x="14" y="3" width="7" height="7" rx="1.2"/><rect x="3" y="14" width="7" height="7" rx="1.2"/><rect x="14" y="14" width="7" height="7" rx="1.2"/>',
  arrowDown: '<path d="m6 9 6 6 6-6"/>',
  arrowLeft: '<path d="m15 18-6-6 6-6"/>',
  arrowRight: '<path d="m9 18 6-6-6-6"/>',
  arrowUp: '<path d="m18 15-6-6-6 6"/>',
  back: '<path d="m15 18-6-6 6-6"/><path d="M9 12h10"/>',
  battery: '<rect x="3" y="6.5" width="15" height="11" rx="2"/><path d="M21 10v4"/><path d="M6.5 10v4"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  chevronDown: '<path d="m6 9 6 6 6-6"/>',
  chevronRight: '<path d="m9 18 6-6-6-6"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  close: '<path d="m6 6 12 12M18 6 6 18"/>',
  command: '<path d="M18 7a3 3 0 1 0-3-3v14a3 3 0 1 0 3-3H6a3 3 0 1 0 3 3V4a3 3 0 1 0-3 3h12Z"/>',
  headphones: '<path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M3 17a2 2 0 0 1 2-2h1v6H5a2 2 0 0 1-2-2v-2ZM21 17a2 2 0 0 0-2-2h-1v6h1a2 2 0 0 0 2-2v-2Z"/>',
  home: '<path d="m3 10 9-7 9 7"/><path d="M5 9v11h14V9"/><path d="M9 20v-6h6v6"/>',
  keyboard: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 9h.01M10 9h.01M13 9h.01M16 9h.01M7 13h.01M10 13h4M16 13h.01"/>',
  launch: '<path d="M14 5h5v5"/><path d="m19 5-8 8"/><path d="M19 13v5a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/>',
  lock: '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
  menu: '<path d="M4 6h16M4 12h16M4 18h16"/>',
  mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3M8 21h8"/>',
  moon: '<path d="M20.5 14.5A8.5 8.5 0 0 1 9.5 3.5 8.5 8.5 0 1 0 20.5 14.5Z"/>',
  more: '<circle cx="5" cy="12" r="1" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/><circle cx="19" cy="12" r="1" fill="currentColor" stroke="none"/>',
  pause: '<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>',
  play: '<path d="m8 5 11 7-11 7V5Z" fill="currentColor" stroke="none"/>',
  power: '<path d="M12 3v9"/><path d="M18.36 6.64a9 9 0 1 1-12.73 0"/>',
  refresh: '<path d="M20 11a8.1 8.1 0 0 0-14.9-3L3 11"/><path d="M3 5v6h6"/><path d="M4 13a8.1 8.1 0 0 0 14.9 3L21 13"/><path d="M21 19v-6h-6"/>',
  rewind: '<path d="m11 19-7-7 7-7"/><path d="m20 19-7-7 7-7"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
  send: '<path d="m22 2-7 20-4-9-9-4 20-7Z"/><path d="M22 2 11 13"/>',
  settings: '<path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-1.41 1.41-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.04 1.55v.09h-2v-.09A1.7 1.7 0 0 0 12.37 18a1.7 1.7 0 0 0-1.88.34l-.06.06-1.41-1.41.06-.06A1.7 1.7 0 0 0 9.42 15a1.7 1.7 0 0 0-1.55-1.04h-.09v-2h.09A1.7 1.7 0 0 0 9.42 11a1.7 1.7 0 0 0-.34-1.88l-.06-.06 1.41-1.41.06.06a1.7 1.7 0 0 0 1.88.34A1.7 1.7 0 0 0 13.41 6.5v-.09h2v.09A1.7 1.7 0 0 0 16.45 8a1.7 1.7 0 0 0 1.88-.34l.06-.06 1.41 1.41-.06.06A1.7 1.7 0 0 0 19.4 11c.16.6.7 1.04 1.33 1.04h.09v2h-.09A1.7 1.7 0 0 0 19.4 15Z"/>',
  sparkles: '<path d="m12 3-1.1 4.2L7 8.5l3.9 1.3L12 14l1.1-4.2L17 8.5l-3.9-1.3L12 3ZM19 14l-.65 2.35L16 17l2.35.65L19 20l.65-2.35L22 17l-2.35-.65L19 14ZM5 14l-.65 2.35L2 17l2.35.65L5 20l.65-2.35L8 17l-2.35-.65L5 14Z"/>',
  subtitles: '<path d="M4 5h16v12H4z"/><path d="M7 10h3M14 10h2M7 13h2M12 13h5"/>',
  tv: '<rect x="3" y="5" width="18" height="13" rx="2"/><path d="m8 2 4 3 4-3M8 21h8"/>',
  user: '<circle cx="12" cy="8" r="3"/><path d="M5 20a7 7 0 0 1 14 0"/>',
  volumeDown: '<path d="M4 10v4h4l5 4V6l-5 4H4Z"/><path d="M17 9a5 5 0 0 1 0 6"/>',
  volumeUp: '<path d="M3 10v4h4l5 4V6l-5 4H3Z"/><path d="M16 8a6 6 0 0 1 0 8M19 5a10 10 0 0 1 0 14"/>',
  volumeMute: '<path d="M4 10v4h4l5 4V6l-5 4H4Z"/><path d="m17 9 4 6M21 9l-4 6"/>',
  wifi: '<path d="M5 12.55a11 11 0 0 1 14.08 0M8.5 16.05a6 6 0 0 1 7 0M12 19.5h.01"/>',
  zap: '<path d="m13 2-9 12h7l-1 8 9-12h-7l1-8Z"/>',
};

const icon = (name, className = 'h-4 w-4') => `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${iconPaths[name] || iconPaths.sparkles}</svg>`;

const escapeHtml = (value = '') => String(value)
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#039;');

const state = {
  demo: demoMode,
  connection: demoMode ? 'connected' : 'offline',
  panel: null,
  sidebarOpen: false,
  volume: 34,
  muted: false,
  playing: true,
  currentApp: 'YouTube',
  currentTitle: 'Midnight City Radio',
  currentMeta: 'M83 · Hurry Up, We’re Dreaming',
  query: '',
  pairCode: '',
  pairError: '',
  pairingStarted: false,
  voiceActive: false,
  transcript: '',
  toasts: [],
  lastAction: 'Remote ready',
  device: {
    name: 'Living Room TV',
    model: 'SpectraCast Display · 4K HDR',
    room: 'Living room',
    ip: '192.168.1.42',
  },
};

const apps = [
  { name: 'Netflix', meta: 'Continue watching', className: 'netflix', mark: 'N' },
  { name: 'YouTube', meta: 'Playing now', className: 'youtube', mark: '▶' },
  { name: 'Disney+', meta: 'Recently opened', className: 'disney', mark: 'D+' },
  { name: 'Spotify', meta: 'Your music', className: 'spotify', mark: '●' },
];

const searchResults = [
  { title: 'Midnight City Radio', meta: 'YouTube · Music mix', icon: 'headphones', app: 'YouTube' },
  { title: 'The Bear', meta: 'Disney+ · Continue watching', icon: 'sparkles', app: 'Disney+' },
  { title: 'Planet Earth III', meta: 'Netflix · Documentary', icon: 'tv', app: 'Netflix' },
  { title: 'Lo-fi beats to relax', meta: 'Spotify · Playlist', icon: 'activity', app: 'Spotify' },
];

function statusLabel() {
  if (state.connection === 'connected') return state.demo ? 'Demo connected' : 'TV connected';
  if (state.connection === 'connecting') return 'Connecting';
  return 'Ready to pair';
}

function isConnected() {
  return state.connection === 'connected';
}

function toast(message, tone = 'info') {
  const id = Date.now() + Math.random();
  state.toasts = [...state.toasts, { id, message, tone }].slice(-3);
  render();
  window.setTimeout(() => {
    state.toasts = state.toasts.filter((item) => item.id !== id);
    render();
  }, 3300);
}

async function apiRequest(path, options = {}) {
  const { timeout = API_TIMEOUT, ...requestOptions } = options;
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(path, {
      ...requestOptions,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(requestOptions.headers || {}),
      },
    });
    if (!response.ok) throw new Error(`API ${response.status}`);
    const contentType = response.headers.get('content-type') || '';
    return contentType.includes('application/json') ? response.json() : {};
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function loadStatus() {
  if (state.demo) return;
  try {
    const payload = await apiRequest('/api/status');
    const device = payload.device || payload;
    state.connection = payload.connected === false || device.connected === false ? 'offline' : 'connected';
    state.device = {
      ...state.device,
      ...(device.name ? { name: device.name } : {}),
      ...(device.model ? { model: device.model } : {}),
      ...(device.room ? { room: device.room } : {}),
      ...(device.ip ? { ip: device.ip } : {}),
    };
    if (typeof payload.volume === 'number') state.volume = Math.max(0, Math.min(100, payload.volume));
    if (typeof payload.muted === 'boolean') state.muted = payload.muted;
    render();
  } catch {
    state.connection = 'offline';
    render();
  }
}

function connectEventStream() {
  if (state.demo || !window.WebSocket) return;
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const socket = new WebSocket(`${protocol}//${window.location.host}/api/events`);
  socket.addEventListener('message', (event) => {
    try {
      const payload = JSON.parse(event.data);
      const status = payload.status;
      if (!status) return;
      state.connection = status.connected ? 'connected' : status.connection === 'connecting' ? 'connecting' : 'offline';
      state.device = { ...state.device, ...(status.device || {}) };
      if (typeof status.volume === 'number') state.volume = status.volume;
      if (typeof status.muted === 'boolean') state.muted = status.muted;
      render();
    } catch {
      // Ignore malformed events; the next status snapshot will recover the UI.
    }
  });
  socket.addEventListener('close', () => {
    window.setTimeout(connectEventStream, 2500);
  });
}

async function sendCommand(key, body = {}) {
  state.lastAction = key;
  render();
  if (state.demo) return;
  try {
    await apiRequest('/api/remote/key', {
      method: 'POST',
      body: JSON.stringify({ key, ...body }),
    });
  } catch {
    // The local UI remains useful while the Python service is unavailable.
  }
}

function renderIconButton(action, iconName, label, className = 'icon-button') {
  return `<button class="${className}" type="button" data-action="${action}" aria-label="${label}" title="${label}">${icon(iconName)}</button>`;
}

function renderNavItem(action, iconName, label, active = false, badge = '') {
  return `<button class="nav-item${active ? ' active' : ''}" type="button" data-action="${action}">${icon(iconName)}<span>${label}</span>${badge ? `<span class="nav-badge">${badge}</span>` : ''}</button>`;
}

function renderSidebar() {
  return `<aside class="sidebar${state.sidebarOpen ? ' open' : ''}" aria-label="Primary navigation">
    <div class="sidebar-inner">
      <a class="brand-lockup" href="?${state.demo ? 'demo=1' : ''}" aria-label="SpectraCast home">
        <img src="${brandMark}" alt="" />
        <span class="brand-name">Spectra<span>Cast</span></span>
      </a>
      <div class="workspace-label">Workspace</div>
      <nav class="nav-list">
        ${renderNavItem('nav-overview', 'command', 'Command center', true)}
        ${renderNavItem('nav-remote', 'tv', 'Remote')}
        ${renderNavItem('nav-apps', 'apps', 'Apps', false, '4')}
        ${renderNavItem('nav-activity', 'activity', 'Activity')}
      </nav>
      <div class="workspace-label">Manage</div>
      <nav class="nav-list">
        ${renderNavItem('open-pair', 'wifi', 'Devices')}
        ${renderNavItem('open-settings', 'settings', 'Settings')}
      </nav>
      <div class="sidebar-spacer"></div>
      <div class="connection-mini">
        <div class="mini-label">${icon('wifi', 'h-3.5 w-3.5')} ${state.demo ? 'Demo environment' : 'Connection'}</div>
        <div class="mini-device-name">${escapeHtml(state.device.name)}</div>
        <div class="mini-device-meta">${escapeHtml(statusLabel())} · ${escapeHtml(state.device.room)}</div>
      </div>
      <div class="sidebar-profile">
        <div class="avatar">OL</div>
        <div class="profile-copy"><div class="profile-name">Olivia Lee</div><div class="profile-plan">Personal workspace</div></div>
        ${renderIconButton('open-settings', 'more', 'More profile options', 'more-button')}
      </div>
    </div>
  </aside>`;
}

function renderTopbar() {
  const connected = isConnected();
  return `<header class="topbar">
    <div class="flex items-center min-w-0">
      ${renderIconButton('toggle-sidebar', 'menu', 'Open navigation', 'mobile-menu-button')}
      <div class="crumbs"><span>Workspace</span>${icon('chevronRight', 'h-3 w-3')}<strong>Command center</strong></div>
    </div>
    <div class="topbar-actions">
      ${renderIconButton('open-search', 'search', 'Search your TV')}
      ${renderIconButton('open-notifications', 'bell', 'Notifications', 'topbar-icon')}
      <div class="connection-pill"><span class="status-dot${connected ? '' : ' offline'}"></span><span>${escapeHtml(statusLabel())}</span></div>
    </div>
  </header>`;
}

function renderHero() {
  const connected = isConnected();
  return `<section class="hero" aria-labelledby="hero-title">
    <div class="hero-copy">
      <div class="eyebrow"><span class="eyebrow-mark"></span>${state.demo ? 'Interactive demo mode' : connected ? 'Living room · Live' : 'Your private command center'}</div>
      <h1 id="hero-title">Control the room.<br /><span>From anywhere.</span></h1>
      <p class="hero-description">A calmer way to move between what you love. Your TV, apps, and controls — all in one beautiful space.</p>
      <div class="hero-actions">
        <button class="primary-button" type="button" data-action="${connected ? 'open-remote' : 'open-pair'}">${icon(connected ? 'tv' : 'wifi', 'h-4 w-4')} ${connected ? 'Open remote' : 'Pair a device'}</button>
        <button class="secondary-button" type="button" data-action="open-search">${icon('search', 'h-4 w-4')} Find something to watch</button>
      </div>
    </div>
    <div class="hero-visual" aria-hidden="true">
      <div class="hero-orbit"></div>
      <div class="hero-orb"></div>
      <div class="signal-badge top">${icon('zap', 'h-3.5 w-3.5')} Low latency</div>
      <div class="signal-badge bottom">${icon('lock', 'h-3.5 w-3.5')} Private by design</div>
    </div>
  </section>`;
}

function renderNowPlaying() {
  return `<div class="now-playing-mini">
    <div class="playing-label">${icon('play', 'h-3 w-3')} Now playing</div>
    <h3>${escapeHtml(state.currentTitle)}</h3>
    <p>${escapeHtml(state.currentMeta)}</p>
    <div class="progress-track"><span></span></div>
    <div class="progress-times"><span>18:42</span><span>42:08</span></div>
  </div>`;
}

function renderRemote() {
  const volume = state.muted ? 0 : state.volume;
  return `<section class="panel remote-panel" id="remote-panel">
    <div class="panel-header">
      <div><div class="panel-kicker">${escapeHtml(state.device.name)}</div><h2 class="panel-title">Remote controls</h2></div>
      ${renderIconButton('open-remote-menu', 'more', 'Remote options', 'more-button')}
    </div>
    <div class="remote-layout">
      ${renderNowPlaying()}
      <div class="remote-control">
        <div class="remote-control-head"><span>Navigation</span><span class="remote-battery">${icon('battery', 'h-3.5 w-3.5')} 82%</span></div>
        <div class="d-pad" aria-label="Directional pad">
          <button class="d-pad-button" type="button" data-key="UP" aria-label="Up">${icon('arrowUp', 'h-4.5 w-4.5')}</button>
          <span></span><span></span>
          <button class="d-pad-button" type="button" data-key="LEFT" aria-label="Left">${icon('arrowLeft', 'h-4.5 w-4.5')}</button>
          <button class="d-pad-center" type="button" data-key="ENTER" aria-label="Select">${icon('check', 'h-4 w-4')}</button>
          <button class="d-pad-button" type="button" data-key="RIGHT" aria-label="Right">${icon('arrowRight', 'h-4.5 w-4.5')}</button>
          <span></span>
          <button class="d-pad-button" type="button" data-key="DOWN" aria-label="Down">${icon('arrowDown', 'h-4.5 w-4.5')}</button>
          <span></span>
        </div>
        <div class="remote-secondary-controls">
          <button class="round-control" type="button" data-key="BACK" aria-label="Back">${icon('back')}</button>
          <button class="round-control" type="button" data-key="HOME" aria-label="Home">${icon('home')}</button>
          <button class="round-control" type="button" data-key="POWER" aria-label="Power">${icon('power')}</button>
        </div>
        <div class="media-controls">
          <button class="media-button" type="button" data-key="REWIND" aria-label="Rewind">${icon('rewind', 'h-3.5 w-3.5')}</button>
          <button class="media-button main" type="button" data-action="toggle-play" aria-label="${state.playing ? 'Pause' : 'Play'}">${icon(state.playing ? 'pause' : 'play', 'h-3.5 w-3.5')}</button>
          <button class="media-button" type="button" data-key="FAST_FORWARD" aria-label="Fast forward">${icon('arrowRight', 'h-3.5 w-3.5')}</button>
        </div>
        <div class="volume-strip">
          <button class="volume-button" type="button" data-action="toggle-mute" aria-label="${state.muted ? 'Unmute' : 'Mute'}">${icon(state.muted ? 'volumeMute' : 'volumeDown', 'h-3.5 w-3.5')}</button>
          <div class="volume-meter"><span style="width: ${volume}%"></span></div>
          <span class="volume-value">${state.muted ? '—' : `${state.volume}%`}</span>
          <button class="volume-button" type="button" data-action="volume-up" aria-label="Volume up">${icon('volumeUp', 'h-3.5 w-3.5')}</button>
        </div>
      </div>
    </div>
  </section>`;
}

function renderDevicePanel() {
  const connected = isConnected();
  return `<section class="panel device-panel" id="device-panel">
    <div class="panel-header"><div><div class="panel-kicker">Device status</div><h2 class="panel-title">Your screen</h2></div>${renderIconButton('open-pair', 'refresh', 'Refresh device connection', 'more-button')}</div>
    <div class="device-summary">
      <div class="device-icon">${icon('tv', 'h-5 w-5')}</div>
      <div class="device-summary-copy"><div class="device-summary-name">${escapeHtml(state.device.name)}</div><div class="device-summary-meta">${escapeHtml(state.device.model)}</div></div>
      <div class="device-summary-status"><span class="status-dot${connected ? '' : ' offline'}"></span>${connected ? 'Online' : 'Offline'}</div>
    </div>
    <div class="health-row">
      <div class="health-stat"><div class="health-stat-label">Device health</div><div class="health-stat-value">98<small>/ 100</small></div><div class="health-line"><span></span></div></div>
      <div class="health-stat"><div class="health-stat-label">Signal strength</div><div class="health-stat-value">Good</div><div class="health-line wifi"><span></span></div></div>
    </div>
  </section>`;
}

function renderAppsPanel() {
  return `<section class="panel apps-panel" id="apps-panel">
    <div class="panel-header"><div><div class="panel-kicker">Quick launch</div><h2 class="panel-title">Your apps</h2></div><button class="section-link" type="button" data-action="nav-apps">View all ${icon('chevronRight', 'h-3.5 w-3.5')}</button></div>
    <div class="app-list">${apps.map((app) => `<button class="app-launch${state.currentApp === app.name ? ' selected' : ''}" type="button" data-app="${escapeHtml(app.name)}"><span class="app-logo ${app.className}">${app.mark}</span><span class="app-launch-copy"><span class="app-launch-name">${app.name}</span><span class="app-launch-meta">${app.meta}</span></span>${icon('launch', 'h-3.5 w-3.5')}</button>`).join('')}</div>
  </section>`;
}

function renderShortcutPanel() {
  return `<section class="panel shortcut-panel">
    <div class="panel-header"><div><div class="panel-kicker">Made for the moment</div><h2 class="panel-title">Shortcuts</h2></div></div>
    <div class="shortcut-grid">
      <button class="shortcut-button" type="button" data-action="open-search">${icon('keyboard', 'h-4 w-4')}Search</button>
      <button class="shortcut-button" type="button" data-action="open-voice">${icon('mic', 'h-4 w-4')}Voice</button>
      <button class="shortcut-button" type="button" data-key="MUTE">${icon('volumeMute', 'h-4 w-4')}Mute</button>
      <button class="shortcut-button" type="button" data-key="SUBTITLES">${icon('subtitles', 'h-4 w-4')}Subtitles</button>
      <button class="shortcut-button" type="button" data-key="CAST">${icon('tv', 'h-4 w-4')}Cast</button>
      <button class="shortcut-button" type="button" data-key="SLEEP">${icon('moon', 'h-4 w-4')}Sleep</button>
    </div>
  </section>`;
}

function renderActivity() {
  return `<div class="activity-strip"><div class="activity-strip-icon">${icon('activity', 'h-4 w-4')}</div><div class="activity-strip-copy"><div class="activity-strip-title">Last action</div><div class="activity-strip-meta">${escapeHtml(state.lastAction)} · ${state.demo ? 'Local demo state' : 'Waiting for backend confirmation'}</div></div><span class="activity-time">just now</span></div>`;
}

function filteredResults() {
  const query = state.query.trim().toLowerCase();
  return query ? searchResults.filter((result) => `${result.title} ${result.meta}`.toLowerCase().includes(query)) : searchResults;
}

function renderSearchPanel() {
  const results = filteredResults();
  return `<div class="drawer-backdrop" data-action="close-panel"></div><aside class="drawer" aria-label="Search TV">
    <div class="drawer-header"><div><div class="eyebrow">Search your TV</div><h2 class="drawer-title">Find your next thing</h2><p class="drawer-description">Search apps and jump straight into a show, song, or movie.</p></div>${renderIconButton('close-panel', 'close', 'Close search', 'more-button')}</div>
    <div class="drawer-body">
      <div class="search-input-wrap">${icon('search', 'h-4 w-4')}<input class="search-input" type="search" data-search-input value="${escapeHtml(state.query)}" placeholder="Try “The Bear” or “music”" autocomplete="off" /><span class="search-shortcut">⌘ K</span></div>
      <div class="drawer-section-label">${state.query ? 'Matching titles' : 'Suggested for you'}</div>
      <div data-search-results>${results.length ? results.map((result) => `<button class="search-result" type="button" data-result-title="${escapeHtml(result.title)}" data-result-app="${escapeHtml(result.app)}"><span class="result-art">${icon(result.icon, 'h-4 w-4')}</span><span class="result-copy"><span class="result-title">${escapeHtml(result.title)}</span><span class="result-meta">${escapeHtml(result.meta)}</span></span>${icon('chevronRight', 'h-4 w-4')}</button>`).join('') : '<div class="transcript">No matching titles yet. Try a different search.</div>'}</div>
    </div>
  </aside>`;
}

function renderVoicePanel() {
  return `<div class="drawer-backdrop" data-action="close-panel"></div><aside class="drawer" aria-label="Voice remote">
    <div class="drawer-header"><div><div class="eyebrow">Hands-free remote</div><h2 class="drawer-title">Ask your TV</h2><p class="drawer-description">Press and hold to speak. Your audio stays with the connected room.</p></div>${renderIconButton('close-panel', 'close', 'Close voice remote', 'more-button')}</div>
    <div class="drawer-body"><div class="voice-card"><button class="voice-orb${state.voiceActive ? ' listening' : ''}" type="button" data-action="toggle-voice" aria-label="${state.voiceActive ? 'Stop listening' : 'Start listening'}">${icon(state.voiceActive ? 'activity' : 'mic', 'h-6 w-6')}</button><h3>${state.voiceActive ? 'Listening…' : 'What would you like to hear?'}</h3><p>${state.voiceActive ? 'Go ahead — say a title, app, or command.' : 'Try “open Netflix”, “turn it up”, or “play something mellow”.'}</p>${state.transcript ? `<div class="transcript">${icon('check', 'h-3.5 w-3.5')} ${escapeHtml(state.transcript)}</div>` : ''}</div></div>
  </aside>`;
}

function renderPairModal() {
  const pairingReady = state.demo || state.pairingStarted;
  return `<div class="drawer-backdrop" data-action="close-panel"></div><div class="modal-wrap" role="dialog" aria-modal="true" aria-labelledby="pair-title"><div class="modal"><div class="drawer-header"><div><div class="eyebrow">Device setup</div><h2 class="drawer-title" id="pair-title">Connect a screen</h2></div>${renderIconButton('close-panel', 'close', 'Close pairing', 'more-button')}</div><div class="drawer-body"><div class="pairing-layout"><div class="pairing-illustration"><div class="pairing-tv"></div></div><form class="pairing-form" data-pair-form><div class="eyebrow">Two steps to get started</div><h3>Bring your living room online.</h3><p>We’ll find a screen on your local network and securely link this browser to it.</p><div class="pairing-steps"><div class="pairing-step"><span class="step-number">1</span><p>Choose <strong>Pair new device</strong> on your TV.</p></div><div class="pairing-step"><span class="step-number">2</span><p>Enter the six-character code shown on screen.</p></div></div><label class="pairing-input-label" for="pair-code">Pairing code</label><input class="pairing-input" id="pair-code" name="code" inputmode="text" maxlength="6" pattern="[0-9A-Fa-f]{6}" placeholder="A1B2C3" value="${escapeHtml(state.pairCode)}" autocomplete="one-time-code" ${pairingReady ? '' : 'disabled'} />${state.pairError ? `<p class="pairing-error">${escapeHtml(state.pairError)}</p>` : ''}<button class="primary-button pairing-submit" type="submit" ${pairingReady ? '' : 'disabled'}>${icon('wifi', 'h-4 w-4')} ${pairingReady ? 'Pair device' : 'Finding your TV…'}</button></form></div></div></div></div>`;
}

function renderPanel() {
  if (state.panel === 'search') return renderSearchPanel();
  if (state.panel === 'voice') return renderVoicePanel();
  if (state.panel === 'pair') return renderPairModal();
  return '';
}

function renderToasts() {
  if (!state.toasts.length) return '';
  return `<div class="toast-stack" aria-live="polite">${state.toasts.map((item) => `<div class="toast">${icon(item.tone === 'error' ? 'zap' : 'check', 'h-4 w-4')}<span>${escapeHtml(item.message)}</span></div>`).join('')}</div>`;
}

function render() {
  appRoot.innerHTML = `<div class="app-shell"><div class="sidebar-overlay${state.sidebarOpen ? ' visible' : ''}" data-action="toggle-sidebar"></div>${renderSidebar()}<main class="main-content">${renderTopbar()}<div class="page-body">${renderHero()}<div class="dashboard-heading"><div><div class="eyebrow">One glance, full control</div><h2 class="section-title">Your room at a glance</h2></div><button class="section-link" type="button" data-action="refresh-status">${icon('refresh', 'h-3 w-3')} Refresh status</button></div><div class="dashboard-grid"><div class="dashboard-column">${renderRemote()}${renderActivity()}</div><div class="dashboard-column">${renderDevicePanel()}${renderAppsPanel()}${renderShortcutPanel()}</div></div></div></main>${renderPanel()}${renderToasts()}</div>`;
  bindEvents();
}

function setPanel(panel) {
  state.panel = panel;
  state.sidebarOpen = false;
  render();
  if (panel === 'search') window.setTimeout(() => document.querySelector('[data-search-input]')?.focus(), 0);
  if (panel === 'pair') window.setTimeout(() => document.querySelector('#pair-code')?.focus(), 0);
  if (panel === 'pair') void beginPairing();
}

async function beginPairing() {
  if (state.demo || state.pairingStarted) return;
  state.connection = 'connecting';
  state.pairError = '';
  render();
  try {
    const payload = await apiRequest('/api/pair/start', { method: 'POST', body: JSON.stringify({}), timeout: 15000 });
    state.device = { ...state.device, ...(payload.device || {}) };
    state.pairingStarted = true;
    state.lastAction = 'Pairing handshake ready';
    render();
  } catch {
    state.connection = 'offline';
    state.pairError = 'No TV found yet. Keep both devices on the same Wi-Fi, then try again.';
    render();
  }
}

function localActionMessage(action) {
  if (state.demo) return `${action} · Demo control sent`;
  if (isConnected()) return `${action} · Sent to ${state.device.name}`;
  return `${action} · Pair a TV to send this command`;
}

async function handleKey(key) {
  if (key === 'POWER') {
    state.connection = state.connection === 'connected' ? 'offline' : 'connected';
    toast(state.connection === 'connected' ? 'Living Room TV powered on' : 'Living Room TV is now in standby');
  } else if (key === 'MUTE') {
    state.muted = !state.muted;
    toast(state.muted ? 'Volume muted' : `Volume restored to ${state.volume}%`);
  } else if (key === 'SUBTITLES') {
    toast(localActionMessage('Subtitles toggled'));
  } else if (key === 'SLEEP') {
    toast(localActionMessage('Sleep timer ready'));
  } else if (key === 'CAST') {
    toast(localActionMessage('Cast menu opened'));
  } else {
    toast(localActionMessage(key.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase())));
  }
  await sendCommand(key);
}

async function handleAction(action) {
  switch (action) {
    case 'toggle-sidebar':
      state.sidebarOpen = !state.sidebarOpen;
      render();
      break;
    case 'open-search':
      state.query = '';
      setPanel('search');
      break;
    case 'open-voice':
      state.transcript = '';
      setPanel('voice');
      break;
    case 'open-pair':
    case 'open-settings':
      state.pairError = '';
      setPanel('pair');
      break;
    case 'close-panel':
      state.panel = null;
      state.voiceActive = false;
      render();
      break;
    case 'open-remote':
    case 'nav-remote':
      document.querySelector('#remote-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      state.sidebarOpen = false;
      render();
      break;
    case 'nav-apps':
      document.querySelector('#apps-panel')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      state.sidebarOpen = false;
      render();
      break;
    case 'nav-overview':
      window.scrollTo({ top: 0, behavior: 'smooth' });
      state.sidebarOpen = false;
      render();
      break;
    case 'nav-activity':
      document.querySelector('.activity-strip')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      state.sidebarOpen = false;
      render();
      break;
    case 'toggle-play':
      state.playing = !state.playing;
      toast(state.playing ? 'Playback resumed' : 'Playback paused');
      await sendCommand(state.playing ? 'PLAY' : 'PAUSE');
      break;
    case 'toggle-mute':
      await handleKey('MUTE');
      break;
    case 'volume-up':
      state.volume = Math.min(100, state.volume + 5);
      state.muted = false;
      toast(`Volume ${state.volume}%`);
      await sendCommand('VOLUME_UP', { value: state.volume });
      break;
    case 'volume-down':
      state.volume = Math.max(0, state.volume - 5);
      state.muted = false;
      toast(`Volume ${state.volume}%`);
      await sendCommand('VOLUME_DOWN', { value: state.volume });
      break;
    case 'refresh-status':
      state.lastAction = 'Status refreshed';
      await loadStatus();
      toast(state.demo ? 'Demo status is up to date' : 'Status refreshed');
      break;
    case 'open-notifications':
      toast('You’re all caught up');
      break;
    case 'open-remote-menu':
      toast('Remote preferences are ready');
      break;
    case 'toggle-voice':
      state.voiceActive = !state.voiceActive;
      state.transcript = '';
      render();
      if (state.voiceActive) {
        if (!state.demo) {
          apiRequest('/api/voice', { method: 'POST', body: JSON.stringify({ action: 'start' }) }).catch(() => {});
        }
        window.setTimeout(() => {
          if (!state.voiceActive) return;
          state.voiceActive = false;
          state.transcript = 'Try saying “open Netflix” or “play something mellow”.';
          render();
        }, 2300);
      }
      break;
    default:
      break;
  }
}

async function submitPairing(form) {
  const formData = new FormData(form);
  const code = String(formData.get('code') || '').trim();
  state.pairCode = code;
  if (!/^[0-9a-f]{6}$/i.test(code)) {
    state.pairError = 'Enter the six-character code shown on your TV.';
    render();
    document.querySelector('#pair-code')?.focus();
    return;
  }
  state.pairError = '';
  state.connection = 'connecting';
  render();
  try {
    if (!state.demo) {
      const payload = await apiRequest('/api/pair', { method: 'POST', body: JSON.stringify({ code }), timeout: 15000 });
      const device = payload.device || {};
      state.device = { ...state.device, ...device };
    }
    state.connection = 'connected';
    state.panel = null;
    state.pairCode = '';
    state.pairingStarted = false;
    render();
    toast(state.demo ? 'Demo TV connected — explore freely' : `${state.device.name} is connected`);
  } catch {
    state.connection = 'offline';
    state.pairError = 'The remote service is unavailable. Check the backend and try again.';
    render();
  }
}

function updateSearchResults() {
  const target = document.querySelector('[data-search-results]');
  if (!target) return;
  const results = filteredResults();
  target.innerHTML = results.length ? results.map((result) => `<button class="search-result" type="button" data-result-title="${escapeHtml(result.title)}" data-result-app="${escapeHtml(result.app)}"><span class="result-art">${icon(result.icon, 'h-4 w-4')}</span><span class="result-copy"><span class="result-title">${escapeHtml(result.title)}</span><span class="result-meta">${escapeHtml(result.meta)}</span></span>${icon('chevronRight', 'h-4 w-4')}</button>`).join('') : '<div class="transcript">No matching titles yet. Try a different search.</div>';
  const label = target.previousElementSibling;
  if (label?.classList.contains('drawer-section-label')) label.textContent = state.query ? 'Matching titles' : 'Suggested for you';
  bindSearchResultEvents();
}

function bindSearchResultEvents() {
  document.querySelectorAll('[data-result-title]').forEach((button) => {
    button.addEventListener('click', async () => {
      state.currentTitle = button.dataset.resultTitle || state.currentTitle;
      state.currentApp = button.dataset.resultApp || state.currentApp;
      state.currentMeta = `${state.currentApp} · Playing now`;
      state.panel = null;
      render();
      toast(`Playing ${state.currentTitle}`);
      if (!state.demo) {
        await apiRequest(`/api/search?q=${encodeURIComponent(state.currentTitle)}`, { method: 'POST', body: JSON.stringify({ title: state.currentTitle, app: state.currentApp }) }).catch(() => {});
      }
    });
  });
}

function bindEvents() {
  document.querySelectorAll('[data-action]').forEach((element) => {
    element.addEventListener('click', () => handleAction(element.dataset.action));
  });
  document.querySelectorAll('[data-key]').forEach((element) => {
    element.addEventListener('click', () => handleKey(element.dataset.key));
  });
  document.querySelectorAll('[data-app]').forEach((element) => {
    element.addEventListener('click', async () => {
      const appName = element.dataset.app || 'YouTube';
      state.currentApp = appName;
      state.currentTitle = appName === 'Spotify' ? 'Your Daily Mix' : `Welcome back to ${appName}`;
      state.currentMeta = `${appName} · App opened just now`;
      render();
      toast(`Opening ${appName}`);
      if (!state.demo) await apiRequest('/api/apps/launch', { method: 'POST', body: JSON.stringify({ app: appName }) }).catch(() => {});
    });
  });
  bindSearchResultEvents();
  document.querySelector('[data-pair-form]')?.addEventListener('submit', (event) => {
    event.preventDefault();
    submitPairing(event.currentTarget);
  });
  document.querySelector('[data-search-input]')?.addEventListener('input', (event) => {
    state.query = event.target.value;
    updateSearchResults();
  });
  document.querySelector('[data-search-input]')?.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') handleAction('close-panel');
  });
  document.querySelector('#pair-code')?.addEventListener('input', (event) => {
    event.target.value = event.target.value.replace(/[^0-9a-f]/gi, '').slice(0, 6).toUpperCase();
    state.pairCode = event.target.value;
  });
}

window.addEventListener('keydown', (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault();
    setPanel('search');
  }
  if (event.key === 'Escape' && state.panel) {
    state.panel = null;
    state.voiceActive = false;
    render();
  }
});

render();
loadStatus();
connectEventStream();
if ('serviceWorker' in navigator && !demoMode) {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}
