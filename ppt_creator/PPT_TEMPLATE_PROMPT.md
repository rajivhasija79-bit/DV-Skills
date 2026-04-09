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
