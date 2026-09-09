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

// ─── Per-pattern cut legend ──────────────────────────────────────
// A narrow cut (e.g. a 25mm offcut) has no room to print "25mm · Gable" on
// its own segment — the text just overlaps into an unreadable mess (the
// problem that prompted this legend, matching Genia's approach). Instead
// every segment gets a single bold letter, always readable at any width,
// and the letter's real length/mark is spelled out once in a small table
// above that pattern's diagram. Scoped per pattern (not shared across
// patterns on the page) — deliberately simple: each pattern is a
// self-contained cutting instruction, so its legend only needs to cover
// what's actually on that one stick, and never needs more than a couple of
// dozen letters even on a busy pattern.

function letterFor(index) {
    let n = index + 1;
    let s = '';
    while (n > 0) {
        const rem = (n - 1) % 26;
        s = String.fromCharCode(65 + rem) + s;
        n = Math.floor((n - 1) / 26);
    }
    return s;
}

function buildCutLegend(cuts) {
    const legend = new Map(); // key (mark|length) -> { letter, mark, length, qty }
    cuts.forEach(cutInfo => {
        const mark   = typeof cutInfo === 'object' ? (cutInfo.mark || '') : '';
        const length = cutLengthOf(cutInfo);
        const key    = `${mark}|${length}`;
        if (!legend.has(key)) {
            legend.set(key, { letter: letterFor(legend.size), mark, length, qty: 0 });
        }
        legend.get(key).qty += 1;
    });
    return legend;
}

function buildCutLegendTable(legend, remaining) {
    const rows = Array.from(legend.values()).map(({ letter, mark, length, qty }) => `
      <tr>
        <td><strong>${letter}</strong></td>
        <td class="num">${length}mm</td>
        <td>${mark ? escReportText(mark) : '&mdash;'}</td>
        <td class="num">${qty}</td>
      </tr>`).join('');

    // Waste gets its own row instead of a letter — it's leftover material, not a piece
    // that was cut to a mark, so there's nothing to letter-tag on the diagram for it.
    const wasteRow = remaining > 0 ? `
      <tr class="print-cut-legend__waste">
        <td>&mdash;</td>
        <td class="num">${remaining}mm</td>
        <td>Waste</td>
        <td class="num">1</td>
      </tr>` : '';

    return `<table class="print-table print-cut-legend">
        <thead>
          <tr>
            <th>ID</th>
            <th class="num">Length</th>
            <th>Mark</th>
            <th class="num">Qty</th>
          </tr>
        </thead>
        <tbody>${rows}${wasteRow}</tbody>
      </table>`;
}

// ─── Horizontal cutting diagram ─────────────────────────────────
// A dedicated report-only renderer, deliberately separate from
// generateCuttingDiagram() in cutlist.js — the interactive Step 4 editor
// keeps its vertical sticks (needed for drag/drop and stick-length editing)
// and its full mm/mark labels on every segment; this only ever runs on a
// (print or on-screen) report page, where the cut legend above replaces
// that. Widths are simple percentages of stock length; a report doesn't
// need the pixel-exact kerf-gap math the live editor does.

function generateHorizontalDiagram(bin, label, qtyOff) {
    const { stockLength, cuts, remaining, timberType } = bin;
    const timberClass = timberType ? `timber-${timberType.toLowerCase()}` : 'timber-other';
    const legend = buildCutLegend(cuts);

    let segmentsHtml = '';
    let cutPctTotal = 0;
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
        cutPctTotal += widthPct;
        const letter        = legend.get(`${mark}|${cutLengthOf(cutInfo)}`).letter;
        const titleText      = mark ? `${letter}: ${displayLength}mm [${mark}]` : `${letter}: ${displayLength}mm`;
        segmentsHtml += `
          <div class="${cutClass}" style="width:${widthPct}%;" title="${escReportText(titleText)}">
            <span class="h-seg-letter">${letter}</span>
          </div>`;
    });

    if (remaining > 0) {
        // Sized as "whatever's left of the 100%", not remaining/stockLength directly — the
        // bin's own `remaining` figure only tracks material never claimed by a cut, not the
        // saw-kerf lost *between* cuts (bin.remaining in cutlist.js's FFD placement doesn't
        // charge a kerf for the first cut on a bin, so kerfWidth * (cuts.length - 1) of real
        // stock is spoken for but not attributed to any single segment). Sizing off remaining
        // alone leaves that sliver as unshaded blank space after the waste block; folding it
        // into the waste segment's width keeps the diagram's segments summing to exactly 100%
        // without changing the (correct, unchanged) mm figure printed on the label.
        const wastePct = Math.max(0, 100 - cutPctTotal);
        // No visible label — the legend table above already has a Waste row with the real
        // figure, which fits in every case, unlike text squeezed into a segment that can be
        // just a few pixels wide. Tooltip still carries it for anyone hovering the diagram.
        segmentsHtml += `
          <div class="waste-segment" style="width:${wastePct}%;" title="Leftover: ${remaining}mm"></div>`;
    }

    const stockM = (stockLength / 1000).toFixed(1);
    const meta   = `${stockM}m stock, ${qtyOff} off`;

    return `
        <div class="h-diagram ${timberClass}">
          <div class="h-diagram__header"><strong>${escReportText(label)}</strong> &mdash; ${escReportText(meta)}</div>
          ${buildCutLegendTable(legend, remaining)}
          <div class="h-stick">${segmentsHtml}</div>
        </div>`;
}
