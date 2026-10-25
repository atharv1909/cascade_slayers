# The 72-Hour Warning: UI upgrade specification

Status: plan, pre-implementation
Scope: `index.html` (landing + command view) rebuilt as a typed, tested, map-grounded, scroll-choreographed 3D dashboard
Audience: you, teammates, and any coding agent that implements this

This file is the single source of truth for the upgrade. Read sections 0–2 before anything else. Sections 3–9 are the design spec. Sections 10–16 are engineering, QA and delivery. Section 14 is the dos and don'ts.

---

## Table of contents

0. How to use this document
1. Design thesis
2. Honest status, prerequisites and things to verify
3. Design tokens
4. Layout and information architecture
5. Component specifications
6. Screens and scroll choreography
7. Motion system
8. The 3D system
9. The map system
10. State, data and perfect synchronisation
11. Real-data pipeline
12. Accessibility
13. Performance budgets
14. Dos and don'ts
15. Repository structure and tooling
16. Roadmap, cut lines, QA and demo-day runbook
17. Risks
18. Appendix: copy deck, keyboard map, references

---

## 0. How to use this document

- Every number in here (px, ms, hex) is a default to implement, not a suggestion. Change a value only by editing it here first.
- Items marked **[VERIFY]** are things I could not confirm. They are collected in section 2.4. Do not build on them until checked.
- Items marked **[MUST]**, **[SHOULD]**, **[COULD]** define cut lines (section 16.2).
- "Landing" means the scroll-driven story page. "Command view" means the operational dashboard. They are two products with one design language. Never mix their interaction models (section 1.4).

---

## 1. Design thesis

### 1.1 Subject, audience, job

- **Subject:** a city's infrastructure failing in sequence: drains, roads, substations, ambulances, hospitals. The setting is the Mithi river corridor in Mumbai during a monsoon, and one held-out city.
- **Audience:** (a) judges and viewers who decide in 30 seconds whether this is serious; (b) a duty officer at an emergency operations centre who must decide what to do in the next hour.
- **Primary job of the command view:** answer four questions in under five seconds, without clicking.
  1. How bad is it, and how sure are we?
  2. When does it become critical?
  3. What fails next, and why do we believe that?
  4. What can we do, and by when?

Everything on screen either answers one of these four, or is hidden until asked for.

### 1.2 The one memorable thing: the propagation front

Spend boldness in one place. The signature is a **luminous front that sweeps across the real city as time advances**. It is the boundary between "already failed" and "not yet", with a soft band whose width is the forecast uncertainty (q10–q90). Behind it, a fading wake shows what has already failed. Ahead of it, the city is calm.

- It exists on the landing page (Three.js) and on the map (deck.gl) from the **same onset-time field**, so the story page and the product are visibly the same thing.
- It is driven by exactly one scalar, the time cursor `t`. Scrubbing, scrolling, playing and the heatmap all move the same front.
- It is the only continuously animated ambient element in the command view. Nothing else pulses (exception: act-by deadline under 2 h, section 5.9).

Everything around the front stays quiet and disciplined.

### 1.3 Visual direction (and why not the current one)

The current build uses a cream background, a serif display face, a terracotta accent, identical rounded cards, tracked-out all-caps labels, `A · B · C` meta strings, and `→` on every button. That combination is the most common default look for generated interfaces. It also reads as editorial and calm, which fights the product's job.

New direction: **monsoon slate**. A cool, dim, instrument-like surface where colour is rare and therefore meaningful. Dark is the default theme because the map and the front need contrast and because operations rooms are dim. A light theme ("fog") exists for projectors and print.

Principles:

1. **Colour is information.** Only risk state, confidence and the time cursor are coloured. Chrome is slate.
2. **One meaning per encoding.** Hatching means low confidence and nothing else. Pulsing means act-by urgency and nothing else. Dashes mean a failed or closed link and nothing else.
3. **Hierarchy through size and weight, not boxes.** Use whitespace and type before borders, borders before fills, fills before shadows.
4. **The map is the page.** Panels float over it or dock beside it. They never compete with it.
5. **Honesty is a feature.** Provenance and uncertainty are always reachable and never decorative (section 5.6).
6. **Motion explains.** Motion answers a person's action or shows a causal sequence. Non-user-triggered motion is rationed (section 7.1).

### 1.4 Two layers, strictly separated

| | Landing (presentation) | Command view (operational) |
|---|---|---|
| Purpose | First impression, explain the idea | Make decisions |
| Scroll | Drives the story (scroll-jacking allowed, pinned scenes) | Never drives the main view |
| Camera | Authored spline | User-controlled, eased `flyTo` on selection |
| Map | Own Three.js scene, no Google tiles | Google vector map + deck.gl |
| Motion budget | High | Low, functional |
| Cost | No API usage | API usage (quota-guarded) |

The only crossing point is the handoff transition (section 6.1, scene 6). Scroll-based animation in the command view exists in exactly one place: **Briefing mode** (section 6.3), which is opt-in.

---

## 2. Honest status, prerequisites and things to verify

### 2.1 What is not real in the current build

| Issue | Consequence | Fix |
|---|---|---|
| Roads are 3-point straight lines between invented nodes; drains are invented polylines; buildings are procedurally clipped to hexes | On a real map nothing lines up with real streets. Instant credibility loss | Rebuild assets from OSM (section 11) |
| Cascade chains are hard-coded in the render function while `MOCK.cascade` exists | Two sources of truth | Single timeline contract (section 10) |
| Horizon chips affect only the right panel | The most important forecast control does not change the map | Horizon drives zone colouring everywhere |
| Counters, "61.4% → 88.6%", Why-tab drivers, hazard widgets are static strings | Numbers ignore time, fault and plan | All numbers are selectors |
| Right panel is rewritten with `innerHTML` on every playback tick | Scroll position and slider focus are destroyed | Component rendering with keyed updates |
| Full canvas redraw every frame, including all buildings | Wasted GPU, heat, jank | On-demand rendering; GPU layers |
| "Cytoscape" graph is a hand-drawn canvas | Misleading label, no real layout, no hit-testing | Real Cytoscape.js or elkjs |
| Font stack names Fraunces/Inter/JetBrains Mono but nothing loads them | Users see Georgia and system fonts | Self-hosted variable fonts (section 3.3) |
| Zone risk is a heuristic of max severity, trigger flag and time | Fine for a mock, but it must be labelled | Keep `SIMULATED` provenance until fixtures come from a real pipeline |

### 2.2 Prerequisites

- Google Cloud project with billing enabled. Free monthly caps exist, but a billing account is required.
- APIs to enable: Maps JavaScript API (vector maps), Map Tiles API (only if the immersive photorealistic mode is kept).
- A **Map ID** with a custom dark style (Cloud-based map styling).
- Node 20+, pnpm, Python 3.11+ (OSM scripts), a modern Chromium for development.

### 2.3 API key and cost rules

- "Google Earth API" no longer exists in the sense you want. Use Maps JavaScript API for the primary map and Map Tiles API for optional photorealistic 3D.
- As of Google's March 2025 pricing change, Photorealistic 3D Tiles is billed as an Enterprise SKU with a small free monthly allowance and per-1,000 pricing after that, and 2D tiles have a much larger free allowance. Pricing and caps change. **[VERIFY]** in the Cloud console pricing page before relying on any number.
- Set: a budget alert at a low threshold, a per-day quota cap on Map Tiles API, and an HTTP-referrer restriction plus API restriction on the key.
- The key lives in `.env.local` (`VITE_GOOGLE_MAPS_KEY`), is never committed, and is never pasted into chat or issues.
- The landing page must never request Google tiles.
- Google's terms prohibit caching its tiles. The offline fallback basemap must be non-Google (section 9.5).
- Keep the Google logo and attribution visible at all times. Never cover it with a panel.

### 2.4 Verify list

1. Photorealistic 3D Tiles coverage and quality over the Mithi corridor (Phase 0 gate).
2. Current free caps and SKU categories for Maps JS 3D and Map Tiles.
3. Licences of every Codrops repository and Bruno Simon folio you copy from. Treat them as technique references. Do not paste code without reading the licence.
4. GSAP licensing for your use. Recent GSAP releases are free including plugins, but read the current licence.
5. `GoogleMapsOverlay` interleaved mode behaviour with your deck.gl version and a vector Map ID.
6. Tabular-figure support in the chosen UI font (section 3.3).
7. Whether the existing H3 zone ids are valid cells (`h3-js` `isValidCell`). If not, use the polygons directly and stop calling them H3.
8. Exact npm package names for the fonts at install time.

---

## 3. Design tokens

All tokens live in `src/styles/tokens.css` as CSS custom properties. Components never contain raw hex values.

### 3.1 Colour

#### Dark theme (default), "monsoon slate"

| Token | Hex | Use |
|---|---|---|
| `--bg-0` | `#111A23` | App background, behind the map |
| `--bg-1` | `#16212C` | Docked panels |
| `--bg-2` | `#1C2935` | Raised surfaces, inputs |
| `--bg-3` | `#243443` | Hover, selected row |
| `--hairline` | `#2A3947` | 1px dividers |
| `--hairline-strong` | `#3A4D5F` | Focused dividers, input borders |
| `--text-1` | `#E6EDF3` | Primary text |
| `--text-2` | `#9AABBA` | Secondary text |
| `--text-3` | `#6C7E8E` | Tertiary, disabled (not for essential info) |
| `--tide` | `#5CC8D6` | Interactive accent, time cursor, forecast band |
| `--tide-dim` | `#2C6F79` | Forecast fill, uncertainty cone |

#### Light theme ("fog")

| Token | Hex |
|---|---|
| `--bg-0` | `#E8EDF1` |
| `--bg-1` | `#F3F6F8` |
| `--bg-2` | `#FFFFFF` |
| `--bg-3` | `#DCE4EA` |
| `--hairline` | `#CBD6DE` |
| `--text-1` | `#14202B` |
| `--text-2` | `#4A5C6B` |
| `--text-3` | `#7A8C9A` |
| `--tide` | `#0E7F8E` |

#### Risk ramp (semantic, same meaning in both themes)

| State | Dark | Light | Shape | Notes |
|---|---|---|---|---|
| NORMAL | `#6B8F95` | `#4F7279` | ● | Deliberately quiet slate-teal, not green. Green reads as "safe" and invites complacency |
| WATCH | `#E3B341` | `#B8860B` | ▲ | Amber |
| HIGH RISK | `#EE7B45` | `#C95A24` | ◆ | Orange-coral |
| CRITICAL | `#D8305A` | `#B01E45` | ■ | Crimson-magenta. Hue-separated from HIGH, not only darker |

Rules:

- Always encode risk with **colour + shape + text**. Never colour alone.
- CRITICAL additionally gets a 2px inner stroke on map polygons and a bolder label weight. Hatching is **not** used for CRITICAL (hatching is reserved for low confidence).
- Fill opacity on the map is set by state: NORMAL 0.04, WATCH 0.14, HIGH 0.24, CRITICAL 0.34.
- Verify the ramp with a deuteranopia and protanopia simulation before sign-off.

#### Data-viz neutrals

Use `--text-2` for axes, `--hairline` for grid, `--tide` for the selected series, `--tide-dim` at 0.35 alpha for uncertainty bands. No rainbow palettes anywhere.

### 3.2 Spacing, radii, elevation

- **Spacing:** 4px base. Allowed values: 2, 4, 8, 12, 16, 24, 32, 48, 64, 96.
- **Radii by role, not one value everywhere:**
  - 2px: chips, table cells, badges
  - 6px: buttons, inputs, segmented controls
  - 12px: floating map panels
  - 20px: large landing media frames
  - 0px: docked panel edges that touch the viewport
- **Elevation:** no generic grey drop shadows.
  - Docked panels: 1px hairline only.
  - Floating panels over the map: background `color-mix(in srgb, var(--bg-1) 72%, transparent)`, `backdrop-filter: blur(18px) saturate(1.2)`, 1px hairline, and a 1px top inner highlight `inset 0 1px 0 rgba(255,255,255,0.05)`.
  - Modals: same as floating plus a scrim at `rgba(8,12,17,0.6)`.

### 3.3 Typography

Two families, clearly distinct. Both self-hosted as variable fonts, `font-display: swap`, subset to Latin plus the symbols you use (● ▲ ◆ ■ ± → ≤ ≥ ρ Δ).

| Role | Family | Why |
|---|---|---|
| Display and big numbers | **Bricolage Grotesque** (variable: weight, width, optical size) | Distinctive grotesque with a width axis that can be animated on scroll |
| UI, body, data | **IBM Plex Sans** | Dense-data friendly, strong numerals, tabular figures **[VERIFY]** |
| IDs only (`DRN-06`, `RD-13`) | IBM Plex Mono | Small, rare use |

Rules:

- Numbers in tables, counters, clocks and axes: `font-variant-numeric: tabular-nums`.
- Do not use a monospace face for general labels. Use Plex Sans with tabular figures.
- Sentence case everywhere. No all-caps eyebrows. No tracked-out labels.
- Line length under 72 characters in prose. Landing prose max `62ch`.
- Never accent a single word in a headline with italic, bold or colour.

Scale (UI):

| Token | Size / line | Weight | Use |
|---|---|---|---|
| `--t-micro` | 11 / 14 | 500 | Provenance glyphs, axis ticks |
| `--t-small` | 12 / 16 | 400–500 | Secondary text, table body |
| `--t-body` | 13 / 20 | 400 | Default UI text |
| `--t-label` | 13 / 16 | 600 | Control labels |
| `--t-title` | 16 / 22 | 600 | Panel titles |
| `--t-metric` | 28 / 32 | 600 (Bricolage, wdth 90) | Status pill metric |
| `--t-hero-metric` | 44 / 48 | 600 (Bricolage) | Act tab headline numbers |

Scale (landing, fluid):

| Token | Value | Use |
|---|---|---|
| `--d-1` | `clamp(48px, 8vw, 128px)` / 0.95, Bricolage wght 600, wdth 75→100 on scroll | Scene headlines |
| `--d-2` | `clamp(28px, 3.6vw, 52px)` / 1.05 | Sub-headlines |
| `--d-body` | `clamp(16px, 1.25vw, 19px)` / 1.55, Plex Sans, `max-width: 62ch` | Landing prose |

### 3.4 Iconography

- One icon set, 1.5px stroke, 16px and 20px grids (Lucide or Phosphor, **[VERIFY]** licence).
- Layer icons are custom and consistent: WX cloud, HYD drop, TRF road, PWR bolt, EMS cross-in-circle, HOS building-with-plus, HLT pulse, AIR plume, SEI wave, COM antenna.
- Risk shapes (● ▲ ◆ ■) are drawn as SVG, not text glyphs, so they render identically across fonts.

### 3.5 Copy voice

- Plain verbs, sentence case, no filler. Name things by what a duty officer understands.
- Active voice. The button name, the toast and the log line use the same verb ("Apply plan", "Plan applied").
- Errors say what happened and what to do. They do not apologise.
- See the copy deck in section 18.1.

---

## 4. Layout and information architecture

### 4.1 Command view at 1440 × 900

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Top bar 48px: brand | scenario ▾ | city ▾ | clock + play | mode | ⋯ menu   │
├────┬───────────────────────────────────────────────────────┬───────────────┤
│    │  ┌────────────────────────────────┐                   │ Inspector     │
│ R  │  │ Status pill (city state, P24,  │                   │ 400px         │
│ a  │  │ ρ, time to critical)           │                   │               │
│ i  │  └────────────────────────────────┘                   │ [Forecast]    │
│ l  │                                                       │ [Cascade]     │
│    │            MAP (full bleed, Google vector             │ [Act]         │
│ 56 │             + deck.gl + propagation front)            │ [Trust]       │
│ px │                                                       │               │
│    │  ┌──────────────────┐                  ┌───────────┐  │ scrolling     │
│    │  │ Selection card   │                  │ Legend    │  │ content       │
│    │  │ (only on select) │                  │ chip      │  │               │
│    │  └──────────────────┘                  └───────────┘  │               │
│    │  Google logo + attribution (never covered)            │               │
├────┴───────────────────────────────────────────────────────┴───────────────┤
│ Timeline 112px: heatmap-as-track, now marker, forecast cone, stage ticks,  │
│ act-by marker, horizon segmented control                                   │
└────────────────────────────────────────────────────────────────────────────┘
```

Removed from the current build: the 5-card counter strip, the standalone cause-effect card, the always-open legend, the attribution bar, the footer strip, the 8-tab strip, 8 of 14 top-bar controls, and the separate heatmap row.

### 4.2 Dimensions

| Region | Size | Behaviour |
|---|---|---|
| Top bar | 48px | Fixed |
| Rail | 56px | Icons with tooltips; expands to 200px on hover-pin (optional) |
| Inspector | 400px default, 360–520px resizable | Collapsible to 0 with `]` |
| Timeline | 112px, collapsible to 56px | The heatmap **is** the track |
| Status pill | auto, max 560px, top-left of map, 16px inset | Always visible |
| Selection card | 320px, bottom-left of map, 16px inset | Exists only when something is selected |
| Legend chip | 32px collapsed, 280px expanded, bottom-right above Google attribution | Collapsed by default |

### 4.3 Breakpoints

| Width | Layout |
|---|---|
| ≥ 1440 | As above |
| 1100–1439 | Inspector 360px; rail icons only |
| 768–1099 | Inspector becomes a bottom sheet (snap 30% / 60% / 90%); timeline stays |
| < 768 | Command view shows a read-only summary (status pill, top zones, timeline). Full map interaction stays desktop-first. Landing is fully responsive |

### 4.4 Top bar contents (final)

Left to right: brand mark, scenario selector, city selector, play/pause with speed menu, clock (`T+16h`, ISO on hover), mode pill (DEMO or LIVE), overflow menu.

The overflow menu holds: theme, fault profile (stress test), outputs (CAP, GeoJSON), limitations, ledger check, canary check, API base, keyboard help.

### 4.5 Rail contents

Top group: six hazard icons plus compound. Middle: one layer button that opens a popover (10 layers plus risk, with the current one checked). Bottom group: explode view, plan on/off, quarantine on/off, camera presets (overview, corridor, asset).

### 4.6 Inspector tabs (4, not 8)

| Tab | Contains | Replaces |
|---|---|---|
| Forecast | Selected zone: state, confidence, time to critical, probability by horizon, event types, top zones list. Hazard-specific widget below | Risk, Hazard |
| Cascade | Top-3 chains as a timeline, branch points, feedback loops, drivers ("why"), dependency graph with evidence card | Cascade, Why, Graph |
| Act | Plan sliders, act-by, ΔP, Δρ, retained emergency access, side effects, impact counters, CAP outputs | Lab, counters |
| Trust | Data sources and reliability, fault profile, quarantined reports, ledger, canary, calibration, ablation, limitations | Data, Score |

Each tab uses progressive disclosure: the top 3 facts are always visible, the rest sit in collapsible sections (`<details>` semantics, animated height).

---

## 5. Component specifications

Each component lists purpose, anatomy, states, and the rule it must obey.

### 5.1 Status pill

- **Purpose:** question 1 and 2 of section 1.1 at a glance.
- **Anatomy (left to right):** city risk badge (shape + word), probability of cascade within 24 h as a large number (`--t-metric`), ρ with a small up/down indicator versus 1.0, time to critical as `in about 11 h` with the range `(6 to 17 h)` in secondary text, confidence badge.
- **Rule:** if `P(critical within 72 h) < 0.9` show `beyond 72 h, P = 0.68` instead of a median. Never invent an ETA.
- **States:** default; stale (data older than threshold, text turns `--text-2` and a "stale" tag appears); low confidence (hatched underline, wider range); degraded by fault profile.
- **Motion:** numbers tick over 200ms when they change. A state upgrade (for example HIGH to CRITICAL) plays one 600ms ring pulse around the badge. Downgrades do not pulse.

### 5.2 Selection card

- **Purpose:** show what is selected and why, without covering the map.
- **Anatomy:** title (`DRN-06 · BKC Mithi channel`), layer and zone line, onset as `T+57 h (53.5 to 61.5)`, two short lists "Caused by" and "Leads to" with lag and weight, and a link "Show evidence" that jumps to the Cascade tab with the edge selected.
- **Rules:** appears with a 200ms fade and 8px upward settle. Disappears on Esc, on clicking empty map, or on selecting another item (which replaces content without re-animating the frame).
- **Map coupling:** the selected asset gets a halo; parents animate as tide-coloured flowing dashes toward it, children as risk-coloured dashes away from it; each link shows its lag label.

### 5.3 Timeline track (heatmap-as-scrubber)

- **Anatomy:** 10 rows (layers) × 240 columns rendered on one canvas; row height 6px, total 60px. Above it, a 20px ruler with hour ticks every 12 h and day boundaries. Right of "now", a forecast cone (tide-dim, widening with horizon) overlays the track. Cascade stage ticks sit on a thin lane above the track. The act-by marker is a small flag on the same lane. Below: horizon segmented control and play controls.
- **Interaction:** click or drag anywhere to seek. Arrow keys step ±1 h, Shift+arrow ±6 h. Hover shows a tooltip with `T+h`, the strongest layer at that time and its state.
- **Rule:** the track, the map front and the clock are one source of truth: `store.t`. Dragging updates `t` at pointer rate; heavy work is deferred to the next animation frame and uses the precomputed timeline, so it never blocks.
- **Warm-up region:** 0–48 h is shaded and labelled "history". The forecast cone starts at "now".

### 5.4 Horizon control

- Segmented control: 1, 3, 6, 12, 24, 48, 72 h. Single choice.
- **It changes the map.** Zone fill uses P at the chosen horizon. The status pill probability and the Forecast tab headline follow it. The cone on the timeline ends at that horizon.

### 5.5 Risk badge and confidence badge

- Risk badge: SVG shape + sentence-case word (`High risk`) + colour. Height 20px, radius 2px.
- Confidence badge: three levels. LOW uses a diagonal hatch background (and only LOW uses it). Text always says `Low confidence`, `Medium confidence`, `High confidence`.
- Hover or focus shows the reason in plain language: "2 rain gauges stopped reporting. Radar is attenuated in heavy rain."

### 5.6 Provenance

Requirement: every number can say where it came from (observed, forecast, modelled, simulated, assumption).

Minimalism-safe implementation:

- Default: a 9px superscript glyph after the number (`o`, `f`, `m`, `s`, `a`) in `--text-3`, with a tooltip on hover or focus.
- **Provenance lens** toggle in the overflow menu and on keyboard `V`: expands every glyph into a full labelled chip for audits and screenshots.
- Panel headers carry one summary chip when all numbers in the panel share a provenance.
- Exports (CAP, GeoJSON) always carry provenance headers regardless of the lens.

### 5.7 Probability bars

- Seven rows (1 to 72 h). The selected horizon's row is full contrast; others at 60%.
- Bar colour follows the risk ramp thresholds (0.35, 0.60, 0.85).
- Each bar shows a thin whisker for the interval where available.
- The numeric value is right-aligned with tabular figures.

### 5.8 Cascade chain view

- Vertical stage list; **numbering is allowed here because stages are a true sequence.**
- Each stage: layer icon, event text, zone, ETA as median with a q10–q90 bar on a shared 0–72 h axis. Realised stages get a solid marker and a check; future stages hollow.
- Hovering a stage highlights its zone and assets on the map (200ms), and the front scrubs to its median ETA on click.
- Chain switcher shows probabilities as `64%`, `24%`, `12%` with the chain's first and last layer icons.
- Feedback loops are drawn as small circular arrows between layer icons with the gain value; loops with gain > 1 get the HIGH colour.

### 5.9 Act tab

- Six sliders: pumps, crews, ambulances, generators, shelter seats, dispatch delay. Each shows value, unit and a tiny marginal-effect hint ("each pump: about −0.012 on P24, assumption").
- Output block: ΔP at 24 h with the sensitivity band, Δρ, retained emergency access (baseline versus plan, plus residents), act-by deadline.
- Act-by deadline text turns HIGH colour under 6 h and gains the **only** ambient pulse in the command view under 2 h (one subtle 1.6 s opacity loop, off when reduced motion is set).
- Side effects are listed as plain sentences with an `a` provenance glyph: "Emergency contraflow on LBS Marg adds about 18 min of delay for other traffic in Kurla West."
- A before/after toggle on the map ("Baseline", "Plan") with a draggable curtain (section 9.4).
- Never phrase outcomes as lives saved. Use modelled reachability (section 14).

### 5.10 Dependency graph

- Real graph (Cytoscape.js with a layered layout, or elkjs).
- Nodes are the ten layers; amplifier nodes get a ring; edge width is weight; edge dash means unsupported (p > 0.05).
- **No edge renders without an evidence card.** The card shows weight, peak lag with 90% CI, likelihood-ratio p-value, preceded-versus-shuffled counts, mechanism tag and a weight-history sparkline (a real sparkline, not text).
- A history slider (T−48 h to now) animates weights and highlights regime changes with a marker.

### 5.11 Layer popover

- Opens from the rail. Lists the 10 layers and Risk with icon, name and one-line meaning ("Hydrology: drain surcharge"). Radio selection.
- Changing the layer swaps the map overlay and the legend content with a 280ms crossfade.

### 5.12 Legend chip

- Collapsed: shows the current overlay name and a miniature ramp.
- Expanded: ramp with units, plus one line for each non-obvious encoding (hatching = low confidence, dashes = failed link, ring = reachability).
- Always sits above the Google attribution.

### 5.13 Tooltip

- Custom DOM, not deck's default. 200ms delay in, instant out. Max width 240px. Shows name, state badge, one driver sentence, and provenance glyph. Follows the pointer with 12px offset and flips at viewport edges.

### 5.14 Buttons, inputs, segmented controls

- Heights: 28px dense, 36px default, 44px on touch. Radius 6px.
- Primary: `--tide` text on `--bg-3`, with a 1px `--tide` border at 40%. Hover raises the border to 100%. No gradient fills.
- Focus ring: 2px `--tide`, offset 2px, never removed.
- Sliders: 4px track, 16px thumb, value shown in a pill above the thumb while dragging.

### 5.15 Empty, loading and error states

| State | Treatment |
|---|---|
| Loading map | Skeleton of zone outlines drawn from local data in 400ms, then the basemap fades in. Never a spinner on a blank screen |
| No selection | Forecast tab shows the top 5 zones by risk with "Select a zone on the map or pick one here" |
| Data source down | Inline notice in the affected panel: "Rain gauges in Chunabhatti stopped reporting 14 min ago. Forecasts here are less certain." Zone is hatched, not hidden |
| API key missing or invalid | Banner: "Live map unavailable. Showing offline map." The app continues in DEMO |
| Tile quota reached | Banner with the quota counter and an automatic fall back to offline map |
| Worker failure | "Forecast engine stopped. Reload to restart." with a Reload button |

### 5.16 Toasts

- Bottom-centre above the timeline, 3 s, one at a time. Same verb as the triggering action ("Plan applied", "Ledger verified").

---

## 6. Screens and scroll choreography

### 6.1 Landing: seven scenes

Global setup:

- Lenis smooth scroll, ScrollTrigger for pinning and scrubbing, one shared `requestAnimationFrame` through `gsap.ticker`.
- One persistent fixed WebGL canvas behind all content. HTML scene content sits above it.
- Scroll progress per scene is a normalised 0–1 value that feeds a **scene timeline**, a paused GSAP timeline scrubbed by ScrollTrigger (`scrub: 0.6`).

Integration snippet (the standard Lenis plus ScrollTrigger pairing):

```ts
const lenis = new Lenis({ lerp: 0.085, wheelMultiplier: 0.9, smoothWheel: true });
lenis.on('scroll', ScrollTrigger.update);
gsap.ticker.add((time) => lenis.raf(time * 1000));
gsap.ticker.lagSmoothing(0);
```

Scene table:

| # | Scene | Scroll length | Pinned | What the viewer sees | Scrubbed values |
|---|---|---|---|---|---|
| 0 | Hero | 100vh | No | One orchestrated load sequence: the corridor's buildings rise from the ground in a wave radiating from the river (1.6 s, staggered by distance), the headline reveals line by line, the front makes one slow sweep (8 s loop, then idles). After load the scene idles with ±2° camera drift | None (time-based, once) |
| 1 | The chain | 300vh | Yes | Camera travels a spline from Mahim to Kurla while `t` goes 0→28 h. Six stage markers light in order (WX, HYD, TRF, PWR, EMS, HOS), each with a one-line caption beside the canvas. The front sweeps ahead of the camera | `t`, camera progress, caption index |
| 2 | Dependencies | 220vh | Yes | Buildings dim to 15%. Five translucent planes separate vertically (explode) while dependency edges draw between them with stroke offset delays proportional to each edge's lag. Hovering an edge opens the evidence card | Plane Z offsets, edge draw progress |
| 3 | Uncertainty | 160vh | Yes | A fault slider driven by scroll steps F0 to F5. Forecast bands widen, low-confidence zones gain hatching, the headline numbers degrade gracefully and remain readable | Fault index (continuous), band width |
| 4 | Decide | 200vh | Yes | A vertical curtain splits the city: left baseline (failures spreading), right plan (contained). Scroll moves the curtain. Counters (roads open, retained emergency access) tick with it | Curtain x, counter values |
| 5 | Trust | 140vh | Yes | Hash-chained ledger blocks slide into a row; a canary line turns from pending to verified | Block offset, verified state |
| 6 | Enter | 120vh | Yes | Camera descends toward the corridor, the WebGL canvas crossfades to the real Google map at the same camera, then the command view UI assembles in 600 ms | Camera dolly, crossfade alpha |

Scene 1 detail (the centrepiece):

- Camera path: `CatmullRomCurve3` through 8 waypoints; look-at target on a second curve. Position `p` is `scrollProgress` eased by `power2.inOut`.
- Stage activation windows (fraction of scene progress): WX 0.00–0.12, HYD 0.12–0.32, TRF 0.32–0.52, PWR 0.52–0.70, EMS 0.70–0.84, HOS 0.84–1.00.
- Each activation: the relevant assets switch to the stage colour over 280ms (scrubbed), a ground ring expands from the zone centre over the window, caption crossfades (200ms out, 200ms in, no slide).
- The headline uses the width axis of the display font. Width moves 75 → 100 across the scene so the type visibly "opens" as the cascade grows. This is the only typographic animation on the page.

Scroll rules for the landing:

- No horizontal hijack. No parallax on body text. No fade-and-slide-up entrance on every section.
- Every pinned scene has a skip affordance (a small "Skip to command view" in the top-right, always visible).
- A progress indicator on the right edge shows scene position and allows jumping.
- Keyboard: Space, PageDown, arrows scroll as usual; Home/End jump.
- With `prefers-reduced-motion`: Lenis off, pins removed, scenes render as stacked static frames with simple 200ms crossfades.

### 6.2 Command view: default state

- Opens at the scenario's default overlay and camera preset, `t` at the scenario's "now", nothing selected, Forecast tab, Inspector showing the top five zones.
- First 800ms: the zone skeleton draws, the basemap fades in, then the front appears once with a single sweep from the trigger zone to its current position (600ms, one time per session load).

### 6.3 Briefing mode (the only scroll-driven part of the command view)

- Enter via a button in the status pill ("Walk me through it") or key `B`.
- The Inspector becomes a scroll column of stage cards. The map stays sticky. Scrolling the column scrubs `t` across the chain's stages and eases the camera to each stage's zone (`flyTo`, 1.2 s, `expo.out`).
- Scroll snapping: `scroll-snap-type: y proximity`.
- Any direct interaction with the map pauses scroll linkage; a "Resume briefing" chip appears.
- Exit with Esc or the close button. State returns to where the user was.
- This replaces the old "Play the cascade" banner.

### 6.4 Intervention (Act) interaction

- Moving a slider recomputes the plan timeline in the worker (budget 50ms). The map applies the result with a 280ms colour interpolation; the front shifts later; counters tick.
- Pressing "Compare" opens the curtain on the map. Dragging the curtain scrubs between baseline and plan (section 9.4).

### 6.5 Trust

- Verify buttons run the ledger check and canary. Results appear inline with timestamps and a copyable hash. Failures show the first mismatching entry.

### 6.6 Presentation mode (optional [COULD])

- Press `F` to hide the top bar and rail, enlarge the status pill and Inspector type, and lock the camera to auto-orbit between assets. Meant for a projector. Exit with Esc.

---

## 7. Motion system

### 7.1 Principles

1. **Motion answers action or explains causality.** Scrubbing the front is causality. Selecting an asset and seeing flowing dashes is causality. A card sliding up because it entered the viewport is decoration. Do not do it.
2. **Ration ambient motion.** In the command view the only ambient motion is the front (when `t` changes) and the act-by pulse under 2 h. Nothing else loops.
3. **One orchestrated moment per view.** Landing: the hero build-up. Command view: the first front sweep.
4. **Fast in, gentle out.** Entrances at 200ms ease-out; exits at 120–160ms.
5. **Everything interruptible.** Any animation must be cancellable by user input without a jump.

### 7.2 Tokens

| Token | Value | Use |
|---|---|---|
| `--dur-micro` | 120ms | Hover, press, focus |
| `--dur-ui` | 200ms | Tooltips, selection card, tickers |
| `--dur-panel` | 360ms | Inspector tab change, popovers |
| `--dur-view` | 640ms | View transitions |
| `--dur-camera` | 1200ms | Map `flyTo` |
| `--ease-out` | `cubic-bezier(0.22, 1, 0.36, 1)` | Entrances, camera |
| `--ease-in-out` | `cubic-bezier(0.65, 0, 0.35, 1)` | Transitions between states |
| `--ease-linear` | `linear` | Scrubbed values only |

GSAP equivalents: `expo.out`, `power3.out`, `power2.inOut`. Scrubbed animations use `ease: 'none'` and let Lenis do the smoothing.

### 7.3 Codrops-derived effect catalogue

These are techniques to study from Codrops and adapt. **[VERIFY]** each repository's licence before copying any code.

| Effect | Used for | Where | Notes |
|---|---|---|---|
| Scroll-scrubbed camera on a spline | Story travel | Landing scene 1 | Own implementation with Three.js `CatmullRomCurve3` |
| Pinned scene sequences with scrub | Narrative | Landing scenes 1–5 | ScrollTrigger |
| Line-by-line text reveal | Headlines | Landing only, first appearance of each headline | Mask reveal, 640ms, stagger 60ms |
| Shader transition between scenes | Landing to map handoff | Scene 6 | Noise-threshold dissolve, 600ms |
| Grid-to-fullscreen expansion | Hazard card to scenario preview | Landing hazard list | FLIP technique |
| 3D perspective tilt on hover | Hazard cards | Landing only | Max 6°, disabled on touch |
| Magnetic cursor and custom cursor | Landing CTAs | Landing only | Never in the command view |
| Elastic column scroll | Hazard list | Landing, optional [COULD] | Skip if time-short |
| Draggable curtain reveal | Baseline versus plan | Landing scene 4, Act tab | Same component |
| Number ticker | Counters | Both | Tabular numerals, 200ms |

Do not use: 3D card carousels, rotating globes, rain particles for decoration, glitch/RGB-split effects, parallax on text.

### 7.4 Performance of motion

- Animate `transform` and `opacity` only in the DOM. No animating `width`, `height`, `top`, `left`, `box-shadow`, or `filter` blur radius.
- `will-change` only during an animation, removed afterwards.
- Never run two requestAnimationFrame loops. GSAP's ticker is the single clock. Three.js and deck.gl render requests are scheduled from it.
- The WebGL canvas pauses when it is off-screen (IntersectionObserver) or when the tab is hidden.

### 7.5 Reduced motion

`@media (prefers-reduced-motion: reduce)` and an in-app toggle:

- Lenis disabled, pins removed.
- Front becomes a static contour at the current `t` (it still moves on scrub, because that is user-triggered, but without easing).
- Tickers jump to final values. Camera moves are instant cuts.
- Pulses replaced by a static outline.

---

## 8. The 3D system

### 8.1 Landing scene (Three.js, vanilla, imperative)

Use vanilla Three.js wrapped by a thin class, not a declarative wrapper. You need frame-level control of the render loop, resizes and disposal.

**Renderer**

- `WebGLRenderer({ antialias: true, powerPreference: 'high-performance' })`, `outputColorSpace = SRGBColorSpace`, `toneMapping = ACESFilmicToneMapping`.
- Device pixel ratio capped at 1.75, with adaptive degradation: if the 30-frame average frame time exceeds 20ms, drop DPR by 0.25 down to 1.0; restore slowly if it stays under 12ms.
- Context-loss handling: listen for `webglcontextlost`, show the poster frame, attempt restore.

**Geometry**

- Buildings: extruded footprints, merged per zone with `mergeGeometries` (20 draw calls, not 512). A per-vertex `zoneIndex` attribute and a per-vertex `height` attribute feed the shader.
- Roads: thick line meshes (screen-space width) with a dash shader for closed segments.
- River: a ribbon mesh along the real Mithi centreline with a flow shader (UV scroll along the path, cheap fresnel).
- Ground: a large plane with a baked dark basemap texture generated from OSM (rasterised at build time) so the scene looks like a real place without any tile requests.
- Assets: instanced meshes for substations, hospitals, shelters, drains.

**Materials and the front**

- A single custom material for buildings (extending `MeshStandardMaterial` via `onBeforeCompile`), with:
  - base colour from a height gradient (darker at ground, lighter at roofline) to fake ambient occlusion;
  - a uniform `uT` (current time), a texture `uOnset` (onset-time field, RG channels: median and spread), and per-zone risk uniforms;
  - emissive rim where `smoothstep(uT - spread, uT, onset(x,z))` crosses, so the front glows on the facades and the ground.
- The same `uOnset` texture is used by the ground plane, giving a continuous front across everything.

**Lighting**

- Hemisphere light (cool sky, dark slate ground), one low-angle directional "monsoon dusk" light, exponential fog matched to `--bg-0` for depth.
- No real-time shadow maps on the landing page. Use baked gradients. If one shadow is truly needed, one 2048 map on the hero only.

**Post-processing**

- Selective bloom only on critical assets and the front's leading edge: render those to a separate layer, threshold high, strength about 0.5, radius 0.6.
- Optional subtle film grain at 3% for texture. Off on low-power.
- No chromatic aberration, no heavy depth of field.

**Camera**

- Perspective, FOV 38°. Hero pose: yaw −18°, pitch 52°, orbit radius tuned to frame the corridor.
- Scene 1 spline described in section 6.1.

**Budgets**

- ≤ 150 draw calls, ≤ 500k triangles, ≤ 120 MB GPU memory, 60 fps on integrated graphics at 1080p.

**Fallback tiers**

1. Full scene.
2. Reduced: no bloom, no grain, DPR 1.0.
3. Static: poster frames (WebP, 8 frames) cross-faded by scroll position. Chosen when WebGL2 is unavailable, reduced motion is set, or the benchmark at load fails.

### 8.2 Command-view 3D

The command view's 3D is the Google vector map's tilt plus deck.gl layers (section 9). There is no separate Three.js scene in the command view. Keep it that way. One renderer, one camera, one source of truth.

### 8.3 Explode view

- Five horizontal planes lifted above the map: HYD (0 m), TRF (38 m), PWR (76 m), EMS and HOS (114 m), COM (152 m). Offsets are in scene units tuned to map scale.
- Dependency edges between layers are 3D arcs (deck `ArcLayer` with `getHeight`). Opacity encodes edge weight. Unsupported edges are dashed and dimmed.
- Entering explode view: planes separate over 640ms with a 40ms stagger, camera tilts up by 8°. Leaving: reverse. While active, buildings are hidden.

---

## 9. The map system

### 9.1 Basemap

- **Primary:** Google Maps JavaScript API vector map with a **custom dark Map ID**.
  - Initial view: centre `[72.8655, 19.0635]`, zoom ~14.2, tilt 60°, heading −20°.
  - Bounds restricted to the corridor with a 1.5 km margin.
  - Style: desaturate land, hide most POIs, keep hospitals, transit stations and major road labels, lower label opacity to ~70%, make water a quiet blue-slate.
- **Optional immersive mode:** Photorealistic 3D (Map3DElement or Map Tiles). Only if the Phase 0 gate passes. It is a toggle labelled "Photoreal", off by default, with a quota counter visible.

### 9.2 Overlay layers (deck.gl `GoogleMapsOverlay`, interleaved if supported **[VERIFY]**)

| Layer | deck.gl type | Data | Notes |
|---|---|---|---|
| Zones | `GeoJsonLayer` (or `H3HexagonLayer` if ids validate) | Zone polygons | Fill by state/horizon; inner stroke for CRITICAL; hatch via `FillStyleExtension` for LOW confidence |
| Water | `PathLayer` | OSM waterways | Under everything |
| Roads | `PathLayer` | Real OSM road geometry per asset | Open: slate; stressed: amber; failed: crimson dashed (`PathStyleExtension`) |
| Cascade links | `ArcLayer` or `TripsLayer` | Parent → child edges | Only for the selected asset or the active chain |
| Assets | `IconLayer` | Substations, hospitals, EMS, shelters, comms, drains | Size by importance, ring by severity |
| Reachability | `PolygonLayer` | Precomputed 12-minute EMS isochrones | Baseline vs plan |
| Front | Custom layer extending `BitmapLayer` | `uOnset` texture + `uT` | Fragment shader draws the sweeping band |
| Footprints (selected zone only) | `GeoJsonLayer` extruded | Zone buildings | Risk-tinted, only for the selected zone, to avoid doubling Google's own buildings |
| Plume / seismic | `ScatterplotLayer` / `PolygonLayer` | Scenario-specific | Only when relevant |
| Quarantined reports | `ScatterplotLayer` | Flagged clusters | Dashed ring |

Rules:

- Never draw the same thing in both Google's layer and deck.
- Pick and hover through deck's `pickingRadius`, with a 6px tolerance on roads and a 14px tolerance on icons.
- Keep layer order explicit with `layerIds` constants.
- Layers are pure functions of `(store snapshot, timeline)`. They never read DOM state.

### 9.3 Camera behaviour

- Selection triggers `flyTo` with 1.2 s `expo.out`, preserving the user's heading unless they chose a preset.
- Presets: Overview (zoom 13.8, tilt 55), Corridor (zoom 14.8, tilt 62, heading follows the river), Asset (zoom 16.2, tilt 66, centred on the selection).
- User gestures always win: any pointer drag cancels a running flight.
- Camera state is mirrored to the URL hash on `moveend`, throttled.

### 9.4 Baseline versus plan curtain

- A vertical draggable line over the map. The left side of the line uses baseline layer data, the right side uses plan data. Implemented with deck's `clipBounds`-style clipping per layer pair, or two overlay instances with CSS `clip-path` driven by the curtain position.
- The curtain is a keyboard-operable slider (`role="slider"`, arrow keys 5%, Shift 20%).

### 9.5 Offline fallback map

- MapLibre GL JS with a self-hosted Protomaps PMTiles extract of the corridor (a few MB). Styled with the same dark palette.
- The deck.gl layers work on MapLibre with `MapboxOverlay`, so layers stay identical. Only the basemap differs.
- Triggered by: key missing, key invalid, quota reached, offline, or `Shift+D`.

### 9.6 Quota guard

- Count tile-affecting loads in a local counter shown in LIVE mode.
- Hard stop at your configured budget; falls back to offline map and shows a banner. Never silently continue.

---

## 10. State, data and perfect synchronisation

### 10.1 Stack

- React 18 + TypeScript + Vite.
- Zustand for the store, with selectors and shallow equality.
- A Web Worker for the engine.
- GSAP's ticker is the clock for animation; React renders UI chrome, imperative classes own Three.js and deck.gl.

### 10.2 Store shape

```ts
interface AppState {
  scenarioId: ScenarioId;
  cityId: CityId;
  fault: 'F0' | 'F1' | 'F2' | 'F3' | 'F4' | 'F5';
  t: number;                 // 0..240 simulation hour
  horizon: 1 | 3 | 6 | 12 | 24 | 48 | 72;
  selection: { zone?: ZoneCode; asset?: AssetId; edge?: EdgeKey };
  plan: { enabled: boolean; resources: PlanResources };
  layer: LayerId | 'RISK';
  view: { mode: 'overview' | 'briefing'; inspectorTab: Tab; curtain: number };
  ui: { theme: 'dark' | 'light'; provenanceLens: boolean; reducedMotion: boolean };
  mode: { kind: 'DEMO' | 'LIVE'; sub: 'OFFLINE' | 'MOCK' | 'GOOGLE' };
}
```

No derived data lives in the store. Derived data comes from selectors reading the timeline.

### 10.3 Timeline precompute (the key to smooth scrubbing)

Whenever `scenarioId`, `fault` or `plan` changes, the worker computes a **Timeline** object once:

```ts
interface Timeline {
  key: string;                         // hash of scenario+fault+plan
  zoneState: Uint8Array;               // [t][zone]
  zoneP: Float32Array;                 // [t][horizon][zone]
  zoneConf: Uint8Array;                // [zone]
  assetSeverity: Uint8Array;           // [t][asset]
  layerSeverity: Uint8Array;           // [t][layer]  (feeds the heatmap)
  onsetField: Float32Array;            // 128×128×2: median, spread (feeds the front)
  counters: Float32Array;              // [t][counter]
  chains: Chain[];
  rho: Float32Array;                   // [t]
  pCascade24: Float32Array;            // [t]
}
```

Sizes are small (241 × 20 × 7 floats for probabilities, for example), so recompute is cheap. Budget: ≤ 50ms; slider changes are debounced to animation frames and coalesced.

With the timeline in hand, a scrub is only array lookups.

### 10.4 The synchronisation contract

Everything below must be true at all times. These are the acceptance tests.

| Input changes | Must update |
|---|---|
| `t` | Map zone fills, front position, status pill, selection card onset text, Forecast bars, cascade realised ticks, Act counters, heatmap cursor, clock, URL |
| `horizon` | Map zone fill probabilities, status pill probability, Forecast headline, timeline cone end |
| `fault` | Timeline recompute; CI widths; hatching; confidence badges; Trust tab; graph edge opacity; front band width |
| `selection` | Map halo and trail, selection card, Forecast and Cascade content, camera ease, URL |
| `plan` / sliders | Timeline recompute; map; counters; ETA shifts; ρ; act-by marker |
| `scenarioId` | Everything; default layer and camera preset; chain set; hazard widget |
| `layer` | Map overlay and legend; Forecast widget emphasis |
| `theme` | Tokens; deck colour constants; map style ID swap |

Invariants:

1. The zone state shown on the map, in the zones table, in the status pill and in the exported GeoJSON are the same value from the same array.
2. No view has its own copy of any number.
3. All animation is driven by `t` or by user input. No view animates on its own timer except the act-by pulse.
4. Replays are deterministic. No `Math.random()` anywhere. Seeded PRNG only.

### 10.5 Rendering schedule

- Store subscribers do not render immediately. They mark views dirty. A single scheduler on GSAP's ticker flushes dirty views once per frame in a fixed order: timeline lookups → deck layers → DOM counters → Inspector.
- React components subscribe through selectors with shallow equality so `t` changes only re-render the components that read `t`.
- Inspector lists are keyed. Updating a number never replaces its parent node.

### 10.6 URL as state

Hash format: `#s=flood_mithi&c=mumbai_mithi&t=64&h=24&f=F0&z=Z09&a=DRN-06&p=1&l=HYD`.

- Updates are throttled to 4/s and use `replaceState`.
- Opening such a link restores the exact view. This doubles as the demo-day safety net.

### 10.7 Backend contract

Keep the existing endpoint names so the mock and a real backend are interchangeable: `/v1/risk`, `/v1/scenarios`, `/v1/cascade`, `/v1/graph`, `/v1/adapters`, `/v1/ingest`, `/v1/ledger/verify`, `/v1/canary`, `/v1/alerts.cap`, `/v1/risk.geojson`. Validate every response with a schema (zod). A response that fails validation is shown as a data-quality notice, never as a silent zero.

### 10.8 Tests that prove synchronisation

Playwright:

- For each scenario × a set of `t` values × each fault profile × each horizon: read the zone state from the map data attribute, the table, the status pill and the GeoJSON export. Assert equality.
- Scrub from 0 to 240 and assert no frame exceeds 33ms of main-thread time.
- Plan toggle round trip returns exactly to baseline values.
- URL round trip restores state.
- Axe accessibility run on each tab.

---

## 11. Real-data pipeline

### 11.1 Why

The current geometry is schematic. A map-grounded product must put assets where they really are, with provenance on each coordinate.

### 11.2 Scripts (`/scripts`)

| Script | Output |
|---|---|
| `osm_extract.py` | Overpass queries for the corridor bbox: waterways (Mithi, Vakola Nalla, Safed Pool), highways (trunk, primary, secondary), hospitals, fire stations, shelters, substations, telecom exchanges, building footprints with height or levels |
| `snap_network.py` | Snap each of your 20 nodes (N01–N20) to the nearest real intersection; map each road asset (RD-xx) to a path through the real graph; store `osm_way_ids` and geometry |
| `build_isochrones.py` | 12-minute EMS reachability polygons for baseline (all roads open) and for plan scenarios (specified roads removed or restored), from the real graph |
| `validate_h3.ts` | Reports which zone ids are valid H3 cells |
| `gen_onset_field.ts` | Rasterises asset onset medians and spreads into the `onsetField` format for tests |
| `gen_fixtures.py` | Exports the same JSON contract the UI consumes from your Python pipeline (Hawkes, quantile models). Replaces the heuristic mock when ready |

### 11.3 Data provenance

- Every extracted feature carries `source: 'osm'`, the extraction date, and a licence note.
- Attribution: "© OpenStreetMap contributors" in the offline map and in exports.
- Hospital and facility names should be cross-checked manually. Mark any invented asset (for example a drain you modelled) as `modelled` and render it with a dashed outline.

### 11.4 Building heights

- Use OSM `height` or `building:levels` where available, otherwise a land-use-based estimate, and mark `height_approx` in the data. Show approximate heights without a claim of precision.

---

## 12. Accessibility

Target: WCAG 2.2 AA for the command view and landing.

- **Contrast:** text ≥ 4.5:1, large text and UI components ≥ 3:1. Test both themes. Text over the map always sits on a blurred, tinted panel.
- **Colour independence:** risk always has shape + word; confidence has icon + word; hatching has a legend entry.
- **Keyboard:** the whole command view is operable (map via keyboard model below, timeline via arrows, sliders via arrows, tabs via arrows).
- **Map keyboard model:** the map is a focusable region. Arrow keys move the selection to the nearest zone in that direction; Tab cycles the top five zones by risk; Enter opens the selection card; Esc clears.
- **Screen readers:** an `aria-live="polite"` region announces city state changes and zone upgrades, rate-limited to one per 5 s. The Forecast tab provides a text equivalent of the map (a sortable table of zones).
- **Focus:** always visible; focus is never trapped except inside modals, which restore focus to their trigger on close.
- **Motion:** section 7.5.
- **Touch targets:** 44px on touch, minimum 32px on desktop.
- **Language:** `lang="en"`, no text in images.
- **Forced colours and high contrast:** `prefers-contrast: more` increases hairline contrast and removes translucency.

---

## 13. Performance budgets

| Metric | Target |
|---|---|
| Landing LCP | < 2.5 s on a typical broadband laptop |
| Landing initial JS | < 200 KB gzip before Three.js lazy chunk; Three.js and scenes ≤ 450 KB gzip total |
| Command view chunk | Lazy loaded; ≤ 700 KB gzip including deck.gl |
| Fonts | ≤ 160 KB total (subset variable files) |
| Frame rate | 60 fps scrubbing and camera moves on integrated graphics at 1080p |
| Scrub input latency | < 16 ms from pointer move to updated layers |
| Timeline recompute | ≤ 50 ms |
| Memory | < 600 MB total tab |
| Draw calls (landing) | ≤ 150 |
| Idle CPU (command view, nothing moving) | < 3% (render on demand) |

Techniques:

- Render on demand in the command view. No loop when `t` is idle and nothing animates.
- Merge geometry per zone; instance repeated assets; share one onset texture.
- Dispose Three.js geometries, materials and textures on scene teardown. Check with `renderer.info`.
- Code-split landing and command view; prefetch the command view chunk on idle after scene 3.
- Compress posters and textures (WebP / KTX2 where supported).
- Never import all of lodash, moment, etc.
- Use `content-visibility: auto` for long Inspector lists.

---

## 14. Dos and don'ts

### 14.1 Design

**Do**
- Use colour only for risk, confidence and the time cursor.
- Pair every colour with a shape and a word.
- Use whitespace and type size to build hierarchy before borders or fills.
- Make the propagation front the single memorable visual.
- Keep radius, elevation and spacing tied to role.
- Write copy for a duty officer: plain verbs, sentence case.
- Keep one meaning per visual encoding (hatching, dashes, pulse).
- Show uncertainty beside every forecast number.
- Keep the Google logo and attribution visible.

**Don't**
- Don't reuse the cream-and-terracotta editorial look, or any "warm paper" palette.
- Don't use all-caps tracked eyebrows, `A · B · C` meta strings, or `→` on buttons.
- Don't number things that are not a sequence (the cascade stages are a sequence; the hazard list is not).
- Don't make every panel an identical rounded card with the same soft shadow.
- Don't use gradient washes, glassmorphism everywhere, neon glow on chrome, or rainbow charts.
- Don't use green for NORMAL.
- Don't accent one word in a headline.
- Don't hide uncertainty to make a screen look cleaner. Hide detail, not honesty.

### 14.2 Motion and scroll

**Do**
- Make every scroll animation scrub-linked and reversible.
- Give pinned scenes a skip control and a progress indicator.
- Keep UI transitions ≤ 360 ms and camera moves ≤ 1.4 s.
- Cancel animations cleanly on user input.
- Respect reduced motion with an equivalent static experience.
- Animate only transform and opacity in the DOM.

**Don't**
- Don't scroll-jack the command view.
- Don't fade-and-slide-up every section or card.
- Don't loop ambient animations in the command view (except the act-by pulse).
- Don't run multiple animation loops.
- Don't autoplay sound.
- Don't let landing animations delay access to the command view.

### 14.3 3D and map

**Do**
- Use one renderer and one camera per view.
- Merge geometry; instance repeats; share textures.
- Validate that overlays line up with real streets before polishing visuals.
- Provide a non-Google offline basemap.
- Restrict and budget the API key; show quota in LIVE mode.

**Don't**
- Don't load Google tiles on the landing page.
- Don't cache or extract Google imagery.
- Don't cover Google attribution.
- Don't render the same building in two layers.
- Don't claim centimetre flood depth. Use a dimensionless waterlogging risk index and modelled reachability.
- Don't ship synthetic geometry as if it were real. Label it `modelled`.

### 14.4 Data and honesty

**Do**
- Show provenance on every number (glyph by default, full chips under the lens).
- Show `beyond 72 h, P = x` instead of a median when P(≤72 h) < 0.9.
- Show an evidence card for every dependency edge, and flag unsupported edges.
- Label counterfactual outputs with sensitivity bands and assumptions.
- Describe earthquake and chemical scenarios as detection-locked.
- Keep the permanent "simulator-calibrated prototype" notice reachable.

**Don't**
- Don't say "lives saved". Say "modelled retained emergency access".
- Don't present simulated results as validated against real events.
- Don't hide low-confidence zones. Hatch them.
- Don't let any number exist in two places.
- Don't use `Math.random()` in anything that affects displayed values.

### 14.5 Engineering

**Do**
- Keep tokens as the only source of colours and sizes.
- Type everything; validate API responses with schemas.
- Write the sync tests before the third feature.
- Dispose of every GPU resource on teardown.
- Keep the demo path working offline.

**Don't**
- Don't use `innerHTML` for dynamic panels.
- Don't read from the DOM to get app state.
- Don't commit keys. Don't paste keys into chat.
- Don't copy third-party code without checking its licence.
- Don't optimise before measuring; do measure before shipping.

---

## 15. Repository structure and tooling

```
ui/
├─ index.html
├─ vite.config.ts
├─ package.json
├─ .env.example                   # VITE_GOOGLE_MAPS_KEY=, VITE_MAP_ID_DARK=, VITE_MAP_ID_LIGHT=
├─ public/
│  ├─ fonts/                      # subset variable fonts
│  ├─ pmtiles/corridor.pmtiles    # offline basemap
│  ├─ posters/                    # landing static fallback frames (webp)
│  └─ data/                       # extracted OSM + fixtures
├─ scripts/                       # section 11.2
├─ src/
│  ├─ main.tsx
│  ├─ app/
│  │  ├─ store.ts
│  │  ├─ selectors.ts
│  │  ├─ url.ts
│  │  ├─ keys.ts                  # keyboard map
│  │  ├─ scheduler.ts             # one frame flush on gsap.ticker
│  │  └─ theme.ts
│  ├─ engine/
│  │  ├─ worker.ts
│  │  ├─ timeline.ts
│  │  ├─ contracts.ts             # zod schemas
│  │  └─ fixtures/
│  ├─ landing/
│  │  ├─ Landing.tsx
│  │  ├─ scene/                   # Three.js: renderer, buildings, roads, river, front, post
│  │  ├─ scenes/                  # scene0..scene6 timelines
│  │  ├─ scroll.ts                # lenis + scrolltrigger setup
│  │  └─ handoff.ts               # camera and crossfade to map
│  ├─ command/
│  │  ├─ CommandView.tsx
│  │  ├─ map/
│  │  │  ├─ GoogleMap.ts
│  │  │  ├─ OfflineMap.ts
│  │  │  ├─ overlay.ts            # GoogleMapsOverlay / MapboxOverlay
│  │  │  ├─ layers/               # zones, roads, assets, links, reach, front, ...
│  │  │  └─ camera.ts
│  │  ├─ panels/
│  │  │  ├─ Inspector.tsx
│  │  │  └─ tabs/{Forecast,Cascade,Act,Trust}.tsx
│  │  └─ timeline/Track.tsx
│  ├─ components/                 # StatusPill, SelectionCard, RiskBadge, ConfBadge, Prov, Evidence, Ticker, Curtain, ...
│  ├─ styles/{tokens.css,base.css,motion.css,components.css}
│  └─ a11y/{announce.ts,focus.ts}
└─ tests/{sync.spec.ts,a11y.spec.ts,perf.spec.ts,url.spec.ts}
```

Tooling:

- pnpm, Vite, TypeScript strict, ESLint, Prettier.
- Libraries: `three`, `gsap`, `lenis`, `@deck.gl/*`, `@googlemaps/js-api-loader`, `maplibre-gl` + `pmtiles`, `cytoscape` (+ layout), `zustand`, `zod`, `h3-js`, `d3-scale` / `d3-shape` for charts.
- Testing: Playwright, axe-core, Lighthouse CI.
- Fonts: `@fontsource-variable/bricolage-grotesque`, `@fontsource/ibm-plex-sans`, `@fontsource/ibm-plex-mono` **[VERIFY]** names.

---

## 16. Roadmap, cut lines, QA and demo-day runbook

### 16.1 Phases

| Phase | Deliverable | Exit criteria |
|---|---|---|
| 0 | Key and billing configured with referrer restriction and budget alert; Mumbai photoreal coverage check; OSM extract; H3 validity report; licence review of reference repos | Written decision: photoreal yes/no. OSM data in `public/data`. Zone id validity known |
| 1 | Vite + TS + React scaffold; tokens; fonts; store; worker; timeline contract; URL state | Existing screens reproduced from one store with no hard-coded numbers |
| 2 | Google vector map + deck.gl layers using real geometry; offline MapLibre fallback | Roads, hospitals, substations visibly on real streets; Shift+D works |
| 3 | New layout: top bar, rail, status pill, Inspector with 4 tabs, selection card, legend chip | All questions in section 1.1 answerable without clicking |
| 4 | Timeline-as-heatmap, horizon control, propagation front on the map | Scrubbing moves the front, the map, the pill and the heatmap in lockstep |
| 5 | Act tab, curtain, reachability isochrones, counters as selectors | Plan toggle round-trips exactly |
| 6 | Cascade tab: chains, loops, graph with evidence cards; Trust tab | No edge without evidence; ledger and canary work |
| 7 | Sync and a11y test suite green; performance pass | Section 10.8 and section 13 satisfied |
| 8 | Landing page: Three.js scene, scenes 0–6, handoff | 60 fps at 1080p on integrated graphics; skip control works |
| 9 | Briefing mode; presentation mode [COULD]; polish; copy pass | Rehearsed 3-minute demo with no dead air |

### 16.2 Cut lines

| Priority | Items |
|---|---|
| **[MUST]** | Real geometry; Google map + deck layers; offline fallback; store + timeline sync; 4-tab Inspector; status pill; timeline-as-heatmap; horizon-driven map; selection trails; Act tab with plan toggle; evidence cards; provenance; accessibility basics; sync tests |
| **[SHOULD]** | Propagation front shader on map; landing scenes 0, 1, 2, 4, 6; Briefing mode; curtain; real graph layout; light theme |
| **[COULD]** | Photorealistic 3D toggle; landing scenes 3 and 5; presentation mode; elastic scroll; custom cursor; film grain |

If time is short, cut from the bottom of the list. Never cut the sync tests.

### 16.3 QA checklist

Visual
- [ ] Both themes pass contrast checks.
- [ ] Risk ramp distinguishable under deuteranopia and protanopia.
- [ ] No panel covers the Google attribution.
- [ ] Hatching appears only for low confidence.
- [ ] No all-caps eyebrows, middle-dot strings or trailing arrows on buttons.

Behaviour
- [ ] Scrub, play, heatmap click, keyboard step all move the same state.
- [ ] Horizon change changes the map.
- [ ] Plan on/off is exactly reversible.
- [ ] URL link restores view.
- [ ] Esc always backs out one level.

Performance
- [ ] Lighthouse performance ≥ 85 on landing.
- [ ] No long task > 50 ms during scrubbing.
- [ ] `renderer.info` stable after scene teardown (no leaks).

Resilience
- [ ] Wi-Fi off: DEMO works fully.
- [ ] Key removed: banner and offline map.
- [ ] WebGL2 disabled: static landing works.
- [ ] Worker killed: clear error with a Reload.

Honesty
- [ ] Every number reachable to its provenance.
- [ ] No "lives saved" anywhere.
- [ ] Limitations modal reachable from the overflow menu.

### 16.4 Demo-day runbook

1. Build production, serve locally, open the **permalink** for the exact starting state.
2. Pre-warm: load command view once with the real key, then switch to DEMO to verify fallback.
3. Close other heavy tabs; set the display to 1080p; set browser zoom 100%.
4. Rehearsed path (3 minutes): landing scenes 1 and 4 (60 s) → enter → select Z09 (20 s) → scrub to critical, show the front (30 s) → Cascade tab evidence (30 s) → Act, apply plan, curtain (30 s) → Trust, F3 fault (10 s).
5. Keyboard shortcuts rehearsed: `Shift+D` fallback, `B` briefing, `V` provenance lens, `P` plan toggle.
6. Have a recorded video of the same path as a last resort.

---

## 17. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Photoreal tiles poor or missing for Mumbai | Wasted effort | Phase 0 gate; vector map is the default |
| Google quota or key problem during the demo | Broken map | Offline MapLibre fallback; permalink; recorded video |
| deck.gl interleaved overlay quirks with Google vector maps | Depth or picking bugs | Test early in Phase 2; fall back to non-interleaved overlay |
| Landing 3D too heavy for judges' laptops | Jank, bad first impression | Adaptive DPR; tiered fallbacks; poster mode |
| Scope too large | Unfinished | Cut lines in 16.2; must-haves first |
| OSM geometry mismatch with your invented nodes | Rework | Snap script with manual override file |
| Licence issues from copied effects | Legal risk | Treat references as techniques; read licences |
| Heuristic mock engine looks fake to technical judges | Credibility | Keep `SIMULATED` visible; swap in real fixtures from your Python models |

---

## 18. Appendix

### 18.1 Copy deck

| Where | Copy |
|---|---|
| Status pill, high risk | `High risk. 89% chance of a cascade within 24 h. First critical failure in about 11 h (6 to 17 h).` |
| Status pill, beyond horizon | `Beyond 72 h, probability 0.68.` |
| Low confidence reason | `Two rain gauges stopped reporting. Forecasts here are less certain.` |
| Selection card | `Caused by: Kurla West pumping trunk, 2.5 h earlier. Leads to: Mithi bridge closure, 3.5 h later.` |
| Act | `Apply plan` / toast: `Plan applied` |
| Act-by | `Act by T−5.5 h, before the culvert locks.` |
| Retained access | `Modelled 12-minute ambulance reach: 61% without a plan, 89% with the plan.` |
| Side effect | `Emergency contraflow on LBS Marg adds about 18 min of delay for other traffic in Kurla West.` |
| Offline banner | `Live map unavailable. Showing the offline map.` |
| Quota banner | `Map quota reached for today. Showing the offline map.` |
| Detection-locked | `No early warning exists for earthquakes. The 72-hour clock starts when the main shock is detected.` |
| Limitations | `This is a prototype calibrated on a simulator. It is not an official warning system.` |
| Empty selection | `Select a zone on the map, or pick one from the list.` |
| Worker error | `The forecast engine stopped. Reload to restart it.` |

Landing headline set (sentence case, no trailing arrows):

- Hero: `Know 72 hours before it cascades.`
- Scene 1: `One failure sets off the next.`
- Scene 2: `Cities fail through each other.`
- Scene 3: `When data fails, the forecast says so.`
- Scene 4: `Change the outcome before it locks in.`
- Scene 5: `Every forecast is signed before it is tested.`
- Scene 6: `See your corridor.` (button: `Open the command view`)

### 18.2 Keyboard map

| Key | Action |
|---|---|
| Space | Play / pause |
| ← / → | Step time ±1 h |
| Shift + ← / → | Step time ±6 h |
| 1–4 | Inspector tabs |
| L | Open layer popover |
| P | Toggle baseline / plan |
| B | Briefing mode |
| V | Provenance lens |
| E | Explode view |
| ] | Toggle Inspector |
| / | Command palette (scenario, zone, asset search) [COULD] |
| F | Presentation mode [COULD] |
| Esc | Back out one level |
| Shift + D | Switch to DEMO offline immediately |

### 18.3 Reference points (technique sources, not code to paste)

- Codrops (`github.com/codrops`): scroll-driven 3D, WebGL transitions, grid effects, hover distortions. **[VERIFY]** licence per repo.
- Bruno Simon's portfolio repositories: interaction engineering and scene craft. **[VERIFY]** licence.
- GSAP ScrollTrigger and Lenis documentation: pinning, scrub, smooth scroll integration.
- deck.gl documentation: `GoogleMapsOverlay`, `TripsLayer`, `ArcLayer`, `PathStyleExtension`, `FillStyleExtension`.
- Google Maps Platform documentation: vector maps and Map IDs, Map Tiles API, usage and billing, policies and attribution.
- Protomaps and MapLibre documentation: offline basemaps.
- Studios for visual benchmarking (not code): Active Theory, Lusion, Resn, 14islands, Locomotive.

### 18.4 Definition of done

The upgrade is done when:

1. A stranger can state the city's risk, when it becomes critical and what to do, within five seconds of opening the command view.
2. Every number on screen can be traced to a provenance and updates when, and only when, its inputs change.
3. Overlays sit on real streets and real facilities.
4. The propagation front moves identically on the landing page and the map.
5. The demo survives Wi-Fi loss and a missing key.
6. The sync, accessibility and performance suites pass.
