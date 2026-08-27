#!/usr/bin/env python3
"""
Generate the static profile README assets into ../assets.

    python scripts/gen_assets.py

WHY EACH ASSET SHIPS IN TWO WIDTHS
----------------------------------
GitHub caps README images at the content column width but never upscales them,
so a single 880px asset is really a fixed *type scale*: on a 343px phone the
column is ~311px, the asset renders at 0.35x, and anything set below ~28px in
the source drops under 10 CSS px and stops being readable. Measured on the real
GitHub-rendered DOM, the first version of these assets put the role line at
6.7px and every pipeline stage label at 5.7px on a phone.

The fix is art direction per breakpoint rather than one compromised canvas:

    assets/hero.svg           880px, desktop composition
    assets/hero-narrow.svg    380px, recomposed for a phone column

The README selects between them with

    <picture>
      <source media="(max-width: 690px)" srcset="assets/hero-narrow.svg">
      <img src="assets/hero.svg" alt="..." width="100%">
    </picture>

which survives GitHub's HTML sanitizer intact (verified against
POST https://api.github.com/markdown) and needs no JavaScript — the browser
resolves <source media> natively. Clients that ignore <picture> fall back to
the <img>, so the desktop asset is always the safe default.

BREAKPOINT MATHS
----------------
`width="100%"` is what makes two variants enough. Without it an asset never
upscales, so a 380px panel would sit in a 658px column leaving 42% of the row
empty; with it the chosen panel always fills the column and the only question
per band is the scale factor:

    viewport <= 690   ->  column 288..658  ->  narrow/380 at 0.76x..1.73x
    viewport >  690   ->  column 659..880  ->  wide/880   at 0.75x..1.00x

Both bands therefore bottom out near 0.75x, so a source floor of ~13px clears
10 CSS px everywhere. 690px is the crossover where the two scale factors meet;
above it the wide composition is the denser and better-looking of the two.
The cost of the upper band is that the narrow panel looks chunky on a tablet
in portrait — a deliberate trade against it being unreadable on a phone.

Type floors, therefore: 12px in narrow assets, 13.5px in wide ones.

Prose stays in the README's Markdown regardless — it reflows, stays selectable,
and is read correctly by screen readers. These assets carry only headline type
and diagrams.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import svgkit as k  # noqa: E402

ASSETS = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets"))

WIDE_W = 880
NARROW_W = 380

NAME = "DUSHYANT BHARDWAJ"
ROLE = "SOFTWARE ENGINEER  ·  AI BUILDER  ·  PRODUCT ENGINEER"
STATUS = "BUILDING  ·  OPEN TO SWE / AI ROLES"

# Wrapped forms used only in the narrow composition.
NAME_NARROW = ("DUSHYANT", "BHARDWAJ")
ROLE_NARROW = ("SOFTWARE ENGINEER  ·  AI BUILDER", "PRODUCT ENGINEER")


# =============================================================== hero.svg ====
def hero(narrow=False):
    """Identity panel: terminal chrome, name, role, status.

    Both widths are laid out by accumulating y, so the canvas height falls out
    of the content instead of being a magic number that has to be kept in sync.
    """
    W = NARROW_W if narrow else WIDE_W
    pad = 16 if narrow else 28
    bar_h = 42 if narrow else 46

    name_size = 34 if narrow else 40
    name_lead = 40 if narrow else 0
    role_size = 14 if narrow else 21
    role_lead = 20 if narrow else 0
    chrome_size = 13 if narrow else 14
    status_size = 13 if narrow else 14

    name_lines = NAME_NARROW if narrow else (NAME,)
    role_lines = ROLE_NARROW if narrow else (ROLE,)

    # --- vertical flow -----------------------------------------------------
    y = bar_h + (34 if narrow else 44)
    name_y = y
    y += name_lead * (len(name_lines) - 1)
    accent_y = y + (14 if narrow else 16)
    role_y = accent_y + (26 if narrow else 36)
    y = role_y + role_lead * (len(role_lines) - 1)
    status_y = y + 26 if narrow else None
    h = int((status_y + 28) if narrow else 208)

    body = [
        k.rect(0, 0, W, h, fill=k.BG, rx=12),
        k.grid_bg(1, 1, W - 2, h - 2, step=28 if narrow else 34, opacity=0.5),
        k.rect(0, 0, W, h, fill="url(#panelGlow)", rx=12),
        k.scanlines(1, 1, W - 2, h - 2, step=5),
    ]

    # --- window chrome bar -------------------------------------------------
    body.append(k.rect(1, 1, W - 2, bar_h, fill=k.PANEL, rx=11))
    body.append(k.rect(1, bar_h - 11, W - 2, 11, fill=k.PANEL))  # square off bottom
    body.append(k.line(1, bar_h, W - 1, bar_h, stroke=k.BORDER))
    body.append(k.window_dots(pad + 4, bar_h / 2 + 1))
    body.append(k.text(pad + 46, bar_h / 2 + 5, "~/dushyant-bhardwaj",
                       size=chrome_size, fill=k.FG3))

    # On desktop the status pill rides in the chrome bar's right edge. At 380px
    # there is no room beside the path, so it moves below the role instead.
    sw = k.mono_w(STATUS, status_size) + 34
    if narrow:
        body.append(k.rect(pad + 2, status_y - 17, round(sw, 1), 24,
                           fill=k.PANEL_ALT, stroke=k.BORDER_HI, rx=12))
        body.append(k.status_dot(pad + 17, status_y - 5))
        body.append(k.text(pad + 29, status_y, STATUS, size=status_size,
                           fill=k.FG2, spacing="0.5"))
    else:
        body.append(k.rect(W - pad - sw, bar_h / 2 - 12, round(sw, 1), 24,
                           fill=k.PANEL_ALT, stroke=k.BORDER_HI, rx=12))
        body.append(k.status_dot(W - pad - sw + 15, bar_h / 2))
        body.append(k.text(W - pad - sw + 27, bar_h / 2 + 4.5, STATUS,
                           size=status_size, fill=k.FG2, spacing="0.5"))

    # --- identity ----------------------------------------------------------
    for i, ln in enumerate(name_lines):
        body.append(k.text(pad + 2, name_y + i * name_lead, ln, size=name_size,
                           fill=k.FG, weight="bold",
                           spacing="1.8" if narrow else "2.4"))
    body.append(k.accent_bar(pad + 4, accent_y, 176 if narrow else 300, 2.5))
    for i, ln in enumerate(role_lines):
        body.append(k.text(pad + 2, role_y + i * role_lead, ln, size=role_size,
                           fill=k.CYAN, spacing="0.8" if narrow else "1.1"))

    # --- layer glyph, right edge ------------------------------------------
    # Centre-aligned narrowing bars with a node on each: a system read top-down,
    # product surface down to infrastructure. Purely a motif, no data implied.
    # Dropped on narrow — there is no horizontal room, and decoration is the
    # first thing that should go when the column shrinks.
    if not narrow:
        cx = W - 118
        gy = 78
        layers = ((150, k.CYAN), (122, k.BLUE), (94, k.VIOLET), (66, k.FG3))
        for i, (lw, colour) in enumerate(layers):
            ly = gy + i * 24
            body.append(k.rect(cx - lw / 2, ly, lw, 10, fill=colour, rx=5, opacity=0.45))
            body.append(k.circle(cx - lw / 2 - 9, ly + 5, 2.6, fill=colour, opacity=0.8))
            if i:
                body.append(k.line(cx, ly - 14, cx, ly, stroke=k.BORDER_HI, opacity=0.9))

        # Faint baseline rule to close the panel.
        body.append(k.line(pad + 2, h - 20, W - pad - 2, h - 20,
                           stroke=k.BORDER, opacity=0.7))

    body.append(k.rect(0.5, 0.5, W - 1, h - 1, fill="none", stroke=k.BORDER, rx=12))

    return k.svg_doc(W, h, "".join(body), "%s — %s" % (NAME.title(), ROLE))


# =========================================================== pipeline.svg ====
# Stage names only. The reasoning behind each stage is prose in the README, so
# this stays a diagram — five words, readable when scaled to a phone.
STAGES = (
    ("PROBLEM", k.FG3),
    ("AI LAYER", k.CYAN),
    ("SERVICES", k.BLUE),
    ("DATA", k.VIOLET),
    ("SHIPPED", k.GREEN),
)


def pipeline(narrow=False):
    """How a build actually moves, problem to public URL.

    Horizontal rail on desktop. At 380px five chips plus four arrows cannot sit
    side by side at a legible type size, so the narrow variant rotates the same
    flow to a vertical one — which is what the linear semantics deserve on a
    phone anyway.
    """
    W = NARROW_W if narrow else WIDE_W
    pad = 16 if narrow else 28
    fs = 16 if narrow else 18
    padx = 15 if narrow else 17
    label_size = 13 if narrow else 14

    body = []

    head_y = 36 if narrow else 40
    body.append(k.section_label(pad + 2, head_y, "// BUILD PIPELINE", size=label_size))
    body.append(k.accent_bar(pad + 2, head_y + 9, 165 if narrow else 172, 2))
    if not narrow:
        body.append(k.text(W - pad - 2, head_y, "PROBLEM  ->  PUBLIC URL",
                           size=label_size, fill=k.FG3, anchor="end", spacing="0.8"))

    if narrow:
        chip_h = 34
        gap = 16
        # Widen past the longest label to ~62% of the panel: sized to the text
        # alone, five short chips in a 380px column read as a thin thread with
        # dead space either side.
        cw = max(max(k.mono_w(lb, fs) for lb, _ in STAGES) + padx * 2,
                 (W - pad * 2) * 0.62)
        x = (W - cw) / 2.0
        top = head_y + 26
        h = int(top + len(STAGES) * chip_h + (len(STAGES) - 1) * gap + 18)

        # Single spine behind the column, so the stages read as one system.
        body.insert(0, k.line(W / 2.0, top + 6, W / 2.0,
                              top + len(STAGES) * chip_h + (len(STAGES) - 1) * gap - 6,
                              stroke=k.BORDER_HI, sw=1.5, opacity=0.9))

        for i, (label, colour) in enumerate(STAGES):
            cy = top + i * (chip_h + gap)
            body.append(k.rect(round(x, 1), cy, round(cw, 1), chip_h,
                               fill=k.PANEL_ALT, stroke=colour, rx=9, sw=1.4))
            body.append(k.rect(round(x, 1), cy, round(cw, 1), chip_h,
                               fill=colour, rx=9, opacity=0.07))
            body.append(k.text(W / 2.0, cy + chip_h / 2 + fs * 0.36, label,
                               size=fs, fill=k.FG, weight="bold", anchor="middle",
                               spacing="1.1"))
            # No accent tick here: the full-width chip already carries a
            # colour-coded stroke, and a 3u nub straddling that border reads as
            # a rendering artifact once the panel is scaled to a phone.
            if i < len(STAGES) - 1:
                ay = cy + chip_h
                body.append(k.path("M %.1f %.1f l -4 -6 l 8 0 z" % (W / 2.0, ay + gap - 3),
                                   stroke=None, fill=k.FG3, opacity=0.85))
    else:
        h = 150
        gap = 30
        chip_h = 40
        cy = 96
        widths = [k.mono_w(label, fs) + padx * 2 for label, _ in STAGES]
        total = sum(widths) + gap * (len(STAGES) - 1)
        start = (W - total) / 2.0

        # Continuous rail behind the chips ties the stages into one system.
        body.append(k.line(start - 12, cy + chip_h / 2, start + total + 12,
                           cy + chip_h / 2, stroke=k.BORDER_HI, sw=1.5, opacity=0.9))

        x = start
        for i, (label, colour) in enumerate(STAGES):
            cw = widths[i]
            body.append(k.rect(round(x, 1), cy, round(cw, 1), chip_h,
                               fill=k.PANEL_ALT, stroke=colour, rx=9, sw=1.4))
            body.append(k.rect(round(x, 1), cy, round(cw, 1), chip_h,
                               fill=colour, rx=9, opacity=0.07))
            body.append(k.text(x + cw / 2, cy + chip_h / 2 + fs * 0.36, label,
                               size=fs, fill=k.FG, weight="bold", anchor="middle",
                               spacing="1.1"))
            body.append(k.rect(x + cw / 2 - 13, cy - 1.5, 26, 3, fill=colour, rx=1.5))

            if i < len(STAGES) - 1:
                ax = x + cw
                mid = cy + chip_h / 2
                body.append(k.line(ax + 7, mid, ax + gap - 10, mid,
                                   stroke=k.BORDER_HI, sw=1.5))
                body.append(k.path("M %.1f %.1f l -6 -4 l 0 8 z" % (ax + gap - 6, mid),
                                   stroke=None, fill=k.FG3, opacity=0.85))
            x += cw + gap

    frame = [
        k.rect(0, 0, W, h, fill=k.BG, rx=12),
        k.grid_bg(1, 1, W - 2, h - 2, step=28 if narrow else 34, opacity=0.5),
        k.rect(0, 0, W, h, fill="url(#panelGlow)", rx=12),
    ]
    return k.svg_doc(W, h, "".join(frame) + "".join(body), "Build pipeline: " +
                     " to ".join(s[0].lower() for s in STAGES))


# ==================================================================== main ===
def main():
    built = []
    for name, fn, kw in (
        ("hero", hero, {}),
        ("hero-narrow", hero, {"narrow": True}),
        ("pipeline", pipeline, {}),
        ("pipeline-narrow", pipeline, {"narrow": True}),
    ):
        svg = fn(**kw)
        k.write(os.path.join(ASSETS, name + ".svg"), svg)
        built.append("%s.svg (%.1f KB)" % (name, len(svg) / 1024.0))
    print("generated: " + ", ".join(built))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
