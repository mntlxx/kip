let layoutData = { active_tab: "main", tabs: [] };
let pluginsData = [];
let currentMode = 'user';
let selectedTabForPicker = null;

const Utils = {
    getSafeString(val) {
        if (val === null || val === undefined) return '';
        if (typeof val === 'object') return JSON.stringify(val);
        return String(val);
    },
    escapeHtml(str) {
        return this.getSafeString(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
};

const WidgetRegistry = {
    button(item, action, props, label) {
        let pluginTag = item.plugin.replace('Plugin', '').replace('Control', '');
        return `
            <div class="action-item" 
                 data-action-trigger 
                 data-plugin="${item.plugin}" 
                 data-action="${item.action}">
                <div class="action-title">${Utils.escapeHtml(label)}</div>
                <div class="action-meta">${Utils.escapeHtml(pluginTag)}</div>
            </div>
        `;
    },

    'buttons-group'(item, action, props, label) {
        let buttons = props.buttons || [];
        let pluginTag = item.plugin.replace('Plugin', '').replace('Control', '');

        return `
            <div class="widget-row" style="display: flex; flex-direction: column; gap: 8px;">
                <div class="action-title" style="margin-bottom: 4px;">${Utils.escapeHtml(label)}</div>
                <div style="display: flex; grid-template-columns: repeat(${buttons.length > 2 ? 2 : buttons.length}, 1fr); gap: 8px;">
                    ${buttons.map(btn => `
                        <button class="widget-btn action-item" style="margin: 0; min-height: 48px; display: flex; flex-direction: column; justify-content: center; align-items: center;"
                                data-action-trigger 
                                data-plugin="${item.plugin}" 
                                data-action="${item.action}"
                                data-value="${btn.value}">
                            <span class="action-title" style="font-size: 0.85rem;">${Utils.escapeHtml(btn.label)}</span>
                        </button>
                    `).join('')}
                </div>
            </div>
        `;
    },

    slider(item, action, props, label) {
        const min = props.min ?? 0;
        const max = props.max ?? 100;
        const step = props.step ?? 1;
        const val = props.default ?? min;

        return `
            <div class="widget-row">
                <div class="widget-header">
                    <span class="action-title">${Utils.escapeHtml(label)}</span>
                    <span class="slider-value" id="val-${item.plugin}-${item.action}">${val}</span>
                </div>
                <input type="range" class="widget-slider"
                       min="${min}" max="${max}" step="${step}" value="${val}"
                       data-action-trigger="input"
                       data-plugin="${item.plugin}" 
                       data-action="${item.action}"
                       data-target-label="val-${item.plugin}-${item.action}" />
            </div>
        `;
    },

    toggle(item, action, props, label) {
        const checked = props.default ? 'checked' : '';
        return `
            <div class="widget-row widget-toggle-row">
                <span class="action-title">${Utils.escapeHtml(label)}</span>
                <label class="switch">
                    <input type="checkbox" ${checked}
                           data-action-trigger="change"
                           data-plugin="${item.plugin}" 
                           data-action="${item.action}" />
                    <span class="slider round"></span>
                </label>
            </div>
        `;
    },

    select(item, action, props, label) {
        let options = props.options || [];
        if (!Array.isArray(options)) {
            options = (typeof options === 'object' && options !== null)
                ? Object.entries(options).map(([k, v]) => ({ value: k, label: v }))
                : [];
        }

        const defaultValue = props.default || (options[0]?.value ?? options[0] ?? '');

        const optionsHTML = options.map(opt => {
            const optVal = typeof opt === 'object' ? opt.value : opt;
            const optLbl = typeof opt === 'object' ? opt.label : opt;
            const isSelected = String(optVal) === String(defaultValue) ? 'selected' : '';
            return `<option value="${Utils.escapeHtml(optVal)}" ${isSelected}>${Utils.escapeHtml(optLbl)}</option>`;
        }).join('');

        return `
            <div class="widget-row">
                <div class="widget-header">
                    <span class="action-title">${Utils.escapeHtml(label)}</span>
                </div>
                <select class="widget-select" 
                        data-action-trigger="change"
                        data-plugin="${item.plugin}" 
                        data-action="${item.action}">
                    ${optionsHTML}
                </select>
            </div>
        `;
    },

    unknown(item, rawWidget) {
        return `
            <div class="widget-row widget-unknown">
                <span>Виджет [${Utils.escapeHtml(rawWidget || 'не указан')}] не поддерживается (${Utils.escapeHtml(item.plugin)}::${Utils.escapeHtml(item.action)})</span>
            </div>
        `;
    }
};

function renderWidget(item) {
    const plugin = pluginsData.find(p => p.id === item.plugin);
    const action = plugin?.actions?.[item.action] || null;
    const props = action?.props || {};
    const label = item.label || action?.label || item.action;

    const rawWidget = item.widget || action?.widget || 'button';
    const widgetType = String(rawWidget).toLowerCase().trim();

    const renderer = WidgetRegistry[widgetType] || ((i) => WidgetRegistry.unknown(i, rawWidget));
    return renderer(item, action, props, label);
}

function renderFeed(tabId) {
    const feedContainer = document.getElementById('feed');
    if (!feedContainer) return;

    const currentTab = (layoutData.tabs || []).find(t => t.id === tabId);
    
    const tabLabel = document.getElementById('tab-label');
    if (tabLabel) {
        tabLabel.innerText = currentTab ? `system // ${currentTab.title || currentTab.id}` : 'system  no tab';
    }

    if (!currentTab?.items?.length) {
        feedContainer.innerHTML = '<div class="empty-state">Нет элементов для отображения</div>';
        return;
    }

    feedContainer.innerHTML = currentTab.items.map(renderWidget).join('');
}

function renderNav() {
    const navContainer = document.getElementById('tab-nav');
    if (!navContainer || !layoutData.tabs) return;

    navContainer.innerHTML = layoutData.tabs.map(tab => `
        <button class="nav-tab ${tab.id === layoutData.active_tab ? 'active' : ''}" 
                data-tab-id="${tab.id}">
            ${Utils.escapeHtml(tab.title || tab.id)}
        </button>
    `).join('');
}

function renderUserModeBuilder() {
    const container = document.getElementById('builder-tabs-list');
    if (!container) return;

    container.innerHTML = (layoutData.tabs || []).map((tab) => `
        <div class="builder-tab-card">
            <div class="builder-tab-header">
                <input type="text" value="${Utils.escapeHtml(tab.title)}" 
                       onchange="updateTabTitle('${tab.id}', this.value)" 
                       placeholder="Название вкладки" class="input-mono" />
                <button class="btn-link" onclick="removeTab('${tab.id}')" style="color: #ff5555;">[удалить]</button>
            </div>
            
            <div class="builder-items-list">
                ${(tab.items || []).map((item, itemIdx) => {
                    const plugin = pluginsData.find(p => p.id === item.plugin);
                    const action = plugin?.actions?.[item.action];
                    const label = item.label || action?.label || item.action;
                    return `
                        <div class="builder-item-row">
                            <span style="font-family: var(--font-mono); font-size: 0.8rem;"><b>${Utils.escapeHtml(item.plugin)}</b>:${Utils.escapeHtml(label)}</span>
                            <button class="btn-link" onclick="removeItemFromTab('${tab.id}',${itemIdx})" style="color: #ff5555;">[×]</button>
                        </div>
                    `;
                }).join('')}
            </div>
            <button class="btn-link btn-add" onclick="openPickerForTab('${tab.id}')">+ [добавить элемент]</button>
        </div>
    `).join('');
}

function updateTabTitle(tabId, newTitle) {
    const tab = layoutData.tabs.find(t => t.id === tabId);
    if (tab) tab.title = newTitle;
}

function addTab() {
    const newId = 'tab_' + Date.now();
    layoutData.tabs.push({ id: newId, title: 'Новая вкладка', items: [] });
    renderUserModeBuilder();
}

function removeTab(tabId) {
    layoutData.tabs = layoutData.tabs.filter(t => t.id !== tabId);
    if (layoutData.active_tab === tabId) {
        layoutData.active_tab = layoutData.tabs[0]?.id || '';
    }
    renderUserModeBuilder();
}

function removeItemFromTab(tabId, itemIdx) {
    const tab = layoutData.tabs.find(t => t.id === tabId);
    if (tab && tab.items) {
        tab.items.splice(itemIdx, 1);
        renderUserModeBuilder();
    }
}

function openPickerForTab(tabId) {
    selectedTabForPicker = tabId;
    const pickerContent = document.getElementById('picker-content');
    if (!pickerContent) return;

    pickerContent.innerHTML = pluginsData.map(plugin => `
        <div style="margin-bottom: 15px;">
            <div style="font-weight: bold; border-bottom: 1px solid #444; padding-bottom: 4px; margin-bottom: 6px;">
                ${Utils.escapeHtml(plugin.name || plugin.id)}
            </div>
            <div style="display: flex; flex-direction: column; gap: 4px;">
                ${Object.entries(plugin.actions || {}).map(([actKey, actData]) => `
                    <button class="btn-link" style="text-align: left; background: #222; padding: 6px;" 
                            onclick="selectActionForTab('${plugin.id}', '${actKey}')">
                        + ${Utils.escapeHtml(actData.label || actKey)} (${Utils.escapeHtml(actData.widget || 'button')})
                    </button>
                `).join('')}
            </div>
        </div>
    `).join('');

    toggleModal('picker-modal', true);
}

function selectActionForTab(pluginId, actionKey) {
    const tab = layoutData.tabs.find(t => t.id === selectedTabForPicker);
    if (tab) {
        if (!tab.items) tab.items = [];
        tab.items.push({ plugin: pluginId, action: actionKey });
        renderUserModeBuilder();
    }
    toggleModal('picker-modal', false);
}

function renderDevModeInfo() {
    const pluginsList = document.getElementById('plugins-list');
    if (pluginsList) {
        pluginsList.innerHTML = `<pre style="background: #111; color: #0f0; padding: 10px; font-size: 12px; overflow-x: auto;">${Utils.escapeHtml(JSON.stringify(pluginsData, null, 2))}</pre>`;
    }
}

async function triggerAction(plugin, action, value = null) {
    try {
        const res = await fetch(`/api/plugins/${plugin}/actions/${action}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ value })
        });
        if (!res.ok) throw new Error(`Status: ${res.status}`);
    } catch (e) {
        console.error(`[API Error] ${plugin}.${action}:`, e);
    }
}

function setupGlobalEventListeners() {
    document.getElementById('btn-config')?.addEventListener('click', () => {
        toggleModal('modal', true);
    });

    document.getElementById('btn-close')?.addEventListener('click', () => {
        toggleModal('modal', false);
    });

    document.getElementById('btn-apply')?.addEventListener('click', () => {
        saveLayoutToServer();
    });

    document.getElementById('btn-mode-toggle')?.addEventListener('click', (e) => {
        currentMode = currentMode === 'user' ? 'dev' : 'user';
        e.target.innerText = `[mode: ${currentMode}]`;
        
        const userView = document.getElementById('view-user-mode');
        const devView = document.getElementById('view-dev-mode');
        
        if (userView && devView) {
            userView.style.display = currentMode === 'user' ? 'block' : 'none';
            devView.style.display = currentMode === 'dev' ? 'block' : 'none';
        }

        if (currentMode === 'dev') renderDevModeInfo();
    });

    document.getElementById('btn-close-picker')?.addEventListener('click', () => {
        toggleModal('picker-modal', false);
    });

    document.getElementById('btn-add-tab')?.addEventListener('click', () => {
        addTab();
    });

    document.getElementById('tab-nav')?.addEventListener('click', (e) => {
        const tabBtn = e.target.closest('[data-tab-id]');
        if (tabBtn) {
            const tabId = tabBtn.dataset.tabId;
            layoutData.active_tab = tabId;
            renderNav();
            renderFeed(tabId);
        }
    });

    const feed = document.getElementById('feed');
    if (feed) {
        feed.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-action-trigger]:not(input):not(select)');
            if (btn) {
                const plugin = btn.dataset.plugin;
                const action = btn.dataset.action;
                const value = btn.dataset.value !== undefined ? btn.dataset.value : null;
                triggerAction(plugin, action, value);
            }
        });

        const handleInputChange = (e) => {
            const elem = e.target.closest('[data-action-trigger]');
            if (!elem) return;

            const { plugin, action, targetLabel } = elem.dataset;
            let val;

            if (elem.type === 'checkbox') {
                val = elem.checked;
            } else if (elem.type === 'range') {
                val = Number(elem.value);
                if (targetLabel) {
                    const labelElem = document.getElementById(targetLabel);
                    if (labelElem) labelElem.innerText = val;
                }
            } else {
                val = elem.value;
            }

            triggerAction(plugin, action, val);
        };

        feed.addEventListener('change', handleInputChange);
        feed.addEventListener('input', (e) => {
            if (e.target.type === 'range') handleInputChange(e);
        });
    }
}

async function initApp() {
    try {
        const [layoutRes, pluginsRes] = await Promise.all([
            fetch('/api/layout'),
            fetch('/api/plugins')
        ]);

        if (!layoutRes.ok) {
            throw new Error(`/api/layout вернул статус ${layoutRes.status}`);
        }
        if (!pluginsRes.ok) {
            const errText = await pluginsRes.text().catch(() => '');
            throw new Error(`/api/plugins вернул статус ${pluginsRes.status}: ${errText}`);
        }

        layoutData = await layoutRes.json();
        pluginsData = await pluginsRes.json();

        setupGlobalEventListeners();
        renderNav();
        renderFeed(layoutData.active_tab || layoutData.tabs[0]?.id);
    } catch (e) {
        console.error("Initialization error:", e);
        alert("Ошибка инициализации: " + e.message);
    }
}

async function saveLayoutToServer() {
    if (currentMode === 'dev') {
        try {
            layoutData = JSON.parse(document.getElementById('layout-json').value);
        } catch (jsonErr) {
            alert("Ошибка в синтаксисе JSON: " + jsonErr.message);
            return;
        }
    }

    try {
        const res = await fetch('/api/layout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(layoutData)
        });

        if (!res.ok) throw new Error(`Код ответа: ${res.status}`);

        toggleModal('modal', false);
        renderNav();
        renderFeed(layoutData.active_tab || layoutData.tabs[0]?.id);
    } catch (e) {
        alert("Не удалось сохранить конфигурацию: " + e.message);
    }
}

function toggleModal(modalId, show) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    modal.style.display = show ? 'flex' : 'none';

    if (show && modalId === 'modal') {
        renderUserModeBuilder();
        renderDevModeInfo();
        const jsonArea = document.getElementById('layout-json');
        if (jsonArea) jsonArea.value = JSON.stringify(layoutData, null, 2);
    }
}

document.addEventListener('DOMContentLoaded', initApp);