// =============================================================================
// STATE
// =============================================================================

const project = {
    jobDetails: {
        preparedBy: '',
        kerfWidth: 25
    },
    tabs: [],
    activeTabId: null,
    skippedData: []
};

const wizard = { reachedStep: 1 };

let tabCounter    = 0;
let binIdCounter  = 0;
let _editTabId    = null;
let _editCutIndex = null;
let _stickEditTabId = null;
let _stickEditBinId = null;
let _dragSource      = null; // { tabId, binId, cutIndex }

// =============================================================================
// STATE ACCESSORS
// =============================================================================

function getTab(tabId) { return project.tabs.find(t => t.id === tabId); }
function getActiveTab() { return getTab(project.activeTabId); }

function readJobDetailsFromDOM() {
    project.jobDetails.preparedBy = document.getElementById('preparedBy').value;
    project.jobDetails.kerfWidth  = parseFloat(document.getElementById('kerfWidth').value) || 25;
}

function writeJobDetailsToDOM() {
    document.getElementById('preparedBy').value = project.jobDetails.preparedBy;
    document.getElementById('kerfWidth').value  = project.jobDetails.kerfWidth;
}

// =============================================================================
// INITIALISATION
// =============================================================================

document.addEventListener('DOMContentLoaded', function () {
    if (window.CUTLIST_PRINT_MODE) return;
    initJobDetailListeners();
    initGlobalEventListeners();
    initCSVDropzone();
    if (window.CUTLIST_STATE && window.CUTLIST_STATE.tabs && window.CUTLIST_STATE.tabs.length) {
        restoreProject(window.CUTLIST_STATE);
    }
});

function initJobDetailListeners() {
    document.getElementById('preparedBy').addEventListener('input', e => {
        project.jobDetails.preparedBy = e.target.value;
    });
    document.getElementById('kerfWidth').addEventListener('input', e => {
        project.jobDetails.kerfWidth = parseFloat(e.target.value) || 25;
    });
}

function initGlobalEventListeners() {
    document.getElementById('copySkippedBtn').addEventListener('click', copySkippedToClipboard);
    document.getElementById('saveProjectBtn').addEventListener('click', saveProject);
    document.getElementById('exportProjectBtn').addEventListener('click', exportProjectJSON);
    document.getElementById('loadProjectBtn').addEventListener('click', () => {
        document.getElementById('loadProjectInput').click();
    });
    document.getElementById('loadProjectInput').addEventListener('change', loadProject);
    document.getElementById('printBtn').addEventListener('click', openPrintView);
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') { closeCutEditor(); closeConvertModal(); }
    });
}

function initCSVDropzone() {
    const textarea = document.getElementById('csvInput');
    textarea.addEventListener('dragover', e => {
        e.preventDefault();
        textarea.classList.add('drag-over');
    });
    textarea.addEventListener('dragleave', () => textarea.classList.remove('drag-over'));
    textarea.addEventListener('drop', e => {
        e.preventDefault();
        textarea.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        if (file && (file.name.endsWith('.csv') || file.type === 'text/csv')) {
            loadCSVFile(file);
        } else if (file) {
            showToast('Please drop a CSV file', 'error');
        }
    });
    document.getElementById('csvFileInput').addEventListener('change', e => {
        const file = e.target.files[0];
        if (file) loadCSVFile(file);
        e.target.value = '';
    });
}

function loadCSVFile(file) {
    const reader = new FileReader();
    reader.onload = e => { document.getElementById('csvInput').value = e.target.result; };
    reader.readAsText(file);
}

// =============================================================================
// WIZARD NAVIGATION
// =============================================================================

function openStep(n) {
    for (let i = 1; i <= 5; i++) {
        const body   = document.getElementById(`step-${i}-body`);
        const stepEl = document.getElementById(`step-${i}`);
        if (body)   body.style.display = 'none';
        if (stepEl) stepEl.classList.remove('step--open');
    }
    const body   = document.getElementById(`step-${n}-body`);
    const stepEl = document.getElementById(`step-${n}`);
    if (body)   body.style.display = '';
    if (stepEl) stepEl.classList.add('step--open');
    wizard.currentStep = n;
    if (stepEl) stepEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function advanceToStep(n) {
    wizard.reachedStep = Math.max(wizard.reachedStep, n);
    for (let i = 1; i <= wizard.reachedStep; i++) {
        const el = document.getElementById(`step-${i}`);
        if (el) el.classList.remove('wizard-step--locked');
    }
    openStep(n);
}

function goToStep(n) {
    if (n > wizard.reachedStep) return;
    openStep(n);
}

function setStepMeta(n, text) {
    const el = document.getElementById(`step-${n}-meta`);
    if (el) el.textContent = text;
}

function markStepDone(n) {
    const el = document.getElementById(`step-${n}`);
    if (el) el.classList.add('step--done');
}

function completeStep1() {
    readJobDetailsFromDOM();
    const label = project.jobDetails.preparedBy
        ? `Prepared by ${project.jobDetails.preparedBy}`
        : 'Set';
    setStepMeta(1, label);
    markStepDone(1);
    advanceToStep(2);
}

function completeStep2() {
    const csvText = document.getElementById('csvInput').value.trim();
    if (!csvText) {
        showToast('Please enter or paste your cut list first', 'warning');
        return;
    }
    const success = parseCSVIntoTabs(csvText);
    if (!success) return;

    resetFromStep(3);
    renderReviewStep();

    const totalCuts = project.tabs.reduce((s, t) => s + t.cuts.length, 0);
    setStepMeta(2, `${project.tabs.length} member type${project.tabs.length !== 1 ? 's' : ''}, ${totalCuts} cuts`);
    markStepDone(2);
    advanceToStep(3);
}

function resetFromStep(n) {
    if (n <= 3) document.getElementById('reviewContent').innerHTML = '';
    if (n <= 4) {
        document.getElementById('tabsList').innerHTML    = '';
        document.getElementById('tabsContent').innerHTML = '';
        project.tabs.forEach(t => { t.results = null; });
    }
    if (n <= 5) document.getElementById('summaryContent').innerHTML = '';

    wizard.reachedStep = Math.max(1, n - 1);
    for (let i = n; i <= 5; i++) {
        const el = document.getElementById(`step-${i}`);
        if (el) {
            el.classList.add('wizard-step--locked');
            el.classList.remove('step--done', 'step--open');
        }
        setStepMeta(i, '');
        if (i === n - 1) {
            // Re-open the last valid step
        }
    }
}

// =============================================================================
// TIMBER HELPERS
// =============================================================================

function getTimberType(memberName) {
    const name = memberName.toUpperCase();
    if (name.includes('LIB'))   return 'LIB';
    if (name.includes('LVL8'))  return 'LVL8';
    if (name.includes('LVL11')) return 'LVL11';
    if (name.includes('LVL13')) return 'LVL13';
    if (name.includes('GL'))    return 'GL';
    return 'OTHER';
}

// Whitespace/case-normalized lookup key — mirrors _normalize_member_name() in cutlist/views.py.
function normalizeMemberName(name) {
    return (name || '').replace(/\s+/g, '').toUpperCase();
}

function lookupMemberProductId(memberName) {
    const mapping = (window.CUTLIST_MEMBER_MAPPINGS || {})[normalizeMemberName(memberName)];
    return mapping ? mapping.product_id : null;
}

// Last-resort safety net only — used if the DB-backed timber-type default is somehow missing
// (e.g. a fresh install before the seed migration runs). Normal operation never reaches this.
const FALLBACK_STOCK_LENGTHS = [7200, 6000, 5400, 4800, 3600];

// Default stock lengths for a new tab: prefer the specific list for a linked Product (editable
// in Django admin — Product.stock_lengths), else the broader per-timber-type default (also
// admin-editable — TimberTypeDefaultStockLengths), else the hardcoded safety net above.
function getDefaultStockLengths(memberName, productId) {
    if (productId) {
        const product = (window.CUTLIST_PRODUCTS || []).find(p => p.id === productId);
        if (product && product.stock_lengths) {
            const lengths = product.stock_lengths.split(',').map(v => parseInt(v.trim(), 10)).filter(v => !isNaN(v));
            if (lengths.length) return lengths;
        }
    }
    const timberType = getTimberType(memberName);
    const byType = (window.CUTLIST_TIMBER_TYPE_DEFAULTS || {})[timberType];
    return (byType && byType.length) ? byType : FALLBACK_STOCK_LENGTHS;
}

// =============================================================================
// CSV IMPORT
// =============================================================================

function parseCSVIntoTabs(csvText) {
    const lines      = csvText.split('\n').filter(line => line.trim());
    const parsedData = {};

    lines.forEach(line => {
        const parts = line.split(',').map(s => s.trim());
        if (parts.length >= 3) {
            const memberName = parts[0];
            const quantity   = parseInt(parts[1]);
            const length     = parseFloat(parts[2]);
            const mark       = parts[3] || '';
            const group      = parts[4] || '';
            if (!isNaN(length) && !isNaN(quantity) && memberName) {
                if (!parsedData[memberName]) parsedData[memberName] = [];
                parsedData[memberName].push({ length, quantity, mark, group });
            }
        }
    });

    const memberNames = Object.keys(parsedData);
    if (memberNames.length === 0) {
        showToast('No valid data found. Format: Member Name, Qty, Length, Mark, Group', 'error');
        return false;
    }

    project.tabs        = [];
    project.activeTabId = null;
    tabCounter          = 0;

    memberNames.slice(0, 5).forEach(memberName => {
        const cuts      = sortAndCombineCuts(parsedData[memberName]);
        const tabId     = `tab-${tabCounter++}`;
        const productId = lookupMemberProductId(memberName);
        project.tabs.push({
            id: tabId, memberName, cuts,
            stockLengths: getDefaultStockLengths(memberName, productId),
            productId,
            cutTolerance: 50, overlengthSplitStock: 6000, results: null
        });
    });

    const skippedMembers = memberNames.slice(5);
    if (skippedMembers.length > 0) {
        displaySkippedMembers(skippedMembers, parsedData);
    } else {
        document.getElementById('skippedMembers').style.display = 'none';
    }

    return true;
}

function sortAndCombineCuts(cuts) {
    const combined = {};
    cuts.forEach(cut => {
        const key = `${cut.length}:${cut.mark || ''}:${cut.group || ''}`;
        if (combined[key]) {
            combined[key].quantity += cut.quantity;
        } else {
            combined[key] = { length: cut.length, quantity: cut.quantity, mark: cut.mark || '', group: cut.group || '' };
        }
    });
    return Object.values(combined).sort((a, b) => b.length - a.length);
}

function displaySkippedMembers(skippedMembers, parsedData) {
    const tbody = document.querySelector('#skippedTable tbody');
    tbody.innerHTML    = '';
    project.skippedData = [];

    skippedMembers.forEach(memberName => {
        const cuts     = parsedData[memberName];
        const cutsText = cuts.map(c => `${c.length}, ${c.quantity}`).join('\n');
        const row      = document.createElement('tr');
        row.innerHTML  = `<td>${memberName}</td><td style="white-space:pre-line;">${cutsText}</td>`;
        tbody.appendChild(row);
        cuts.forEach(c => project.skippedData.push(`${c.length}, ${c.quantity}, ${memberName}`));
    });

    document.getElementById('skippedMembers').style.display = 'block';
}

function copySkippedToClipboard() {
    const text = project.skippedData.join('\n');
    navigator.clipboard.writeText(text)
        .then(() => showToast('Skipped members copied to clipboard', 'success'))
        .catch(() => showToast('Failed to copy to clipboard', 'error'));
}

// =============================================================================
// REVIEW STEP (Step 3)
// =============================================================================

function renderReviewStep() {
    const container = document.getElementById('reviewContent');
    container.innerHTML = '';
    project.tabs.forEach(tab => {
        container.insertAdjacentHTML('beforeend', generateReviewMemberHTML(tab));
        attachReviewEventListeners(tab.id);
    });
}

function generateReviewMemberHTML(tab) {
    return `
        <div class="review-member collapsed" data-tab-id="${tab.id}">
            <div class="review-member__header" onclick="toggleReviewMember('${tab.id}')">
                <span class="review-member__name">${tab.memberName}</span>
                <span class="review-member__count">${tab.cuts.length} cut${tab.cuts.length !== 1 ? 's' : ''}</span>
                <span class="chevron" style="font-size:1rem;transform:rotate(-90deg);">&#8964;</span>
            </div>
            <div class="review-member__body">
                ${generateReviewMemberBodyHTML(tab)}
            </div>
        </div>`;
}

function generateCutRowHTML(tabId, cut, index) {
    return `
        <tr class="cut-row">
            <td><input type="number" class="cut-length"   data-index="${index}" value="${cut.length}"       min="0"></td>
            <td><input type="number" class="cut-quantity" data-index="${index}" value="${cut.quantity}"     min="1"></td>
            <td><input type="text"   class="cut-mark"     data-index="${index}" value="${cut.mark   || ''}" maxlength="10" placeholder="—"></td>
            <td><input type="text"   class="cut-group"    data-index="${index}" value="${cut.group  || ''}" maxlength="20" placeholder="—"></td>
            <td><button class="btn-small" onclick="removeCut('${tabId}', ${index})">×</button></td>
        </tr>`;
}

function generateReviewMemberBodyHTML(tab) {
    // Group cuts by group name, preserving original indices
    const grouped = {};
    tab.cuts.forEach((cut, index) => {
        const key = cut.group || '';
        if (!grouped[key]) grouped[key] = [];
        grouped[key].push({ cut, index });
    });

    const groupKeys  = Object.keys(grouped).sort((a, b) => {
        if (a === '') return 1;
        if (b === '') return -1;
        return a.localeCompare(b);
    });
    const hasGroups = groupKeys.some(k => k !== '');

    let cutsHTML;
    if (!hasGroups) {
        const rows = tab.cuts.map((cut, index) => generateCutRowHTML(tab.id, cut, index)).join('');
        cutsHTML = `
            <table class="cuts-table">
                <thead><tr><th>Length (mm)</th><th>Qty</th><th>Mark</th><th>Group</th><th></th></tr></thead>
                <tbody>${rows}</tbody>
            </table>`;
    } else {
        cutsHTML = groupKeys.map(groupKey => {
            const label       = groupKey || 'Ungrouped';
            const isUngrouped = groupKey === '';
            const rows        = grouped[groupKey].map(({ cut, index }) => generateCutRowHTML(tab.id, cut, index)).join('');
            return `
                <div class="cut-group-section">
                    <div class="cut-group-header" onclick="toggleCutGroup(this)">
                        <span class="cut-group-label${isUngrouped ? ' cut-group-label--ungrouped' : ''}">${label}</span>
                        <span class="cut-group-count">${grouped[groupKey].length} cut${grouped[groupKey].length !== 1 ? 's' : ''}</span>
                        <span class="chevron" style="font-size:.9rem;">&#8964;</span>
                    </div>
                    <div class="cut-group-body">
                        <table class="cuts-table">
                            <thead><tr><th>Length (mm)</th><th>Qty</th><th>Mark</th><th>Group</th><th></th></tr></thead>
                            <tbody>${rows}</tbody>
                        </table>
                    </div>
                </div>`;
        }).join('');
    }

    const stockItems = tab.stockLengths.map((length, index) => `
        <div class="stock-item">
            <input type="number" class="stock-length" data-index="${index}" value="${length}" min="0">
            <button class="btn-small" onclick="removeStock('${tab.id}', ${index})">×</button>
        </div>`).join('');

    const products = window.CUTLIST_PRODUCTS || [];
    const productOptions = products.map(p =>
        `<option value="${p.id}" ${tab.productId === p.id ? 'selected' : ''}>${p.name} (${p.product_type__name})</option>`
    ).join('');

    return `
        <div class="member-settings">
            <div class="settings-grid" style="grid-template-columns:1fr 1fr 1fr 1fr;">
                <div class="form-group">
                    <label>Member Size</label>
                    <input type="text" class="member-name" maxlength="20" value="${tab.memberName}"
                           placeholder="e.g. 240x45 LIB"
                           style="font-weight:700;color:var(--brown-dark);">
                </div>
                <div class="form-group">
                    <label>Product</label>
                    <select class="member-product">
                        <option value="">— Not linked (generic defaults) —</option>
                        ${productOptions}
                    </select>
                </div>
                <div class="form-group">
                    <label>Cut Tolerance (mm)</label>
                    <input type="number" class="cut-tolerance" value="${tab.cutTolerance}" min="0" max="500">
                </div>
                <div class="form-group">
                    <label>Overlength Split (mm)</label>
                    <input type="number" class="overlength-split-stock" value="${tab.overlengthSplitStock}" min="0">
                </div>
            </div>
        </div>

        <div>
            <h3 style="font-size:0.78rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;
                       color:var(--charcoal);margin-bottom:.5rem;padding-bottom:.3rem;border-bottom:2px solid var(--border);">
                Required Cuts
            </h3>
            ${cutsHTML}
            <button class="btn btn-secondary" style="font-size:0.78rem;padding:.3rem .75rem;margin-top:.5rem;"
                    onclick="addCut('${tab.id}')">+ Add Cut</button>
        </div>

        <div class="stock-container">
            <h3>Stock Lengths (mm)</h3>
            <div class="stock-list">${stockItems}</div>
            <button class="btn btn-secondary" style="font-size:0.78rem;padding:.3rem .75rem;"
                    onclick="addStock('${tab.id}')">+ Add Stock Length</button>
        </div>`;
}

function attachReviewEventListeners(tabId) {
    const section = document.querySelector(`.review-member[data-tab-id="${tabId}"]`);
    if (!section) return;
    const tab = getTab(tabId);

    section.querySelector('.member-name')?.addEventListener('input', e => {
        tab.memberName = e.target.value;
        const nameSpan = section.querySelector('.review-member__name');
        if (nameSpan) nameSpan.textContent = e.target.value;
    });

    section.querySelector('.member-product')?.addEventListener('change', e => {
        tab.productId = e.target.value ? parseInt(e.target.value, 10) : null;
        saveMemberMapping(tab.memberName, tab.productId);
    });

    section.querySelector('.cut-tolerance')?.addEventListener('input', e => {
        tab.cutTolerance = parseFloat(e.target.value) || 0;
    });

    section.querySelector('.overlength-split-stock')?.addEventListener('input', e => {
        tab.overlengthSplitStock = parseFloat(e.target.value) || 6000;
    });

    section.querySelectorAll('.cut-length, .cut-quantity, .cut-mark, .cut-group').forEach(input => {
        input.addEventListener('input', e => {
            const index = parseInt(e.target.dataset.index);
            if      (e.target.classList.contains('cut-length'))   tab.cuts[index].length   = parseFloat(e.target.value) || 0;
            else if (e.target.classList.contains('cut-quantity'))  tab.cuts[index].quantity = parseInt(e.target.value)   || 1;
            else if (e.target.classList.contains('cut-mark'))      tab.cuts[index].mark     = e.target.value;
            else if (e.target.classList.contains('cut-group')) {
                tab.cuts[index].group = e.target.value;
            }
        });
    });

    section.querySelectorAll('.stock-length').forEach(input => {
        input.addEventListener('input', e => {
            const index = parseInt(e.target.dataset.index);
            tab.stockLengths[index] = parseFloat(e.target.value) || 0;
        });
    });
}

// Remembers a raw member name -> Product link so it auto-applies on future imports (fire and
// forget, mirroring the auto-save convention used for manual stick overrides — this is a
// low-stakes, easily-corrected convenience mapping, not something worth blocking the UI on).
function saveMemberMapping(rawName, productId) {
    if (!rawName) return;
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    fetch(window.CUTLIST_MEMBER_MAPPING_SAVE_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify({ raw_name: rawName, product_id: productId })
    }).catch(e => console.error('Member mapping save failed:', e));
}

function toggleReviewMember(tabId) {
    const section = document.querySelector(`.review-member[data-tab-id="${tabId}"]`);
    if (!section) return;
    const chevron   = section.querySelector('.review-member__header .chevron');
    const collapsed = section.classList.toggle('collapsed');
    if (chevron) chevron.style.transform = collapsed ? 'rotate(-90deg)' : '';
}

function toggleCutGroup(header) {
    const section   = header.closest('.cut-group-section');
    const body      = section.querySelector('.cut-group-body');
    const chevron   = header.querySelector('.chevron');
    const collapsed = section.classList.toggle('collapsed');
    body.style.display      = collapsed ? 'none' : '';
    chevron.style.transform = collapsed ? 'rotate(-90deg)' : '';
}

function addManualMember() {
    if (project.tabs.length >= 5) {
        showToast('Maximum 5 member types allowed', 'warning');
        return;
    }
    const tabId = `tab-${tabCounter++}`;
    const tab   = {
        id: tabId,
        memberName: `Member ${tabCounter}`,
        cuts: [],
        stockLengths: getDefaultStockLengths('', null),
        productId: null,
        cutTolerance: 50,
        overlengthSplitStock: 6000,
        results: null
    };
    project.tabs.push(tab);
    const container = document.getElementById('reviewContent');
    container.insertAdjacentHTML('beforeend', generateReviewMemberHTML(tab));
    attachReviewEventListeners(tab.id);
    container.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// =============================================================================
// RESULTS TABS (Step 4)
// =============================================================================

function renderResultsTabs() {
    document.getElementById('tabsList').innerHTML    = '';
    document.getElementById('tabsContent').innerHTML = '';

    project.tabs.forEach(tab => {
        renderTabButton(tab);
        renderTabContent(tab);
        if (tab.results) displayResults(tab.id);
    });

    if (project.tabs.length > 0) activateTab(project.tabs[0].id);
}

function renderTabButton(tab) {
    const existing = document.querySelector(`.tab[data-tab-id="${tab.id}"]`);
    if (existing) existing.remove();

    const tabButton       = document.createElement('div');
    tabButton.className   = 'tab';
    tabButton.dataset.tabId = tab.id;
    tabButton.innerHTML   = `
        <span>${tab.memberName}</span>
        <button class="btn-danger" onclick="removeTab('${tab.id}')" title="Remove">×</button>`;
    tabButton.onclick = e => {
        if (!e.target.classList.contains('btn-danger')) activateTab(tab.id);
    };
    document.getElementById('tabsList').appendChild(tabButton);
    if (tab.id === project.activeTabId) tabButton.classList.add('active');
}

function renderTabContent(tab) {
    const existing = document.querySelector(`.tab-content[data-tab-id="${tab.id}"]`);
    if (existing) existing.remove();

    const tabContent          = document.createElement('div');
    tabContent.className      = 'tab-content';
    tabContent.dataset.tabId  = tab.id;
    tabContent.innerHTML      = generateTabContentHTML(tab);
    if (tab.id === project.activeTabId) tabContent.classList.add('active');
    document.getElementById('tabsContent').appendChild(tabContent);
}

function generateTabContentHTML(tab) {
    return `<div class="member-section"><div class="results"></div></div>`;
}

function activateTab(tabId) {
    project.activeTabId = tabId;
    document.querySelectorAll('.tab').forEach(el => {
        el.classList.toggle('active', el.dataset.tabId === tabId);
    });
    document.querySelectorAll('.tab-content').forEach(el => {
        el.classList.toggle('active', el.dataset.tabId === tabId);
    });
}

function updateTabButton(tabId) {
    const tab       = getTab(tabId);
    const tabButton = document.querySelector(`.tab[data-tab-id="${tabId}"]`);
    if (tabButton && tab) tabButton.querySelector('span').textContent = tab.memberName;
}

function removeTab(tabId) {
    if (!confirm('Remove this member type?')) return;
    project.tabs = project.tabs.filter(t => t.id !== tabId);

    document.querySelector(`.tab[data-tab-id="${tabId}"]`)?.remove();
    document.querySelector(`.tab-content[data-tab-id="${tabId}"]`)?.remove();
    document.querySelector(`.review-member[data-tab-id="${tabId}"]`)?.remove();

    if (project.tabs.length > 0 && project.activeTabId === tabId) {
        activateTab(project.tabs[0].id);
    }
}

function refreshTab(tabId) {
    const tab = getTab(tabId);
    if (!tab) return;

    // Refresh Step 3 review member body
    const reviewMember = document.querySelector(`.review-member[data-tab-id="${tabId}"]`);
    if (reviewMember) {
        const body = reviewMember.querySelector('.review-member__body');
        if (body) {
            body.innerHTML = generateReviewMemberBodyHTML(tab);
            attachReviewEventListeners(tabId);
        }
        const countEl = reviewMember.querySelector('.review-member__count');
        if (countEl) countEl.textContent = `${tab.cuts.length} cut${tab.cuts.length !== 1 ? 's' : ''}`;
    }

    // Refresh Step 4 results tab
    const tabContent = document.querySelector(`.tab-content[data-tab-id="${tabId}"]`);
    if (tabContent) {
        tabContent.innerHTML = generateTabContentHTML(tab);
        if (tab.results) displayResults(tabId);
    }
}

// =============================================================================
// COLLAPSE / EXPAND
// =============================================================================

function toggleSection(header) {
    const section    = header.closest('.collapsible-section');
    const body       = section.querySelector('.collapsible-body');
    const chevron    = header.querySelector('.chevron');
    const isCollapsed = section.classList.toggle('collapsed');
    body.style.display      = isCollapsed ? 'none' : '';
    chevron.style.transform = isCollapsed ? 'rotate(-90deg)' : '';
}

// =============================================================================
// CUT & STOCK MUTATIONS
// =============================================================================


function addCut(tabId) {
    getTab(tabId).cuts.push({ length: 0, quantity: 1, mark: '', group: '' });
    refreshTab(tabId);
}

function removeCut(tabId, index) {
    getTab(tabId).cuts.splice(index, 1);
    refreshTab(tabId);
}

function addStock(tabId) {
    getTab(tabId).stockLengths.push(0);
    refreshTab(tabId);
}

function removeStock(tabId, index) {
    getTab(tabId).stockLengths.splice(index, 1);
    refreshTab(tabId);
}

// =============================================================================
// OVERLENGTH SPLITTING
// =============================================================================

function splitOverlengthCut(cutLength, splitStockLength, kerfWidth, cutTolerance) {
    const splits = [];
    let remaining = cutLength;
    while (remaining >= splitStockLength) {
        splits.push({ length: splitStockLength, isFullStick: true });
        remaining -= splitStockLength;
    }
    if (remaining > 0) splits.push({ length: remaining + kerfWidth + cutTolerance, isFullStick: false });
    return splits;
}

// =============================================================================
// OPTIMISATION ALGORITHM (First Fit Decreasing)
// =============================================================================

function calculateOptimization(tabId) {
    const tab = getTab(tabId);

    if (!tab.memberName)                                                        { showToast('Please enter a member size', 'error'); return; }
    if (tab.cuts.length === 0 || tab.cuts.some(c => c.length <= 0 || c.quantity <= 0)) { showToast('Please enter valid cuts', 'error'); return; }
    if (tab.stockLengths.length === 0 || tab.stockLengths.some(l => l <= 0))   { showToast('Please enter valid stock lengths', 'error'); return; }

    const kerfWidth            = project.jobDetails.kerfWidth;
    const cutTolerance         = tab.cutTolerance || 0;
    const overlengthSplitStock = tab.overlengthSplitStock || 6000;
    const maxStockLength       = Math.max(...tab.stockLengths);
    const sortedStock          = [...tab.stockLengths].sort((a, b) => a - b);
    const timberType           = getTimberType(tab.memberName);

    const allBins          = [];
    const overlengthSplits = [];
    let totalOriginalCutLength = 0;

    const groupMap = {};
    tab.cuts.forEach((cut, cutIdx) => {
        const key = cut.group || '';
        if (!groupMap[key]) groupMap[key] = [];
        groupMap[key].push({ cut, cutIdx });
    });

    const groupKeys = Object.keys(groupMap).filter(k => k !== '').sort();
    groupKeys.push('');

    groupKeys.forEach(groupKey => {
        const cutsInGroup  = groupMap[groupKey] || [];
        const expandedCuts = [];

        cutsInGroup.forEach(({ cut, cutIdx }) => {
            for (let i = 0; i < cut.quantity; i++) {
                const cutLength = cut.length;
                totalOriginalCutLength += cutLength;

                if (cutLength > maxStockLength) {
                    const splits = splitOverlengthCut(cutLength, overlengthSplitStock, kerfWidth, cutTolerance);
                    overlengthSplits.push({ originalLength: cutLength, splits, group: groupKey });
                    splits.forEach(splitPiece => {
                        expandedCuts.push({
                            length: splitPiece.length, isSplitPiece: true,
                            isFullStick: splitPiece.isFullStick, displayLength: cutLength,
                            mark: cut.mark || '', group: groupKey, cutIndex: cutIdx, originalLength: 0
                        });
                    });
                } else {
                    expandedCuts.push({
                        length: cutLength + cutTolerance, isSplitPiece: false, isFullStick: false,
                        displayLength: cutLength, mark: cut.mark || '', group: groupKey,
                        cutIndex: cutIdx, originalLength: 0
                    });
                }
            }
        });

        expandedCuts.sort((a, b) => b.length - a.length);

        expandedCuts.forEach(cutInfo => {
            if (cutInfo.isFullStick) {
                allBins.push({ id: binIdCounter++, stockLength: cutInfo.length, cuts: [cutInfo], remaining: 0, timberType, group: groupKey });
                return;
            }
            const groupBins = allBins.filter(b => b.group === groupKey);
            let placed = false;
            for (let bin of groupBins) {
                const spaceNeeded = cutInfo.length + (bin.cuts.length > 0 ? kerfWidth : 0);
                if (bin.remaining >= spaceNeeded) {
                    bin.cuts.push(cutInfo);
                    bin.remaining -= spaceNeeded;
                    placed = true;
                    break;
                }
            }
            if (!placed) {
                const suitableStock = sortedStock.find(stock => stock >= cutInfo.length);
                if (suitableStock) {
                    allBins.push({ id: binIdCounter++, stockLength: suitableStock, cuts: [cutInfo], remaining: suitableStock - cutInfo.length, timberType, group: groupKey });
                } else {
                    showToast(`Cut length ${cutInfo.length}mm exceeds all available stock lengths!`, 'error');
                }
            }
        });
    });

    const bins            = allBins;
    const totalStockUsed  = bins.reduce((sum, bin) => sum + bin.stockLength, 0);
    const totalActualCutLength = bins.reduce((sum, bin) => bin.cuts.reduce((s, c) => s + c.length, sum), 0);
    const totalKerfLoss   = bins.reduce((sum, bin) => sum + (bin.cuts.length - 1) * kerfWidth, 0);
    const totalTolerance  = totalActualCutLength - totalOriginalCutLength;
    const totalWaste      = totalStockUsed - totalActualCutLength - totalKerfLoss;
    const wastePercentage = ((totalWaste / totalStockUsed) * 100).toFixed(2);

    tab.results = {
        bins, totalStockUsed,
        totalCutLength: totalOriginalCutLength,
        totalKerfLoss, totalTolerance, totalWaste, wastePercentage,
        stockCount: bins.length, kerfWidth, overlengthSplits
    };

    displayResults(tabId);
    updateSummary();
}

// =============================================================================
// RESULTS DISPLAY
// =============================================================================

function displayResults(tabId) {
    const tab        = getTab(tabId);
    const resultsDiv = document.querySelector(`.tab-content[data-tab-id="${tabId}"] .results`);
    if (!tab.results || !resultsDiv) return;

    const { bins, totalStockUsed, totalCutLength, totalKerfLoss, totalTolerance,
            totalWaste, wastePercentage, stockCount, kerfWidth, overlengthSplits } = tab.results;

    let html = `
        <div class="collapsible-section">
            <div class="collapsible-header" onclick="toggleSection(this)">
                <h3>Optimisation Results</h3>
                <span class="chevron">&#8964;</span>
            </div>
            <div class="collapsible-body">`;

    if (overlengthSplits && overlengthSplits.length > 0) {
        html += '<div class="overlength-info"><h4>Overlength Cuts Split</h4>';
        overlengthSplits.forEach(split => {
            const splitDesc = split.splits.map(s =>
                s.isFullStick ? `${s.length}mm (full stick)` : `${Math.round(s.length)}mm`
            ).join(' + ');
            html += `<p>${split.originalLength}mm → ${splitDesc}</p>`;
        });
        html += '</div>';
    }

    const groupOrder = [...new Set(bins.map(b => b.group || ''))].sort((a, b) => {
        if (a === '') return 1;
        if (b === '') return -1;
        return a.localeCompare(b);
    });
    const hasNamedGroups = groupOrder.some(k => k !== '');

    html += '<div class="cutting-diagrams"><h4>Cutting Diagrams</h4>';

    let stickCounter = 1;
    groupOrder.forEach(groupKey => {
        // Not re-sorted here — position is established once by advancedOptimizeAll after a
        // full re-optimise, and preserved through manual overrides (drag/drop, stick-length
        // edit) so an edited stick doesn't jump to a different spot on every render.
        const groupBins = bins.filter(b => (b.group || '') === groupKey);

        const label = groupKey ? `Group: ${groupKey}`
                    : hasNamedGroups ? 'Ungrouped'
                    : null;

        if (label) {
            html += `
                <div class="collapsible-section group-section">
                    <div class="collapsible-header group-collapsible-header" onclick="toggleSection(this)">
                        <h5 class="group-section-label ${groupKey ? '' : 'group-section-ungrouped'}">${label}</h5>
                        <span class="chevron group-chevron">&#8964;</span>
                    </div>
                    <div class="collapsible-body diagrams-container">`;
        } else {
            html += '<div class="diagrams-container">';
        }

        groupBins.forEach(bin => { html += generateCuttingDiagram(bin, stickCounter++, kerfWidth, tabId); });
        if (tabId) {
            const timberType = (groupBins[0] || bins[0] || {}).timberType || null;
            html += generateGhostStickHTML(tabId, groupKey, timberType);
        }
        html += label ? '</div></div>' : '</div>';
    });

    html += '</div>'; // .cutting-diagrams

    html += `
            <div class="stats">
                <div class="stat"><div class="stat-label">Stock Pieces</div><div class="stat-value">${stockCount}</div></div>
                <div class="stat"><div class="stat-label">Total Cut Length</div><div class="stat-value">${totalCutLength}mm</div></div>
                <div class="stat"><div class="stat-label">Total Kerf Loss</div><div class="stat-value">${totalKerfLoss}mm</div></div>
                <div class="stat"><div class="stat-label">Total Tolerance</div><div class="stat-value">${totalTolerance}mm</div></div>
                <div class="stat"><div class="stat-label">Total Waste</div><div class="stat-value">${totalWaste}mm</div></div>
                <div class="stat"><div class="stat-label">Waste %</div><div class="stat-value">${wastePercentage}%</div></div>
            </div>
        </div>
    </div>`;

    resultsDiv.innerHTML      = html;
    resultsDiv.style.display  = 'block';
}

// =============================================================================
// CUTTING DIAGRAM
// =============================================================================

function generateCuttingDiagram(bin, stickNumber, kerfWidth, tabId) {
    const { stockLength, cuts, remaining, timberType } = bin;
    const diagramHeight = 400;
    const diagramWidth  = 60;
    const kerfHeightPx  = 4;

    const timberClass = timberType ? `timber-${timberType.toLowerCase()}` : 'timber-other';
    const editable     = !!tabId; // false in print view (tabId is null there)
    const lockedClass  = bin.locked ? ' stick-locked' : '';

    const stickLabelClass = editable ? ' stick-label-clickable' : '';
    const stickLabelClick = editable ? ` onclick="openStickEditor('${tabId}', ${bin.id})"` : '';
    const dropHandlers = editable
        ? ` ondragover="handleStickDragOver(event)" ondragleave="handleStickDragLeave(event)" ondrop="handleStickDrop(event, '${tabId}', ${bin.id})"`
        : '';

    let html = `
        <div class="stick-diagram ${timberClass}${lockedClass}" data-bin-id="${bin.id}">
            <div class="stick-label${stickLabelClass}" title="${editable ? 'Click to change stock length' : ''}"${stickLabelClick}>Stick ${stickNumber}<br>${stockLength}mm</div>`;

    // Every stick gets a lock toggle in the live editor — locking is a general-purpose choice,
    // not just something that follows automatically from editing. In print view, only show it
    // (non-interactive) when actually locked, since that's the one state worth recording.
    if (editable) {
        html += `
            <button type="button" class="stick-lock-toggle${bin.locked ? ' locked' : ''}"
                    title="${bin.locked ? 'Locked — click to unlock' : 'Not locked — click to lock'}"
                    onclick="toggleBinLock('${tabId}', ${bin.id})">${bin.locked ? '&#128274;' : '&#128275;'}</button>`;
    } else if (bin.locked) {
        html += `<span class="stick-lock-toggle locked" title="Locked">&#128274;</span>`;
    }

    html += `<div class="stick" style="height:${diagramHeight}px;width:${diagramWidth}px;"${dropHandlers}>`;

    if (cuts.length === 0) {
        // An empty stick (e.g. just added via "+ Add empty stick") — render the whole thing
        // as one waste segment rather than running the ratio math below, which assumes at
        // least one cut (cuts.length - 1 goes negative otherwise).
        html += `
            <div class="waste-segment" style="height:${diagramHeight}px;" title="Empty: ${remaining}mm — drag a cut here">
                <span class="waste-label">${remaining}</span>
            </div></div></div>`;
        return html;
    }

    const totalNonKerfHeight = diagramHeight - ((cuts.length - 1) * kerfHeightPx);
    const usableLength       = stockLength - ((cuts.length - 1) * kerfWidth) - remaining;

    cuts.forEach((cutInfo, index) => {
        const cutLength     = typeof cutInfo === 'object' ? cutInfo.length      : cutInfo;
        const isSplitPiece  = typeof cutInfo === 'object' ? cutInfo.isSplitPiece : false;
        const displayLength = typeof cutInfo === 'object' ? cutInfo.displayLength : cutInfo;
        const mark          = typeof cutInfo === 'object' ? cutInfo.mark          : '';
        const cutIndex      = typeof cutInfo === 'object' ? cutInfo.cutIndex      : undefined;

        const cutHeight      = (cutLength / usableLength) * totalNonKerfHeight;
        const cutClass       = isSplitPiece ? 'cut-segment-split' : 'cut-segment';
        const clickableClass = (cutIndex !== undefined && tabId) ? ' cut-clickable' : '';
        const draggableClass = editable ? ' cut-draggable' : '';
        const onclickAttr    = (cutIndex !== undefined && tabId)
            ? ` onclick="openCutEditor('${tabId}', ${cutIndex})"` : '';
        const dragAttr = editable
            ? ` draggable="true" ondragstart="handleCutDragStart(event, '${tabId}', ${bin.id}, ${index})"`
            : '';

        let displayLabel;
        if (isSplitPiece && cutLength === stockLength) {
            displayLabel = mark ? `${mark} (full)` : `${displayLength} (full)`;
        } else {
            displayLabel = mark ? `${mark}: ${Math.round(displayLength)}` : Math.round(displayLength);
        }

        const titleText = `${isSplitPiece ? 'Split piece: ' : ''}${Math.round(cutLength)}mm${mark ? ' [' + mark + ']' : ''}${cutIndex !== undefined ? '\nClick to edit' : ''}${editable ? '\nDrag to move to another stick' : ''}`;

        html += `
            <div class="${cutClass}${clickableClass}${draggableClass}" style="height:${cutHeight}px;" title="${titleText}"${onclickAttr}${dragAttr}>
                <span class="cut-label">${displayLabel}</span>
            </div>`;

        if (index < cuts.length - 1 && kerfWidth > 0) {
            html += `<div class="kerf-segment" style="height:${kerfHeightPx}px;" title="Kerf: ${kerfWidth}mm"></div>`;
        }
    });

    if (remaining > 0) {
        const wasteHeight = (remaining / usableLength) * totalNonKerfHeight;
        html += `
            <div class="waste-segment" style="height:${wasteHeight}px;" title="Waste: ${remaining}mm">
                <span class="waste-label">${remaining}</span>
            </div>`;
    }

    html += `</div></div>`;
    return html;
}

// A full-size, ghosted placeholder stick at the end of each group — not a real bin, just a
// drop target. Dragging a cut onto it (handleGhostDrop) materialises a real 6000mm stick and
// receives the cut in one motion; nothing is added to tab.results.bins until that happens.
function generateGhostStickHTML(tabId, group, timberType) {
    const diagramHeight = 400;
    const diagramWidth  = 60;
    const timberClass   = timberType ? `timber-${timberType.toLowerCase()}` : 'timber-other';

    return `
        <div class="stick-diagram stick-ghost ${timberClass}">
            <div class="stick-label">Empty<br>${GHOST_STICK_LENGTH}mm</div>
            <span class="stick-lock-toggle" style="visibility:hidden;">&#128275;</span>
            <div class="stick" style="height:${diagramHeight}px;width:${diagramWidth}px;"
                 data-group="${group}"
                 ondragover="handleGhostDragOver(event)" ondragleave="handleGhostDragLeave(event)"
                 ondrop="handleGhostDrop(event, '${tabId}', this.dataset.group)">
                <div class="waste-segment" style="height:${diagramHeight}px;">
                    <span class="waste-label">Drag a cut here</span>
                </div>
            </div>
        </div>`;
}

// =============================================================================
// EDIT CUT SEGMENTS (Feature 3)
// =============================================================================

function openCutEditor(tabId, cutIndex) {
    const tab = getTab(tabId);
    if (!tab || cutIndex === undefined || cutIndex === null) return;
    const cut = tab.cuts[cutIndex];
    if (!cut) return;

    _editTabId    = tabId;
    _editCutIndex = cutIndex;

    document.getElementById('editCutLength').value   = cut.length;
    document.getElementById('editCutQuantity').value = cut.quantity;
    document.getElementById('editCutMark').value     = cut.mark  || '';
    document.getElementById('editCutGroup').value    = cut.group || '';
    document.getElementById('editCutHint').textContent =
        `${cut.quantity} piece${cut.quantity !== 1 ? 's' : ''} of this cut. Changes affect all instances and will re-run optimisation.`;

    document.getElementById('cutEditorModal').style.display = 'flex';
    document.getElementById('editCutLength').focus();
}

function closeCutEditor() {
    document.getElementById('cutEditorModal').style.display = 'none';
    _editTabId    = null;
    _editCutIndex = null;
}

function saveCutEdit() {
    if (_editTabId === null || _editCutIndex === null) return;
    const tab = getTab(_editTabId);
    if (!tab) return;

    const newLength   = parseFloat(document.getElementById('editCutLength').value);
    const newQuantity = parseInt(document.getElementById('editCutQuantity').value);
    const newMark     = document.getElementById('editCutMark').value.trim();
    const newGroup    = document.getElementById('editCutGroup').value.trim();

    if (isNaN(newLength)   || newLength < 1)   { showToast('Please enter a valid length',   'error'); return; }
    if (isNaN(newQuantity) || newQuantity < 1)  { showToast('Please enter a valid quantity', 'error'); return; }

    // Editing the raw cut invalidates this tab's whole layout — unlike a plain re-optimise
    // there's no reliable way to tell which locked sticks are unaffected, so this unlocks all
    // of them for the tab rather than trying to preserve some.
    const lockedCount = tab.results ? tab.results.bins.filter(b => b.locked).length : 0;
    if (lockedCount > 0 && !confirm(
        `This tab has ${lockedCount} locked stick${lockedCount !== 1 ? 's' : ''}. ` +
        `Editing this cut will unlock ${lockedCount !== 1 ? 'them' : 'it'} and re-optimise this tab from scratch. Continue?`
    )) {
        return;
    }

    tab.cuts[_editCutIndex] = { ...tab.cuts[_editCutIndex], length: newLength, quantity: newQuantity, mark: newMark, group: newGroup };

    const tabId = _editTabId;
    closeCutEditor();
    tab.results = null;
    refreshTab(tabId);
    calculateOptimization(tabId);
    updateSummary();
}

// =============================================================================
// STICK LENGTH EDITOR (manual override)
// =============================================================================

function openStickEditor(tabId, binId) {
    const tab = getTab(tabId);
    if (!tab || !tab.results) return;
    const bin = tab.results.bins.find(b => b.id === binId);
    if (!bin) return;

    _stickEditTabId = tabId;
    _stickEditBinId = binId;

    const kerfWidth  = project.jobDetails.kerfWidth;
    const usedLength = bin.cuts.reduce((sum, cut) => sum + (typeof cut === 'object' ? cut.length : cut), 0)
        + Math.max(0, bin.cuts.length - 1) * kerfWidth;

    const select = document.getElementById('stickEditorLength');
    select.innerHTML = [...new Set(tab.stockLengths)]
        .filter(l => l >= usedLength)
        .sort((a, b) => a - b)
        .map(l => `<option value="${l}" ${l === bin.stockLength ? 'selected' : ''}>${l}mm</option>`)
        .join('');

    if (!select.options.length) {
        showToast("No stock length in this member's list is long enough for these pieces", 'error');
        return;
    }

    document.getElementById('stickEditorHint').textContent =
        `${bin.cuts.length} piece${bin.cuts.length !== 1 ? 's' : ''} using ${usedLength}mm. Choose any stock length that fits — this locks the stick so a later re-optimise won't change it.`;

    document.getElementById('stickEditorModal').style.display = 'flex';
}

function closeStickEditor() {
    document.getElementById('stickEditorModal').style.display = 'none';
    _stickEditTabId = null;
    _stickEditBinId = null;
}

function saveStickEdit() {
    if (_stickEditTabId === null || _stickEditBinId === null) return;
    const tab = getTab(_stickEditTabId);
    if (!tab || !tab.results) return;
    const bin = tab.results.bins.find(b => b.id === _stickEditBinId);
    if (!bin) return;

    const newLength = parseInt(document.getElementById('stickEditorLength').value, 10);
    if (isNaN(newLength)) { closeStickEditor(); return; }

    const kerfWidth  = project.jobDetails.kerfWidth;
    const usedLength = bin.cuts.reduce((sum, cut) => sum + (typeof cut === 'object' ? cut.length : cut), 0)
        + Math.max(0, bin.cuts.length - 1) * kerfWidth;

    bin.stockLength = newLength;
    bin.remaining   = newLength - usedLength;
    bin.locked      = true;

    const tabId = _stickEditTabId;
    closeStickEditor();
    refreshAfterLockChange(tabId);
}

// Toggles a stick's lock independently of whether it's ever been edited — a user can lock a
// perfectly normal optimiser-produced stick just to protect it, or unlock a manually-edited one
// without touching its current contents (those only change on an actual re-optimise).
function toggleBinLock(tabId, binId) {
    const tab = getTab(tabId);
    if (!tab || !tab.results) return;
    const bin = tab.results.bins.find(b => b.id === binId);
    if (!bin) return;
    bin.locked = !bin.locked;
    refreshAfterLockChange(tabId);
}

// Re-renders one tab's diagrams + Step 5 summary and auto-saves — used after any lock/edit
// action (stick length change, drag/drop, lock toggle) so the change can't be lost before the
// user remembers to hit Save, unlike Feature 3's cut editor which leaves saving to the user.
function refreshAfterLockChange(tabId) {
    displayResults(tabId);
    updateSummary();
    const totalSticks = project.tabs.reduce((s, t) => t.results ? s + t.results.stockCount : s, 0);
    setStepMeta(4, `${totalSticks} stick${totalSticks !== 1 ? 's' : ''}`);
    saveProject();
}

// =============================================================================
// DRAG CUTS BETWEEN STICKS (manual override)
// =============================================================================

function handleCutDragStart(event, tabId, binId, cutIndex) {
    _dragSource = { tabId, binId, cutIndex };
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', ''); // Firefox requires data to be set for drag to start
}

function canDropCutOnBin(source, tab, targetBin) {
    if (!source || !tab || !tab.results || !targetBin) return false;
    if (targetBin.id === source.binId) return false;
    const sourceBin = tab.results.bins.find(b => b.id === source.binId);
    if (!sourceBin) return false;
    const cut = sourceBin.cuts[source.cutIndex];
    if (!cut) return false;
    const cutLength   = typeof cut === 'object' ? cut.length : cut;
    const kerfWidth   = project.jobDetails.kerfWidth;
    const spaceNeeded = cutLength + (targetBin.cuts.length > 0 ? kerfWidth : 0);
    return targetBin.remaining >= spaceNeeded;
}

function handleStickDragOver(event) {
    if (!_dragSource) return;
    event.preventDefault();
    const stickEl = event.currentTarget;
    const tab     = getTab(_dragSource.tabId);
    const binId   = parseInt(stickEl.closest('.stick-diagram').dataset.binId, 10);
    const targetBin = tab && tab.results ? tab.results.bins.find(b => b.id === binId) : null;
    const valid   = canDropCutOnBin(_dragSource, tab, targetBin);
    stickEl.classList.toggle('drag-over-valid', valid);
    stickEl.classList.toggle('drag-over-invalid', !valid);
    event.dataTransfer.dropEffect = valid ? 'move' : 'none';
}

function handleStickDragLeave(event) {
    event.currentTarget.classList.remove('drag-over-valid', 'drag-over-invalid');
}

// Moves the dragged cut from its source bin into targetBin (already present in
// tab.results.bins — the caller creates it first for a ghost-stick drop) and locks both
// bins. Shared by handleStickDrop and handleGhostDrop.
function moveCutIntoBin(tab, source, targetBin) {
    const sourceBin = tab.results.bins.find(b => b.id === source.binId);
    const cut        = sourceBin.cuts[source.cutIndex];
    const cutLength  = typeof cut === 'object' ? cut.length : cut;
    const kerfWidth  = project.jobDetails.kerfWidth;

    sourceBin.cuts.splice(source.cutIndex, 1);
    targetBin.cuts.push(cut);
    targetBin.remaining -= (cutLength + (targetBin.cuts.length > 1 ? kerfWidth : 0));
    targetBin.locked = true;

    if (sourceBin.cuts.length === 0) {
        tab.results.bins = tab.results.bins.filter(b => b.id !== sourceBin.id);
    } else {
        const usedLength = sourceBin.cuts.reduce((sum, c) => sum + (typeof c === 'object' ? c.length : c), 0)
            + Math.max(0, sourceBin.cuts.length - 1) * kerfWidth;
        sourceBin.remaining = sourceBin.stockLength - usedLength;
        sourceBin.locked    = true;
    }

    tab.results.stockCount     = tab.results.bins.length;
    tab.results.totalStockUsed = calculateTotalMaterial(tab.results.bins);
}

function handleStickDrop(event, tabId, targetBinId) {
    event.preventDefault();
    event.currentTarget.classList.remove('drag-over-valid', 'drag-over-invalid');

    const source = _dragSource;
    _dragSource = null;
    if (!source || source.tabId !== tabId) return;

    const tab = getTab(tabId);
    if (!tab || !tab.results) return;

    const targetBin = tab.results.bins.find(b => b.id === targetBinId);
    if (!canDropCutOnBin(source, tab, targetBin)) {
        showToast("That piece won't fit on this stick", 'error');
        return;
    }

    moveCutIntoBin(tab, source, targetBin);
    refreshAfterLockChange(tabId);
}

// Default length for a new stick materialised by dragging a cut onto the ghost tile.
const GHOST_STICK_LENGTH = 6000;

function handleGhostDragOver(event) {
    if (!_dragSource) return;
    event.preventDefault();
    const tab       = getTab(_dragSource.tabId);
    const sourceBin = tab && tab.results ? tab.results.bins.find(b => b.id === _dragSource.binId) : null;
    const cut       = sourceBin ? sourceBin.cuts[_dragSource.cutIndex] : null;
    const cutLength = cut ? (typeof cut === 'object' ? cut.length : cut) : Infinity;
    const valid     = cutLength <= GHOST_STICK_LENGTH;
    event.currentTarget.classList.toggle('drag-over-valid', valid);
    event.currentTarget.classList.toggle('drag-over-invalid', !valid);
    event.dataTransfer.dropEffect = valid ? 'move' : 'none';
}

function handleGhostDragLeave(event) {
    event.currentTarget.classList.remove('drag-over-valid', 'drag-over-invalid');
}

// Dragging a cut onto the ghost tile materialises a real stick at GHOST_STICK_LENGTH and
// receives it in one motion, rather than requiring a separate "add empty stick" click first.
function handleGhostDrop(event, tabId, group) {
    event.preventDefault();
    event.currentTarget.classList.remove('drag-over-valid', 'drag-over-invalid');

    const source = _dragSource;
    _dragSource = null;
    if (!source || source.tabId !== tabId) return;

    const tab = getTab(tabId);
    if (!tab || !tab.results) return;

    const sourceBin = tab.results.bins.find(b => b.id === source.binId);
    const cut       = sourceBin ? sourceBin.cuts[source.cutIndex] : null;
    if (!cut) return;
    const cutLength = typeof cut === 'object' ? cut.length : cut;

    if (cutLength > GHOST_STICK_LENGTH) {
        showToast(`That piece is longer than the default ${GHOST_STICK_LENGTH}mm stick`, 'error');
        return;
    }

    const timberType = (tab.results.bins.find(b => (b.group || '') === group) || tab.results.bins[0] || {}).timberType || null;
    const newBin = {
        id: binIdCounter++,
        stockLength: GHOST_STICK_LENGTH,
        cuts: [],
        remaining: GHOST_STICK_LENGTH,
        group,
        timberType,
        locked: true,
    };
    tab.results.bins.push(newBin);

    moveCutIntoBin(tab, source, newBin);
    refreshAfterLockChange(tabId);
}

// =============================================================================
// RUN OPTIMISATION (background — replaces "Calculate All" button)
// =============================================================================

function hasLockedSticks() {
    return project.tabs.some(t => t.results && t.results.bins.some(b => b.locked));
}

function openLockGuardModal() {
    const count = project.tabs.reduce((s, t) =>
        s + (t.results ? t.results.bins.filter(b => b.locked).length : 0), 0);
    document.getElementById('lockGuardHint').textContent =
        `${count} stick${count !== 1 ? 's are' : ' is'} locked. ` +
        `Re-optimising can either unlock ${count !== 1 ? 'them' : 'it'} and start fresh, ` +
        `or leave ${count !== 1 ? 'them' : 'it'} exactly as set and re-optimise everything else around ${count !== 1 ? 'them' : 'it'}.`;
    document.getElementById('lockGuardModal').style.display = 'flex';
}

function closeLockGuardModal() {
    document.getElementById('lockGuardModal').style.display = 'none';
}

async function runOptimisation() {
    if (hasLockedSticks()) {
        openLockGuardModal();
        return;
    }
    await performOptimisation(false);
}

// Runs FFD for a tab while respecting any locked bins: their pieces are temporarily
// subtracted from the raw cut quantities so FFD doesn't regenerate duplicates, then the
// locked bins are merged back into the freshly-computed results unchanged.
function runFFDRespectingLocks(tabId) {
    const tab = getTab(tabId);
    const lockedBins = (tab.results && tab.results.bins) ? tab.results.bins.filter(b => b.locked) : [];

    if (lockedBins.length === 0) {
        calculateOptimization(tabId);
        return;
    }

    const consumed = {};
    lockedBins.forEach(bin => {
        bin.cuts.forEach(cut => {
            const idx = typeof cut === 'object' ? cut.cutIndex : undefined;
            if (idx === undefined) return;
            consumed[idx] = (consumed[idx] || 0) + 1;
        });
    });

    const originalQuantities = {};
    Object.entries(consumed).forEach(([idx, count]) => {
        const cut = tab.cuts[idx];
        if (!cut) return;
        originalQuantities[idx] = cut.quantity;
        cut.quantity = Math.max(0, cut.quantity - count);
    });

    calculateOptimization(tabId);

    Object.entries(originalQuantities).forEach(([idx, qty]) => { tab.cuts[idx].quantity = qty; });

    const kerfWidth = project.jobDetails.kerfWidth;
    tab.results.bins = tab.results.bins.concat(lockedBins);
    tab.results.stockCount     = tab.results.bins.length;
    tab.results.totalStockUsed = calculateTotalMaterial(tab.results.bins);
    const lockedCutLength = lockedBins.reduce((sum, bin) =>
        sum + bin.cuts.reduce((s, c) => s + (typeof c === 'object' ? (c.displayLength ?? c.length) : c), 0), 0);
    tab.results.totalCutLength = (tab.results.totalCutLength || 0) + lockedCutLength;
    const totalKerfLoss = tab.results.bins.reduce((sum, bin) => sum + Math.max(0, bin.cuts.length - 1) * kerfWidth, 0);
    tab.results.totalKerfLoss   = totalKerfLoss;
    tab.results.totalWaste      = tab.results.totalStockUsed - tab.results.totalCutLength - totalKerfLoss;
    tab.results.wastePercentage = ((tab.results.totalWaste / tab.results.totalStockUsed) * 100).toFixed(2);
}

async function performOptimisation(unlockAll) {
    const btn = document.getElementById('optimiseBtn');
    btn.disabled    = true;
    btn.textContent = 'Optimising…';

    // Yield to browser to render loading state
    await new Promise(r => setTimeout(r, 30));

    let allValid = true;
    for (const tab of project.tabs) {
        if (!tab.memberName || !tab.cuts.length || tab.cuts.some(c => c.length <= 0 || c.quantity <= 0)
            || !tab.stockLengths.length || tab.stockLengths.some(l => l <= 0)) {
            showToast(`Check data for: ${tab.memberName || 'unnamed member'}`, 'error');
            allValid = false;
        }
    }

    if (!allValid) {
        btn.disabled    = false;
        btn.textContent = 'Optimise →';
        return;
    }

    if (unlockAll) {
        project.tabs.forEach(tab => {
            if (tab.results) tab.results.bins.forEach(b => { delete b.locked; });
        });
    }

    project.tabs.forEach(tab => {
        try { runFFDRespectingLocks(tab.id); }
        catch (e) { showToast(`Error: ${tab.memberName} — ${e.message}`, 'error'); allValid = false; }
    });

    if (!allValid) {
        btn.disabled    = false;
        btn.textContent = 'Optimise →';
        return;
    }

    // Run advanced optimisation silently (no toast, no intermediate saves)
    advancedOptimizeAll(true);

    // Rebuild results tabs with final results
    document.getElementById('tabsList').innerHTML    = '';
    document.getElementById('tabsContent').innerHTML = '';
    renderResultsTabs();

    const totalSticks = project.tabs.reduce((s, t) => t.results ? s + t.results.stockCount : s, 0);
    setStepMeta(3, 'Optimised');
    setStepMeta(4, `${totalSticks} stick${totalSticks !== 1 ? 's' : ''}`);
    markStepDone(3);

    updateSummary();
    saveProject();

    btn.disabled    = false;
    btn.textContent = 'Re-optimise →';

    advanceToStep(4);
}

// =============================================================================
// ADVANCED OPTIMISATION
// =============================================================================

function advancedOptimizeAll(silent = false) {
    if (project.tabs.length === 0) return;

    const calculatedTabs = project.tabs.filter(t => t.results);
    if (calculatedTabs.length === 0) return;

    const kerfWidth = project.jobDetails.kerfWidth;
    let totalSavings  = 0;
    let groupsChanged = 0;

    calculatedTabs.forEach(tab => {
        const stockSorted      = [...new Set(tab.stockLengths)].sort((a, b) => a - b);
        const originalMaterial = calculateTotalMaterial(tab.results.bins);

        const groups  = [...new Set(tab.results.bins.map(b => b.group || ''))];
        let newBins   = [];
        groups.forEach(group => {
            // Locked bins are excluded from re-optimisation entirely — they're passed through
            // untouched and their pieces aren't offered up for reuse.
            const groupBins = tab.results.bins.filter(b => (b.group || '') === group);
            const locked    = groupBins.filter(b => b.locked);
            const free      = groupBins.filter(b => !b.locked);
            const { bins: optimized, changes } = optimizeGroupBins(free, stockSorted, kerfWidth);
            if (changes > 0) groupsChanged++;
            newBins = newBins.concat(optimized, locked);
        });

        // Sorted once here (not on every render — see displayResults) so a manual override
        // afterwards (drag/drop, stick-length edit) doesn't reshuffle sticks that weren't
        // touched; only a full re-optimise like this one re-establishes position.
        newBins.sort((a, b) => {
            const groupA = a.group || '', groupB = b.group || '';
            if (groupA !== groupB) return groupA.localeCompare(groupB);
            return b.stockLength - a.stockLength || a.remaining - b.remaining;
        });
        tab.results.bins = newBins;

        const newMaterial = calculateTotalMaterial(tab.results.bins);
        totalSavings += (originalMaterial - newMaterial);

        tab.results.totalStockUsed = newMaterial;
        tab.results.stockCount     = tab.results.bins.length;
        const totalCutLength = tab.results.bins.reduce((sum, bin) =>
            sum + bin.cuts.reduce((s, cut) => s + (typeof cut === 'object' ? cut.length : cut), 0), 0);
        const totalKerfLoss  = tab.results.bins.reduce((sum, bin) => sum + Math.max(0, bin.cuts.length - 1) * kerfWidth, 0);
        tab.results.totalWaste      = newMaterial - totalCutLength - totalKerfLoss;
        tab.results.wastePercentage = ((tab.results.totalWaste / newMaterial) * 100).toFixed(2);
    });

    if (!silent) {
        calculatedTabs.forEach(tab => displayResults(tab.id));
        updateSummary();
        saveProject();

        if (totalSavings > 0) {
            showToast(`Advanced optimisation saved ${totalSavings}mm of material across ${groupsChanged} group${groupsChanged !== 1 ? 's' : ''}.`, 'success');
        } else {
            showToast('Already optimal — no further savings possible.', 'info');
        }
    }
}

function calculateTotalMaterial(bins) {
    return bins.reduce((sum, bin) => sum + bin.stockLength, 0);
}

// =============================================================================
// UNIFIED GROUP CONSOLIDATION
//
// Replaces the old advancedOptimizeTab (global cross-group offcut-absorption) and
// consolidateBins (three sequential, order-dependent heuristics: a hardcoded 3x3600->2x5400
// pattern, a "double the stock length" pair rule that never checked whether a smaller stock
// would fit, and a general search with a stale-index bug that silently skipped valid merges).
// Those defects were confirmed against real production data (project 41): identical input
// groups landing on different results depending on unrelated groups sharing the same
// optimisation pass, a stick picked twice its needed size, and valid merges skipped outright.
//
// This runs per (tab, group) in isolation — no shared cross-group queue — and scores every
// candidate lexicographically by (total_material, stick_count, distinct_stock_lengths_not_
// already_used_elsewhere_in_the_group). Material is minimised first as a hard constraint;
// stick count is the tie-break BEFORE distinct-length reuse is ever considered, so folding
// leftovers onto a stock length already in use (fewer distinct lengths, easier picking/
// packing/shipping) can only win when it doesn't cost extra sticks. Validated against every
// real cutlist in the database before being ported here.
// =============================================================================

function combinationsOfIndices(n, k) {
    const result = [];
    const combo  = [];
    (function backtrack(start) {
        if (combo.length === k) { result.push(combo.slice()); return; }
        for (let i = start; i < n; i++) {
            combo.push(i);
            backtrack(i + 1);
            combo.pop();
        }
    })(0);
    return result;
}

function combinationsWithReplacement(values, k) {
    const result = [];
    const combo  = [];
    (function backtrack(start) {
        if (combo.length === k) { result.push(combo.slice()); return; }
        for (let i = start; i < values.length; i++) {
            combo.push(values[i]);
            backtrack(i);
            combo.pop();
        }
    })(0);
    return result;
}

function tupleLess(a, b) {
    for (let i = 0; i < a.length; i++) {
        if (a[i] < b[i]) return true;
        if (a[i] > b[i]) return false;
    }
    return false;
}

function tryPlaceCuts(cuts, targetLengths, kerfWidth) {
    const targetBins = targetLengths.map(l => ({ stockLength: l, cuts: [], remaining: l }));
    const sortedCuts = [...cuts].sort((a, b) => {
        const aLen = typeof a === 'object' ? a.length : a;
        const bLen = typeof b === 'object' ? b.length : b;
        return bLen - aLen;
    });
    for (const cut of sortedCuts) {
        const cutLength = typeof cut === 'object' ? cut.length : cut;
        let placed = false;
        for (const tb of targetBins) {
            const spaceNeeded = cutLength + (tb.cuts.length > 0 ? kerfWidth : 0);
            if (tb.remaining >= spaceNeeded) {
                tb.cuts.push(cut);
                tb.remaining -= spaceNeeded;
                placed = true;
                break;
            }
        }
        if (!placed) return null;
    }
    return targetBins;
}

function repackPoolBestFit(cuts, stockSorted, kerfWidth, newBinChoice, descending) {
    const ordered = [...cuts].sort((a, b) => {
        const aLen = typeof a === 'object' ? a.length : a;
        const bLen = typeof b === 'object' ? b.length : b;
        return descending ? bLen - aLen : aLen - bLen;
    });
    const bins = [];
    for (const cut of ordered) {
        const cutLength = typeof cut === 'object' ? cut.length : cut;
        let bestBin = null, bestSpaceNeeded = 0, bestLeftover = null;
        for (const b of bins) {
            const spaceNeeded = cutLength + (b.cuts.length > 0 ? kerfWidth : 0);
            if (b.remaining >= spaceNeeded) {
                const leftover = b.remaining - spaceNeeded;
                if (bestLeftover === null || leftover < bestLeftover) {
                    bestLeftover = leftover; bestBin = b; bestSpaceNeeded = spaceNeeded;
                }
            }
        }
        if (bestBin) {
            bestBin.cuts.push(cut);
            bestBin.remaining -= bestSpaceNeeded;
        } else {
            const suitable = newBinChoice === 'largest' && stockSorted.length && stockSorted[stockSorted.length - 1] >= cutLength
                ? stockSorted[stockSorted.length - 1]
                : stockSorted.find(s => s >= cutLength);
            if (suitable === undefined) return null;
            bins.push({ stockLength: suitable, cuts: [cut], remaining: suitable - cutLength });
        }
    }
    return bins;
}

function scoreBins(bins, outsideLengths) {
    const material = bins.reduce((s, b) => s + b.stockLength, 0);
    let newLengths  = 0;
    new Set(bins.map(b => b.stockLength)).forEach(l => { if (!outsideLengths.has(l)) newLengths++; });
    return [material, bins.length, newLengths];
}

// One best-improvement pass: recombine small clusters of existing bins onto better stock.
// `wasteThreshold` is deliberately tiny — not "can this bin absorb a big offcut" but "does it
// have enough slack for a kerf gap to matter at all". Two bins with only ~450mm remaining each
// can still legitimately combine onto one bigger stick; excluding them at a high threshold
// (the old code's `remaining >= 500`) silently hides real merges. Performance is instead
// bounded by capping subset size when the candidate pool is large.
function subsetSearchPass(bins, stockSorted, kerfWidth, wasteThreshold, maxSubset, maxTargets) {
    const candidateIdx = [];
    bins.forEach((b, i) => { if (b.remaining >= wasteThreshold) candidateIdx.push(i); });
    const n = candidateIdx.length;
    if (n < 2) return { bins, changed: false };

    const effectiveMaxSubset = n <= 15 ? maxSubset : 2;
    let best = null;

    for (let k = 2; k <= Math.min(n, effectiveMaxSubset); k++) {
        for (const posCombo of combinationsOfIndices(n, k)) {
            const subsetBinIdx = posCombo.map(p => candidateIdx[p]);
            const subsetSet    = new Set(subsetBinIdx);
            const subset       = subsetBinIdx.map(i => bins[i]);
            const outsideLengths = new Set();
            bins.forEach((b, i) => { if (!subsetSet.has(i)) outsideLengths.add(b.stockLength); });

            const currentTuple = scoreBins(subset, outsideLengths);
            const allCuts = subset.flatMap(b => b.cuts);

            for (let t = 1; t <= Math.min(maxTargets, k); t++) {
                for (const targetCombo of combinationsWithReplacement(stockSorted, t)) {
                    const totalTarget = targetCombo.reduce((s, v) => s + v, 0);
                    if (totalTarget > currentTuple[0]) continue;
                    const placed = tryPlaceCuts(allCuts, targetCombo, kerfWidth);
                    if (!placed) continue;
                    let newLengths = 0;
                    new Set(targetCombo).forEach(l => { if (!outsideLengths.has(l)) newLengths++; });
                    const candTuple = [totalTarget, t, newLengths];
                    if (tupleLess(candTuple, currentTuple) && (!best || tupleLess(candTuple, best.score))) {
                        best = { score: candTuple, subsetBinIdx, newBins: placed };
                    }
                }
            }
        }
    }

    if (!best) return { bins, changed: false };

    const subsetSet  = new Set(best.subsetBinIdx);
    const groupVal   = bins[best.subsetBinIdx[0]].group;
    const timberType = bins[best.subsetBinIdx[0]].timberType;
    const kept       = bins.filter((b, i) => !subsetSet.has(i));
    const newBins    = best.newBins.map(nb => ({ stockLength: nb.stockLength, cuts: nb.cuts, remaining: nb.remaining, group: groupVal, timberType }));
    return { bins: kept.concat(newBins), changed: true };
}

// Escape hatch for the subset search: pool every bin's cuts in the group (no waste-threshold
// filter — unlike the subset search this pass is near-linear, not combinatorial, so there's no
// cost reason to exclude already-decent bins) and re-derive a fresh packing from scratch with a
// few Best-Fit-Decreasing strategies, keeping whichever scores best. Not bounded to recombining
// existing bin groupings, so it can reach packings the subset search's local moves can't step
// through one merge at a time.
function poolRepackPass(bins, stockSorted, kerfWidth) {
    if (bins.length < 2) return { bins, changed: false };

    const groupVal      = bins[0].group;
    const timberType    = bins[0].timberType;
    const currentTuple  = scoreBins(bins, new Set());
    const poolCuts      = bins.flatMap(b => b.cuts);

    let best = null;
    for (const newBinChoice of ['smallest', 'largest']) {
        for (const descending of [true, false]) {
            const repacked = repackPoolBestFit(poolCuts, stockSorted, kerfWidth, newBinChoice, descending);
            if (!repacked) continue;
            const candTuple = scoreBins(repacked, new Set());
            if (tupleLess(candTuple, currentTuple) && (!best || tupleLess(candTuple, best.score))) {
                best = { score: candTuple, repacked };
            }
        }
    }

    if (!best) return { bins, changed: false };

    const newBins = best.repacked.map(nb => ({ stockLength: nb.stockLength, cuts: nb.cuts, remaining: nb.remaining, group: groupVal, timberType }));
    return { bins: newBins, changed: true };
}

// Alternates the two passes to a fixed point: subset search first (precise, provably
// non-regressing, bounded to local moves), then pool repack (can escape local optima the
// subset search can't reach in one step, and may open up new subset-mergeable shapes for the
// next round).
function optimizeGroupBins(bins, stockLengths, kerfWidth, wasteThreshold = 50, maxSubset = 5, maxTargets = 3) {
    let current = bins.map(b => ({ ...b }));
    const stockSorted = [...new Set(stockLengths)].sort((a, b) => a - b);
    let changes = 0;

    while (true) {
        const pass1 = subsetSearchPass(current, stockSorted, kerfWidth, wasteThreshold, maxSubset, maxTargets);
        current = pass1.bins;
        const pass2 = poolRepackPass(current, stockSorted, kerfWidth);
        current = pass2.bins;

        if (pass1.changed || pass2.changed) changes++;
        if (!pass1.changed && !pass2.changed) break;
        if (changes > 200) { console.error('optimizeGroupBins: non-convergence guard hit'); break; }
    }

    return { bins: current, changes };
}

// =============================================================================
// SUMMARY (Step 5)
// =============================================================================

function updateSummary() {
    const calculatedTabs = project.tabs.filter(t => t.results);
    if (calculatedTabs.length === 0) return;

    const stockData = [];
    calculatedTabs.forEach(tab => {
        const groupLengthCounts = {};
        tab.results.bins.forEach(bin => {
            const group  = bin.group || '';
            const length = bin.stockLength / 1000;
            const key    = `${group}||${length}`;
            groupLengthCounts[key] = (groupLengthCounts[key] || 0) + 1;
        });
        Object.entries(groupLengthCounts).forEach(([key, qty]) => {
            const [group, lengthStr] = key.split('||');
            stockData.push({ group, product: tab.memberName, length: parseFloat(lengthStr), qty });
        });
    });

    stockData.sort((a, b) => {
        const groupA = a.group || '￿';
        const groupB = b.group || '￿';
        if (groupA !== groupB) return groupA.localeCompare(groupB);
        if (a.product !== b.product) return a.product.localeCompare(b.product);
        return b.length - a.length;
    });

    const hasGroups = stockData.some(r => r.group);

    const tableHTML = `
        <div class="summary-table-wrapper">
            <table class="summary-table">
                <thead>
                    <tr>
                        ${hasGroups ? '<th>Group</th>' : ''}
                        <th>Product</th><th>Length (m)</th><th>Qty</th>
                    </tr>
                </thead>
                <tbody>
                    ${stockData.map(row => `
                        <tr>
                            ${hasGroups ? `<td>${row.group || '—'}</td>` : ''}
                            <td>${row.product}</td>
                            <td>${row.length.toFixed(1)}</td>
                            <td>${row.qty}</td>
                        </tr>`).join('')}
                </tbody>
            </table>
            <button id="exportSummaryBtn" class="btn btn-secondary">Export to CSV</button>
        </div>`;

    document.getElementById('summaryContent').innerHTML = tableHTML;
    document.getElementById('exportSummaryBtn').addEventListener('click', () => exportSummaryToCSV(stockData, hasGroups));

    // Unlock Step 5
    const step5 = document.getElementById('step-5');
    if (step5) {
        step5.classList.remove('wizard-step--locked');
        wizard.reachedStep = Math.max(wizard.reachedStep, 5);
    }
}

function exportSummaryToCSV(stockData, hasGroups) {
    const header = hasGroups ? 'Group,Product,Length (m),Qty\n' : 'Product,Length (m),Qty\n';
    let csv = header;
    stockData.forEach(row => {
        csv += hasGroups
            ? `${row.group || ''},${row.product},${row.length.toFixed(1)},${row.qty}\n`
            : `${row.product},${row.length.toFixed(1)},${row.qty}\n`;
    });
    const blob = new Blob([csv], { type: 'text/csv' });
    const url  = window.URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'cutlist_summary.csv';
    document.body.appendChild(a); a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// =============================================================================
// CONVERT TO ESTIMATE
// =============================================================================

function openConvertModal() {
    const calculatedTabs = project.tabs
        .map((tab, idx) => ({ tab, idx }))
        .filter(({ tab }) => tab.results);
    if (calculatedTabs.length === 0) { showToast('Optimise at least one member first', 'error'); return; }

    const products = window.CUTLIST_PRODUCTS || [];
    const rowsHTML = calculatedTabs.map(({ tab, idx }) => {
        // Prefer the member's confirmed Product link over the weak timber-type guess.
        let preselectedId = tab.productId || null;
        if (!preselectedId) {
            const timberType = getTimberType(tab.memberName);
            const guess = timberType !== 'OTHER'
                ? products.find(p => p.name.toUpperCase().includes(timberType))
                : null;
            preselectedId = guess ? guess.id : null;
        }
        const options = products.map(p =>
            `<option value="${p.id}" ${preselectedId === p.id ? 'selected' : ''}>${p.name} (${p.product_type__name})</option>`
        ).join('');
        return `
            <div class="form-group">
                <label>${tab.memberName}</label>
                <select data-tab-index="${idx}" class="convert-product-select">
                    <option value="">— skip this member —</option>
                    ${options}
                </select>
            </div>`;
    }).join('');

    document.getElementById('convertModalRows').innerHTML = rowsHTML;
    document.getElementById('convertEstimateModal').style.display = 'flex';
}

function closeConvertModal() {
    document.getElementById('convertEstimateModal').style.display = 'none';
}

async function submitConvertToEstimate() {
    const mapping = {};
    document.querySelectorAll('.convert-product-select').forEach(sel => {
        if (sel.value) mapping[sel.dataset.tabIndex] = parseInt(sel.value, 10);
    });
    if (Object.keys(mapping).length === 0) {
        showToast('Map at least one member to a product first', 'error');
        return;
    }

    const submitBtn = document.getElementById('convertSubmitBtn');
    submitBtn.disabled = true;

    await saveProject();

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    try {
        const resp = await fetch(window.CUTLIST_CONVERT_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
            body: JSON.stringify({ mapping })
        });
        const data = await resp.json();
        if (data.ok) {
            window.location.href = data.redirect;
        } else {
            showToast(data.error || 'Conversion failed', 'error');
            submitBtn.disabled = false;
        }
    } catch (e) {
        showToast('Conversion failed', 'error');
        submitBtn.disabled = false;
    }
}

// =============================================================================
// SAVE / LOAD / EXPORT
// =============================================================================

async function saveProject() {
    if (project.tabs.length === 0) return;
    readJobDetailsFromDOM();

    const pk = window.CUTLIST_PROJECT_PK;
    if (!pk) return;

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    try {
        const resp = await fetch(`/cutlist/${pk}/save/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
            body: JSON.stringify(project)
        });
        const data = await resp.json();
        if (data.ok) {
            showSaveIndicator();
            if (data.name) {
                const titleEl = document.getElementById('projectTitle');
                if (titleEl) titleEl.textContent = data.name;
            }
        }
    } catch (e) { console.error('Auto-save failed:', e); }
}

function exportProjectJSON() {
    if (project.tabs.length === 0) { showToast('No project data to export', 'warning'); return; }
    readJobDetailsFromDOM();

    const projectData = {
        version: '2.0',
        timestamp: new Date().toISOString(),
        jobDetails: { ...project.jobDetails },
        tabs: project.tabs.map(tab => ({
            memberName: tab.memberName, cuts: tab.cuts,
            stockLengths: tab.stockLengths, productId: tab.productId,
            cutTolerance: tab.cutTolerance,
            overlengthSplitStock: tab.overlengthSplitStock, results: tab.results
        }))
    };

    const titleEl  = document.getElementById('projectTitle');
    const nameSlug = ((titleEl && titleEl.textContent.trim()) || 'untitled')
        .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'untitled';
    const dateStr  = new Date().toISOString().split('T')[0];
    const blob     = new Blob([JSON.stringify(projectData, null, 2)], { type: 'application/json' });
    const url      = window.URL.createObjectURL(blob);
    const a        = document.createElement('a');
    a.href = url; a.download = `cutlist_${nameSlug}_${dateStr}.json`;
    document.body.appendChild(a); a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

function restoreProject(projectData) {
    if (!projectData.tabs || !projectData.tabs.length) return;

    if (projectData.jobDetails) {
        Object.assign(project.jobDetails, projectData.jobDetails);
        writeJobDetailsToDOM();
        const label = project.jobDetails.preparedBy
            ? `Prepared by ${project.jobDetails.preparedBy}`
            : 'Set';
        setStepMeta(1, label);
        markStepDone(1);
    }

    project.tabs        = [];
    project.activeTabId = null;
    tabCounter          = 0;

    projectData.tabs.forEach(tabData => {
        const tabId = `tab-${tabCounter++}`;
        const tab = {
            id: tabId,
            memberName: tabData.memberName,
            cuts: tabData.cuts,
            stockLengths: tabData.stockLengths,
            productId: tabData.productId !== undefined ? tabData.productId : null,
            cutTolerance: tabData.cutTolerance !== undefined ? tabData.cutTolerance : 50,
            overlengthSplitStock: tabData.overlengthSplitStock || 6000,
            results: tabData.results || null
        };
        project.tabs.push(tab);

        if (tab.results && tab.results.bins) {
            tab.results.bins.forEach(bin => {
                if (bin.id === undefined)     bin.id     = binIdCounter++;
                // binIdCounter is a fresh per-page-load counter starting at 0, but restored
                // bins keep whatever id they were assigned in the session that saved them —
                // without this, a newly created bin (add-empty-stick, a later re-optimise)
                // can collide with an existing bin's id, since binIdCounter never otherwise
                // learns that ids up to this bin's are already taken.
                if (typeof bin.id === 'number' && bin.id >= binIdCounter) binIdCounter = bin.id + 1;
            });
        }
    });

    const hasResults  = project.tabs.some(t => t.results);
    const targetStep  = hasResults ? 4 : 3;

    wizard.reachedStep = targetStep;
    for (let i = 1; i <= targetStep; i++) {
        const el = document.getElementById(`step-${i}`);
        if (el) el.classList.remove('wizard-step--locked');
    }

    const totalCuts = project.tabs.reduce((s, t) => s + t.cuts.length, 0);
    setStepMeta(2, `${project.tabs.length} member type${project.tabs.length !== 1 ? 's' : ''}, ${totalCuts} cuts`);
    markStepDone(2);

    renderReviewStep();

    if (hasResults) {
        setStepMeta(3, 'Optimised');
        markStepDone(3);
        document.getElementById('tabsList').innerHTML    = '';
        document.getElementById('tabsContent').innerHTML = '';
        renderResultsTabs();

        const totalSticks = project.tabs.reduce((s, t) => t.results ? s + t.results.stockCount : s, 0);
        setStepMeta(4, `${totalSticks} stick${totalSticks !== 1 ? 's' : ''}`);
        updateSummary();
    }

    openStep(targetStep);
}

function loadProject(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function (e) {
        try {
            const projectData = JSON.parse(e.target.result);
            if (!projectData.tabs) throw new Error('Invalid project file format');
            restoreProject(projectData);
            showToast('Project imported from file', 'success');
        } catch (error) {
            showToast('Error loading file: ' + error.message, 'error');
        }
    };
    reader.readAsText(file);
    event.target.value = '';
}

function showSaveIndicator() {
    const el = document.getElementById('saveIndicator');
    if (!el) return;
    el.classList.add('visible');
    clearTimeout(el._timer);
    el._timer = setTimeout(() => el.classList.remove('visible'), 2000);
}

function showToast(message, type = 'info') {
    const tray = document.getElementById('toast-tray');
    if (!tray) { console.log(message); return; }
    const li = document.createElement('li');
    li.className   = `toast ${type}`;
    li.textContent = message;
    tray.appendChild(li);
    setTimeout(() => {
        li.classList.add('toast-hiding');
        setTimeout(() => li.remove(), 400);
    }, 3500);
}

// =============================================================================
// PDF / PRINT
// =============================================================================

async function openPrintView() {
    if (project.tabs.filter(t => t.results).length === 0) {
        showToast('Please run optimisation first', 'warning');
        return;
    }
    await saveProject();
    window.open(window.CUTLIST_PRINT_URL, '_blank');
}
