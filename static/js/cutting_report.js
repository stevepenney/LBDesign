// Shared cutting-report rendering helpers — used by cutlist's own print view
// (estimate-agnostic, works for any cutlist) and by the jobs-app cladding Part
// report. Deliberately standalone: plain functions over (bins, kerfWidth) data
// only, no dependency on cutlist.js's global `project` object, DOM event
// handlers, or any of the interactive editor's state — safe to load on any
// page without pulling in the whole wizard.

function escReportText(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// ─── Repetition grouping ────────────────────────────────────────
// Two sticks count as "the same layout" if they share a stock length and
// the same multiset of cut lengths, regardless of the order those cuts
// happen to sit in on any one physical bin (two independently-produced
// bins with identical cuts can end up in a different order). The
// representative bin picked for the diagram has its cuts re-sorted
// largest-to-smallest so every printed pattern reads consistently.

function cutLengthOf(cut) {
    return typeof cut === 'object' ? (cut.displayLength ?? cut.length) : cut;
}

function groupIdenticalLayouts(bins) {
    const groups = new Map();
    bins.forEach(bin => {
        const lengths = bin.cuts.map(cutLengthOf).slice().sort((a, b) => b - a);
        const key = `${bin.stockLength}|${lengths.join(',')}`;
        if (!groups.has(key)) {
            const sortedCuts = [...bin.cuts].sort((a, b) => cutLengthOf(b) - cutLengthOf(a));
            groups.set(key, { representative: { ...bin, cuts: sortedCuts }, count: 0 });
        }
        groups.get(key).count += 1;
    });
    return Array.from(groups.values());
}

// ─── Pattern summary table ────────────────────────────────────
// One row per distinct pattern — stock length, how many sticks use it,
// number of saw cuts, kerf loss, and leftover remnant. All per-stick
// (not multiplied by qty off), matching how Genia states these facts,
// just consolidated into one table instead of a box repeated per layout.

function buildPatternSummaryTable(layouts, kerfWidth) {
    const rows = layouts.map((layout, i) => {
        const rep      = layout.representative;
        const numCuts  = rep.cuts.length;
        const cutWaste = numCuts * kerfWidth;
        return `<tr>
          <td>Pattern ${i + 1}</td>
          <td class="num">${rep.stockLength}mm</td>
          <td class="num">${layout.count}</td>
          <td class="num">${numCuts}</td>
          <td class="num">${cutWaste}mm</td>
          <td class="num">${rep.remaining || 0}mm</td>
        </tr>`;
    }).join('');

    return `<table class="print-table print-pattern-table">
        <thead>
          <tr>
            <th>Pattern</th>
            <th class="num">Stock Length</th>
            <th class="num">Qty off</th>
            <th class="num">Cuts</th>
            <th class="num">Cut Waste</th>
            <th class="num">Leftover</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>`;
}

// ─── Horizontal cutting diagram ─────────────────────────────────
// A dedicated report-only renderer, deliberately separate from
// generateCuttingDiagram() in cutlist.js — the interactive Step 4 editor
// keeps its vertical sticks (needed for drag/drop and stick-length editing);
// this only ever runs on a report page. Widths are simple percentages of
// stock length; a report doesn't need the pixel-exact kerf-gap math the
// live editor does.

function generateHorizontalDiagram(bin, label) {
    const { stockLength, cuts, remaining, timberType } = bin;
    const timberClass = timberType ? `timber-${timberType.toLowerCase()}` : 'timber-other';

    let segmentsHtml = '';
    cuts.forEach(cutInfo => {
        const isSplitPiece  = typeof cutInfo === 'object' ? cutInfo.isSplitPiece : false;
        // `length` (not `displayLength`) is the actual physical stock consumed by this cut —
        // displayLength/segmentLength are nominal, label-only values (see cutlist.js's
        // generateCuttingDiagram, which sizes segments the same way). Sizing by displayLength
        // instead leaves an unshaded gap at the end of the stick equal to the padding baked
        // into `length` (cut tolerance / kerf-fit allowance) across every cut.
        const cutLength     = typeof cutInfo === 'object' ? cutInfo.length : cutInfo;
        const displayLength = typeof cutInfo === 'object' ? (cutInfo.displayLength ?? cutInfo.length) : cutInfo;
        const mark          = typeof cutInfo === 'object' ? (cutInfo.mark || '') : '';
        const cutClass      = isSplitPiece ? 'cut-segment-split' : 'cut-segment';
        const widthPct      = (cutLength / stockLength) * 100;
        segmentsHtml += `
          <div class="${cutClass}" style="width:${widthPct}%;" title="${escReportText(mark)}">
            <span>${displayLength}mm</span>
            ${mark ? `<span class="h-seg-mark">${escReportText(mark)}</span>` : ''}
          </div>`;
    });

    if (remaining > 0) {
        const wastePct = (remaining / stockLength) * 100;
        segmentsHtml += `
          <div class="waste-segment" style="width:${wastePct}%;">
            <span>${remaining}mm</span>
          </div>`;
    }

    return `
        <div class="h-diagram ${timberClass}">
          <div class="h-diagram__header"><strong>${escReportText(label)}</strong><span>${stockLength}mm stock</span></div>
          <div class="h-stick">${segmentsHtml}</div>
        </div>`;
}
