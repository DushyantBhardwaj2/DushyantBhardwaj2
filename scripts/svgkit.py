"""
svgkit — a tiny SVG primitive library for the profile README assets.

Design constraints this module deliberately respects, because GitHub renders
README assets through an image proxy and a HTML sanitizer:

  * No <style> blocks and no CSS classes. Every visual property is set as an
    SVG presentation attribute (fill=, stroke=, font-size=, ...), which no
    sanitizer strips.
  * No <script>, no <foreignObject>, no external references. Assets are fully
    self-contained so they render identically everywhere.
  * Monospace-first typography. Monospace advance width is ~0.6em across
    Consolas / Menlo / DejaVu Sans Mono, so text boxes can be sized without
    measuring glyphs on the viewer's machine.
  * Every panel paints its own dark background. That way the asset reads as a
    deliberate terminal panel on GitHub's light theme and blends into the
    canvas on dark theme, without needing two variants.
"""

from html import escape

# ---------------------------------------------------------------- palette ----
# Base values track GitHub's own dark canvas so the panels feel native in dark
# mode; the accents carry the cyan / blue / violet identity.
BG        = "#0A0E14"
PANEL     = "#0D1117"
PANEL_ALT = "#111823"
BORDER    = "#21262D"
BORDER_HI = "#30363D"
GRID      = "#161B22"

FG        = "#E6EDF3"
FG2       = "#8B949E"
FG3       = "#6E7681"

CYAN      = "#22D3EE"
BLUE      = "#58A6FF"
VIOLET    = "#A78BFA"
GREEN     = "#3FB950"
AMBER     = "#D29922"

MONO = "ui-monospace,SFMono-Regular,SF Mono,Menlo,Consolas,Liberation Mono,monospace"

# Monospace advance width as a fraction of font size. Used only to reserve
# space, never to centre text tightly.
CW = 0.6


def mono_w(text, size):
    """Approximate rendered width of monospace text at the given font size."""
    return len(text) * size * CW


def esc(text):
    return escape(str(text), quote=True)


# ------------------------------------------------------------- primitives ----
def text(x, y, s, size=13, fill=FG, weight="normal", anchor="start",
         spacing=None, opacity=None):
    attrs = [
        'x="%s"' % x,
        'y="%s"' % y,
        'font-family="%s"' % MONO,
        'font-size="%s"' % size,
        'fill="%s"' % fill,
    ]
    if weight != "normal":
        attrs.append('font-weight="%s"' % weight)
    if anchor != "start":
        attrs.append('text-anchor="%s"' % anchor)
    if spacing is not None:
        attrs.append('letter-spacing="%s"' % spacing)
    if opacity is not None:
        attrs.append('opacity="%s"' % opacity)
    return "<text %s>%s</text>" % (" ".join(attrs), esc(s))


def rect(x, y, w, h, fill="none", stroke=None, rx=0, sw=1, opacity=None):
    attrs = ['x="%s"' % x, 'y="%s"' % y, 'width="%s"' % w, 'height="%s"' % h,
             'fill="%s"' % fill]
    if rx:
        attrs.append('rx="%s"' % rx)
    if stroke:
        attrs.append('stroke="%s"' % stroke)
        attrs.append('stroke-width="%s"' % sw)
    if opacity is not None:
        attrs.append('opacity="%s"' % opacity)
    return "<rect %s/>" % " ".join(attrs)


def line(x1, y1, x2, y2, stroke=BORDER, sw=1, opacity=None, dash=None):
    attrs = ['x1="%s"' % x1, 'y1="%s"' % y1, 'x2="%s"' % x2, 'y2="%s"' % y2,
             'stroke="%s"' % stroke, 'stroke-width="%s"' % sw]
    if opacity is not None:
        attrs.append('opacity="%s"' % opacity)
    if dash:
        attrs.append('stroke-dasharray="%s"' % dash)
    return "<line %s/>" % " ".join(attrs)


def circle(cx, cy, r, fill=GREEN, opacity=None):
    attrs = ['cx="%s"' % cx, 'cy="%s"' % cy, 'r="%s"' % r, 'fill="%s"' % fill]
    if opacity is not None:
        attrs.append('opacity="%s"' % opacity)
    return "<circle %s/>" % " ".join(attrs)


def path(d, stroke=BORDER, fill="none", sw=1, opacity=None):
    attrs = ['d="%s"' % d, 'fill="%s"' % fill]
    if stroke:
        attrs.append('stroke="%s"' % stroke)
        attrs.append('stroke-width="%s"' % sw)
    if opacity is not None:
        attrs.append('opacity="%s"' % opacity)
    return "<path %s/>" % " ".join(attrs)


# --------------------------------------------------------------- compound ----
def grid_bg(x, y, w, h, step=32, stroke=GRID, opacity=0.55):
    """Faint engineering-drawing grid, clipped to the panel via a group id."""
    out = []
    gx = x + step
    while gx < x + w:
        out.append(line(gx, y, gx, y + h, stroke=stroke, opacity=opacity))
        gx += step
    gy = y + step
    while gy < y + h:
        out.append(line(x, gy, x + w, gy, stroke=stroke, opacity=opacity))
        gy += step
    return "".join(out)


def scanlines(x, y, w, h, step=4, stroke="#FFFFFF", opacity=0.014):
    """Very subtle horizontal scanline texture. Kept near-invisible on purpose."""
    out = []
    gy = y
    while gy < y + h:
        out.append(line(x, gy, x + w, gy, stroke=stroke, opacity=opacity))
        gy += step
    return "".join(out)


def panel(x, y, w, h, rx=10, fill=PANEL, stroke=BORDER):
    return rect(x, y, w, h, fill=fill, stroke=stroke, rx=rx)


def window_dots(x, y, r=3.5, gap=13):
    """Three-dot terminal window chrome."""
    return "".join([
        circle(x, y, r, fill="#FF5F57", opacity=0.85),
        circle(x + gap, y, r, fill=AMBER, opacity=0.85),
        circle(x + gap * 2, y, r, fill=GREEN, opacity=0.85),
    ])


def status_dot(cx, cy, color=GREEN, r=4):
    """Status LED with a soft halo, drawn as two circles (no filters needed)."""
    return circle(cx, cy, r * 2.6, fill=color, opacity=0.16) + circle(cx, cy, r, fill=color)


def chip(x, y, label, size=11, fg=FG2, border=BORDER_HI, bg=PANEL_ALT,
         padx=8, h=20, rx=5):
    """A small bordered tag. Returns (svg, width) so callers can flow them."""
    w = mono_w(label, size) + padx * 2
    svg = rect(x, y, round(w, 1), h, fill=bg, stroke=border, rx=rx)
    svg += text(x + padx, y + h / 2 + size * 0.36, label, size=size, fill=fg)
    return svg, w


def chip_row(x, y, labels, size=11, gap=6, max_w=None, **kw):
    """Flow chips left to right, wrapping when max_w is exceeded."""
    out, cx, cy, rows = [], x, y, 1
    h = kw.get("h", 20)
    for lb in labels:
        svg, w = chip(cx, cy, lb, size=size, **kw)
        if max_w and cx + w > x + max_w and cx > x:
            cx = x
            cy += h + gap
            rows += 1
            svg, w = chip(cx, cy, lb, size=size, **kw)
        out.append(svg)
        cx += w + gap
    return "".join(out), rows


def accent_bar(x, y, w, h=2, grad_id="accent"):
    """Thin cyan -> blue -> violet rule used as a section signature."""
    return rect(x, y, w, h, fill="url(#%s)" % grad_id, rx=h / 2)


def defs(extra=""):
    return (
        "<defs>"
        '<linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="%s"/>'
        '<stop offset="0.5" stop-color="%s"/>'
        '<stop offset="1" stop-color="%s"/>'
        "</linearGradient>"
        '<linearGradient id="accentFade" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="%s" stop-opacity="0.9"/>'
        '<stop offset="0.55" stop-color="%s" stop-opacity="0.5"/>'
        '<stop offset="1" stop-color="%s" stop-opacity="0"/>'
        "</linearGradient>"
        '<linearGradient id="panelGlow" x1="0" y1="0" x2="0.6" y2="1">'
        '<stop offset="0" stop-color="%s" stop-opacity="0.07"/>'
        '<stop offset="1" stop-color="%s" stop-opacity="0"/>'
        "</linearGradient>"
        "%s</defs>"
    ) % (CYAN, BLUE, VIOLET, CYAN, BLUE, VIOLET, CYAN, VIOLET, extra)


def svg_doc(w, h, body, title, extra_defs=""):
    """Wrap body in a self-contained, responsive SVG document."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
        'viewBox="0 0 %d %d" role="img" aria-label="%s">'
        "<title>%s</title>%s%s</svg>"
    ) % (w, h, w, h, esc(title), esc(title), defs(extra_defs), body)


def section_label(x, y, kicker, size=11, color=CYAN):
    """Small uppercase system label, e.g. '// FEATURED BUILDS'."""
    return text(x, y, kicker, size=size, fill=color, weight="bold", spacing="1.6")


def write(path_, svg):
    with open(path_, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(svg + "\n")
    return len(svg)
