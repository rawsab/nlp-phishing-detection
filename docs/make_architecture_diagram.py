"""Generate the system architecture diagram as an SVG.

Usage: python make_architecture_diagram.py OUTPUT.svg [--style dark|paper|paper-dark]

Three styles share one layout: ``dark`` (modern dark mode with icons), ``paper``
(a LaTeX/TikZ-like figure for academic use) and ``paper-dark`` (the same in dark mode).

The PNGs in this folder are rendered at 2x with librsvg, which needs the fonts
installed locally (Inter, JetBrains Mono and CMU Serif / CMU Typewriter Text):

    python docs/make_architecture_diagram.py /tmp/a.svg --style dark
    rsvg-convert -z 2 /tmp/a.svg -o docs/architecture.png
    python docs/make_architecture_diagram.py /tmp/b.svg --style paper-dark
    rsvg-convert -z 2 /tmp/b.svg -o docs/architecture-paper-dark.png

Labels may contain inline math between $...$, written in a small LaTeX-like
syntax: x_t, x_{12}, h_t^{(f)}, \\text{URL}. Math is set in Computer Modern with
italic variables and upright digits and operators. Text between backticks is
set in the monospace font.
"""

import argparse
from dataclasses import dataclass, field, replace
from html import escape

CM = "'CMU Serif', 'Latin Modern Roman', 'Times New Roman', serif"
CM_MATH = (
    "'CMU Serif', 'Latin Modern Math', 'STIX Two Math', 'Cambria Math', 'Times New Roman', serif"
)


@dataclass(frozen=True)
class Style:
    bg: str
    panel_fill: str
    panel_stroke: str
    block_fill: str
    block_stroke: str
    box_fill: str
    box_stroke: str
    chip_fill: str
    text: str
    text_2: str
    arrow: str
    accent: str
    # (fill, stroke) for the forward / backward / output boxes.
    accents: dict = field(default_factory=dict)
    alert: str = ""
    ok: str = ""
    sans: str = ""
    mono: str = ""
    math: str = CM_MATH
    math_scale: float = 1.0
    mono_scale: float = 1.0
    title_weight: object = "bold"
    stroke_width: float = 1.5
    arrow_width: float = 1.6
    arrow_radius: float = 8
    arrowhead: str = "M0,0 L10,5 L0,10 z"
    arrowhead_size: float = 7
    box_rx: float = 8
    block_rx: float = 10
    panel_rx: float = 12
    panel_dash: str = ""
    pill_chips: bool = True
    icons: bool = True
    academic: bool = False  # caption below instead of a title, (a)-(f) panel labels
    bold_math: bool = True  # False keeps math upright-weight inside bold titles, as LaTeX does


DARK = Style(
    # Neutral blacks and greys; colour is reserved for a few accents.
    bg="#0a0a0a",
    panel_fill="#141414",
    panel_stroke="#2a2a2a",
    block_fill="#101010",
    block_stroke="#2a2a2a",
    box_fill="#1c1c1c",
    box_stroke="#383838",
    chip_fill="#0a0a0a",
    text="#ededed",
    text_2="#a3a3a3",
    arrow="#8a8a8a",
    accent="#4c9aff",
    accents={
        "fwd": ("#1c1c1c", "#3b7dd8"),
        "bwd": ("#1c1c1c", "#d9822b"),
        "out": ("#1c1c1c", "#3fa45b"),
    },
    alert="#e5534b",
    ok="#3fa45b",
    sans="Inter, 'Helvetica Neue', Arial, sans-serif",
    mono="'JetBrains Mono', Menlo, Consolas, monospace",
    math_scale=1.14,  # Computer Modern runs small next to Inter.
    mono_scale=0.92,  # JetBrains Mono runs large next to Inter.
    title_weight=600,
)

PAPER = Style(
    # Black on white with TikZ-style tints (blue!10, orange!15, green!10).
    bg="#ffffff",
    panel_fill="#ffffff",
    panel_stroke="#000000",
    block_fill="#fafafa",
    block_stroke="#4d4d4d",
    box_fill="#ffffff",
    box_stroke="#000000",
    chip_fill="#f2f2f2",
    text="#000000",
    text_2="#262626",
    arrow="#000000",
    accent="#000000",
    accents={
        "fwd": ("#e6e6ff", "#000000"),
        "bwd": ("#ffecd9", "#000000"),
        "out": ("#e6ffe6", "#000000"),
    },
    sans=CM,
    mono="'CMU Typewriter Text', 'Latin Modern Mono', Courier, monospace",
    stroke_width=0.9,
    arrow_width=0.9,
    arrow_radius=0,
    arrowhead="M0,0 L10,5 L0,10 L3,5 z",  # LaTeX "stealth" tip
    arrowhead_size=10,
    box_rx=1.5,
    block_rx=1.5,
    panel_rx=0,
    panel_dash="5 3",
    pill_chips=False,
    icons=False,
    academic=True,
    bold_math=False,
)

PAPER_DARK = replace(
    PAPER,
    # The academic figure inverted onto near-black, with the tints darkened.
    bg="#0f0f0f",
    panel_fill="#0f0f0f",
    panel_stroke="#5e5e5e",
    block_fill="#161616",
    block_stroke="#3d3d3d",
    box_fill="#0f0f0f",
    box_stroke="#4a4a4a",
    chip_fill="#242424",
    text="#f0f0f0",
    text_2="#c4c4c4",
    arrow="#d4d4d4",
    accent="#f0f0f0",
    accents={
        "fwd": ("#1e2246", "#4a4a4a"),
        "bwd": ("#3d2a16", "#4a4a4a"),
        "out": ("#183a1d", "#4a4a4a"),
    },
)

STYLES = {"dark": DARK, "paper": PAPER, "paper-dark": PAPER_DARK}

S: Style = DARK  # set in main()

W = 1400
HEADER_H = 78  # space taken by the title in the dark style

# Approximate CMU Serif advance widths (em), used to stack a superscript over a subscript.
CHAR_EM = {"1": 0.5, "2": 0.5, "t": 0.36, "T": 0.72}

# Icons from Lucide (https://lucide.dev), ISC License. 24x24 outline glyphs.
ICONS = {
    "database": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/>'
    '<path d="M3 12A9 3 0 0 0 21 12"/>',
    "binary": '<rect x="14" y="14" width="4" height="6" rx="2"/><rect x="6" y="4" width="4" '
    'height="6" rx="2"/><path d="M6 20h4"/><path d="M14 10h4"/><path d="M6 14h2v6"/>'
    '<path d="M14 4h2v6"/>',
    "layers": '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 '
    '0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 '
    '17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
    "sigma": '<path d="M18 7V5a1 1 0 0 0-1-1H6.5a.5.5 0 0 0-.4.8l4.5 6a2 2 0 0 1 0 2.4l-4.5 '
    '6a.5.5 0 0 0 .4.8H17a1 1 0 0 0 1-1v-2"/>',
    "chart-line": '<path d="M3 3v16a2 2 0 0 0 2 2h16"/><path d="m19 9-5 5-4-4-3 3"/>',
    "server": '<rect width="20" height="8" x="2" y="2" rx="2" ry="2"/><rect width="20" height="8" '
    'x="2" y="14" rx="2" ry="2"/><line x1="6" x2="6.01" y1="6" y2="6"/>'
    '<line x1="6" x2="6.01" y1="18" y2="18"/>',
    "shield-alert": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 '
    "13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 "
    '1 1 1z"/><path d="M12 8v4"/><path d="M12 16h.01"/>',
    "shield-check": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 '
    "13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 "
    '1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    "braces": '<path d="M8 3H7a2 2 0 0 0-2 2v5a2 2 0 0 1-2 2 2 2 0 0 1 2 2v5c0 1.1.9 2 2 2h1"/>'
    '<path d="M16 21h1a2 2 0 0 0 2-2v-5c0-1.1.9-2 2-2a2 2 0 0 1-2-2V5a2 2 0 0 0-2-2h-1"/>',
}

# Pre-broken, left-aligned lines (LaTeX's raggedright caption style).
CAPTION = [
    "Figure 1: Architecture of the phishing URL detection system. (a) URLs are labelled, tokenized "
    "at the character level and padded to $T = 128$. (b) Each character is embedded as a vector",
    "in $ℝ^{128}$. (c) Three stacked bidirectional LSTM layers encode the sequence, and the final "
    "forward and backward states are concatenated into $z ∈ ℝ^{256}$. (d) A sigmoid output layer",
    "maps $z$ to the phishing probability $p$. The model is (e) trained with binary "
    "cross-entropy and "
    "early stopping, and (f) served through a REST API.",
]

out: list[str] = []


def parse_math(s: str):
    """Yield (text, level, italic) runs; level is 0, 'sub' or 'sup'."""
    i = 0
    while i < len(s):
        if s.startswith("\\text{", i):
            j = s.index("}", i)
            yield s[i + 6 : j], 0, False
            i = j + 1
        elif s[i] in "_^":
            level = "sub" if s[i] == "_" else "sup"
            if s[i + 1] == "{":
                j = s.index("}", i)
                body = s[i + 2 : j]
                i = j + 1
            else:
                body = s[i + 1]
                i += 2
            for ch in body:
                yield ch, level, ch.isalpha()
        else:
            yield s[i], 0, s[i].isalpha() and s[i] != "ℝ"
            i += 1


def rich(s: str, size: float) -> str:
    """Render plain text plus inline $...$ math as SVG tspans."""
    msize = round(size * S.math_scale, 2)
    small = round(msize * 0.7, 2)
    offsets = {0: 0.0, "sub": round(msize * 0.28, 2), "sup": round(-msize * 0.42, 2)}

    parts = []
    baseline = 0.0
    for k, chunk in enumerate(s.split("$")):
        if not chunk:
            continue
        if k % 2 == 0:  # plain text, with `code` set in the monospace font
            for j, piece in enumerate(chunk.split("`")):
                if not piece:
                    continue
                font = (
                    f' font-family="{S.mono}" font-size="{round(size * S.mono_scale, 2)}"'
                    if j % 2
                    else ""
                )
                parts.append(f'<tspan{font} dy="{-baseline}">{escape(piece)}</tspan>')
                baseline = 0.0
            continue

        prev_level, sub_width = 0, 0.0
        for run, level, italic in parse_math(chunk):
            dy = offsets[level] - baseline
            baseline = offsets[level]
            dx = ""
            width = CHAR_EM.get(run, 0.5) * small
            if level == "sub":
                sub_width = sub_width + width if prev_level == "sub" else width
            elif level == "sup" and prev_level == "sub":
                dx = f' dx="{-round(sub_width, 2)}"'
            style = ' font-style="italic"' if italic else ""
            if not S.bold_math:
                style += ' font-weight="normal"'
            fsize = small if level else msize
            parts.append(
                f'<tspan font-family="{S.math}" font-size="{fsize}"{style} dy="{dy}"{dx}>'
                f"{escape(run)}</tspan>"
            )
            prev_level = level
    if baseline:
        parts.append(f'<tspan dy="{-baseline}">​</tspan>')
    return "".join(parts)


def text(x, y, s, size=13, fill=None, weight="normal", anchor="middle"):
    fill = fill or S.text
    out.append(
        f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
        f'text-anchor="{anchor}">{rich(s, size)}</text>'
    )


def rect(x, y, w, h, fill, stroke, rx, dash=""):
    dash = f' stroke-dasharray="{dash}"' if dash else ""
    out.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{S.stroke_width}"{dash}/>'
    )


def icon(name, x, y, size=16, color=None):
    """Draw a Lucide icon with its top-left corner at (x, y)."""
    scale = size / 24
    out.append(
        f'<g transform="translate({x},{y}) scale({scale})" fill="none" '
        f'stroke="{color or S.text_2}" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</g>'
    )


def box(x, y, w, h, title=None, lines=(), accent=None, size=14, icon_name=None, icon_color=None):
    """A box with a bold title and secondary detail lines, vertically centred.

    `accent` is "fwd", "bwd" or "out". An optional icon sits at the left edge
    (dark style only), and the text shifts right to make room.
    """
    fill, stroke = S.accents[accent] if accent else (S.box_fill, S.box_stroke)
    rect(x, y, w, h, fill, stroke, S.box_rx)
    cx = x + w / 2
    if icon_name and S.icons:
        icon(icon_name, x + 16, y + h / 2 - 11, 22, icon_color)
        cx += 16
    rows = ([(title, size, S.text, S.title_weight)] if title else []) + [
        (line, size - 1.5, S.text_2, "normal") for line in lines
    ]
    gap = 7
    total = sum(r[1] for r in rows) + gap * (len(rows) - 1)
    cy = y + (h - total) / 2
    for s, sz, fill_, weight in rows:
        cy += sz
        text(cx, cy - sz * 0.15, s, sz, fill_, weight)
        cy += gap


def chip(x, y, w, h, s, size=14):
    rect(x, y, w, h, S.chip_fill, S.box_stroke, h / 2 if S.pill_chips else S.box_rx)
    text(x + w / 2, y + h / 2 + size * 0.35, s, size)


def panel(x, y, w, h, number, label, icon_name):
    rect(x, y, w, h, S.panel_fill, S.panel_stroke, S.panel_rx, S.panel_dash)
    if S.academic:
        text(
            x + 16, y + 26, f"({'abcdef'[number - 1]})  {label}", 15, weight="bold", anchor="start"
        )
        return
    icon(icon_name, x + 20, y + 15, 17, S.accent)
    text(x + 46, y + 29, f"{number}", 13, S.text_2, S.title_weight, "start")
    text(x + 62, y + 29, label.upper(), 13, S.text, S.title_weight, "start")


def arrow(*points, head=True):
    """Orthogonal connector through `points`, with bends rounded by the style's radius."""
    d = [f"M{points[0][0]},{points[0][1]}"]
    for prev, corner, nxt in zip(points, points[1:], points[2:], strict=False):
        # Clamp so the curves on short segments don't overlap.
        r = min(S.arrow_radius, _dist(prev, corner) / 2, _dist(corner, nxt) / 2)
        if r == 0:
            d.append(f"L{corner[0]},{corner[1]}")
            continue
        a = _toward(corner, prev, r)
        b = _toward(corner, nxt, r)
        d.append(f"L{a[0]},{a[1]} Q{corner[0]},{corner[1]} {b[0]},{b[1]}")
    d.append(f"L{points[-1][0]},{points[-1][1]}")
    marker = ' marker-end="url(#arrow)"' if head else ""
    out.append(
        f'<path d="{" ".join(d)}" fill="none" stroke="{S.arrow}" '
        f'stroke-width="{S.arrow_width}"{marker}/>'
    )


def _dist(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])  # segments are axis-aligned


def _toward(p, q, r):
    """The point `r` along the segment from p towards q."""
    length = _dist(p, q)
    return (
        round(p[0] + (q[0] - p[0]) * r / length, 2),
        round(p[1] + (q[1] - p[1]) * r / length, 2),
    )


def draw() -> None:
    # --- Header ---------------------------------------------------------------
    if not S.academic:
        text(W / 2, 54, "NLP Phishing Detection", 28, S.text, 700)
        text(
            W / 2,
            82,
            "Character-level bidirectional LSTM for phishing URL classification  ·  Rawsab Said",
            15,
            S.text_2,
        )

    # --- 1. Data & preprocessing ----------------------------------------------
    panel(40, 112, 1320, 196, 1, "Data & preprocessing", "database")
    box(
        65,
        156,
        250,
        60,
        "PhishTank export",
        ["29,769 phishing URLs · label 1"],
        icon_name="shield-alert",
        icon_color=S.alert,
    )
    box(
        65,
        228,
        250,
        60,
        "Benign URL whitelist",
        ["38,228 URLs · label 0"],
        icon_name="shield-check",
        icon_color=S.ok,
    )
    arrow((315, 186), (335, 186), (335, 222), head=False)
    arrow((315, 258), (335, 258), (335, 222), head=False)
    arrow((335, 222), (355, 222))
    box(
        355,
        180,
        200,
        84,
        "Deduplicate & label",
        ["67,997 unique URLs", "URL in both sources → benign"],
    )
    arrow((555, 222), (590, 222))
    box(
        590,
        180,
        240,
        84,
        "Character tokenization",
        ["lowercase · 69-character vocabulary", "id 0 reserved for padding"],
    )
    arrow((830, 222), (865, 222))
    box(
        865,
        180,
        215,
        84,
        "Pad / truncate",
        ["left-pad to $T = 128$ characters", "longer URLs keep last 128"],
    )
    arrow((1080, 222), (1115, 222))
    box(
        1115,
        180,
        220,
        84,
        "Train / val / test split",
        ["80% / 15% / 5%", "fixed seed for reproducibility"],
    )

    # --- 2. Embedding ---------------------------------------------------------
    panel(40, 328, 1320, 108, 2, "Character embedding", "binary")
    arrow((1225, 264), (1225, 368))
    chip(1115, 368, 220, 40, "token ids  $c_1, …, c_T$")
    arrow((1115, 388), (945, 388))
    box(605, 360, 340, 56, "Embedding layer", ["70 × 128 lookup table · 8,960 parameters"])
    arrow((605, 388), (440, 388))
    chip(90, 368, 350, 40, "$x_1, x_2, …, x_T$   (each $x_t ∈ ℝ^{128}$)")

    # --- 3. BiLSTM encoder ----------------------------------------------------
    panel(40, 456, 1320, 348, 3, "Bidirectional LSTM encoder", "layers")
    by = 496
    layers = [
        (
            65,
            1,
            256,
            "$x_1, …, x_T$",
            "Concatenate at every step",
            "$y_t^{(1)} = [h_t^{(f)}; h_t^{(b)}] ∈ ℝ^{512}$",
        ),
        (
            500,
            2,
            256,
            "$y_1^{(1)}, …, y_T^{(1)}$",
            "Concatenate at every step",
            "$y_t^{(2)} = [h_t^{(f)}; h_t^{(b)}] ∈ ℝ^{512}$",
        ),
        (
            935,
            3,
            128,
            "$y_1^{(2)}, …, y_T^{(2)}$",
            "Concatenate final states only",
            "$z = [h_T^{(f)}; h_1^{(b)}] ∈ ℝ^{256}$",
        ),
    ]
    for bx, n, units, inp, concat_title, concat_formula in layers:
        rect(bx, by, 400, 292, S.block_fill, S.block_stroke, S.block_rx)
        text(
            bx + 200,
            by + 26,
            f"BiLSTM layer {n}  ·  {units} units per direction",
            15,
            S.text,
            S.title_weight,
        )
        text(bx + 200, by + 46, "dropout 0.3  ·  recurrent dropout 0.3", 12.5, S.text_2)
        chip(bx + 45, by + 58, 310, 34, inp, 13.5)
        arrow((bx + 115, by + 92), (bx + 115, by + 114))
        arrow((bx + 285, by + 92), (bx + 285, by + 114))
        box(
            bx + 25,
            by + 114,
            172,
            84,
            "Forward LSTM",
            ["reads $t = 1 → T$", "$h_1^{(f)} → … → h_T^{(f)}$"],
            "fwd",
            13.5,
        )
        box(
            bx + 203,
            by + 114,
            172,
            84,
            "Backward LSTM",
            ["reads $t = T → 1$", "$h_1^{(b)} ← … ← h_T^{(b)}$"],
            "bwd",
            13.5,
        )
        arrow((bx + 115, by + 198), (bx + 115, by + 222))
        arrow((bx + 285, by + 198), (bx + 285, by + 222))
        box(bx + 25, by + 222, 350, 56, concat_title, [concat_formula], size=13.5)
        if n < 3:
            arrow(
                (bx + 375, by + 250), (bx + 417, by + 250), (bx + 417, by + 75), (bx + 480, by + 75)
            )

    # Drawn after the layer blocks so it isn't hidden behind them.
    arrow((90, 388), (52, 388), (52, by + 75), (110, by + 75))  # embedding -> layer 1

    # --- 4. Output ------------------------------------------------------------
    panel(935, 824, 425, 218, 4, "Output layer", "sigma")
    arrow((1135, by + 278), (1135, 866))
    chip(1035, 866, 200, 32, "$z ∈ ℝ^{256}$", 13.5)
    arrow((1135, 898), (1135, 914))
    box(958, 914, 380, 44, "Dense:  $σ(w^{⊤}z + b)$   ·   257 parameters", [], size=14)
    arrow((1135, 958), (1135, 974))
    box(
        958,
        974,
        380,
        50,
        "$p = P(\\text{phishing} | \\text{URL}) ∈ [0, 1]$",
        ["sigmoid output: probability the URL is phishing"],
        "out",
        14,
    )

    # --- 5. Training & evaluation ---------------------------------------------
    panel(490, 824, 425, 218, 5, "Training & evaluation", "chart-line")
    arrow((958, 999), (930, 999), (930, 884), (895, 884))
    box(510, 866, 385, 36, "Adam optimizer · binary cross-entropy loss", [], size=13.5)
    arrow((702, 902), (702, 916))
    box(
        510,
        916,
        385,
        50,
        "Per-epoch validation loss",
        ["early stopping (patience 2) · checkpoint best model"],
        size=13.5,
    )
    arrow((702, 966), (702, 980))
    box(
        510,
        980,
        385,
        46,
        "Held-out test evaluation",
        ["accuracy · precision · recall · F1 · ROC AUC"],
        size=13.5,
    )

    # --- 6. Serving -----------------------------------------------------------
    panel(40, 824, 430, 218, 6, "Serving", "server")
    arrow((510, 941), (452, 941))
    text(481, 933, "model", 11.5, S.text_2)
    box(60, 866, 390, 36, "Flask REST API  ·  `POST /predict`", [], size=13.5)
    arrow((255, 902), (255, 916))
    box(
        60,
        916,
        390,
        50,
        "Tokenize → BiLSTM → $p$",
        ["same vocabulary as training (`tokenizer.json`)"],
        size=13.5,
    )
    arrow((255, 966), (255, 980))
    box(
        60,
        980,
        390,
        46,
        "JSON response",
        ["`malicious_probability` · `is_malicious` ($p ≥ 0.5$)"],
        size=13.5,
        icon_name="braces",
    )

    # --- Caption (academic style) ---------------------------------------------
    if S.academic:
        for i, line in enumerate(CAPTION):
            text(40, 1080 + i * 22, line, 15, anchor="start")


def main() -> None:
    global S
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("output")
    parser.add_argument("--style", choices=list(STYLES), default="dark")
    args = parser.parse_args()
    S = STYLES[args.style]

    draw()

    # The academic figure has no title, so shift it up and leave room for the caption.
    shift, height = (-HEADER_H, 1070 - HEADER_H + 70) if S.academic else (0, 1070)
    transform = f' transform="translate(0,{shift})"' if shift else ""
    size = S.arrowhead_size
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}"
     width="{W}" height="{height}" role="img" aria-labelledby="title">
<title id="title">NLP Phishing Detection system architecture</title>
<defs>
  <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5"
          markerWidth="{size}" markerHeight="{size}" orient="auto-start-reverse">
    <path d="{S.arrowhead}" fill="{S.arrow}"/>
  </marker>
</defs>
<rect width="{W}" height="{height}" fill="{S.bg}"/>
<g font-family="{S.sans}" xml:space="preserve"{transform}>
{chr(10).join(out)}
</g>
</svg>
"""
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
