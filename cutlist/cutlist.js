// =============================================================================
// STATE
// =============================================================================

const project = {
    jobDetails: {
        jobNumber: '',
        jobDescription: '',
        client: '',
        preparedBy: '',
        kerfWidth: 25
    },
    tabs: [],
    activeTabId: null,
    skippedData: []
};

let tabCounter = 0;
let binIdCounter = 0;
let _editTabId = null;
let _editCutIndex = null;

// =============================================================================
// STATE ACCESSORS
// =============================================================================

function getTab(tabId) {
    return project.tabs.find(t => t.id === tabId);
}

function getActiveTab() {
    return getTab(project.activeTabId);
}

function readJobDetailsFromDOM() {
    project.jobDetails.jobNumber      = document.getElementById('jobNumber').value;
    project.jobDetails.jobDescription = document.getElementById('jobDescription').value;
    project.jobDetails.client         = document.getElementById('client').value;
    project.jobDetails.preparedBy     = document.getElementById('preparedBy').value;
    project.jobDetails.kerfWidth      = parseFloat(document.getElementById('kerfWidth').value) || 25;
}

function writeJobDetailsToDOM() {
    document.getElementById('jobNumber').value      = project.jobDetails.jobNumber;
    document.getElementById('jobDescription').value = project.jobDetails.jobDescription;
    document.getElementById('client').value         = project.jobDetails.client;
    document.getElementById('preparedBy').value     = project.jobDetails.preparedBy;
    document.getElementById('kerfWidth').value      = project.jobDetails.kerfWidth;
}

// =============================================================================
// INITIALISATION
// =============================================================================

document.addEventListener('DOMContentLoaded', function () {
    initJobDetailListeners();
    initGlobalEventListeners();
});

function initJobDetailListeners() {
    const fields = ['jobNumber', 'jobDescription', 'client', 'preparedBy'];
    fields.forEach(id => {
        document.getElementById(id).addEventListener('input', function (e) {
            project.jobDetails[id] = e.target.value;
        });
    });
    document.getElementById('kerfWidth').addEventListener('input', function (e) {
        project.jobDetails.kerfWidth = parseFloat(e.target.value) || 25;
    });
}

function initGlobalEventListeners() {
    document.getElementById('parseBtn').addEventListener('click', parseCSVAndCreateTabs);
    document.getElementById('addTabBtn').addEventListener('click', addManualTab);
    document.getElementById('calculateAllBtn').addEventListener('click', calculateAll);
    document.getElementById('advancedOptimizeBtn').addEventListener('click', advancedOptimizeAll);
    document.getElementById('printBtn').addEventListener('click', generatePDF);
    document.getElementById('copySkippedBtn').addEventListener('click', copySkippedToClipboard);
    document.getElementById('csvFileInput').addEventListener('change', handleCSVFileUpload);
    document.getElementById('saveProjectBtn').addEventListener('click', saveProject);
    document.getElementById('loadProjectBtn').addEventListener('click', () => {
        document.getElementById('loadProjectInput').click();
    });
    document.getElementById('loadProjectInput').addEventListener('change', loadProject);
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') closeCutEditor();
    });
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

function getDefaultStockLengths(memberName) {
    const framingSizes = ['150x45', '200x45', '240x45', '300x45', '300x63'];
    if (memberName.toLowerCase().includes('lvl8')) {
        return [6000];
    } else if (memberName.toLowerCase().includes('lib')) {
        return [7200, 6000, 4800, 4200, 3600, 3000];
    } else if (framingSizes.some(size => memberName.toLowerCase().includes(size))) {
        return [7200, 6000, 5400, 4800, 3600];
    }
    return [7200, 6000, 5400, 4800, 3600];
}

// =============================================================================
// CSV IMPORT
// =============================================================================

function handleCSVFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    document.getElementById('csvFileName').textContent = file.name;
    const reader = new FileReader();
    reader.onload = function (e) {
        document.getElementById('csvInput').value = e.target.result;
    };
    reader.readAsText(file);
}

function parseCSVAndCreateTabs() {
    const csvText = document.getElementById('csvInput').value.trim();
    if (!csvText) {
        alert('Please enter CSV data first');
        return;
    }

    const lines = csvText.split('\n').filter(line => line.trim());
    const parsedData = {};

    lines.forEach(line => {
        const parts = line.split(',').map(s => s.trim());
        if (parts.length >= 3) {
            const memberName = parts[0];
            const quantity   = parseInt(parts[1]);
            const length     = parseFloat(parts[2]);
            const mark       = parts.length >= 4 ? parts[3] : '';
            const group      = parts.length >= 5 ? parts[4] : '';

            if (!isNaN(length) && !isNaN(quantity) && memberName) {
                if (!parsedData[memberName]) parsedData[memberName] = [];
                parsedData[memberName].push({ length, quantity, mark, group });
            }
        }
    });

    const memberNames = Object.keys(parsedData);
    if (memberNames.length === 0) {
        alert('No valid data found. Format should be: Member Name, Quantity, Length, [Mark]');
        return;
    }

    // Reset tab state
    project.tabs = [];
    project.activeTabId = null;
    tabCounter = 0;
    document.getElementById('tabsList').innerHTML    = '';
    document.getElementById('tabsContent').innerHTML = '';

    const membersToProcess = memberNames.slice(0, 5);
    const skippedMembers   = memberNames.slice(5);

    membersToProcess.forEach(memberName => {
        const cuts = sortAndCombineCuts(parsedData[memberName]);
        createTab(memberName, cuts);
    });

    if (skippedMembers.length > 0) {
        displaySkippedMembers(skippedMembers, parsedData);
    } else {
        document.getElementById('skippedMembers').style.display = 'none';
    }

    if (project.tabs.length > 0) {
        activateTab(project.tabs[0].id);
    }
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
        const cutsText = cuts.map(c => `${c.length},${c.quantity}`).join('\n');

        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${memberName}</td>
            <td style="white-space: pre-line;">${cutsText}</td>
        `;
        tbody.appendChild(row);

        cuts.forEach(c => {
            project.skippedData.push(`${c.length}, ${c.quantity}, ${memberName}`);
        });
    });

    document.getElementById('skippedMembers').style.display = 'block';
}

function copySkippedToClipboard() {
    const text = project.skippedData.join('\n');
    navigator.clipboard.writeText(text)
        .then(() => alert('Skipped members copied to clipboard!'))
        .catch(() => alert('Failed to copy to clipboard'));
}

// =============================================================================
// TAB MANAGEMENT
// =============================================================================

function createTab(memberName = '', cuts = []) {
    const tabId = `tab-${tabCounter++}`;

    const tab = {
        id: tabId,
        memberName: memberName || `Member ${tabCounter}`,
        cuts: cuts,
        stockLengths: getDefaultStockLengths(memberName),
        cutTolerance: 50,
        overlengthSplitStock: 6000,
        results: null
    };

    project.tabs.push(tab);
    renderTabButton(tab);
    renderTabContent(tab);
    attachTabEventListeners(tabId);
}

function renderTabButton(tab) {
    // Remove existing if present (for updates)
    const existing = document.querySelector(`.tab[data-tab-id="${tab.id}"]`);
    if (existing) existing.remove();

    const tabButton = document.createElement('div');
    tabButton.className      = 'tab';
    tabButton.dataset.tabId  = tab.id;
    tabButton.innerHTML = `
        <span>${tab.memberName}</span>
        <button class="btn btn-danger" onclick="removeTab('${tab.id}')">×</button>
    `;
    tabButton.onclick = (e) => {
        if (!e.target.classList.contains('btn-danger')) {
            activateTab(tab.id);
        }
    };
    document.getElementById('tabsList').appendChild(tabButton);

    if (tab.id === project.activeTabId) {
        tabButton.classList.add('active');
    }
}

function renderTabContent(tab) {
    // Remove existing if present (for refreshes)
    const existing = document.querySelector(`.tab-content[data-tab-id="${tab.id}"]`);
    if (existing) existing.remove();

    const tabContent = document.createElement('div');
    tabContent.className     = 'tab-content';
    tabContent.dataset.tabId = tab.id;
    tabContent.innerHTML     = generateTabContentHTML(tab);

    if (tab.id === project.activeTabId) {
        tabContent.classList.add('active');
    }

    document.getElementById('tabsContent').appendChild(tabContent);
}

function refreshTab(tabId) {
    const tab = getTab(tabId);
    if (!tab) return;
    renderTabContent(tab);
    attachTabEventListeners(tabId);
    if (tab.results) displayResults(tabId);
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
    if (tabButton && tab) {
        tabButton.querySelector('span').textContent = tab.memberName;
    }
}

function addManualTab() {
    if (project.tabs.length >= 5) {
        alert('Maximum 5 member types allowed');
        return;
    }
    createTab();
    activateTab(project.tabs[project.tabs.length - 1].id);
}

function removeTab(tabId) {
    if (confirm('Remove this member type?')) {
        project.tabs = project.tabs.filter(t => t.id !== tabId);
        document.querySelector(`.tab[data-tab-id="${tabId}"]`).remove();
        document.querySelector(`.tab-content[data-tab-id="${tabId}"]`).remove();

        if (project.tabs.length > 0 && project.activeTabId === tabId) {
            activateTab(project.tabs[0].id);
        }
    }
}

// =============================================================================
// TAB CONTENT HTML
// =============================================================================

function generateTabContentHTML(tab) {
    const cutsHTML = `
        <table class="cuts-table">
            <thead>
                <tr>
                    <th>Length (mm)</th>
                    <th>Quantity</th>
                    <th>Mark/ID</th>
                    <th>Group</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                ${tab.cuts.map((cut, index) => `
                    <tr class="cut-row">
                        <td><input type="number" class="cut-length" data-index="${index}" value="${cut.length}" min="0"></td>
                        <td><input type="number" class="cut-quantity" data-index="${index}" value="${cut.quantity}" min="1"></td>
                        <td><input type="text" class="cut-mark" data-index="${index}" value="${cut.mark || ''}" maxlength="10" placeholder="Optional"></td>
                        <td><input type="text" class="cut-group" data-index="${index}" value="${cut.group || ''}" maxlength="20" placeholder="Optional"></td>
                        <td><button class="btn btn-danger btn-small" onclick="removeCut('${tab.id}', ${index})">×</button></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    const stockHTML = tab.stockLengths.map((length, index) => `
        <div class="stock-item">
            <input type="number" class="stock-length" data-index="${index}" value="${length}" min="0">
            <button class="btn btn-danger" onclick="removeStock('${tab.id}', ${index})">×</button>
        </div>
    `).join('');

    const groupNames = [...new Set(tab.cuts.map(c => c.group).filter(g => g))];
    const groupSummaryHTML = groupNames.length > 0
        ? `<div class="form-group group-summary-block">
               <label>Cut Groups</label>
               <div class="group-tags">
                   ${groupNames.map(g => `<span class="group-tag">${g}</span>`).join('')}
                   <span class="group-tag group-tag-ungrouped">+ ungrouped</span>
               </div>
           </div>`
        : '';

    return `
        <div class="member-section">
            <div class="member-header">
                <div class="form-group">
                    <label>Member Size</label>
                    <input type="text" class="member-name" maxlength="20" value="${tab.memberName}" placeholder="e.g. 240x88 LIB">
                </div>
            </div>

            <div class="member-settings">
                <h3>Member Settings</h3>
                <div class="settings-grid">
                    <div class="form-group">
                        <label>Cut Tolerance (mm)</label>
                        <input type="number" class="cut-tolerance" value="${tab.cutTolerance}" min="0" max="500">
                    </div>
                    <div class="form-group">
                        <label>Overlength Split Stock (mm)</label>
                        <input type="number" class="overlength-split-stock" value="${tab.overlengthSplitStock}" min="0">
                    </div>
                    ${groupSummaryHTML}
                </div>
            </div>

            <div class="cuts-container collapsible-section">
                <div class="collapsible-header" onclick="toggleSection(this)">
                    <h3>Required Cuts</h3>
                    <span class="chevron">&#8964;</span>
                </div>
                <div class="collapsible-body">
                    ${cutsHTML}
                    <button class="btn btn-add add-cut-btn">+ Add Cut</button>
                </div>
            </div>

            <div class="stock-container">
                <h3>Available Stock Lengths (mm)</h3>
                <div class="stock-list">
                    ${stockHTML}
                </div>
                <button class="btn btn-add add-stock-btn">+ Add Stock Length</button>
            </div>

            <button class="btn btn-primary calculate-btn">Calculate Optimization</button>

            <div class="results" style="display: none;"></div>
        </div>
    `;
}

function attachTabEventListeners(tabId) {
    const tabContent = document.querySelector(`.tab-content[data-tab-id="${tabId}"]`);
    const tab        = getTab(tabId);

    tabContent.querySelector('.member-name').addEventListener('input', function (e) {
        tab.memberName = e.target.value;
        updateTabButton(tabId);
    });

    tabContent.querySelector('.cut-tolerance').addEventListener('input', function (e) {
        tab.cutTolerance = parseFloat(e.target.value) || 0;
    });

    tabContent.querySelector('.overlength-split-stock').addEventListener('input', function (e) {
        tab.overlengthSplitStock = parseFloat(e.target.value) || 6000;
    });

    tabContent.querySelectorAll('.cut-length, .cut-quantity, .cut-mark, .cut-group').forEach(input => {
        input.addEventListener('input', function (e) {
            const index = parseInt(e.target.dataset.index);
            if (e.target.classList.contains('cut-length')) {
                tab.cuts[index].length = parseFloat(e.target.value) || 0;
            } else if (e.target.classList.contains('cut-quantity')) {
                tab.cuts[index].quantity = parseInt(e.target.value) || 1;
            } else if (e.target.classList.contains('cut-mark')) {
                tab.cuts[index].mark = e.target.value;
            } else if (e.target.classList.contains('cut-group')) {
                tab.cuts[index].group = e.target.value;
                refreshGroupSummary(tabId);
            }
        });
    });

    tabContent.querySelectorAll('.stock-length').forEach(input => {
        input.addEventListener('input', function (e) {
            const index = parseInt(e.target.dataset.index);
            tab.stockLengths[index] = parseFloat(e.target.value) || 0;
        });
    });

    tabContent.querySelector('.add-cut-btn').addEventListener('click', () => addCut(tabId));
    tabContent.querySelector('.add-stock-btn').addEventListener('click', () => addStock(tabId));
    tabContent.querySelector('.calculate-btn').addEventListener('click', () => calculateOptimization(tabId));
}

// =============================================================================
// COLLAPSE / EXPAND
// =============================================================================

function toggleSection(header) {
    const section = header.closest('.collapsible-section');
    const body    = section.querySelector('.collapsible-body');
    const chevron = header.querySelector('.chevron');
    const isCollapsed = section.classList.toggle('collapsed');
    body.style.display      = isCollapsed ? 'none' : '';
    chevron.style.transform = isCollapsed ? 'rotate(-90deg)' : '';
}

// =============================================================================
// CUT & STOCK MUTATIONS
// =============================================================================

function refreshGroupSummary(tabId) {
    const tab        = getTab(tabId);
    const tabContent = document.querySelector(`.tab-content[data-tab-id="${tabId}"]`);
    const grid       = tabContent.querySelector('.settings-grid');
    if (!grid) return;

    const existing = grid.querySelector('.group-summary-block');
    if (existing) existing.remove();

    const groupNames = [...new Set(tab.cuts.map(c => c.group).filter(g => g))];
    if (groupNames.length > 0) {
        const div = document.createElement('div');
        div.className = 'form-group group-summary-block';
        div.innerHTML = `
            <label>Cut Groups</label>
            <div class="group-tags">
                ${groupNames.map(g => `<span class="group-tag">${g}</span>`).join('')}
                <span class="group-tag group-tag-ungrouped">+ ungrouped</span>
            </div>
        `;
        grid.appendChild(div);
    }
}

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

    if (remaining > 0) {
        splits.push({ length: remaining + kerfWidth + cutTolerance, isFullStick: false });
    }

    return splits;
}

// =============================================================================
// OPTIMISATION ALGORITHM (First Fit Decreasing)
// =============================================================================

function calculateOptimization(tabId) {
    const tab = getTab(tabId);

    if (!tab.memberName) {
        alert('Please enter a member size');
        return;
    }
    if (tab.cuts.length === 0 || tab.cuts.some(c => c.length <= 0 || c.quantity <= 0)) {
        alert('Please enter valid cuts');
        return;
    }
    if (tab.stockLengths.length === 0 || tab.stockLengths.some(l => l <= 0)) {
        alert('Please enter valid stock lengths');
        return;
    }

    const kerfWidth            = project.jobDetails.kerfWidth;
    const cutTolerance         = tab.cutTolerance || 0;
    const overlengthSplitStock = tab.overlengthSplitStock || 6000;
    const maxStockLength       = Math.max(...tab.stockLengths);
    const sortedStock          = [...tab.stockLengths].sort((a, b) => a - b);
    const timberType           = getTimberType(tab.memberName);

    const allBins          = [];
    const overlengthSplits = [];
    let totalOriginalCutLength = 0;

    // Separate cuts into named groups and ungrouped ('')
    const groupMap = {};
    tab.cuts.forEach((cut, cutIdx) => {
        const key = cut.group || '';
        if (!groupMap[key]) groupMap[key] = [];
        groupMap[key].push({ cut, cutIdx });
    });

    // Process named groups first (alpha order), ungrouped last
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
                            length: splitPiece.length,
                            isSplitPiece: true,
                            isFullStick: splitPiece.isFullStick,
                            displayLength: cutLength,
                            mark: cut.mark || '',
                            group: groupKey,
                            cutIndex: cutIdx,
                            originalLength: 0
                        });
                    });
                } else {
                    expandedCuts.push({
                        length: cutLength + cutTolerance,
                        isSplitPiece: false,
                        isFullStick: false,
                        displayLength: cutLength,
                        mark: cut.mark || '',
                        group: groupKey,
                        cutIndex: cutIdx,
                        originalLength: 0
                    });
                }
            }
        });

        expandedCuts.sort((a, b) => b.length - a.length);

        expandedCuts.forEach(cutInfo => {
            if (cutInfo.isFullStick) {
                allBins.push({ id: binIdCounter++, locked: false, stockLength: cutInfo.length, cuts: [cutInfo], remaining: 0, timberType, group: groupKey });
                return;
            }
            // Only fit into bins from the same group
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
                    allBins.push({ id: binIdCounter++, locked: false, stockLength: suitableStock, cuts: [cutInfo], remaining: suitableStock - cutInfo.length, timberType, group: groupKey });
                } else {
                    alert(`Cut length ${cutInfo.length}mm exceeds all available stock lengths!`);
                }
            }
        });
    });

    const bins                 = allBins;
    const totalStockUsed       = bins.reduce((sum, bin) => sum + bin.stockLength, 0);
    const totalActualCutLength = bins.reduce((sum, bin) => bin.cuts.reduce((s, c) => s + c.length, sum), 0);
    const totalKerfLoss        = bins.reduce((sum, bin) => sum + (bin.cuts.length - 1) * kerfWidth, 0);
    const totalTolerance       = totalActualCutLength - totalOriginalCutLength;
    const totalWaste           = totalStockUsed - totalActualCutLength - totalKerfLoss;
    const wastePercentage      = ((totalWaste / totalStockUsed) * 100).toFixed(2);

    tab.results = {
        bins,
        totalStockUsed,
        totalCutLength: totalOriginalCutLength,
        totalKerfLoss,
        totalTolerance,
        totalWaste,
        wastePercentage,
        stockCount: bins.length,
        kerfWidth,
        overlengthSplits
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
                <h3>Optimization Results</h3>
                <span class="chevron">&#8964;</span>
            </div>
            <div class="collapsible-body">
    `;

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

    // Named groups alpha, ungrouped last
    const groupOrder = [...new Set(bins.map(b => b.group || ''))].sort((a, b) => {
        if (a === '') return 1;
        if (b === '') return -1;
        return a.localeCompare(b);
    });
    const hasNamedGroups = groupOrder.some(k => k !== '');

    html += '<div class="cutting-diagrams"><h4>Cutting Diagrams</h4>';

    let stickCounter = 1;
    groupOrder.forEach(groupKey => {
        const groupBins = bins
            .filter(b => (b.group || '') === groupKey)
            .sort((a, b) => b.stockLength - a.stockLength || a.remaining - b.remaining);

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
                    <div class="collapsible-body diagrams-container">
            `;
        } else {
            html += '<div class="diagrams-container">';
        }

        groupBins.forEach(bin => {
            html += generateCuttingDiagram(bin, stickCounter++, kerfWidth, tabId);
        });

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

    resultsDiv.innerHTML = html;
    resultsDiv.style.display = 'block';
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
    const lockedClass = bin.locked ? ' bin-locked' : '';

    let html = `
        <div class="stick-diagram ${timberClass}${lockedClass}" data-bin-id="${bin.id}">
            <div class="stick-label">Stick ${stickNumber}<br>${stockLength}mm</div>
            <button class="btn-lock${bin.locked ? ' btn-lock-active' : ''}"
                    onclick="toggleBinLock('${tabId}', ${bin.id})"
                    title="${bin.locked ? 'Unlock stick' : 'Lock stick'}"
                    type="button">&#128274;</button>
            <div class="stick" style="height: ${diagramHeight}px; width: ${diagramWidth}px;">
    `;

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
        const onclickAttr   = (cutIndex !== undefined && tabId)
            ? ` onclick="openCutEditor('${tabId}', ${cutIndex})"`
            : '';

        let displayLabel;
        if (isSplitPiece && cutLength === stockLength) {
            displayLabel = mark ? `${mark} (full)` : `${displayLength} (full)`;
        } else {
            displayLabel = mark ? `${mark}: ${Math.round(displayLength)}` : Math.round(displayLength);
        }

        const titleText = `${isSplitPiece ? 'Split piece: ' : ''}${Math.round(cutLength)}mm${mark ? ' [' + mark + ']' : ''}${cutIndex !== undefined ? '\nClick to edit' : ''}`;

        html += `
            <div class="${cutClass}${clickableClass}" style="height: ${cutHeight}px;" title="${titleText}"${onclickAttr}>
                <span class="cut-label">${displayLabel}</span>
            </div>
        `;

        if (index < cuts.length - 1 && kerfWidth > 0) {
            html += `<div class="kerf-segment" style="height: ${kerfHeightPx}px;" title="Kerf: ${kerfWidth}mm"></div>`;
        }
    });

    if (remaining > 0) {
        const wasteHeight = (remaining / usableLength) * totalNonKerfHeight;
        html += `
            <div class="waste-segment" style="height: ${wasteHeight}px;" title="Waste: ${remaining}mm">
                <span class="waste-label">${remaining}</span>
            </div>
        `;
    }

    html += `</div></div>`;
    return html;
}

// =============================================================================
// LOCK STICKS (Feature 2)
// =============================================================================

function toggleBinLock(tabId, binId) {
    const tab = getTab(tabId);
    if (!tab || !tab.results) return;
    const bin = tab.results.bins.find(b => b.id === binId);
    if (!bin) return;

    bin.locked = !bin.locked;

    const stickEl = document.querySelector(
        `.tab-content[data-tab-id="${tabId}"] .stick-diagram[data-bin-id="${binId}"]`
    );
    if (stickEl) {
        stickEl.classList.toggle('bin-locked', bin.locked);
        const lockBtn = stickEl.querySelector('.btn-lock');
        if (lockBtn) {
            lockBtn.classList.toggle('btn-lock-active', bin.locked);
            lockBtn.title = bin.locked ? 'Unlock stick' : 'Lock stick';
        }
    }
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
    document.getElementById('editCutMark').value     = cut.mark || '';
    document.getElementById('editCutGroup').value    = cut.group || '';
    document.getElementById('editCutHint').textContent =
        `${cut.quantity} piece${cut.quantity !== 1 ? 's' : ''} of this cut entry. Changes affect all instances and will re-run optimisation.`;

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

    const tabId    = _editTabId;
    const cutIndex = _editCutIndex;
    const tab      = getTab(tabId);
    if (!tab) return;

    const newLength   = parseFloat(document.getElementById('editCutLength').value);
    const newQuantity = parseInt(document.getElementById('editCutQuantity').value);
    const newMark     = document.getElementById('editCutMark').value.trim();
    const newGroup    = document.getElementById('editCutGroup').value.trim();

    if (isNaN(newLength) || newLength <= 0) {
        alert('Please enter a valid length');
        return;
    }
    if (isNaN(newQuantity) || newQuantity < 1) {
        alert('Please enter a valid quantity');
        return;
    }

    tab.cuts[cutIndex].length   = newLength;
    tab.cuts[cutIndex].quantity = newQuantity;
    tab.cuts[cutIndex].mark     = newMark;
    tab.cuts[cutIndex].group    = newGroup;

    closeCutEditor();

    // Clear results so refreshTab doesn't re-render stale diagram
    tab.results = null;
    refreshTab(tabId);
    calculateOptimization(tabId);
    updateSummary();
}

// =============================================================================
// CALCULATE ALL
// =============================================================================

function calculateAll() {
    if (project.tabs.length === 0) {
        alert('No member types to calculate');
        return;
    }

    let allCalculated = true;
    project.tabs.forEach(tab => {
        try {
            calculateOptimization(tab.id);
        } catch (error) {
            allCalculated = false;
            console.error(`Error calculating ${tab.memberName}:`, error);
        }
    });

    if (allCalculated) {
        updateSummary();
        document.getElementById('advancedOptimizeBtn').style.display = 'inline-block';
    }
}

// =============================================================================
// ADVANCED OPTIMISATION
// =============================================================================

function advancedOptimizeAll() {
    if (project.tabs.length === 0) {
        alert('No member types to calculate');
        return;
    }

    const calculatedTabs = project.tabs.filter(t => t.results);
    if (calculatedTabs.length === 0) {
        alert('Please run standard calculation first');
        return;
    }

    const kerfWidth        = project.jobDetails.kerfWidth;
    let totalSavings       = 0;
    let upgradeCount       = 0;
    let consolidationCount = 0;
    const maxUpgrades      = 10;

    calculatedTabs.forEach(tab => {
        if (upgradeCount >= maxUpgrades) return;
        const savings = advancedOptimizeTab(tab, kerfWidth, maxUpgrades - upgradeCount);
        totalSavings  += savings.materialSaved;
        upgradeCount  += savings.upgradesPerformed;
    });

    calculatedTabs.forEach(tab => {
        const consolidation    = consolidateBins(tab, kerfWidth);
        totalSavings          += consolidation.materialSaved;
        consolidationCount    += consolidation.consolidationsPerformed;
    });

    calculatedTabs.forEach(tab => displayResults(tab.id));
    updateSummary();

    if (totalSavings > 0) {
        let message = `Advanced optimization saved ${totalSavings}mm of material!`;
        if (upgradeCount > 0)       message += `\n- ${upgradeCount} stick upgrades`;
        if (consolidationCount > 0) message += `\n- ${consolidationCount} stick consolidations`;
        alert(message);
    } else {
        alert('No further optimization possible - current solution is already optimal!');
    }
}

function advancedOptimizeTab(tab, kerfWidth, maxUpgradesRemaining) {
    let materialSaved    = 0;
    let upgradesPerformed = 0;

    const sortedStock  = [...tab.stockLengths].sort((a, b) => a - b);
    let workingBins    = JSON.parse(JSON.stringify(tab.results.bins));

    const binsWithOffcuts = workingBins
        .map((bin, index) => ({ bin, index }))
        .filter(item => item.bin.remaining >= 500 && !item.bin.locked)
        .sort((a, b) => b.bin.remaining - a.bin.remaining);

    for (let item of binsWithOffcuts) {
        if (upgradesPerformed >= maxUpgradesRemaining) break;

        const bin                = item.bin;
        const currentStockLength = bin.stockLength;
        const currentStockIndex  = sortedStock.indexOf(currentStockLength);

        if (currentStockIndex === -1) continue;

        const maxStockToTry = Math.min(currentStockIndex + 4, sortedStock.length);
        let bestUpgrade = null;
        let bestSavings = 0;

        for (let stockIndex = currentStockIndex + 1; stockIndex < maxStockToTry; stockIndex++) {
            const newStockLength = sortedStock[stockIndex];
            const usedLength     = bin.cuts.reduce((sum, cut) => sum + cut, 0) + (bin.cuts.length - 1) * kerfWidth;
            const availableSpace = newStockLength - usedLength;

            const cutsToMove = findCutsToMove(workingBins, item.index, availableSpace, kerfWidth, bin.group);

            if (cutsToMove.length > 0) {
                const binsToEliminate = new Set();
                cutsToMove.forEach(cutInfo => {
                    const sourceBin      = workingBins[cutInfo.binIndex];
                    const remainingCuts  = sourceBin.cuts.filter(c =>
                        !cutsToMove.some(cm => cm.binIndex === cutInfo.binIndex && cm.cut === c)
                    );
                    if (remainingCuts.length === 0) binsToEliminate.add(cutInfo.binIndex);
                });

                let materialFreed = 0;
                binsToEliminate.forEach(binIndex => {
                    materialFreed += workingBins[binIndex].stockLength;
                });

                const upgradeCost = newStockLength - currentStockLength;
                const netSavings  = materialFreed - upgradeCost;

                if (netSavings > bestSavings && netSavings > 0) {
                    bestSavings = netSavings;
                    bestUpgrade = { newStockLength, cutsToMove, binsToEliminate };
                }
            }
        }

        if (bestUpgrade) {
            bin.stockLength = bestUpgrade.newStockLength;
            bestUpgrade.cutsToMove.forEach(cutInfo => {
                bin.cuts.push(cutInfo.cut);
            });

            const newUsedLength = bin.cuts.reduce((sum, cut) => sum + cut, 0) + (bin.cuts.length - 1) * kerfWidth;
            bin.remaining = bestUpgrade.newStockLength - newUsedLength;

            bestUpgrade.cutsToMove.forEach(cutInfo => {
                const sourceBin = workingBins[cutInfo.binIndex];
                const cutIndex  = sourceBin.cuts.indexOf(cutInfo.cut);
                if (cutIndex > -1) sourceBin.cuts.splice(cutIndex, 1);
            });

            workingBins = workingBins.filter(b => b.cuts.length > 0);
            workingBins.forEach(b => {
                if (b.cuts.length > 0) {
                    const usedLength = b.cuts.reduce((sum, cut) => sum + cut, 0) + (b.cuts.length - 1) * kerfWidth;
                    b.remaining = b.stockLength - usedLength;
                }
            });

            materialSaved    += bestSavings;
            upgradesPerformed++;

            const newBinsWithOffcuts = workingBins
                .map((b, index) => ({ bin: b, index }))
                .filter(i => i.bin.remaining >= 500)
                .sort((a, b) => b.bin.remaining - a.bin.remaining);

            binsWithOffcuts.length = 0;
            binsWithOffcuts.push(...newBinsWithOffcuts);
        }
    }

    if (materialSaved > 0) {
        tab.results.bins       = workingBins;
        const newMaterial      = calculateTotalMaterial(tab.results.bins);
        tab.results.totalStockUsed = newMaterial;
        tab.results.stockCount = tab.results.bins.length;

        const totalCutLength = tab.results.bins.reduce((sum, bin) =>
            sum + bin.cuts.reduce((s, cut) => s + cut, 0), 0);
        const totalKerfLoss  = tab.results.bins.reduce((sum, bin) =>
            sum + (bin.cuts.length - 1) * kerfWidth, 0);

        tab.results.totalWaste       = newMaterial - totalCutLength - totalKerfLoss;
        tab.results.wastePercentage  = ((tab.results.totalWaste / newMaterial) * 100).toFixed(2);
    }

    return { materialSaved, upgradesPerformed };
}

function findCutsToMove(workingBins, excludeBinIndex, availableSpace, kerfWidth, group) {
    const cutsToMove   = [];
    let spaceRemaining = availableSpace;

    const sortedBinIndices = workingBins
        .map((bin, index) => ({ bin, index }))
        .filter(item => item.index !== excludeBinIndex && !item.bin.locked && (item.bin.group || '') === (group || ''))
        .sort((a, b) => a.bin.stockLength - b.bin.stockLength);

    for (let item of sortedBinIndices) {
        const bin     = item.bin;
        const binIndex = item.index;

        const totalCutsLength = bin.cuts.reduce((sum, cut) => sum + cut, 0);
        const kerfsNeeded     = (bin.cuts.length + cutsToMove.length) * kerfWidth;
        const spaceNeeded     = totalCutsLength + kerfsNeeded;

        if (spaceNeeded <= spaceRemaining) {
            bin.cuts.forEach(cut => cutsToMove.push({ cut, binIndex }));
            spaceRemaining -= spaceNeeded;
        } else {
            for (let cut of bin.cuts) {
                const cutSpaceNeeded = cut + (cutsToMove.length > 0 ? kerfWidth : 0);
                if (cutSpaceNeeded <= spaceRemaining) {
                    cutsToMove.push({ cut, binIndex });
                    spaceRemaining -= cutSpaceNeeded;
                }
            }
        }
    }

    return cutsToMove;
}

function calculateTotalMaterial(bins) {
    return bins.reduce((sum, bin) => sum + bin.stockLength, 0);
}

// =============================================================================
// BIN CONSOLIDATION
// =============================================================================

function consolidateBins(tab, kerfWidth) {
    let materialSaved          = 0;
    let consolidationsPerformed = 0;

    const bins         = tab.results.bins;
    const stockLengths = [...tab.stockLengths].sort((a, b) => a - b);

    // Standard pair consolidation map (2×N → 1×2N)
    const pairConsolidationMap = new Map();
    stockLengths.forEach(length => {
        const doubleLength = length * 2;
        if (stockLengths.includes(doubleLength)) {
            pairConsolidationMap.set(length, doubleLength);
        }
    });

    // Multi-bin consolidation patterns
    const multiConsolidationPatterns = [
        {
            from: { length: 3600, count: 3 },
            to: [5400, 5400],
            save: 0
        }
    ];

    // Group bins by (group, stock length) — keeps groups isolated
    const uniqueGroups = [...new Set(bins.map(b => b.group || ''))];
    const binsByLength = {};
    bins.forEach((bin, index) => {
        if (bin.locked) return;
        const k = `${bin.group || ''}||${bin.stockLength}`;
        if (!binsByLength[k]) binsByLength[k] = [];
        binsByLength[k].push({ bin, index });
    });

    // Try multi-bin consolidation first
    multiConsolidationPatterns.forEach(pattern => {
        const { from, to, save } = pattern;
        if (!to.every(targetLength => stockLengths.includes(targetLength))) return;
        uniqueGroups.forEach(group => {
        const binsOfThisLength = binsByLength[`${group}||${from.length}`];
        if (!binsOfThisLength || binsOfThisLength.length < from.count) return;

        while (binsOfThisLength.length >= from.count) {
            const binGroup    = binsOfThisLength.slice(0, from.count);
            const allCuts     = binGroup.flatMap(item => item.bin.cuts);
            const totalUsedLength = allCuts.reduce((sum, cut) => {
                const cutLength = typeof cut === 'object' ? cut.length : cut;
                return sum + cutLength;
            }, 0);
            const totalKerfLoss = to.reduce((sum, targetLength, idx) => {
                const cutsPerBin = Math.ceil(allCuts.length / to.length);
                return sum + ((idx < to.length - 1 ? cutsPerBin : allCuts.length - (cutsPerBin * (to.length - 1))) - 1) * kerfWidth;
            }, 0);
            const totalNeeded    = totalUsedLength + totalKerfLoss;
            const totalAvailable = to.reduce((sum, len) => sum + len, 0);

            if (totalNeeded <= totalAvailable) {
                const targetBins = to.map(length => ({ stockLength: length, cuts: [], remaining: length }));
                const sortedCuts = [...allCuts].sort((a, b) => {
                    const aLen = typeof a === 'object' ? a.length : a;
                    const bLen = typeof b === 'object' ? b.length : b;
                    return bLen - aLen;
                });

                let allFit = true;
                for (let cut of sortedCuts) {
                    const cutLength = typeof cut === 'object' ? cut.length : cut;
                    let placed = false;
                    for (let targetBin of targetBins) {
                        const spaceNeeded = cutLength + (targetBin.cuts.length > 0 ? kerfWidth : 0);
                        if (targetBin.remaining >= spaceNeeded) {
                            targetBin.cuts.push(cut);
                            targetBin.remaining -= spaceNeeded;
                            placed = true;
                            break;
                        }
                    }
                    if (!placed) { allFit = false; break; }
                }

                if (allFit) {
                    binGroup[0].bin.stockLength = targetBins[0].stockLength;
                    binGroup[0].bin.cuts        = targetBins[0].cuts;
                    binGroup[0].bin.remaining   = targetBins[0].remaining;

                    if (targetBins.length > 1 && binGroup.length > 1) {
                        binGroup[1].bin.stockLength = targetBins[1].stockLength;
                        binGroup[1].bin.cuts        = targetBins[1].cuts;
                        binGroup[1].bin.remaining   = targetBins[1].remaining;
                    }

                    for (let i = targetBins.length; i < binGroup.length; i++) {
                        binGroup[i].bin.cuts = [];
                    }

                    materialSaved          += save;
                    consolidationsPerformed++;
                    binsOfThisLength.splice(0, from.count);
                } else {
                    break;
                }
            } else {
                break;
            }
        }
        }); // end group
    });

    // Standard pair consolidation
    pairConsolidationMap.forEach((targetLength, sourceLength) => {
        uniqueGroups.forEach(group => {
        const binsOfThisLength = binsByLength[`${group}||${sourceLength}`];
        if (!binsOfThisLength || binsOfThisLength.length < 2) return;

        for (let i = 0; i < binsOfThisLength.length - 1; i++) {
            for (let j = i + 1; j < binsOfThisLength.length; j++) {
                const bin1 = binsOfThisLength[i].bin;
                const bin2 = binsOfThisLength[j].bin;
                const combinedCuts = [...bin1.cuts, ...bin2.cuts];

                const combinedUsedLength = combinedCuts.reduce((sum, cut) => {
                    const cutLength = typeof cut === 'object' ? cut.length : cut;
                    return sum + cutLength;
                }, 0);
                const combinedKerfLoss = (combinedCuts.length - 1) * kerfWidth;
                const totalNeeded      = combinedUsedLength + combinedKerfLoss;

                if (totalNeeded <= targetLength) {
                    const oldMaterial = 2 * sourceLength;
                    const savings     = oldMaterial - targetLength;
                    const newWaste    = targetLength - totalNeeded;
                    const oldTotalWaste = bin1.remaining + bin2.remaining;

                    if (savings > 0 || (newWaste >= 500 && newWaste < oldTotalWaste)) {
                        bin1.stockLength = targetLength;
                        bin1.cuts        = combinedCuts;
                        bin1.remaining   = newWaste;
                        bin2.cuts        = [];

                        materialSaved          += savings;
                        consolidationsPerformed++;

                        binsOfThisLength.splice(j, 1);
                        j--;
                    }
                }
            }
        }
        }); // end group
    });

    // Remove empty bins
    tab.results.bins = bins.filter(b => b.cuts.length > 0);

    // General greedy consolidation
    const binsByLengthFinal = {};
    tab.results.bins.forEach((bin, index) => {
        if (bin.locked) return;
        const k = `${bin.group || ''}||${bin.stockLength}`;
        if (!binsByLengthFinal[k]) binsByLengthFinal[k] = [];
        binsByLengthFinal[k].push({ bin, index });
    });

    Object.entries(binsByLengthFinal).forEach(([key, binsGroup]) => {
        if (binsGroup.length < 2) return;
        const sourceLength = parseInt(key.split('||')[1]);

        for (let groupSize = 2; groupSize <= Math.min(binsGroup.length, 5); groupSize++) {
            for (let startIdx = 0; startIdx <= binsGroup.length - groupSize; startIdx++) {
                const binGroup = binsGroup.slice(startIdx, startIdx + groupSize);
                const allCuts  = binGroup.flatMap(item => item.bin.cuts);

                const totalUsedLength = allCuts.reduce((sum, cut) => {
                    const cutLength = typeof cut === 'object' ? cut.length : cut;
                    return sum + cutLength;
                }, 0);

                const oldMaterial    = groupSize * sourceLength;
                const possibleTargets = [];

                stockLengths.forEach(targetLength => {
                    if (targetLength >= sourceLength) {
                        const kerfLoss    = (allCuts.length - 1) * kerfWidth;
                        const totalNeeded = totalUsedLength + kerfLoss;
                        if (totalNeeded <= targetLength) {
                            possibleTargets.push({
                                stockSizes: [targetLength],
                                totalMaterial: targetLength,
                                savings: oldMaterial - targetLength
                            });
                        }
                    }
                });

                stockLengths.forEach(target1 => {
                    if (target1 <= sourceLength) {
                        stockLengths.forEach(target2 => {
                            if (target2 <= sourceLength) {
                                const totalTarget = target1 + target2;
                                if (totalTarget < oldMaterial) {
                                    possibleTargets.push({
                                        stockSizes: [target1, target2],
                                        totalMaterial: totalTarget,
                                        savings: oldMaterial - totalTarget
                                    });
                                }
                            }
                        });
                    }
                });

                possibleTargets.sort((a, b) => b.savings - a.savings);

                for (let target of possibleTargets) {
                    if (target.savings <= 0) break;

                    const targetBins = target.stockSizes.map(length => ({
                        stockLength: length, cuts: [], remaining: length
                    }));
                    const sortedCuts = [...allCuts].sort((a, b) => {
                        const aLen = typeof a === 'object' ? a.length : a;
                        const bLen = typeof b === 'object' ? b.length : b;
                        return bLen - aLen;
                    });

                    let allFit = true;
                    for (let cut of sortedCuts) {
                        const cutLength = typeof cut === 'object' ? cut.length : cut;
                        let placed = false;
                        for (let targetBin of targetBins) {
                            const spaceNeeded = cutLength + (targetBin.cuts.length > 0 ? kerfWidth : 0);
                            if (targetBin.remaining >= spaceNeeded) {
                                targetBin.cuts.push(cut);
                                targetBin.remaining -= spaceNeeded;
                                placed = true;
                                break;
                            }
                        }
                        if (!placed) { allFit = false; break; }
                    }

                    if (allFit) {
                        for (let i = 0; i < targetBins.length && i < binGroup.length; i++) {
                            binGroup[i].bin.stockLength = targetBins[i].stockLength;
                            binGroup[i].bin.cuts        = targetBins[i].cuts;
                            binGroup[i].bin.remaining   = targetBins[i].remaining;
                        }
                        for (let i = targetBins.length; i < binGroup.length; i++) {
                            binGroup[i].bin.cuts = [];
                        }

                        materialSaved          += target.savings;
                        consolidationsPerformed++;
                        binsGroup.splice(startIdx, groupSize);
                        break;
                    }
                }
            }
        }
    });

    tab.results.bins = tab.results.bins.filter(b => b.cuts.length > 0);

    if (consolidationsPerformed > 0) {
        const newMaterial          = calculateTotalMaterial(tab.results.bins);
        tab.results.totalStockUsed = newMaterial;
        tab.results.stockCount     = tab.results.bins.length;

        const totalCutLength = tab.results.bins.reduce((sum, bin) =>
            sum + bin.cuts.reduce((s, cut) => {
                const cutLength = typeof cut === 'object' ? cut.length : cut;
                return s + cutLength;
            }, 0), 0);

        const totalKerfLoss       = tab.results.bins.reduce((sum, bin) =>
            sum + (bin.cuts.length - 1) * kerfWidth, 0);
        tab.results.totalWaste    = newMaterial - totalCutLength - totalKerfLoss;
        tab.results.wastePercentage = ((tab.results.totalWaste / newMaterial) * 100).toFixed(2);
    }

    return { materialSaved, consolidationsPerformed };
}

// =============================================================================
// SUMMARY
// =============================================================================

function updateSummary() {
    const calculatedTabs = project.tabs.filter(t => t.results);

    if (calculatedTabs.length === 0) {
        document.getElementById('summarySection').style.display = 'none';
        return;
    }

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

    // Sort: group (blank last), then product, then length desc
    stockData.sort((a, b) => {
        const groupA = a.group || '\uFFFF';
        const groupB = b.group || '\uFFFF';
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
                        <th>Product</th>
                        <th>Length (m)</th>
                        <th>Qty</th>
                    </tr>
                </thead>
                <tbody>
                    ${stockData.map(row => `
                        <tr>
                            ${hasGroups ? `<td>${row.group || '—'}</td>` : ''}
                            <td>${row.product}</td>
                            <td>${row.length.toFixed(1)}</td>
                            <td>${row.qty}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            <button id="exportSummaryBtn" class="btn btn-secondary">Export to CSV</button>
        </div>
    `;

    document.getElementById('summaryContent').innerHTML = tableHTML;
    document.getElementById('summarySection').style.display = 'block';
    document.getElementById('exportSummaryBtn').addEventListener('click', () => exportSummaryToCSV(stockData, hasGroups));
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
    a.href     = url;
    a.download = 'cutlist_summary.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// =============================================================================
// SAVE / LOAD PROJECT
// =============================================================================

function saveProject() {
    if (project.tabs.length === 0) {
        alert('No project data to save');
        return;
    }

    // Sync job details from DOM before saving
    readJobDetailsFromDOM();

    const projectData = {
        version: '1.2',
        timestamp: new Date().toISOString(),
        jobDetails: { ...project.jobDetails },
        tabs: project.tabs.map(tab => ({
            memberName: tab.memberName,
            cuts: tab.cuts,
            stockLengths: tab.stockLengths,
            cutTolerance: tab.cutTolerance,
            overlengthSplitStock: tab.overlengthSplitStock,
            results: tab.results
        }))
    };

    const jobNum   = project.jobDetails.jobNumber || 'untitled';
    const dateStr  = new Date().toISOString().split('T')[0];
    const filename = `cutlist_${jobNum}_${dateStr}.json`;

    const blob = new Blob([JSON.stringify(projectData, null, 2)], { type: 'application/json' });
    const url  = window.URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);

    console.log('Project saved:', filename);
}

function loadProject(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function (e) {
        try {
            const projectData = JSON.parse(e.target.result);

            if (!projectData.version || !projectData.tabs) {
                throw new Error('Invalid project file format');
            }

            // Reset state
            project.tabs        = [];
            project.activeTabId = null;
            tabCounter          = 0;
            document.getElementById('tabsList').innerHTML    = '';
            document.getElementById('tabsContent').innerHTML = '';
            document.getElementById('summarySection').style.display = 'none';

            // Restore job details
            if (projectData.jobDetails) {
                Object.assign(project.jobDetails, projectData.jobDetails);
                writeJobDetailsToDOM();
            }

            // Restore tabs
            projectData.tabs.forEach(tabData => {
                const tabId = `tab-${tabCounter++}`;
                const tab = {
                    id: tabId,
                    memberName: tabData.memberName,
                    cuts: tabData.cuts,
                    stockLengths: tabData.stockLengths,
                    cutTolerance: tabData.cutTolerance || 0,
                    overlengthSplitStock: tabData.overlengthSplitStock || 6000,
                    results: tabData.results || null
                };

                project.tabs.push(tab);
                renderTabButton(tab);
                renderTabContent(tab);
                attachTabEventListeners(tabId);

                // Assign IDs and locked flags to bins from older save files
                if (tab.results && tab.results.bins) {
                    tab.results.bins.forEach(bin => {
                        if (bin.id === undefined) bin.id = binIdCounter++;
                        if (bin.locked === undefined) bin.locked = false;
                    });
                }

                if (tab.results) displayResults(tabId);
            });

            if (project.tabs.length > 0) {
                activateTab(project.tabs[0].id);
            }

            const calculatedTabs = project.tabs.filter(t => t.results);
            if (calculatedTabs.length > 0) {
                updateSummary();
                document.getElementById('advancedOptimizeBtn').style.display = 'inline-block';
            }

            alert('Project loaded successfully!');
            console.log('Project loaded:', file.name);

        } catch (error) {
            alert('Error loading project file: ' + error.message);
            console.error('Load error:', error);
        }
    };

    reader.readAsText(file);
    event.target.value = '';
}

// =============================================================================
// PDF / PRINT
// =============================================================================

function generatePDF() {
    if (project.tabs.length === 0) {
        alert('No data to print');
        return;
    }

    const calculatedTabs = project.tabs.filter(t => t.results);
    if (calculatedTabs.length === 0) {
        alert('Please calculate at least one member type first');
        return;
    }

    document.querySelectorAll('.tab-content').forEach(content => {
        const tabId = content.dataset.tabId;
        const tab   = getTab(tabId);

        if (tab && tab.results) {
            content.classList.remove('active');
            content.style.display = 'block';
            content.classList.add('print-visible');
        } else {
            content.style.display = 'none';
            content.classList.remove('print-visible');
        }
    });

    setTimeout(() => {
        window.print();

        setTimeout(() => {
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('print-visible');
                content.style.display = '';
                content.classList.toggle('active', content.dataset.tabId === project.activeTabId);
            });
        }, 100);
    }, 50);
}
