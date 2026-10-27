/**
 * Main Application Logic
 */

// --- State ---
const CHAT_SESSION_TTL_MINUTES = 30;

const state = {
    token: localStorage.getItem('jwt_token'),
    user: JSON.parse(localStorage.getItem('user') || 'null'),
    theme: localStorage.getItem('theme') || 'dark',
    currentPath: '/overview',
    chatHistory: []
};

// --- DOM Elements ---
const DOM = {
    app: document.getElementById('app'),
    sidebar: document.getElementById('sidebar'),
    topbar: document.getElementById('topbar'),
    viewContainer: document.getElementById('view-container'),
    pageTitle: document.getElementById('page-title'),
    themeToggle: document.getElementById('theme-toggle'),
    logoutBtn: document.getElementById('logout-btn'),
    syncBtn: document.getElementById('sync-btn'),
    mobileMenuBtn: document.getElementById('mobile-menu-btn'),
    navItems: document.querySelectorAll('.nav-item'),
    toastContainer: document.getElementById('toast-container'),
};

// --- API Client ---
const API = {
    baseUrl: '/project/jira-logger/api',

    async request(endpoint, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...(state.token && { 'Authorization': `Bearer ${state.token}` }),
            ...options.headers
        };

        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, { ...options, headers });
            const data = await response.json();

            if (response.status === 401) {
                auth.logout();
                throw new Error("Session expired");
            }
            if (!response.ok) {
                throw new Error(data.detail || data.message || "API Error");
            }
            return data.data;
        } catch (error) {
            ui.showToast(error.message, 'error');
            throw error;
        }
    },

    post(endpoint, body) {
        return this.request(endpoint, { method: 'POST', body: JSON.stringify(body) });
    },
    get(endpoint) {
        return this.request(endpoint);
    }
};

// --- Auth ---
const auth = {
    check() {
        if (!state.token) {
            this.renderLogin();
            return false;
        }
        DOM.sidebar.classList.remove('hidden');
        DOM.topbar.classList.remove('hidden');
        this.updateProfileUI();
        return true;
    },

    async login(email, password) {
        try {
            const data = await API.post('/auth/login', { email, password });
            state.token = data.access_token;
            state.user = data.user;
            localStorage.setItem('jwt_token', data.access_token);
            localStorage.setItem('user', JSON.stringify(data.user));

            ui.showToast('Login successful', 'success');
            DOM.sidebar.classList.remove('hidden');
            DOM.topbar.classList.remove('hidden');
            this.updateProfileUI();
            router.navigate('/overview');
        } catch (e) {
            // Toast handled in API request
        }
    },

    async logout() {

        try {
            await API.post('/auth/logout');
        } catch(e) {}

        state.token = null;
        state.user = null;

        localStorage.removeItem('jwt_token');
        localStorage.removeItem('user');

        DOM.sidebar.classList.add('hidden');
        DOM.topbar.classList.add('hidden');

        this.renderLogin();
    },

    updateProfileUI() {
        if (state.user) {
            document.getElementById('user-name').textContent = state.user.name;
            document.getElementById('user-role').textContent = state.user.role;
            document.getElementById('user-avatar').textContent = state.user.name.substring(0, 2).toUpperCase();
        }
    },

    renderLogin() {
        DOM.pageTitle.textContent = "Login";
        DOM.viewContainer.innerHTML = `
            <div class="auth-wrapper">
                <div class="glass-card auth-card">
                    <div class="auth-header">
                        <div class="auth-logo">📊</div>
                        <h2>Jira Logger</h2>
                        <p style="color: var(--text-muted); margin-top: 0.5rem;">Sign in to your account</p>
                    </div>
                    <form id="login-form">
                        <div class="form-group">
                            <label class="form-label">Email</label>
                            <input type="email" id="email" class="form-control" required autocomplete="username">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Password</label>
                            <input type="password" id="password" class="form-control" required autocomplete="current-password">
                        </div>
                        <button type="submit" class="btn btn-primary" style="width: 100%; margin-top: 1rem;">Sign In</button>
                    </form>
                </div>
            </div>
        `;

        document.getElementById('login-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.login(document.getElementById('email').value, document.getElementById('password').value);
        });
    }
};

// --- UI Helpers ---
const ui = {
    initTheme() {
        if (state.theme === 'dark') {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
    },

    toggleTheme() {
        state.theme = state.theme === 'dark' ? 'light' : 'dark';
        localStorage.setItem('theme', state.theme);
        this.initTheme();
    },

    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span>${message}</span>
            <button style="background:none;border:none;color:inherit;cursor:pointer" onclick="this.parentElement.remove()">✕</button>
        `;
        DOM.toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('closing');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    updateNav(path) {
        DOM.navItems.forEach(item => {
            if (item.getAttribute('data-path') === path) {
                item.classList.add('active');
                DOM.pageTitle.textContent = item.textContent.trim();
            } else {
                item.classList.remove('active');
            }
        });
    }
};

// --- Views ---
const views = {
    async overview() {
        DOM.viewContainer.innerHTML = '<p>Loading dashboard...</p>';
        try {
            const stats = await API.get('/dashboard/overview');
            DOM.viewContainer.innerHTML = `
                <div class="grid-stats">
                    <div class="glass-card stat-card">
                        <div class="stat-icon" style="background: rgba(36, 41, 47, 0.1); color: var(--github)">🐙</div>
                        <div class="stat-info">
                            <h3>Total Commits</h3>
                            <p>${stats.total_commits}</p>
                        </div>
                    </div>
                    <div class="glass-card stat-card">
                        <div class="stat-icon" style="background: rgba(36, 41, 47, 0.1); color: var(--github)">🔄</div>
                        <div class="stat-info">
                            <h3>Pull Requests</h3>
                            <p>${stats.total_prs}</p>
                        </div>
                    </div>
                    <div class="glass-card stat-card">
                        <div class="stat-icon" style="background: rgba(0, 82, 204, 0.1); color: var(--jira)">🎫</div>
                        <div class="stat-info">
                            <h3>Jira Issues</h3>
                            <p>${stats.total_issues}</p>
                        </div>
                    </div>
                    <div class="glass-card stat-card">
                        <div class="stat-icon" style="background: var(--primary-light); color: var(--primary)">🤖</div>
                        <div class="stat-info">
                            <h3>AI Summaries</h3>
                            <p>${stats.total_summaries}</p>
                        </div>
                    </div>
                </div>
                <div class="glass-card">
                    <h3 class="card-title" style="margin-bottom:1rem;">Welcome to Jira Logger</h3>
                    <p style="color: var(--text-muted)">Navigate using the sidebar to view detailed analytics, configure integrations, or generate AI reports.</p>
                    <br>
                    <button class="btn btn-primary" onclick="window.location.hash='#/settings'">Configure Integrations</button>
                </div>
            `;
        } catch (e) {
            DOM.viewContainer.innerHTML = '<p>Failed to load dashboard data.</p>';
        }
    },

    async jira() {
        DOM.viewContainer.innerHTML = `
            <div class="glass-card">
                <div class="card-header" style="justify-content: space-between; gap: 1rem; align-items:center;">
                    <div>
                        <h3 class="card-title">Jira Analytics</h3>
                        <p style="color: var(--text-muted); margin: 0.25rem 0 0;">Calendar view of daily hours and details.</p>
                    </div>
                    <div style="display:flex; gap:0.5rem; align-items:center;">
                        <button id="jira-sync-btn" class="btn btn-primary">🔄 Sync Jira</button>
                        <button id="jira-export-btn" class="btn btn-secondary">Export MD</button>
                    </div>
                </div>

                <div style="margin-top:1rem; display:flex; gap:1rem; flex-direction:column;">
                    <div style="display:flex; gap:0.5rem;">
                        <button id="tab-calendar" class="btn btn-secondary">Calendar</button>
                        <button id="tab-day" class="btn btn-secondary">Day Details</button>
                        <button id="tab-releases" class="btn btn-secondary">Releases</button>
                        <button id="tab-filter" class="btn btn-secondary">Date Range</button>
                    </div>

                    <div id="jira-status-message" style="color: var(--text-muted); margin-top:0.5rem;">Loading Jira data...</div>

                    <div id="calendar-container" style="margin-top:1rem;"></div>

                    <div id="day-details" style="margin-top:1rem; display:none;"></div>

                    <div id="releases-container" style="margin-top:1rem; display:none;"></div>

                    <div id="range-filter-container" style="margin-top:1rem; display:none;"></div>
                </div>
            </div>
        `;

        const setStatus = (msg) => {
            const el = document.getElementById('jira-status-message');
            if (el) el.textContent = msg;
        };

        // cache for current month
        let calendarYear = (new Date()).getFullYear();
        let calendarMonth = (new Date()).getMonth(); // 0-based
        let cachedData = { worklogs: [], comments: [], issues: [], releases: [] };

        const monthRange = (y, m) => {
            const start = new Date(y, m, 1);
            const end = new Date(y, m + 1, 0);
            const pad = (n) => n < 10 ? `0${n}` : `${n}`;
            const startStr = `${start.getFullYear()}-${pad(start.getMonth()+1)}-${pad(start.getDate())}`;
            const endStr = `${end.getFullYear()}-${pad(end.getMonth()+1)}-${pad(end.getDate())}`;
            return { startStr, endStr };
        };

        const fetchAll = async (year = calendarYear, month = calendarMonth) => {
            setStatus('Loading Jira data...');
            const { startStr, endStr } = monthRange(year, month);
            try {
                const [worklogs, comments, issues, releases] = await Promise.all([
                    API.get(`/jira/worklogs?start_date=${startStr}&end_date=${endStr}`),
                    API.get(`/jira/comments?start_date=${startStr}&end_date=${endStr}`),
                    API.get(`/jira/issues?start_date=${startStr}&end_date=${endStr}`),
                    API.get(`/jira/releases?start_date=${startStr}&end_date=${endStr}`),
                ]);
                cachedData = { worklogs, comments, issues, releases };
                setStatus(`Loaded ${worklogs.length} worklogs, ${comments.length} comments, ${issues.length} issues, ${releases.length} releases for ${startStr.substring(0,7)}.`);
                return cachedData;
            } catch (err) {
                setStatus('Failed to load Jira data.');
                cachedData = { worklogs: [], comments: [], issues: [], releases: [] };
                return cachedData;
            }
        };

        const renderCalendar = (worklogs) => {
            const container = document.getElementById('calendar-container');
            container.classList.add('calendar-container');
            container.innerHTML = '';

            const year = calendarYear;
            const month = calendarMonth;
            const monthNames = ['January','February','March','April','May','June','July','August','September','October','November','December'];
            const today = new Date();
            const pad = (value) => value < 10 ? `0${value}` : String(value);
            const localDateKey = (date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
            const todayKey = localDateKey(today);

            const header = document.createElement('div');
            header.className = 'calendar-header';
            const title = document.createElement('div');
            title.className = 'title';
            title.innerHTML = `<strong>${monthNames[month]} ${year}</strong>`;
            const nav = document.createElement('div');
            nav.className = 'calendar-nav';
            const prevBtn = document.createElement('button'); prevBtn.className = 'btn btn-secondary'; prevBtn.textContent = '←';
            const nextBtn = document.createElement('button'); nextBtn.className = 'btn btn-secondary'; nextBtn.textContent = '→';
            const monthInput = document.createElement('input');
            monthInput.type = 'month';
            monthInput.value = `${year}-${pad(month+1)}`;
            monthInput.style.margin = '0 8px';
            monthInput.className = 'month-picker form-control';

            nav.appendChild(prevBtn);
            nav.appendChild(monthInput);
            nav.appendChild(nextBtn);
            header.appendChild(title);
            header.appendChild(nav);
            container.appendChild(header);

            prevBtn.addEventListener('click', async () => {
                calendarMonth -= 1;
                if (calendarMonth < 0) { calendarMonth = 11; calendarYear -= 1; }
                const data = await fetchAll(calendarYear, calendarMonth);
                renderCalendar(data.worklogs);
                renderReleases(data.releases);
            });
            nextBtn.addEventListener('click', async () => {
                calendarMonth += 1;
                if (calendarMonth > 11) { calendarMonth = 0; calendarYear += 1; }
                const data = await fetchAll(calendarYear, calendarMonth);
                renderCalendar(data.worklogs);
                renderReleases(data.releases);
            });
            monthInput.addEventListener('change', async () => {
                const [y,m] = monthInput.value.split('-');
                calendarYear = Number(y);
                calendarMonth = Number(m)-1;
                const data = await fetchAll(calendarYear, calendarMonth);
                renderCalendar(data.worklogs);
                renderReleases(data.releases);
            });

            const first = new Date(year, month, 1);
            const last = new Date(year, month + 1, 0);
            const daysInMonth = last.getDate();

            const dayMap = {};
            const issueCountMap = {};
            const worklogCountMap = {};
            (worklogs || []).forEach(w => {
                const d = w.work_date || w.work_date_string || w.date || null;
                if (!d) return;
                const key = d.substring(0, 10);
                const hours = Number(w.hours_logged || w.hours || 0) || 0;
                dayMap[key] = (dayMap[key] || 0) + hours;
                worklogCountMap[key] = (worklogCountMap[key] || 0) + 1;
                if (w.issue_key) issueCountMap[key] = (issueCountMap[key] || new Set()).add(w.issue_key);
            });
            Object.keys(issueCountMap).forEach(k => { issueCountMap[k] = issueCountMap[k].size; });
            (cachedData.issues || []).forEach(i => {
                const k = (i.updated_at || i.created_at || '').substring(0,10);
                if (!k) return;
                issueCountMap[k] = (issueCountMap[k] || 0) + 1;
            });

            const grid = document.createElement('div');
            grid.className = 'calendar-grid';
            const weekdayRow = document.createElement('div');
            weekdayRow.className = 'weekday-row';
            ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].forEach(dayName => {
                const weekdayCell = document.createElement('div');
                weekdayCell.className = 'weekday-cell';
                weekdayCell.textContent = dayName;
                weekdayRow.appendChild(weekdayCell);
            });
            container.appendChild(weekdayRow);

            for (let i = 0; i < first.getDay(); i++) {
                const blank = document.createElement('div');
                blank.className = 'calendar-empty';
                grid.appendChild(blank);
            }

            for (let d = 1; d <= daysInMonth; d++) {
                const date = new Date(year, month, d);
                const key = localDateKey(date);
                const hours = dayMap[key] || 0;
                const issuesCount = issueCountMap[key] || 0;
                const logsCount = worklogCountMap[key] || 0;

                const cell = document.createElement('div');
                cell.className = 'calendar-cell';
                if (key === todayKey) cell.classList.add('today');
                cell.dataset.date = key;
                cell.innerHTML = `
                    <div class="cell-top"><div class="day-number">${d}</div></div>
                    <div class="cell-body">
                        <div class="progress"><div class="progress-bar${hours >= 8 ? ' full' : ''}" style="width:${Math.min(100, Math.round((hours/8)*100))}%"></div></div>
                        <div class="hours-text">${hours.toFixed(2)} / 8 hrs</div>
                        <div class="meta"><span class="issues-count">${issuesCount} issues</span> <span class="worklogs-count">${logsCount} logs</span></div>
                    </div>
                `;
                cell.title = `${hours.toFixed(2)} hrs — ${issuesCount} issues — ${logsCount} logs`;
                cell.addEventListener('click', () => showDayDetails(key));
                grid.appendChild(cell);
            }

            const totalCells = first.getDay() + daysInMonth;
            const trailing = (7 - (totalCells % 7)) % 7;
            for (let i = 0; i < trailing; i++) {
                const blank = document.createElement('div');
                blank.className = 'calendar-empty';
                grid.appendChild(blank);
            }

            container.appendChild(grid);

            if (!worklogs || !worklogs.length) {
                const emptyMessage = document.createElement('div');
                emptyMessage.className = 'calendar-empty-message';
                emptyMessage.textContent = 'No Jira worklogs found for this month.';
                emptyMessage.style.marginTop = '1rem';
                emptyMessage.style.color = 'var(--text-muted)';
                container.appendChild(emptyMessage);
            }
        };

        const showDayDetails = (dateKey) => {
            const pnl = document.getElementById('day-details');
            const container = document.getElementById('calendar-container');
            // switch to Day Details tab
            document.getElementById('tab-day').classList.add('active');
            document.getElementById('tab-calendar').classList.remove('active');
            document.getElementById('tab-releases').classList.remove('active');
            document.getElementById('calendar-container').style.display = 'none';
            pnl.style.display = 'block';
            pnl.innerHTML = `<h4>Details for ${dateKey}</h4><div id="day-list">Loading...</div>`;

            // use cached data filtered by date
            const worklogs = cachedData.worklogs || [];
            const comments = cachedData.comments || [];
            const issues = cachedData.issues || [];

            const logs = worklogs.filter(w => (w.work_date || '').startsWith(dateKey));
            const comms = comments.filter(c => (c.created_at || '').startsWith(dateKey));
            const iss = issues.filter(i => ((i.updated_at || '').startsWith(dateKey)) || ((i.created_at||'').startsWith(dateKey)) );

            const list = document.getElementById('day-list');
            list.innerHTML = '';

            const section = (title, items, renderFn) => {
                const el = document.createElement('div');
                el.style.marginTop = '0.75rem';
                el.innerHTML = `<h5>${title} (${items.length})</h5>`;
                const ul = document.createElement('div');
                ul.style.display = 'flex';
                ul.style.flexDirection = 'column';
                ul.style.gap = '0.5rem';
                items.forEach(it => {
                    const row = document.createElement('div');
                    row.style.padding = '0.5rem';
                    row.style.border = '1px solid rgba(0,0,0,0.04)';
                    row.style.borderRadius = '8px';
                    row.style.marginBottom = '0.5rem';
                    row.innerHTML = renderFn(it);
                    ul.appendChild(row);
                });
                el.appendChild(ul);
                return el;
            };

            if (logs.length) list.appendChild(section('Worklogs', logs, w => {
                // find comments for this issue on the same day
                const related = (cachedData.comments || []).filter(c => (c.issue_key === w.issue_key) && (c.created_at || '').startsWith(dateKey));
                // include worklog-level comment_text as a justification if present
                const allRelated = related.slice();
                if ((w.comment_text || w.comment) && !related.find(r => (r.comment_text || r.comment) === (w.comment_text || w.comment))) {
                    allRelated.push({ comment_text: w.comment_text || w.comment, author: w.author });
                }
                const relHtml = allRelated.length ? ('<div style="margin-top:6px; color:var(--text-muted)"><strong>Justification:</strong><br>' + allRelated.map(r => `<div>${(r.comment_text||'').replace(/\n/g,'<br>')}</div><div style="color:var(--text-muted); font-size:12px;">— ${r.author||''}</div>`).join('<hr style="opacity:0.06;margin:6px 0;">') + '</div>') : '';
                return `<strong>${w.issue_key || w.project_key || ''}</strong><div>${(w.comment||w.comment_text||'').slice(0,200)}</div><div style="color:var(--text-muted)">${w.hours_logged || w.hours || 0} hrs by ${w.author || ''}</div>${relHtml}`;
            }));
            if (comms.length) list.appendChild(section('Comments', comms, c => `<div>${(c.comment_text||c.comment||'').replace(/\n/g,'<br>')}</div><div style="color:var(--text-muted)">By ${c.author||''}</div>`));
            if (iss.length) list.appendChild(section('Issues touched', iss, i => `<strong>${i.issue_key || i.key || ''}</strong><div>${i.summary || i.title || ''}</div><div style="color:var(--text-muted)">Status: ${i.status||''}</div>`));

            if (!logs.length && !comms.length && !iss.length) list.innerHTML = '<div style="color:var(--text-muted)">No activity for this day.</div>';
        };

        const renderReleases = (releases) => {
            const container = document.getElementById('releases-container');
            container.style.display = 'none';
            container.innerHTML = '';
            if (!releases || !releases.length) {
                container.innerHTML = '<div style="color:var(--text-muted)">No releases found.</div>';
                return;
            }

            releases.forEach(r => {
                const el = document.createElement('div');
                el.style.padding = '0.75rem';
                el.style.border = '1px solid rgba(0,0,0,0.04)';
                el.style.borderRadius = '8px';
                el.style.marginBottom = '0.5rem';
                const start = r.release_start || r.start_date || r.created_at || 'Unknown';
                const end = r.release_date || r.released_at || r.end_date || 'Ongoing';
                el.innerHTML = `<strong>${r.name || r.version || r.id}</strong><div style="color:var(--text-muted)">Project: ${r.project_key || ''}</div><div>From: ${start} — To: ${end}</div>`;
                container.appendChild(el);
            });
        };

        const fetchRangeData = async (startDate, endDate) => {
            const params = new URLSearchParams();
            if (startDate) params.append('start_date', startDate);
            if (endDate) params.append('end_date', endDate);
            const query = params.toString() ? `?${params.toString()}` : '';

            try {
                const [worklogs, comments, issues, releases] = await Promise.all([
                    API.get(`/jira/worklogs${query}`),
                    API.get(`/jira/comments${query}`),
                    API.get(`/jira/issues${query}`),
                    API.get(`/jira/releases${query}`),
                ]);
                return { worklogs, comments, issues, releases };
            } catch (e) {
                return { worklogs: [], comments: [], issues: [], releases: [] };
            }
        };

        const renderRangeResults = ({ worklogs, comments, issues, releases }, startDate, endDate) => {
            const container = document.getElementById('range-filter-container');
            const results = document.getElementById('jira-range-results');
            const rangeLabel = `${startDate || 'Any'} → ${endDate || 'Any'}`;
            results.innerHTML = '';

            const summary = document.createElement('div');
            summary.className = 'range-summary';
            summary.innerHTML = `
                <div class="range-card"><strong>Worklogs</strong><span>${worklogs.length} entries</span></div>
                <div class="range-card"><strong>Issues</strong><span>${issues.length} issues</span></div>
                <div class="range-card"><strong>Comments</strong><span>${comments.length} comments</span></div>
                <div class="range-card"><strong>Releases</strong><span>${releases.length} releases</span></div>
            `;
            results.appendChild(summary);

            const heading = document.createElement('div');
            heading.className = 'range-heading';
            heading.innerHTML = `<h4>Activity in range ${rangeLabel}</h4>`;
            results.appendChild(heading);

            const section = (title, items, renderFn) => {
                const el = document.createElement('div');
                el.className = 'range-section';
                el.innerHTML = `<h5>${title} (${items.length})</h5>`;
                const list = document.createElement('div');
                list.className = 'range-list';
                items.forEach(item => {
                    const row = document.createElement('div');
                    row.className = 'range-list-item';
                    row.innerHTML = renderFn(item);
                    list.appendChild(row);
                });
                el.appendChild(list);
                return el;
            };

            if (worklogs.length) {
                results.appendChild(section('Worklogs', worklogs, w => {
                    const pw = w.work_date || w.date || 'Unknown';
                    return `<strong>${w.issue_key || ''}</strong> · ${w.hours_logged || 0} hrs<br><span class="text-muted">${pw} · ${w.author || ''}</span><div>${(w.comment_text || w.comment || '').slice(0, 180)}</div>`;
                }));
            }
            if (issues.length) {
                results.appendChild(section('Issues', issues, i => `<strong>${i.issue_key || i.key || ''}</strong> · ${i.summary || ''}<br><span class="text-muted">Status: ${i.status || ''}</span>`));
            }
            if (comments.length) {
                results.appendChild(section('Comments', comments, c => `<strong>${c.issue_key || ''}</strong><div>${(c.comment_text || c.comment || '').slice(0,180)}</div><span class="text-muted">${c.created_at || ''} · ${c.author || ''}</span>`));
            }
            if (releases.length) {
                results.appendChild(section('Releases', releases, r => {
                    const start = r.release_start || r.start_date || 'Unknown';
                    const end = r.release_date || r.released_at || 'Ongoing';
                    return `<strong>${r.name || r.version || r.id}</strong><div>Project: ${r.project_key || ''}</div><span class="text-muted">${start} → ${end}</span>`;
                }));
            }

            if (!worklogs.length && !issues.length && !comments.length && !releases.length) {
                results.innerHTML = '<div style="color: var(--text-muted)">No Jira activity found for this range.</div>';
            }
        };

        const applyRangeFilter = async () => {
            const startDate = document.getElementById('jira-range-start').value;
            const endDate = document.getElementById('jira-range-end').value;
            const data = await fetchRangeData(startDate, endDate);
            renderRangeResults(data, startDate, endDate);
        };

        // Tab logic
        document.getElementById('tab-calendar').addEventListener('click', () => {
            document.getElementById('calendar-container').style.display = 'block';
            document.getElementById('day-details').style.display = 'none';
            document.getElementById('releases-container').style.display = 'none';
            document.getElementById('range-filter-container').style.display = 'none';
            document.getElementById('tab-calendar').classList.add('active');
            document.getElementById('tab-day').classList.remove('active');
            document.getElementById('tab-releases').classList.remove('active');
            document.getElementById('tab-filter').classList.remove('active');
        });
        document.getElementById('tab-day').addEventListener('click', () => {
            document.getElementById('calendar-container').style.display = 'none';
            document.getElementById('day-details').style.display = 'block';
            document.getElementById('releases-container').style.display = 'none';
            document.getElementById('range-filter-container').style.display = 'none';
            document.getElementById('tab-calendar').classList.remove('active');
            document.getElementById('tab-day').classList.add('active');
            document.getElementById('tab-releases').classList.remove('active');
            document.getElementById('tab-filter').classList.remove('active');
        });
        document.getElementById('tab-releases').addEventListener('click', () => {
            document.getElementById('calendar-container').style.display = 'none';
            document.getElementById('day-details').style.display = 'none';
            document.getElementById('releases-container').style.display = 'block';
            document.getElementById('range-filter-container').style.display = 'none';
            document.getElementById('tab-calendar').classList.remove('active');
            document.getElementById('tab-day').classList.remove('active');
            document.getElementById('tab-releases').classList.add('active');
            document.getElementById('tab-filter').classList.remove('active');
        });
        document.getElementById('tab-filter').addEventListener('click', () => {
            document.getElementById('calendar-container').style.display = 'none';
            document.getElementById('day-details').style.display = 'none';
            document.getElementById('releases-container').style.display = 'none';
            document.getElementById('range-filter-container').style.display = 'block';
            document.getElementById('tab-calendar').classList.remove('active');
            document.getElementById('tab-day').classList.remove('active');
            document.getElementById('tab-releases').classList.remove('active');
            document.getElementById('tab-filter').classList.add('active');
        });

        document.getElementById('jira-sync-btn').addEventListener('click', async () => {
            try {
                await API.post('/sync/jira');
                ui.showToast('Jira sync completed', 'success');
                const data = await fetchAll();
                renderCalendar(data.worklogs);
                renderReleases(data.releases);
            } catch (e) { setStatus('Sync failed'); }
        });

        const rangePanel = document.getElementById('range-filter-container');
        if (rangePanel) {
            rangePanel.innerHTML = `
                <div class="range-controls">
                    <div class="form-group">
                        <label class="form-label">Start Date</label>
                        <input type="date" id="jira-range-start" class="form-control" />
                    </div>
                    <div class="form-group">
                        <label class="form-label">End Date</label>
                        <input type="date" id="jira-range-end" class="form-control" />
                    </div>
                    <div style="display:flex; align-items:flex-end; gap:0.5rem;">
                        <button id="jira-range-apply" class="btn btn-primary">Apply Filter</button>
                    </div>
                </div>
                <div id="jira-range-results" style="margin-top:1rem;"></div>
            `;

            const defaultStart = new Date(calendarYear, calendarMonth, 1);
            const defaultEnd = new Date(calendarYear, calendarMonth + 1, 0);
            const pad = (value) => value < 10 ? `0${value}` : String(value);
            document.getElementById('jira-range-start').value = `${defaultStart.getFullYear()}-${pad(defaultStart.getMonth()+1)}-${pad(defaultStart.getDate())}`;
            document.getElementById('jira-range-end').value = `${defaultEnd.getFullYear()}-${pad(defaultEnd.getMonth()+1)}-${pad(defaultEnd.getDate())}`;
            document.getElementById('jira-range-apply').addEventListener('click', applyRangeFilter);
        }

        // initial load
        fetchAll().then(data => {
            renderCalendar(data.worklogs);
            renderReleases(data.releases);
        });

        document.getElementById('jira-export-btn').addEventListener('click', async () => {
            try {
                const result = await API.get('/reports/export');
                const blob = new Blob([result.markdown], { type: 'text/markdown;charset=utf-8' });
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = result.file_name || 'jira_report.md';
                document.body.appendChild(link);
                link.click();
                link.remove();
                ui.showToast('Markdown export ready for download.', 'success');
            } catch (e) { ui.showToast('Export failed', 'error'); }
        });

        // initial load
        fetchAll().then(data => {
            renderCalendar(data.worklogs);
            renderReleases(data.releases);
        });
    },

    async github() {
        DOM.viewContainer.innerHTML = `
            <div class="glass-card">
                <div class="card-header" style="justify-content: space-between; gap: 1rem; flex-wrap: wrap;">
                    <div>
                        <h3 class="card-title">GitHub Analytics</h3>
                        <p style="color: var(--text-muted); margin: 0.25rem 0 0;">View commits and pull requests for your GitHub username.</p>
                    </div>
                    <div style="display:flex; gap:0.75rem; flex-wrap: wrap; align-items: center;">
                        <input type="text" id="github-keyword-filter" class="form-control" placeholder="Keyword Filter" style="max-width:190px;" />
                        <input type="date" id="github-start-date" class="form-control" style="max-width:190px;" />
                        <input type="date" id="github-end-date" class="form-control" style="max-width:190px;" />
                        <button id="github-filter-btn" class="btn btn-secondary">Apply Filter</button>
                        <button id="github-export-btn" class="btn btn-primary">Export MD</button>
                        <button id="github-sync-btn" class="btn btn-primary">🔄 Sync GitHub</button>
                    </div>
                </div>

                <div class="table-section glass-card" style="margin-top:1rem; padding:1rem;">
                    <h4>Commits</h4>
                    <table class="table" style="width:100%">
                        <thead>
                            <tr>
                                <th>Repository</th>
                                <th>Message</th>
                                <th>Author</th>
                                <th>Date</th>
                            </tr>
                        </thead>
                        <tbody id="github-table-body">
                            <tr><td colspan="4">Loading...</td></tr>
                        </tbody>
                    </table>
                </div>

                <div class="table-section glass-card" style="margin-top:1rem; padding:1rem;">
                    <h4>Pull Requests</h4>
                    <table class="table" style="width:100%">
                        <thead>
                            <tr>
                                <th>Repository</th>
                                <th>Title</th>
                                <th>Status</th>
                                <th>Created</th>
                            </tr>
                        </thead>
                        <tbody id="github-prs-table-body">
                            <tr><td colspan="4">Loading...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        const loadGithubData = async () => {
            const keyword = document.getElementById('github-keyword-filter').value;
            const startDate = document.getElementById('github-start-date').value;
            const endDate = document.getElementById('github-end-date').value;
            const query = new URLSearchParams();
            if (keyword) query.append('keyword', keyword);
            if (startDate) query.append('start_date', startDate);
            if (endDate) query.append('end_date', endDate);
            const queryString = query.toString() ? `?${query.toString()}` : '';

            const commitBody = document.getElementById('github-table-body');
            const prBody = document.getElementById('github-prs-table-body');

            commitBody.innerHTML = '<tr><td colspan="4">Loading...</td></tr>';
            prBody.innerHTML = '<tr><td colspan="4">Loading...</td></tr>';

            try {
                const [commits, prs] = await Promise.all([
                    API.get(`/github/commits${queryString}`),
                    API.get(`/github/pull-requests${queryString}`),
                ]);

                commitBody.innerHTML = commits.length ? commits.map(commit => `
                    <tr>
                        <td>${commit.repo || ''}</td>
                        <td>${commit.commit_message || ''}</td>
                        <td>${commit.author || ''}</td>
                        <td>${commit.committed_at || ''}</td>
                    </tr>
                `).join('') : '<tr><td colspan="4">No commits found.</td></tr>';

                prBody.innerHTML = prs.length ? prs.map(pr => `
                    <tr>
                        <td>${pr.repo || ''}</td>
                        <td>${pr.title || ''}</td>
                        <td>${pr.status || ''}</td>
                        <td>${pr.created_at || ''}</td>
                    </tr>
                `).join('') : '<tr><td colspan="4">No pull requests found.</td></tr>';
            } catch (error) {
                commitBody.innerHTML = '<tr><td colspan="4">Failed to load GitHub commits.</td></tr>';
                prBody.innerHTML = '<tr><td colspan="4">Failed to load GitHub pull requests.</td></tr>';
            }
        };

        document.getElementById('github-filter-btn').addEventListener('click', loadGithubData);
        document.getElementById('github-sync-btn').addEventListener('click', async () => {
            try {
                const startDate = document.getElementById('github-start-date').value;
                const endDate = document.getElementById('github-end-date').value;
                const query = new URLSearchParams();
                if (startDate) query.append('since', startDate);
                if (endDate) query.append('until', endDate);
                await API.post(`/sync/github?${query.toString()}`);
                ui.showToast('GitHub sync completed', 'success');
                loadGithubData();
            } catch (e) { }
        });

        document.getElementById('github-export-btn').addEventListener('click', async () => {
            try {
                const startDate = document.getElementById('github-start-date').value;
                const endDate = document.getElementById('github-end-date').value;
                const query = new URLSearchParams();
                if (startDate) query.append('start_date', startDate);
                if (endDate) query.append('end_date', endDate);
                const result = await API.get(`/reports/export?${query.toString()}`);
                const blob = new Blob([result.markdown], { type: 'text/markdown;charset=utf-8' });
                const link = document.createElement('a');
                link.href = URL.createObjectURL(blob);
                link.download = result.file_name;
                document.body.appendChild(link);
                link.click();
                link.remove();
                ui.showToast('Markdown export ready for download.', 'success');
            } catch (e) { }
        });

        loadGithubData();
    },

    settings() {
        DOM.viewContainer.innerHTML = `
            <div class="glass-card" style="max-width: 800px; margin: 0 auto;">
                <div class="card-header">
                    <h3 class="card-title">Integration Settings</h3>
                </div>
                <form id="settings-form">
                    <h4 style="margin: 1.5rem 0 1rem;">GitHub Configuration</h4>
                    <div class="grid-2">
                        <div class="form-group">
                            <label class="form-label">GitHub Token</label>
                            <input type="password" id="github_token" class="form-control" placeholder="Personal Access Token (classic)">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Target Organization</label>
                            <input type="text" id="github_org" class="form-control" placeholder="e.g. your-organization">
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="form-label">GitHub Activity Keyword Filter</label>
                        <input type="text" id="github_activity_filter" class="form-control" placeholder="Optional keyword to filter commits and pull requests">
                    </div>
                </div>

                <h4 style="margin: 1.5rem 0 1rem;">Jira Configuration</h4>
                    <div class="grid-2">
                    <div class="form-group">
                        <label class="form-label">Jira Connection</label>
                        <button type="button" id="jira-connect-btn" class="btn btn-secondary" style="width:100%;">Connect Jira</button>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Connected Jira Base URL</label>
                        <input type="text" id="jira_base_url" class="form-control" placeholder="https://your-domain.atlassian.net">
                    </div>
                </div>
                <div class="grid-2">
                    <div class="form-group">
                        <label class="form-label">Jira Email</label>
                        <input type="email" id="jira_email" class="form-control">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Jira Password</label>
                        <input type="password" id="jira_password" class="form-control">
                    </div>
                </div>
                <div class="form-group">
                    <label class="form-label">Jira Project Keys</label>
                    <input type="text" id="jira_project_keys" class="form-control" placeholder="PROJECT1,PROJECT2">
                </div>
                    
                    <h4 style="margin: 1.5rem 0 1rem;">OpenAI Configuration (Optional)</h4>
                    <div class="form-group">
                        <label class="form-label">OpenAI API Key</label>
                        <input type="password" id="openai_api_key" class="form-control" placeholder="sk-...">
                    </div>
                    
                    <button type="submit" class="btn btn-primary">Save Settings</button>
                </form>

                <div style="margin-top: 3rem; border-top: 1px solid var(--border); padding-top: 2rem;">
                    <h4 style="color: #dc3545; margin-bottom: 1rem;">Danger Zone</h4>
                    <p style="color: var(--text-muted); margin-bottom: 1rem;">Clearing the database will remove all synced Jira and GitHub data, but will keep your user settings and logins intact.</p>
                    <button type="button" id="clear-db-btn" class="btn btn-secondary" style="background-color: rgba(220, 53, 69, 0.1); color: #dc3545; border: 1px solid rgba(220, 53, 69, 0.2); margin-right: 1rem;">Clear Database</button>
                    <button type="button" id="clear-creds-btn" class="btn btn-secondary" style="background-color: rgba(220, 53, 69, 0.1); color: #dc3545; border: 1px solid rgba(220, 53, 69, 0.2);">Clear Credentials</button>
                </div>
            </div>
        `;

        // Fetch current settings
        API.get('/settings').then(settings => {
            if (settings) {
                ['openai_api_key', 'jira_base_url', 'jira_email', 'jira_project_keys', 'github_org', 'github_token', 'github_activity_filter'].forEach(key => {
                    const el = document.getElementById(key);
                    if (el && settings[key]) el.value = settings[key];
                });
            }
        });



        document.getElementById('jira-connect-btn').addEventListener('click', () => {
            if (!state.token) {
                ui.showToast('Please log in before connecting Jira.', 'error');
                return;
            }
            window.location = `/project/jira-logger/api/auth/jira/login?state=${encodeURIComponent(state.token)}`;
        });

        document.getElementById('clear-db-btn').addEventListener('click', async () => {
            if (confirm('Are you sure you want to clear the database? This action cannot be undone.')) {
                try {
                    await API.post('/settings/clear-db');
                    ui.showToast('Database cleared successfully.', 'success');
                } catch (e) {
                    ui.showToast('Failed to clear database.', 'error');
                }
            }
        });

        document.getElementById('clear-creds-btn').addEventListener('click', async () => {
            if (confirm('Are you sure you want to clear all your saved credentials? This will log you out of GitHub and Jira.')) {
                try {
                    await API.post('/settings/clear-credentials');
                    ui.showToast('Credentials cleared successfully.', 'success');
                    ['openai_api_key', 'jira_base_url', 'jira_email', 'jira_password', 'jira_project_keys', 'github_org', 'github_token', 'github_activity_filter'].forEach(key => {
                        const el = document.getElementById(key);
                        if (el) el.value = '';
                    });
                } catch (e) {
                    ui.showToast('Failed to clear credentials.', 'error');
                }
            }
        });

        document.getElementById('settings-form').addEventListener('submit', async (e) => {
            e.preventDefault();

            const jiraSettings = {
                jira_base_url: document.getElementById('jira_base_url').value,
                jira_email: document.getElementById('jira_email').value,
                jira_password: document.getElementById('jira_password').value,
                jira_project_keys: document.getElementById('jira_project_keys').value,
            };

            const uiKey = document.getElementById('openai_api_key').value;
            const githubOrg = document.getElementById('github_org').value;
            const githubToken = document.getElementById('github_token').value;
            const githubFilter = document.getElementById('github_activity_filter').value;


            try {
                const settingsPayload = {};
                if (uiKey) settingsPayload.openai_api_key = uiKey;
                if (githubOrg) settingsPayload.github_org = githubOrg;
                if (githubToken) settingsPayload.github_token = githubToken;
                if (githubFilter) settingsPayload.github_activity_filter = githubFilter;
                // Also save jira project keys in general settings
                if (jiraSettings.jira_project_keys) {
                    settingsPayload.jira_project_keys = jiraSettings.jira_project_keys;
                }

                if (Object.keys(settingsPayload).length > 0) {
                    await API.request('/settings', { method: 'PUT', body: JSON.stringify(settingsPayload) });
                }

                if (jiraSettings.jira_base_url && jiraSettings.jira_email && jiraSettings.jira_password) {
                    try {
                        await API.post('/auth/jira/login', jiraSettings);
                    } catch (jiraErr) {
                        console.error('Jira login failed during settings save', jiraErr);
                        ui.showToast('Settings saved, but Jira login failed', 'error');
                        return; // Stop execution if Jira fails so we don't show general success
                    }
                }

                ui.showToast('Settings saved successfully', 'success');
            } catch (e) { 
                console.error('Settings save error:', e);
                ui.showToast('Failed to save settings', 'error');
            }
        });
    },

    async chat() {
        DOM.viewContainer.innerHTML = `
            <div class="glass-card">
                <div class="card-header" style="justify-content: space-between; gap: 1rem; flex-wrap: wrap;">
                    <div>
                        <h3 class="card-title">Activity Chat</h3>
                        <p style="color: var(--text-muted); margin: 0.25rem 0 0;">Ask questions about the Jira and GitHub activity we have synced.</p>
                    </div>
                    <div style="display:flex; gap:0.75rem; flex-wrap: wrap; align-items: center;">
                        <button id="chat-clear-btn" class="btn btn-secondary">Clear Chat</button>
                    </div>
                </div>
                <div id="chat-messages" class="chat-messages" style="min-height:320px; padding:1rem; background: var(--surface); border-radius: 16px; margin-top:1rem; overflow:auto;"></div>
                <div style="display:flex; gap:0.75rem; flex-wrap: wrap; margin-top:1rem; align-items:flex-end;">
                    <textarea id="chat-message" class="form-control" placeholder="Ask about your recent Jira and GitHub activity..." style="flex:1; min-height:120px;"></textarea>
                    <button id="chat-send-btn" class="btn btn-primary" style="min-width:150px;">Send</button>
                </div>
                <div id="chat-status" style="margin-top:0.75rem; color: var(--text-muted);">Your chat history will remain for up to 30 minutes in this session.</div>
            </div>
        `;

        const chatMessages = document.getElementById('chat-messages');
        const chatInput = document.getElementById('chat-message');
        const chatStatus = document.getElementById('chat-status');
        const chatSendBtn = document.getElementById('chat-send-btn');
        const chatClearBtn = document.getElementById('chat-clear-btn');

        const loadChatHistory = () => {
            const stored = sessionStorage.getItem('chat_history');
            if (!stored) {
                state.chatHistory = [];
                return;
            }
            try {
                const parsed = JSON.parse(stored);
                const createdAt = new Date(parsed.createdAt).getTime();
                const ttl = CHAT_SESSION_TTL_MINUTES * 60 * 1000;
                if (Date.now() - createdAt > ttl) {
                    sessionStorage.removeItem('chat_history');
                    state.chatHistory = [];
                } else {
                    state.chatHistory = parsed.history || [];
                }
            } catch (err) {
                state.chatHistory = [];
            }
        };

        const saveChatHistory = () => {
            sessionStorage.setItem('chat_history', JSON.stringify({
                createdAt: new Date().toISOString(),
                history: state.chatHistory,
            }));
        };

        const renderMessages = () => {
            if (!chatMessages) return;
            if (!state.chatHistory.length) {
                chatMessages.innerHTML = '<div style="color: var(--text-muted);">Start by asking a question about your activity.</div>';
                return;
            }
            chatMessages.innerHTML = state.chatHistory.map(msg => `
                <div class="chat-bubble ${msg.role}" style="margin-bottom:1rem; padding:1rem; border-radius:14px; background:${msg.role === 'user' ? 'rgba(21, 101, 192, 0.12)' : 'rgba(6, 24, 43, 0.08)'};">
                    <strong style="display:block; margin-bottom:0.5rem;">${msg.role === 'user' ? 'You' : 'Bot'}</strong>
                    <div style="white-space:pre-wrap; line-height:1.6;">${msg.content}</div>
                </div>
            `).join('');
            chatMessages.scrollTop = chatMessages.scrollHeight;
        };

        const appendMessage = (role, content) => {
            state.chatHistory.push({ role, content });
            saveChatHistory();
            renderMessages();
        };

        const sendMessage = async () => {
            const message = chatInput.value.trim();
            if (!message) return;
            appendMessage('user', message);
            chatInput.value = '';
            if (chatStatus) chatStatus.textContent = 'Thinking...';
            chatSendBtn.disabled = true;

            try {
                const response = await API.post('/chat', { message });
                appendMessage('assistant', response.reply || 'No reply returned.');
                if (chatStatus) chatStatus.textContent = 'Response received. Ask another question or clear the chat.';
            } catch (error) {
                appendMessage('assistant', `Error: ${error.message}`);
                if (chatStatus) chatStatus.textContent = 'Failed to get chat response.';
            } finally {
                chatSendBtn.disabled = false;
            }
        };

        chatClearBtn.addEventListener('click', () => {
            state.chatHistory = [];
            sessionStorage.removeItem('chat_history');
            renderMessages();
            if (chatStatus) chatStatus.textContent = 'Chat cleared. You can start again.';
        });

        chatSendBtn.addEventListener('click', sendMessage);
        chatInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        });

        loadChatHistory();
        renderMessages();
    },

    async reports() {
        DOM.viewContainer.innerHTML = `
            <div class="card-header">
                <h3 class="card-title">Generate AI Summary</h3>
                <div style="display:flex; gap:0.5rem;">
                    <button class="btn btn-primary" onclick="generateReport('daily')">Daily Standup</button>
                    <button class="btn btn-secondary" onclick="generateReport('weekly')">Weekly Report</button>
                </div>
            </div>
            <div id="report-output" class="glass-card" style="min-height: 200px; margin-top: 1rem;">
                <p style="color:var(--text-muted); text-align:center; margin-top:3rem;">Click a button above to generate a report using your synced data.</p>
            </div>
        `;

        window.generateReport = async (type) => {
            const out = document.getElementById('report-output');
            out.innerHTML = '<div style="text-align:center; padding: 2rem;">Generating report with AI... ⏳</div>';
            try {
                const res = await API.post('/reports/generate', { summary_type: type });
                // Simple markdown to HTML conversion for demo
                const htmlContent = res.summary
                    .replace(/^### (.*$)/gim, '<h4>$1</h4>')
                    .replace(/^## (.*$)/gim, '<h3>$1</h3>')
                    .replace(/^# (.*$)/gim, '<h2>$1</h2>')
                    .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
                    .replace(/\*(.*)\*/gim, '<em>$1</em>')
                    .replace(/\n/gim, '<br>');

                out.innerHTML = `<div style="line-height:1.6;">${htmlContent}</div>`;
                ui.showToast('Report generated', 'success');
            } catch (e) {
                out.innerHTML = `<p style="color:var(--danger)">Failed to generate report. Make sure OpenAI key is set.</p>`;
            }
        };
    },

    placeholder(name) {
        DOM.viewContainer.innerHTML = `
            <div class="glass-card">
                <h3 class="card-title">${name}</h3>
                <p style="color: var(--text-muted)">This view is under construction for the demo.</p>
            </div>
        `;
    }
};

// --- Router ---
const router = {
    routes: {
        '/overview': views.overview,
        '/github': views.github,
        '/jira': views.jira,
        '/chat': views.chat,
        '/correlations': () => views.placeholder('Correlations'),
        '/reports': views.reports,
        '/settings': views.settings
    },

    async navigate(path) {
        if (!auth.check()) {
            try {
                await API.get('/auth/me');
            }
            catch(e) {
                auth.logout();
                return false;
            }
        return;
        }

        window.location.hash = path;
        state.currentPath = path;
        ui.updateNav(path);

        const handler = this.routes[path] || this.routes['/overview'];
        handler();
    },

    init() {
        window.addEventListener('hashchange', () => {
            const path = window.location.hash.replace('#', '') || '/overview';
            this.navigate(path);
        });

        if (auth.check()) {
            const initialPath = window.location.hash.replace('#', '') || '/overview';
            this.navigate(initialPath);
        }
    }
};

// --- Event Listeners ---
DOM.themeToggle.addEventListener('click', () => ui.toggleTheme());
DOM.logoutBtn.addEventListener('click', () => auth.logout());

DOM.syncBtn.addEventListener('click', async () => {
    DOM.syncBtn.innerHTML = '<span class="btn-icon">⏳</span> Syncing...';
    DOM.syncBtn.disabled = true;
    try {
        await API.post('/sync');
        ui.showToast('Full sync completed successfully', 'success');
    } catch (e) {
        // Error handled in API client
    } finally {
        DOM.syncBtn.innerHTML = '<span class="btn-icon">🔄</span> Sync Data';
        DOM.syncBtn.disabled = false;
    }
});

DOM.mobileMenuBtn.addEventListener('click', () => {
    DOM.sidebar.classList.toggle('open');
});

// Close sidebar on mobile when clicking nav item
DOM.navItems.forEach(item => {
    item.addEventListener('click', () => {
        if (window.innerWidth <= 768) {
            DOM.sidebar.classList.remove('open');
        }
    });
});

// --- Initialization ---
ui.initTheme();
router.init();
