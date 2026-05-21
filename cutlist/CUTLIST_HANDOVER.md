# Lumberbank Cutlist Optimizer — Project Handover

## What This Is
A browser-based bin-packing tool for optimising timber cutting lists. Users import cuts (member name, quantity, length) via CSV or manual entry; the app runs a First Fit Decreasing algorithm to assign cuts to stock lengths, minimising waste. Built for Lumberbank, a structural timber wholesaler.

## File Structure
- `cutlist.html` — static shell, no logic
- `cutlist.js` — all application logic (~1500 lines)
- `cutlist.css` — styling using Lumberbank brand variables

## Architecture
State is held in a single `project` object:
```js
const project = {
    jobDetails: { jobNumber, jobDescription, client, preparedBy, kerfWidth },
    tabs: [],         // one tab per member type (max 5)
    activeTabId: null,
    skippedData: []
}
```

Each tab object:
```js
{
    id, memberName, cuts, stockLengths,
    cutTolerance, overlengthSplitStock,
    results: null   // populated after optimisation
}
```

Each cut:
```js
{ length, quantity, mark, group }
```

Each bin (inside `tab.results.bins`):
```js
{ stockLength, cuts, remaining, timberType, group }
```

**Key principle:** DOM is always rendered from state, never read back from it. Job detail fields sync via `readJobDetailsFromDOM()` / `writeJobDetailsToDOM()` only at save/load. All other state changes go through the tab objects directly.

## Key Functions
| Function | Purpose |
|---|---|
| `parseCSVAndCreateTabs()` | Parses CSV, creates tabs |
| `createTab()` | Adds tab to state + DOM |
| `refreshTab(tabId)` | Re-renders tab content from state |
| `generateTabContentHTML(tab)` | Returns full tab HTML string |
| `attachTabEventListeners(tabId)` | Wires inputs to state |
| `calculateOptimization(tabId)` | Runs FFD, stores results in `tab.results` |
| `displayResults(tabId)` | Renders cutting diagrams from `tab.results` |
| `advancedOptimizeAll()` | Post-process: offcut reuse + bin consolidation |
| `updateSummary()` | Rebuilds summary table at bottom |
| `toggleSection(header)` | Collapse/expand handler (used inline via onclick) |
| `refreshGroupSummary(tabId)` | Updates group tag badges without full re-render |
| `saveProject()` / `loadProject()` | JSON serialise/deserialise full project state |

## CSV Format
```
Member Name, Quantity, Length, Mark, Group
LIB240.88s, 5, 2400, J1, Unit 1
LIB240.88s, 3, 1800, , Unit 2
240x45 LVL11, 4, 3600
```
- Columns 1–3 required; Mark and Group are optional
- Group causes cuts to optimise independently — cuts in different groups never share a stick
- Ungrouped cuts optimise together as a pool

## Features Implemented
1. **Grouping** — 5th CSV column assigns cuts to named groups. FFD runs per group independently. Results display in collapsible labelled sections per group.
2. **Collapsible sections** — Required Cuts panel, Optimization Results panel, and each group within results all have chevron collapse toggles via `toggleSection()`.
3. **Summary table** — Shows Group, Product, Length, Qty. Sorted group → product → length. Group column hidden when no groups present. Export to CSV matches structure.
4. **Save/Load** — Full project state serialised to JSON including results.
5. **Advanced optimisation** — Offcut reuse (upgrade bins to fit cuts from smaller bins) and bin consolidation (merge pairs/groups of sticks into fewer larger ones).
6. **Overlength cuts** — Cuts longer than max stock are automatically split.
7. **Feature 2:** After initial optimisation, user can lock individual sticks (exclude from re-optimisation). Needs a `locked` flag on each bin and UI checkbox/toggle on each stick diagram.
8. **Feature 3:** Click a cut segment in the diagram to edit its parameters (length, tolerance, group) inline. Needs a click handler on `.cut-segment` divs and a modal/inline editor that writes back to state and re-runs optimisation.

## Planned Features (not yet built)
These were scoped but not implemented:

- **Feature 4 (nice to have):** Drag a cut segment from one stick and drop it onto another. HTML5 drag-and-drop on `.cut-segment` divs. Should trigger re-calculation of bin remaining space and stats.
- **Feature 5 (nice to have):** Add or remove a cut directly in the results output window and have it re-optimise live.

## Notes
- Max 5 member types (tabs) — enforced at parse time; excess members shown in a skippable table with clipboard copy
- Stock lengths are per-tab and auto-populated based on member name (LVL8 → 6000 only; LIB → 6000/4800/4200/3600/3000; framing → 7200/6000/5400/4800/3600)
- Kerf width is global (job-level), cut tolerance is per-tab
- `timberType` is extracted from member name for colour-coding cut diagrams (LIB, LVL8, LVL11, LVL13, GL, OTHER)
- CSS uses custom properties defined in `:root` — brand colours are `--primary-brown` and `--dark-brown`
- Print/PDF is handled via `window.print()` with CSS print styles — all calculated tabs are made visible before printing
