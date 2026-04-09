# Teal Innovation — PPT Template Generation Prompt

Use this prompt with any agent (ChipAgent, Claude, etc.) together with
`build_ppt.py` to generate a new professional PowerPoint presentation
using the **Teal Innovation** theme.

---

## HOW TO USE

1. Copy the section **"AGENT PROMPT"** below and paste it into your agent.
2. Attach or reference `build_ppt.py` from this folder.
3. Tell the agent the **new topic / slide content** you want.
4. The agent will adapt the template to your content and run `build_ppt.py`
   (or generate a new script) to produce the `.pptx` file.

---

## AGENT PROMPT (copy everything below this line)

---

I want you to create a professional PowerPoint presentation using the
**Teal Innovation** design template described below.

The script must use **python-pptx** (not pptxgenjs) and follow the exact
colour palette, typography, layout rules, and component library listed here.
Use `build_ppt.py` as the reference implementation — reuse its helper
functions (`add_rect`, `add_text`, `add_rich_text`, `add_multi_para_text`,
`add_table`) and extend them as needed for new slide layouts.

---

## 1. Slide Canvas

| Property | Value |
|----------|-------|
| Width | 10.0 inches |
| Height | 5.625 inches (16:9) |
| Background (light slides) | `#F0F9FA` (LIGHTBG) |
| Background (dark slides) | `#0A3D47` (DARK) |

---

## 2. Colour Palette

| Name | Hex | Usage |
|------|-----|-------|
| `DARK` | `#0A3D47` | Title/section slide backgrounds, header bars |
| `TEAL` | `#028090` | Primary accent — divider bars, table headers, icons |
| `SEAFOAM` | `#00A896` | Secondary accent — card borders, sub-headings |
| `MINT` | `#02C39A` | Highlight — bullet dots, stat callouts, tags |
| `WHITE` | `#FFFFFF` | Text on dark backgrounds, card fill |
| `LIGHTBG` | `#F0F9FA` | Slide background (light slides) |
| `DARKTEXT` | `#1A2A3A` | Body text on light slides |
| `MUTED` | `#5A7A85` | Captions, sub-labels, secondary text |
| `ACCENT` | `#FF6B35` | Warning / highlight callouts (use sparingly) |
| `CODEBG` | `#0D1117` | Code block background |
| `CODEFG` | `#E6EDF3` | Code block default text |
| `CODEBLUE` | `#79C0FF` | Code keywords / syntax highlight |
| `CODELTBL` | `#A5D6FF` | Code variable names |
| `CODEGRAY` | `#8B949E` | Code comments |
| `RED` | `#C0392B` | Error / stop indicator |
| `GREEN` | `#27AE60` | Success / pass indicator |
| `ORANGE` | `#E67E22` | Warning / in-progress indicator |
| `PURPLE` | `#8E44AD` | Optional accent for diversity |

Card / table backgrounds (light tints of the above):
`REDBG #FFF5F5`, `GREENBG #F0FFF4`, `ORANGEBG #FFFAF0`,
`PURPLEBG #FAF0FF`, `TEALBG #F0FAFA`, `SEAFOAMBG #F0FEFA`

---

## 3. Typography

| Element | Font | Size | Weight | Colour |
|---------|------|------|--------|--------|
| Slide title (dark bg) | Calibri | 32–36 pt | Bold | WHITE |
| Slide title (light bg) | Calibri | 28–32 pt | Bold | DARK |
| Section sub-title | Calibri | 16–18 pt | Normal | SEAFOAM or MUTED |
| Card / section heading | Calibri | 13–15 pt | Bold | DARK or WHITE |
| Body text | Calibri | 11–12 pt | Normal | DARKTEXT |
| Bullet / list item | Calibri | 11 pt | Normal | DARKTEXT |
| Caption / label | Calibri | 9–10 pt | Normal | MUTED |
| Code | Consolas | 9–10 pt | Normal | CODEFG on CODEBG |
| Stat / big number | Calibri | 28–36 pt | Bold | TEAL or MINT |

---

## 4. Slide Layout Templates

### Layout A — Dark Title Slide (use for first and last slides)

```
┌─────────────────────────────────────────────────────┐
│  DARK background (#0A3D47) fills entire slide        │
│                                                      │
│  Left accent bar: 0.08" wide strip in TEAL           │
│  (x=0, y=0, w=0.08, h=5.625)                        │
│                                                      │
│  Title text:  x=0.5  y=1.8  w=9.0  size=36 bold     │
│               colour=WHITE                           │
│  Sub-title:   x=0.5  y=2.7  w=8.0  size=16          │
│               colour=SEAFOAM                         │
│  Footer line: thin TEAL rect at y=5.2                │
│  Footer text: version / date / author  size=9        │
│               colour=MUTED                           │
└─────────────────────────────────────────────────────┘
```

### Layout B — Section Divider (dark bg, centred)

```
┌─────────────────────────────────────────────────────┐
│  DARK background                                     │
│  Top accent bar: TEAL, h=0.06, full width            │
│  Section number: SEAFOAM, size=11, y=1.6             │
│  Section title:  WHITE, size=34 bold, y=2.0          │
│  Thin MINT line below title, w=2.0                   │
│  Sub-text:       MUTED, size=13, y=2.85              │
└─────────────────────────────────────────────────────┘
```

### Layout C — Light Content Slide (standard body)

```
┌─────────────────────────────────────────────────────┐
│  LIGHTBG background                                  │
│  Header bar: DARK, h=0.72, full width                │
│    Title text in header: WHITE 26pt bold  x=0.35     │
│    Right-side tag box:   TEAL bg, WHITE text 9pt     │
│  Left accent strip: TEAL, w=0.06, from y=0.72        │
│                                                      │
│  Content area below header (y > 0.72)                │
│  Use cards, bullet lists, tables, code blocks        │
└─────────────────────────────────────────────────────┘
```

### Layout D — Two-Column Content

Same header as Layout C, then content area split:
- Left column: `x=0.2  w=4.6`
- Right column: `x=5.2  w=4.6`

### Layout E — Metric / Stats Slide

```
Header (DARK) + left accent (TEAL) as per Layout C

Row of 3–4 stat cards, evenly spaced:
  Each card: white rect with TEAL left border (w=0.04)
  Big number:  TEAL 32pt bold
  Label below: MUTED 10pt
  Sub-label:   DARKTEXT 9pt
```

### Layout F — Table Slide

```
Header as Layout C

Table:
  Header row:  DARK bg, WHITE text, 11pt bold
  Even rows:   WHITE bg
  Odd rows:    STRIPALT (#F5FEFF) bg
  Cell text:   DARKTEXT 10pt
  Column header text: WHITE 10pt bold
  Outer border: CARDBRD (#E0E0E0)
```

### Layout G — Code Block Slide

```
Header as Layout C

Code block rect:  CODEBG fill, rounded feel via tight margins
  Monospace text: Consolas 9pt
  Keywords:       CODEBLUE
  Variables:      CODELTBL
  Comments:       CODEGRAY  (italic)
  Default text:   CODEFG
```

---

## 5. Reusable Components

### Card (rounded-feel white box with coloured left border)

```python
add_rect(slide, x, y, w, h, CARDWHT, CARDBRD, line_width_pt=0.5)
add_rect(slide, x, y, 0.04, h, TEAL)   # left accent
add_text(slide, title, x+0.12, y+0.08, w-0.2, 0.25, size=12, bold=True, color=DARK)
add_text(slide, body,  x+0.12, y+0.35, w-0.2, h-0.45, size=10, color=DARKTEXT)
```

### Bullet List (coloured dot + text)

```python
# For each bullet:
add_rect(slide, x, y+0.07, 0.07, 0.07, MINT)   # dot
add_text(slide, text, x+0.14, y, w-0.14, 0.3, size=11, color=DARKTEXT)
```

### Tag / Badge

```python
add_rect(slide, x, y, w, 0.22, TEAL)
add_text(slide, label, x, y, w, 0.22, size=9, bold=True, color=WHITE,
         align=PP_ALIGN.CENTER)
```

### Section Header (within a light slide)

```python
add_rect(slide, x, y, w, 0.04, SEAFOAM)        # thin top line
add_text(slide, heading, x, y+0.06, w, 0.28,
         size=13, bold=True, color=DARK)
```

---

## 5b. Extended Layout Library (Layouts H–AJ)

> Use these in addition to Layouts A–G. Each layout references the same
> colour palette and helper functions from §2–5.

---

### Layout H — Picture Left / Content Right (50/50 Split)

```
┌────────────────────┬────────────────────┐
│                    │  DARK header bar   │
│   Full-bleed       │  Title  WHITE 26pt │
│   picture          ├────────────────────┤
│   (left half)      │  Bullets / text    │
│   x=0 w=4.8        │  x=5.0 w=4.8      │
│   y=0 h=5.625      │                    │
└────────────────────┴────────────────────┘
```
- Left half: `add_picture(slide, img_path, 0, 0, 4.8, 5.625)`
- Thin TEAL vertical divider at x=4.8, full height
- Right half: LIGHTBG background, DARK header at top-right, bullets below

---

### Layout I — Picture Right / Content Left

Mirror of Layout H — image on right (x=5.2), content on left (x=0.2 w=4.8).
Use SEAFOAM vertical divider at x=5.0.

---

### Layout J — Top Picture Banner + Content Below

```
┌─────────────────────────────────────────┐
│   Picture banner  h=2.2  full width      │
│   DARK gradient overlay bottom 0.6"      │
│   Title text on overlay WHITE 28pt bold  │
├─────────────────────────────────────────┤
│  Content area (LIGHTBG)  y=2.2 h=3.4    │
│  3-column cards OR bullet list          │
└─────────────────────────────────────────┘
```
- Picture: `add_picture(slide, img, 0, 0, 10.0, 2.2)`
- Dark gradient overlay rect: `add_rect(slide, 0, 1.6, 10.0, 0.6, DARK)` opacity ~70%
- Title on overlay: WHITE 28pt bold, x=0.4, y=1.65

---

### Layout K — Bottom Picture Strip + Content Above

```
┌─────────────────────────────────────────┐
│  DARK header bar (as Layout C)          │
│  Content area  y=0.72 h=3.3 LIGHTBG    │
│  Bullets / cards / table                │
├─────────────────────────────────────────┤
│  Picture strip  h=1.6  full width y=4.0 │
│  TEAL overlay rect opacity 20% on img   │
└─────────────────────────────────────────┘
```

---

### Layout L — 2×2 Picture Grid with Captions

```
┌──────────────────────────────────────────┐
│  DARK header bar — Title WHITE 26pt      │
├───────────┬──────────┬───────────┬───────┤
│  Img 1    │  Img 2   │  Img 3    │ Img 4 │
│  w=2.3    │  w=2.3   │  w=2.3    │ w=2.3 │
│  h=2.3    │  h=2.3   │  h=2.3    │ h=2.3 │
├───────────┼──────────┼───────────┼───────┤
│ Caption 1 │Caption 2 │ Caption 3 │Cap 4  │
│ MUTED 9pt │          │           │       │
└───────────┴──────────┴───────────┴───────┘
```
- 4 images in a row, y=0.72, equal spacing, 0.1" gap between each
- Caption text below each image: MUTED 9pt centred

---

### Layout M — Polaroid Picture Cards (3 up)

```
┌───────────────────────────────────────────┐
│  LIGHTBG background (no header bar)       │
│  Large title top-left  DARK 30pt          │
│                                           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│  │ picture │  │ picture │  │ picture │  │
│  │         │  │         │  │         │  │
│  │ WHITE   │  │ WHITE   │  │ WHITE   │  │
│  │ border  │  │ border  │  │ border  │  │
│  │ Caption │  │ Caption │  │ Caption │  │
│  └─────────┘  └─────────┘  └─────────┘  │
└───────────────────────────────────────────┘
```
- Each card: WHITE bg rect with CARDBRD border, shadow effect via offset dark rect
- Image inside card with 0.12" padding on all sides
- Caption text: DARKTEXT 11pt centred, below image within card

---

### Layout N — Hero Image with Text Overlay + CTA Badge

```
┌─────────────────────────────────────────┐
│  Full-bleed background image            │
│  DARK overlay rect: full slide, 55% opacity│
│                                         │
│        BIG TITLE  WHITE 40pt bold       │
│        Sub-title  SEAFOAM 18pt          │
│                                         │
│   ┌──────────────┐                      │
│   │  CTA BADGE   │  MINT bg  DARK text  │
│   └──────────────┘  14pt bold           │
└─────────────────────────────────────────┘
```
- Use for opening impact slides or agenda summaries

---

### Layout O — Magazine Mosaic (Large img + 2 smaller)

```
┌──────────────────┬──────────┬──────────┐
│                  │ Img B    │          │
│  Large Img A     │ h=2.0    │  Text    │
│  w=4.5 h=4.0     ├──────────┤  block   │
│                  │ Img C    │  w=2.8   │
│                  │ h=2.0    │          │
└──────────────────┴──────────┴──────────┘
```
- TEAL accent strip between image column and text column (w=0.06)
- Text block: title DARK 18pt bold, body DARKTEXT 11pt

---

### Layout P — Comparison Table (Feature Matrix)

```
┌─────────────────────────────────────────┐
│  DARK header — Title WHITE 26pt         │
├────────────┬────────────┬───────────────┤
│ Feature    │ Option A   │  Option B     │  ← DARK bg WHITE text
├────────────┼────────────┼───────────────┤
│ Row 1      │  ✓ GREEN   │  ✗ RED        │
│ Row 2      │  ✓ GREEN   │  ✓ GREEN      │
│ Row 3 alt  │  ~ ORANGE  │  ✓ GREEN      │
└────────────┴────────────┴───────────────┘
```
- Checkmark cells: GREEN bg `#F0FFF4`, ✓ GREEN text
- Cross cells: RED bg `#FFF5F5`, ✗ RED text
- Partial cells: ORANGE bg `#FFFAF0`, ~ ORANGE text
- Column widths proportional; first col wider (feature names)

---

### Layout Q — Scorecard Table (RAG Status)

```
┌─────────────────────────────────────────────┐
│  DARK header — Title                        │
├──────────┬────────┬────────┬────────────────┤
│ KPI      │ Target │ Actual │ Status         │
├──────────┼────────┼────────┼────────────────┤
│ Metric A │  90%   │  94%   │ ● GREEN        │
│ Metric B │  80%   │  72%   │ ● ORANGE       │
│ Metric C │  95%   │  60%   │ ● RED          │
└──────────┴────────┴────────┴────────────────┘
  Status dot: filled circle (small rect) in RAG colour
  Status label: same colour as dot, 10pt bold
```

---

### Layout R — Table Left + Key Findings Right

```
┌─────────────────────────────────────────┐
│  DARK header — Title                    │
├──────────────────────┬──────────────────┤
│  Data Table  w=5.8   │  Key Findings    │
│  (compact, 9pt)      │  Section w=3.8   │
│                      │  SEAFOAM heading │
│                      │  3–4 bullets     │
│                      │  with MINT dots  │
└──────────────────────┴──────────────────┘
```
- Thin TEAL vertical divider at x=6.0
- Findings area has light TEALBG background

---

### Layout S — Table with Thumbnail Images in Cells

```
┌─────────────────────────────────────────────┐
│  DARK header                                │
├──────────┬──────────┬──────────┬────────────┤
│ Name     │ Preview  │ Status   │ Notes      │
├──────────┼──────────┼──────────┼────────────┤
│ Item 1   │ [img]    │ ● GREEN  │ text       │
│ Item 2   │ [img]    │ ● ORANGE │ text       │
└──────────┴──────────┴──────────┴────────────┘
```
- Thumbnail images: `add_picture` inside each cell area, centred
- Image cell column width: ~1.5"

---

### Layout T — Profile Cards Grid (Image + Name + Role)

```
┌──────────────────────────────────────────────┐
│  DARK header — Title                         │
│                                              │
│  ┌────────┐  ┌────────┐  ┌────────┐         │
│  │ [img]  │  │ [img]  │  │ [img]  │         │
│  │ circle │  │ circle │  │ circle │         │
│  │ Name   │  │ Name   │  │ Name   │         │
│  │ Role   │  │ Role   │  │ Role   │         │
│  │ MUTED  │  │ MUTED  │  │ MUTED  │         │
│  └────────┘  └────────┘  └────────┘         │
└──────────────────────────────────────────────┘
```
- Circle crop via `add_picture` with equal w/h + `crop_*` properties
- Name: DARK 12pt bold; Role: MUTED 10pt; both centred

---

### Layout U — SmartArt: Horizontal Process Flow (Chevrons)

```
┌─────────────────────────────────────────────┐
│  DARK header — Title                        │
│                                             │
│  [Step 1]▶[Step 2]▶[Step 3]▶[Step 4]▶[Step 5]
│   DARK      TEAL    SEAFOAM   MINT    ACCENT │
│   WHITE     WHITE   WHITE     WHITE   WHITE  │
│   label     label   label     label   label  │
│   below     below   below     below   below  │
└─────────────────────────────────────────────┘
```
- Each chevron: parallelogram shape (use `MSO_SHAPE_TYPE` freeform or
  overlapping rect + triangle trick)
- Step number: 9pt bold WHITE top; Step label: 11pt bold WHITE centre;
  Description: 9pt MUTED below chevron
- Gradient of colours left→right: DARK → TEAL → SEAFOAM → MINT → ACCENT

---

### Layout V — SmartArt: Cycle Diagram (4–6 nodes)

```
         ┌─────────┐
         │  Node 1  │   ← TEAL circle
        /└─────────┘\
┌──────┐              ┌──────┐
│Node 4│   CENTRE     │Node 2│
│MINT  │   label      │SEAFOM│
└──────┘              └──────┘
        \┌─────────┐/
         │  Node 3  │   ← DARK circle
         └─────────┘
```
- Each node: circle (add_shape with oval), fill alternating TEAL/SEAFOAM/MINT/DARK
- Connecting arrows: thin curved lines or straight lines between circles
- Central label: DARK 14pt bold, WHITE bg circle
- Node label: WHITE 10pt bold, centred in circle

---

### Layout W — SmartArt: Hierarchy / Org Chart

```
┌─────────────────────────────────────────────┐
│  DARK header                                │
│          ┌───────────┐                      │
│          │  Level 1  │ ← DARK bg WHITE text │
│          └─────┬─────┘                      │
│       ┌────────┴────────┐                   │
│  ┌────┴────┐       ┌────┴────┐              │
│  │ Level 2 │       │ Level 2 │ ← TEAL       │
│  └────┬────┘       └─────────┘              │
│  ┌────┴────┐                                │
│  │ Level 3 │  ← SEAFOAM                     │
│  └─────────┘                                │
└─────────────────────────────────────────────┘
```
- Connector lines: thin MUTED rects (vertical + horizontal)
- Each box: rounded rect with coloured fill, WHITE text
- Level colours: DARK → TEAL → SEAFOAM → MINT

---

### Layout X — SmartArt: Pyramid (4 Levels)

```
┌─────────────────────────────────────────────┐
│  DARK header                                │
│              ▲                              │
│             /█\     Level 1 ACCENT          │
│            /███\    Level 2 TEAL            │
│           /█████\   Level 3 SEAFOAM         │
│          /███████\  Level 4 DARK            │
│  Label   Label   Label   Label  (right side)│
└─────────────────────────────────────────────┘
```
- Build using trapezoid shapes (freeform polygon) for each layer
- Labels right of pyramid: DARKTEXT 11pt with MINT bullet dot
- Layer widths: 1.0", 2.2", 3.4", 4.6" (centred at x=5.0)

---

### Layout Y — SmartArt: Venn / Relations (3 Circles)

```
┌─────────────────────────────────────────────┐
│  DARK header                                │
│                                             │
│     ○──────────○          ← TEAL circles   │
│    /   overlap  \                           │
│   ○──────────────○        ← SEAFOAM circle  │
│                                             │
│  Circle A   Overlap   Circle B   Circle C   │
│  label      label     label      label      │
└─────────────────────────────────────────────┘
```
- 3 overlapping ovals, each 50% transparent fill
- Fills: TEAL, SEAFOAM, MINT (use alpha via XML hack or approximate with lighter tint)
- Labels outside each circle: DARKTEXT 10pt bold; overlap label: WHITE 9pt

---

### Layout Z — SmartArt: 2×2 Matrix / Quadrant

```
┌─────────────────────────────────────────────┐
│  DARK header                                │
│          HIGH VALUE                         │
│    ┌───────────┬───────────┐                │
│ H  │ Q1: Stars │Q2: Invest │                │
│ I  │ MINT bg   │ TEAL bg   │                │
│ G  │           │           │                │
│ H  ├───────────┼───────────┤                │
│    │Q3: Harvest│Q4: Exit   │                │
│ L  │SEAFOAM bg │ MUTED bg  │                │
│ O  │           │           │                │
│ W  └───────────┴───────────┘                │
│          LOW VALUE                          │
└─────────────────────────────────────────────┘
```
- 4 quadrant rects, each ~4.5"×2.0"
- Axis labels: MUTED 9pt italic, rotated 90° for Y-axis
- Quadrant title: 12pt bold matching tint colour; description: 10pt DARKTEXT

---

### Layout AA — SmartArt: Funnel (5 Stages)

```
┌─────────────────────────────────────────────┐
│  DARK header                                │
│  ██████████████  Stage 1  w=8.0  DARK       │
│   ████████████   Stage 2  w=6.8  TEAL       │
│    ██████████    Stage 3  w=5.6  SEAFOAM    │
│     ████████     Stage 4  w=4.4  MINT       │
│      ██████      Stage 5  w=3.2  ACCENT     │
│  Labels right of each bar: DARKTEXT 11pt    │
└─────────────────────────────────────────────┘
```
- Each stage is a centred rect, decreasing width by 1.2" per stage
- Stage label inside bar: WHITE 11pt bold; metric/value right of bar: MUTED 10pt

---

### Layout AB — SmartArt: Horizontal Timeline with Milestones

```
┌─────────────────────────────────────────────┐
│  DARK header                                │
│                                             │
│  ●────────●────────●────────●────────●     │
│  M1       M2       M3       M4       M5     │
│  TEAL     SEAFOAM  MINT     TEAL     ACCENT │
│  label    label    label    label    label  │
│  below    below    below    below    below  │
│                                             │
│  Horizontal spine: MUTED thin rect h=0.04  │
└─────────────────────────────────────────────┘
```
- Spine line: MUTED rect, y=2.8, full content width
- Each milestone: filled circle (oval w=h=0.22), alternating TEAL/SEAFOAM/MINT
- Date/phase above spine: MUTED 9pt; label below: DARKTEXT 10pt bold

---

### Layout AC — SmartArt: Radial Hub-and-Spoke

```
┌─────────────────────────────────────────────┐
│  DARK header                                │
│                                             │
│       Spoke1  ●────┐                        │
│     Spoke6 ●       │                        │
│               ┌────●────┐  ← Centre DARK   │
│     Spoke5 ●  │ CENTRE  │                  │
│               └────●────┘                  │
│       Spoke4  ●    │  Spoke2 ●              │
│                  Spoke3 ●                   │
└─────────────────────────────────────────────┘
```
- Central hub: large circle DARK bg, WHITE text, 0.6" radius
- 5–6 spoke nodes: smaller circles alternating TEAL/SEAFOAM/MINT
- Spoke lines: thin MUTED rects rotated to angle
- Node label: WHITE 9pt bold inside circle; description below node: DARKTEXT 9pt

---

### Layout AD — SmartArt: Staircase / Ascending Steps

```
┌──────────────────────────────────────────────┐
│  DARK header                                 │
│                          ┌──────┐            │
│                 ┌────────┤ St 4 │            │
│        ┌────────┤  St 3  │ACCENT│            │
│ ┌──────┤  St 2  │ SEAFOAM│      │            │
│ │ St 1 │  TEAL  │        │      │            │
│ │ DARK │        │        │      │            │
└─┴──────┴────────┴────────┴──────┴────────────┘
```
- Steps ascending left to right, each step taller than previous
- Step label: WHITE 11pt bold; description to the right of step: DARKTEXT 10pt
- Colours ascending: DARK → TEAL → SEAFOAM → MINT → ACCENT

---

### Layout AE — SmartArt: Pros / Cons Comparison

```
┌─────────────────────────────────────────────┐
│  DARK header                                │
│  ┌──────────────────┬──────────────────┐   │
│  │  ✓  PROS         │  ✗  CONS         │   │
│  │  GREEN bg header │  RED bg header   │   │
│  ├──────────────────┼──────────────────┤   │
│  │  ● Pro point 1   │  ● Con point 1   │   │
│  │  ● Pro point 2   │  ● Con point 2   │   │
│  │  ● Pro point 3   │  ● Con point 3   │   │
│  └──────────────────┴──────────────────┘   │
└─────────────────────────────────────────────┘
```
- Left header bar: GREEN bg (`#27AE60`), WHITE text 13pt bold
- Right header bar: RED bg (`#C0392B`), WHITE text 13pt bold
- Pro bullets: GREEN dot; Con bullets: RED dot

---

### Layout AF — SmartArt: Icon Grid (6 icons + labels)

```
┌──────────────────────────────────────────────┐
│  DARK header                                 │
│                                              │
│  ┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌────┐    │
│  │ ⚙  │  │ 📊  │  │ 🔒  │  │ ⚡  │  │ 🎯  │   │
│  │TEAL│  │SEAF│  │MINT│  │ACCN│  │DARK│    │
│  └────┘  └────┘  └────┘  └────┘  └────┘    │
│  Label1  Label2  Label3  Label4  Label5     │
│  desc    desc    desc    desc    desc       │
└──────────────────────────────────────────────┘
```
- Icon placeholder: coloured circle (oval), icon character centred in WHITE 18pt
- Label: DARK 11pt bold centred; Description: MUTED 9pt centred
- Can use emoji, Unicode symbols, or image placeholders as icons

---

### Layout AG — SmartArt: Numbered List with Icons

```
┌──────────────────────────────────────────────┐
│  DARK header                                 │
│                                              │
│  ① ┌────────────────────────────────────┐   │
│     │ Heading  DARK 13pt bold            │   │
│     │ Description  DARKTEXT 11pt         │   │
│     └────────────────────────────────────┘   │
│  ② ┌────────────────────────────────────┐   │
│  ③ ┌────────────────────────────────────┐   │
│  ④ ┌────────────────────────────────────┐   │
└──────────────────────────────────────────────┘
```
- Number badge: TEAL filled circle, WHITE 12pt bold number
- Row card: LIGHTBG rect with TEAL left border (0.04"), subtle CARDBRD outline
- Alternating subtle tints: TEALBG / SEAFOAMBG

---

### Layout AH — SmartArt: Fishbone / Cause-Effect Diagram

```
┌─────────────────────────────────────────────┐
│  DARK header                                │
│                                             │
│  Cause A ↘         ↗ Cause B               │
│            \      /                         │
│  Cause C ──►[EFFECT]◄── Cause D            │
│            /      \                         │
│  Cause E ↗         ↘ Cause F               │
└─────────────────────────────────────────────┘
```
- Central spine: DARK rect, h=0.04, full width
- Effect box: ACCENT bg, WHITE 13pt bold, centred at x=7.0
- Branch lines: diagonal thin TEAL rects (rotated)
- Cause boxes: SEAFOAMBG rect, DARKTEXT 10pt

---

### Layout AI — Agenda / Table of Contents

```
┌─────────────────────────────────────────────┐
│  DARK full background                       │
│  Title: "Agenda"  WHITE 36pt bold  y=0.4    │
│                                             │
│  ① Section Name  ── TEAL dot-line ── 03    │
│  ② Section Name  ── TEAL dot-line ── 07    │
│  ③ Section Name  ── TEAL dot-line ── 12    │
│  ④ Section Name  ── TEAL dot-line ── 18    │
│  ⑤ Section Name  ── TEAL dot-line ── 24    │
└─────────────────────────────────────────────┘
```
- Each row: number badge (TEAL circle, WHITE text) + section name (WHITE 14pt) +
  dotted leader line + page/slide number (SEAFOAM 12pt)
- Active/current section row: TEAL bg highlight rect behind the row

---

### Layout AJ — Big Quote / Callout Slide

```
┌─────────────────────────────────────────────┐
│  DARK full background                       │
│                                             │
│  ACCENT large quote mark  " "  72pt        │
│                                             │
│  "Your impactful quote or key finding       │
│   goes here in WHITE 24pt italic"           │
│                                             │
│  ── Attribution / Source  SEAFOAM 12pt     │
│                                             │
│  MINT thin bottom bar full width           │
└─────────────────────────────────────────────┘
```
- Oversized opening quote: ACCENT 72pt, x=0.3, y=0.6
- Quote text: WHITE 24pt italic, centred, x=1.0 w=8.0
- Attribution: SEAFOAM 12pt, right-aligned
- Use as section transition, key insight, or closing impact slide

---

## 5c. Layout Quick-Reference Index

| ID | Name | Best For |
|----|------|----------|
| A | Dark Title | First slide, last slide |
| B | Section Divider | Between major sections |
| C | Light Content | Standard body slide |
| D | Two-Column | Side-by-side comparisons |
| E | Metric / Stats | KPI dashboards |
| F | Table | Data tables |
| G | Code Block | Technical/code content |
| H | Picture Left | Image + bullets (image emphasis) |
| I | Picture Right | Image + bullets (text emphasis) |
| J | Top Picture Banner | Story / scene-setting opener |
| K | Bottom Picture Strip | Content + visual footer |
| L | 2×2 Picture Grid | Galleries, multi-product |
| M | Polaroid Cards | Portfolio, case studies |
| N | Hero Image Overlay | Impact opener, cover slide |
| O | Magazine Mosaic | Editorial, news-style |
| P | Comparison Table | Feature matrix, options |
| Q | Scorecard (RAG) | Status reports, health checks |
| R | Table + Findings | Data + insight side-by-side |
| S | Table with Thumbnails | Product/asset catalogues |
| T | Profile Cards Grid | Team, stakeholders |
| U | Process Flow | Step-by-step workflow |
| V | Cycle Diagram | Iterative / circular process |
| W | Hierarchy / Org Chart | Org structure, dependency tree |
| X | Pyramid | Priority levels, maturity model |
| Y | Venn / Relations | Overlap, shared concepts |
| Z | 2×2 Matrix | Strategy, prioritisation |
| AA | Funnel | Pipeline, conversion stages |
| AB | Timeline | Roadmap, milestones |
| AC | Radial Hub-and-Spoke | Central concept + dependencies |
| AD | Staircase | Growth, progression, maturity |
| AE | Pros / Cons | Trade-off analysis |
| AF | Icon Grid | Feature overview, capabilities |
| AG | Numbered List | Top-N lists, ordered steps |
| AH | Fishbone | Root-cause analysis |
| AI | Agenda / TOC | Presentation structure slide |
| AJ | Big Quote | Key finding, closing impact |

---

## 6. Spacing Rules

| Rule | Value |
|------|-------|
| Slide edge margin | ≥ 0.2 inches |
| Between cards / sections | 0.15–0.2 inches |
| Text padding inside card | 0.10–0.12 inches |
| Between bullet rows | 0.28–0.32 inches |
| Footer from bottom edge | 0.1 inches |

---

## 7. What to Give the Agent

When using this template for a new presentation, tell the agent:

1. **Presentation title and sub-title**
2. **List of slides** — for each slide provide:
   - Slide title
   - Layout type (A / B / C / D / E / F / G from §4)
   - Content (bullets, table data, code snippet, stats)
3. **Output file name** (e.g. `my_project.pptx`)
4. **Output directory**
5. Optionally: any colour overrides or extra layouts needed

The agent should then:
- Reuse `build_ppt.py` helper functions directly
- Follow all palette, typography, and spacing rules above
- Run `python build_ppt.py` (or equivalent) to produce the `.pptx`
- Open the file for review when done

---

*File: `ppt_creator/PPT_TEMPLATE_PROMPT.md`*
*Theme: Teal Innovation*
*Repo: DV-Skills-1*
*Created: 2026-04-09*
