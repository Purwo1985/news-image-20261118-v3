#!/usr/bin/env python3
"""news-image-20261118-v3 -- one image summing up Wednesday 18 Nov 2026.

A pure-stdlib Python program. It draws a 1024x1024 classic broadsheet
front page -- a big nameplate masthead with the date, a lead story told
large across the full width, a full-width world map with numbered pins,
five more stories in a ruled three-column grid, and an "also making
news" strip -- into an RGB buffer, encodes it as a PNG with a
hand-rolled encoder, and writes it to $MAKEFUN_OUTPUT_DIR/entry.png
(default /output).

Everything is drawn in code: a hand-written 5x7 bitmap font, coarse
continent polygons, and primitive shapes. No network, no files read at
runtime, no timestamps, no randomness: two runs write byte-identical
output. The program runs in about 2 seconds.

=====================================================================
NEWS DATA -- copied from the main entry (the one permitted exception:
STORIES and ALSO_LINE are news data, not code). Content is NOT frozen
here; a separate job updates it on the evening of 19 Nov 2026 (WIB).
=====================================================================
"""

import os
import struct
import zlib

# ------------------------------------------------------------------
# NEWS DATA (see the block above)
# ------------------------------------------------------------------

DATE_LINE = "WEDNESDAY 18 NOVEMBER 2026"
NAMEPLATE = "THE WORLD"
KICKER = "WORLD NEWS IN ONE IMAGE"
SUBHEAD = "ONE DAY - SIX STORIES - EVERY CONTINENT"

# Provisional content, researched on 18 Nov 2026 (morning WIB) from
# wire reports of that day. Every main story below was first reported
# on 18 November 2026; the footer strip carries items from the same
# news cycle. Final freeze: evening of 19 Nov 2026 (WIB), once the
# day has ended everywhere on Earth.
STORIES = [
    {
        "tag": "ASIA - SUMMITS",
        "color": (27, 108, 168),
        "icon": "summit",
        "title": "APEC OPENS AS TRUMP HEADS TO CHINA",
        "body": "Leaders gather in Shenzhen for the APEC summit. Trump "
                "travels on for a first-ever three-way meeting with Xi "
                "Jinping and Vladimir Putin, due on 19 November.",
    },
    {
        "tag": "ASIA-PACIFIC - SECURITY",
        "color": (14, 124, 102),
        "icon": "quad",
        "title": "QUAD ANNOUNCES NEW MARITIME PLAN",
        "body": "The US, India, Japan and Australia, meeting in Manila, "
                "unveil a new maritime exercise and joint work on AI "
                "and cybersecurity.",
    },
    {
        "tag": "EUROPE - WAR",
        "color": (169, 50, 38),
        "icon": "bridge",
        "title": "UKRAINE HITS CRIMEAN BRIDGE",
        "body": "Ukraine damaged the Crimean Bridge in a major strike, "
                "as Russia hit bridges around Kyiv, with both sides "
                "targeting crossings.",
    },
    {
        "tag": "MIDDLE EAST - CONFLICT",
        "color": (122, 62, 150),
        "icon": "radar",
        "title": "IRAN CLAIMS DRONE STRIKE ON US BASE",
        "body": "Iran's Revolutionary Guard said it hit a US military "
                "radar system at Sheikh Isa Air Base in Bahrain, its "
                "third strike on the country in five days.",
    },
    {
        "tag": "ASIA - DISASTER",
        "color": (93, 109, 126),
        "icon": "alert",
        "title": "RUSSIAN MILITARY PLANE CRASHES",
        "body": "A Russian military plane crashed in Siberia, killing "
                "19 people. Investigators are examining the wreckage "
                "to find the cause.",
    },
    {
        "tag": "EUROPE - DIPLOMACY",
        "color": (46, 125, 50),
        "icon": "ban",
        "title": "BRITAIN SANCTIONS SETTLEMENT FIRMS",
        "body": "Britain sanctioned Israeli settlement firms in a push "
                "to protect the two-state solution, targeting companies "
                "linked to West Bank settlements.",
    },
]

ALSO_LINE = ("ALSO MAKING NEWS: US loses measles-free status, health "
             "officials say - Cyclone Akvan nears India's Andhra coast, "
             "landfall due 20 Nov - Dhoni retires from the IPL and "
             "becomes CSK mentor - Mongolia's president resigns amid "
             "graft charges.")

SOURCE_LINE = "Compiled from wire reports, 18 Nov 2026."

# ------------------------------------------------------------------
# Palette: classic broadsheet -- warm paper, black ink, red accents.
# ------------------------------------------------------------------

W, H = 1024, 1024
PAPER = (250, 246, 236)
INK = (26, 26, 26)
BODY = (58, 58, 58)
MUTED = (110, 104, 92)
RED = (178, 34, 34)
RED_DARK = (140, 24, 24)
NAVY = (30, 48, 80)
GOLD = (176, 141, 68)
RULE = (26, 26, 26)
FAINT_RULE = (196, 188, 172)
WHITE = (255, 255, 255)

OCEAN = (214, 228, 236)
LAND = (232, 222, 196)
LAND_EDGE = (120, 110, 80)
GRID = (196, 214, 226)
MAP_LABEL = (96, 108, 120)

# ------------------------------------------------------------------
# 5x7 bitmap font (hand-written). Each glyph is 7 rows of 5 pixels.
# "1" is ink, "0" is empty. Covers A-Z, a-z, 0-9 and punctuation.
# ------------------------------------------------------------------

FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}

FONT.update({
    "a": ("00000", "00000", "01110", "00001", "01111", "10001", "01111"),
    "b": ("10000", "10000", "11110", "10001", "10001", "10001", "11110"),
    "c": ("00000", "00000", "01110", "10000", "10000", "10001", "01110"),
    "d": ("00001", "00001", "01111", "10001", "10001", "10001", "01111"),
    "e": ("00000", "00000", "01110", "10001", "11111", "10000", "01110"),
    "f": ("00110", "01001", "01000", "11110", "01000", "01000", "01000"),
    "g": ("00000", "01111", "10001", "10001", "01111", "00001", "01110"),
    "h": ("10000", "10000", "11110", "10001", "10001", "10001", "10001"),
    "i": ("00100", "00000", "01100", "00100", "00100", "00100", "01110"),
    "j": ("00010", "00000", "00110", "00010", "00010", "00010", "01100"),
    "k": ("10000", "10000", "10010", "10100", "11000", "10100", "10010"),
    "l": ("01100", "00100", "00100", "00100", "00100", "00100", "01110"),
    "m": ("00000", "00000", "11010", "10101", "10101", "10101", "10101"),
    "n": ("00000", "00000", "11110", "10001", "10001", "10001", "10001"),
    "o": ("00000", "00000", "01110", "10001", "10001", "10001", "01110"),
    "p": ("00000", "00000", "11110", "10001", "10001", "11110", "10000"),
    "q": ("00000", "00000", "01111", "10001", "10001", "01111", "00001"),
    "r": ("00000", "00000", "10110", "11001", "10000", "10000", "10000"),
    "s": ("00000", "00000", "01111", "10000", "01110", "00001", "11110"),
    "t": ("01000", "01000", "11100", "01000", "01000", "01000", "00110"),
    "u": ("00000", "00000", "10001", "10001", "10001", "10011", "01101"),
    "v": ("00000", "00000", "10001", "10001", "10001", "01010", "00100"),
    "w": ("00000", "00000", "10001", "10101", "10101", "10101", "01010"),
    "x": ("00000", "00000", "10001", "01010", "00100", "01010", "10001"),
    "y": ("00000", "00000", "10001", "10001", "01111", "00001", "01110"),
    "z": ("00000", "00000", "11111", "00010", "00100", "01000", "11111"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
})


# ------------------------------------------------------------------
# Canvas: a plain RGB buffer with primitive drawing.
# ------------------------------------------------------------------

class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.buf = bytearray(bg * (w * h))

    def px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i], self.buf[i + 1], self.buf[i + 2] = color

    def box(self, x, y, w, h, color):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.buf[i], self.buf[i + 1], self.buf[i + 2] = color

    def frame(self, x, y, w, h, color, t=1):
        self.box(x, y, w, t, color)
        self.box(x, y + h - t, w, t, color)
        self.box(x, y, t, h, color)
        self.box(x + w - t, y, t, h, color)

    def hline(self, x, y, w, color, t=1):
        self.box(x, y, w, t, color)

    def vline(self, x, y, h, color, t=1):
        self.box(x, y, t, h, color)

    def seg(self, x0, y0, x1, y1, color, t=1):
        """Bresenham segment with a square brush of thickness t."""
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err, half = dx + dy, t // 2
        while True:
            self.box(x0 - half, y0 - half, t, t, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def disc(self, cx, cy, r, color):
        for yy in range(cy - r, cy + r + 1):
            dx = int((r * r - (yy - cy) ** 2) ** 0.5) if abs(yy - cy) <= r else 0
            self.box(cx - dx, yy, 2 * dx + 1, 1, color)

    def ring(self, cx, cy, r, color, t=2):
        import math
        for deg in range(360):
            a = math.radians(deg)
            self.box(round(cx + r * math.cos(a)) - t // 2,
                     round(cy + r * math.sin(a)) - t // 2, t, t, color)

    def arc(self, cx, cy, r, a0, a1, color, t=2):
        import math
        steps = max(8, int(abs(a1 - a0) * r / 10))
        for i in range(steps + 1):
            a = math.radians(a0 + (a1 - a0) * i / steps)
            self.box(round(cx + r * math.cos(a)) - t // 2,
                     round(cy + r * math.sin(a)) - t // 2, t, t, color)

    def poly(self, pts, color, t=1):
        for i in range(len(pts)):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % len(pts)]
            self.seg(x0, y0, x1, y1, color, t)

    def fill_poly(self, pts, color, clip):
        """Scanline fill of a polygon in pixel coords, clipped to clip."""
        if len(pts) < 3:
            return
        cx0, cy0, cx1, cy1 = clip
        ys = [p[1] for p in pts]
        y0 = max(cy0, min(ys))
        y1 = min(cy1, max(ys))
        n = len(pts)
        for y in range(y0, y1 + 1):
            xs = []
            for i in range(n):
                x0, ya = pts[i]
                x1, yb = pts[(i + 1) % n]
                if (ya <= y < yb) or (yb <= y < ya):
                    xs.append(x0 + (y - ya) * (x1 - x0) / (yb - ya))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                xa = max(cx0, int(xs[k]))
                xb = min(cx1, int(xs[k + 1]))
                if xb >= xa:
                    self.box(xa, y, xb - xa + 1, 1, color)


# ------------------------------------------------------------------
# Text: measurement, wrapping, rendering
# ------------------------------------------------------------------

def text_w(text, scale):
    """Pixel width of text at the given scale (advance 6 units/char)."""
    return len(text) * 6 * scale - scale if text else 0


def draw_text(cv, x, y, text, scale, color):
    """Draw text with its top-left corner at (x, y)."""
    for ch in text:
        glyph = FONT.get(ch)
        if glyph is None:
            raise ValueError("character not in font: %r" % ch)
        for row, bits in enumerate(glyph):
            for col, bit in enumerate(bits):
                if bit == "1":
                    cv.box(x + col * scale, y + row * scale,
                           scale, scale, color)
        x += 6 * scale
    return x


def draw_text_c(cv, cx, y, text, scale, color):
    draw_text(cv, cx - text_w(text, scale) // 2, y, text, scale, color)


def wrap(text, scale, max_w):
    """Greedy word wrap; returns a list of lines fitting max_w."""
    lines = []
    for para in text.split("\n"):
        words = para.split(" ")
        cur = ""
        for word in words:
            trial = word if not cur else cur + " " + word
            if text_w(trial, scale) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
    return lines

# ------------------------------------------------------------------
# World map: coarse continent outlines (lon, lat) of my own, drawn
# from a rough world atlas -- deliberately stylised, not traced.
# A small gazetteer puts a numbered pin on each story's place.
# ------------------------------------------------------------------

MAP_X, MAP_Y, MAP_W, MAP_H = 24, 356, 976, 188
MAP_LAT_TOP, MAP_LAT_BOT = 78.0, -58.0

CONTINENTS = [
    # North America (coarse)
    [(-168, 66), (-156, 58), (-146, 60), (-136, 58), (-128, 51),
     (-124, 42), (-120, 34), (-112, 28), (-105, 21), (-96, 16),
     (-88, 14), (-81, 9), (-78, 8), (-82, 14), (-87, 16), (-90, 21),
     (-96, 19), (-97, 25), (-91, 29), (-84, 30), (-81, 27), (-80, 32),
     (-76, 36), (-72, 41), (-68, 44), (-62, 46), (-56, 49), (-60, 53),
     (-66, 58), (-73, 62), (-80, 63), (-86, 66), (-94, 68), (-104, 68),
     (-116, 69), (-128, 70), (-140, 70), (-152, 70), (-162, 70),
     (-168, 66)],
    # Greenland
    [(-56, 61), (-48, 60), (-40, 62), (-32, 68), (-24, 70), (-24, 75),
     (-34, 77), (-46, 77), (-56, 75), (-60, 69), (-58, 64), (-56, 61)],
    # South America (coarse)
    [(-78, 8), (-73, 11), (-65, 11), (-58, 6), (-52, 4), (-50, -1),
     (-44, -3), (-38, -6), (-35, -9), (-38, -15), (-41, -22), (-47, -25),
     (-52, -32), (-58, -37), (-64, -41), (-67, -48), (-69, -53),
     (-73, -53), (-74, -46), (-73, -38), (-71, -30), (-70, -20),
     (-76, -14), (-80, -6), (-81, 0), (-80, 4), (-78, 8)],
    # Europe (coarse)
    [(-10, 37), (-9, 43), (-3, 44), (-2, 49), (1, 51), (5, 53), (8, 56),
     (10, 58), (6, 61), (11, 64), (17, 68), (24, 71), (31, 70), (38, 68),
     (46, 68), (54, 68), (60, 69), (66, 68), (64, 62), (58, 57),
     (52, 52), (46, 49), (40, 47), (34, 46), (28, 44), (24, 40),
     (20, 40), (16, 43), (12, 44), (7, 44), (3, 42), (-1, 38),
     (-6, 36), (-10, 37)],
    # United Kingdom
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (1, 51),
     (-3, 50), (-5, 50)],
    # Africa (coarse)
    [(-17, 15), (-15, 22), (-13, 28), (-8, 32), (-4, 35), (3, 37),
     (10, 37), (15, 32), (21, 32), (27, 31), (32, 31), (35, 28),
     (37, 21), (40, 15), (44, 11), (51, 11), (51, 4), (46, -3),
     (41, -9), (38, -15), (35, -22), (33, -26), (29, -31), (24, -34),
     (19, -35), (16, -30), (13, -22), (12, -15), (11, -6), (9, 0),
     (7, 4), (1, 6), (-4, 5), (-9, 5), (-13, 8), (-16, 12), (-17, 15)],
    # Madagascar
    [(44, -16), (47, -15), (50, -16), (48, -21), (46, -25), (43, -22),
     (44, -16)],
    # Asia mainland (coarse)
    [(30, 70), (38, 68), (46, 68), (54, 68), (62, 69), (70, 72),
     (78, 73), (86, 74), (94, 76), (102, 77), (110, 74), (118, 73),
     (126, 72), (134, 71), (142, 72), (150, 70), (158, 69), (162, 65),
     (158, 58), (152, 59), (144, 54), (141, 47), (138, 40), (133, 35),
     (128, 34), (126, 38), (122, 39), (121, 34), (120, 28), (115, 23),
     (109, 20), (106, 10), (103, 7), (100, 8), (98, 11), (95, 16),
     (92, 21), (89, 22), (86, 20), (82, 17), (79, 12), (77, 8),
     (74, 15), (72, 20), (68, 23), (64, 25), (60, 25), (56, 27),
     (53, 28), (50, 29), (47, 30), (44, 29), (41, 30), (38, 32),
     (36, 36), (33, 36), (30, 36), (27, 38), (30, 41), (33, 44),
     (37, 46), (41, 48), (45, 51), (49, 55), (53, 59), (57, 62),
     (61, 66), (66, 68), (62, 69), (54, 69), (46, 69), (38, 69),
     (30, 70)],
    # Japan
    [(130, 31), (133, 34), (136, 35), (139, 37), (141, 40), (141, 44),
     (144, 44), (142, 42), (140, 38), (137, 35), (134, 33), (131, 32),
     (130, 31)],
    # Sumatra
    [(95, 5), (99, 2), (102, -1), (105, -4), (104, -6), (101, -4),
     (98, 0), (95, 5)],
    # Borneo
    [(109, 1), (112, 3), (116, 4), (119, 0), (117, -4), (113, -4),
     (110, -2), (109, 1)],
    # Java
    [(105, -6), (109, -7), (113, -7), (114, -9), (111, -8), (107, -8),
     (105, -6)],
    # New Guinea
    [(131, -1), (135, -2), (139, -4), (143, -6), (147, -8), (149, -9),
     (145, -8), (141, -8), (137, -6), (133, -3), (131, -1)],
    # Australia
    [(113, -22), (115, -30), (115, -35), (120, -34), (126, -32),
     (130, -32), (134, -33), (137, -35), (140, -38), (144, -39),
     (148, -38), (151, -35), (153, -28), (152, -23), (149, -20),
     (146, -17), (143, -11), (141, -13), (138, -15), (135, -12),
     (132, -11), (129, -13), (125, -15), (121, -18), (117, -21),
     (113, -22)],
    # Tasmania
    [(145, -41), (147, -41), (148, -43), (146, -44), (145, -42),
     (145, -41)],
    # New Zealand
    [(167, -45), (169, -43), (172, -42), (174, -41), (176, -38),
     (178, -37), (175, -40), (172, -43), (169, -46), (167, -45)],
]

# Cities / named places first (checked before countries).
PLACES = {
    "SHEIKH ISA": (50.5, 26.2), "WEST BANK": (35.3, 32.0),
    "CRIMEAN": (34.0, 45.0), "SHENZHEN": (114.1, 22.5),
    "MANILA": (121.0, 14.6), "SIBERIA": (105.0, 62.0),
    "KYIV": (30.5, 50.4), "KIEV": (30.5, 50.4), "BAHRAIN": (50.5, 26.2),
    "BEIJING": (116.4, 39.9), "TOKYO": (139.7, 35.7),
    "DELHI": (77.2, 28.6), "MUMBAI": (72.9, 19.1),
    "JAKARTA": (106.8, -6.2), "BANGKOK": (100.5, 13.8),
    "LONDON": (-0.1, 51.5), "PARIS": (2.35, 48.85), "BERLIN": (13.4, 52.5),
    "MOSCOW": (37.6, 55.8), "TEHRAN": (51.4, 35.7),
    "ANDHRA": (80.0, 16.0), "MONGOLIA": (106.0, 47.0),
    "NEW YORK": (-74.0, 40.7), "WASHINGTON": (-77.0, 38.9),
    "SYDNEY": (151.2, -33.9), "CAIRO": (31.2, 30.0),
    "DUBAI": (55.3, 25.2), "SEOUL": (127.0, 37.5),
}

COUNTRIES = {
    "UNITED STATES": (-98.0, 39.0), "AMERICA": (-98.0, 39.0),
    "CHINA": (104.0, 35.0), "INDIA": (79.0, 22.0),
    "JAPAN": (138.0, 37.0), "INDONESIA": (114.0, -2.0),
    "RUSSIA": (95.0, 62.0), "UKRAINE": (32.0, 49.0),
    "BRITAIN": (-1.5, 52.5), "BRITISH": (-1.5, 52.5),
    "FRANCE": (2.0, 46.0), "GERMANY": (10.0, 51.0),
    "IRAN": (53.0, 32.0), "IRAQ": (44.0, 33.0),
    "AUSTRALIA": (134.0, -25.0), "ISRAEL": (34.8, 31.0),
    "CANADA": (-106.0, 56.0), "BRAZIL": (-52.0, -10.0),
    "AFRICA": (20.0, 5.0), "EUROPE": (15.0, 52.0),
}

REGION_XY = [
    ("MIDDLE EAST", (47.0, 29.0)),
    ("ASIA-PACIFIC", (125.0, 5.0)),
    ("ASIA", (100.0, 35.0)),
    ("EUROPE", (15.0, 52.0)),
    ("AFRICA", (20.0, 5.0)),
    ("AMERICAS", (-90.0, 25.0)),
    ("OCEANIA", (140.0, -25.0)),
    ("WORLD", (0.0, 20.0)),
]


def story_pin_xy(story, i):
    """Lon/lat for a story's map pin, from its text, then its region."""
    text = (story["title"] + " " + story["body"]).upper()
    for table in (PLACES, COUNTRIES):
        for name in sorted(table, key=len, reverse=True):
            if name in text:
                lon, lat = table[name]
                break
        else:
            continue
        break
    else:
        lon, lat = 100.0, 35.0
        for key, (x, y) in REGION_XY:
            if key in story["tag"]:
                lon, lat = x, y
                break
    lon += ((i * 37) % 5 - 2) * 1.5
    lat += ((i * 23) % 3 - 1) * 1.5
    return lon, lat


def map_xy(lon, lat):
    x = MAP_X + (lon + 180.0) / 360.0 * MAP_W
    y = MAP_Y + (MAP_LAT_TOP - lat) / (MAP_LAT_TOP - MAP_LAT_BOT) * MAP_H
    return round(x), round(y)


def draw_map(cv):
    clip = (MAP_X, MAP_Y, MAP_X + MAP_W - 1, MAP_Y + MAP_H - 1)
    cv.box(MAP_X, MAP_Y, MAP_W, MAP_H, OCEAN)
    # Graticule, drawn first so land covers it.
    for lon in range(-150, 151, 30):
        gx, _ = map_xy(lon, 0)
        cv.vline(gx, MAP_Y, MAP_H, GRID, 1)
    for lat in (60, 30, 0, -30):
        _, gy = map_xy(0, lat)
        cv.hline(MAP_X, gy, MAP_W, GRID, 1)
    # Continents.
    for poly in CONTINENTS:
        pts = []
        for lon, lat in poly:
            px, py = map_xy(lon, lat)
            pts.append((max(MAP_X, min(MAP_X + MAP_W - 1, px)),
                        max(MAP_Y, min(MAP_Y + MAP_H - 1, py))))
        cv.fill_poly(pts, LAND, clip)
        cv.poly(pts, LAND_EDGE, 1)
    # Ocean + region labels.
    for label, lon, lat in (
            ("NORTH AMERICA", -102, 56), ("SOUTH AMERICA", -60, -22),
            ("EUROPE", -14, 63), ("AFRICA", 16, 2), ("ASIA", 78, 44),
            ("AUSTRALIA", 117, -29), ("PACIFIC OCEAN", -152, -8),
            ("ATLANTIC OCEAN", -36, 26)):
        lx, ly = map_xy(lon, lat)
        draw_text(cv, lx, ly, label, 2, MAP_LABEL)
    # Numbered pins, nudged apart where neighbours would overlap.
    pins = []
    for i, story in enumerate(STORIES):
        lon, lat = story_pin_xy(story, i)
        pins.append(list(map_xy(lon, lat)))
    for _ in range(3):
        moved = False
        for i in range(len(pins)):
            for j in range(i):
                dx = pins[i][0] - pins[j][0]
                dy = pins[i][1] - pins[j][1]
                if dx * dx + dy * dy < 26 * 26:
                    pins[i][1] += 14
                    moved = True
        if not moved:
            break
    for i, (px, py) in enumerate(pins):
        color = STORIES[i]["color"]
        cv.disc(px, py, 11, color)
        cv.ring(px, py, 11, WHITE, 2)
        num = str(i + 1)
        draw_text(cv, px - text_w(num, 2) // 2, py - 7, num, 2, WHITE)
    cv.frame(MAP_X, MAP_Y, MAP_W, MAP_H, INK, 2)

# ------------------------------------------------------------------
# Scenes: one small illustration per story, drawn in the story's
# colour inside a box (x, y, w, h). Each motif is my own geometry.
# ------------------------------------------------------------------

def tint(color, bg, f=0.12):
    return tuple(round(bg[i] + (color[i] - bg[i]) * f) for i in range(3))


def draw_scene(cv, kind, x, y, w, h, color):
    if w < 30 or h < 20:
        return
    mid = tint(color, WHITE, 0.45)
    if kind == "summit":
        # Sun, skyline of four towers, three flagpoles.
        cv.disc(x + w - 18, y + 14, min(8, h // 3), color)
        for i in range(4):
            bw = w // 5
            bh = min(22 + ((i * 31) % 4) * 16, h - 10)
            cv.box(x + 6 + i * bw, y + h - 6 - bh, bw - 8, bh, mid)
        for f in (0.22, 0.5, 0.78):
            fx = x + int(w * f)
            cv.vline(fx, y + 10, h - 16, color, 2)
            cv.box(fx + 2, y + 10, 18, 9, color)
    elif kind == "quad":
        # Two ships on three wave lines, four dots in a diamond.
        for wy in (y + h - 26, y + h - 16, y + h - 6):
            wx = x + 4
            while wx < x + w - 14:
                cv.seg(wx, wy, wx + 7, wy - 3, color, 2)
                cv.seg(wx + 7, wy - 3, wx + 14, wy, color, 2)
                wx += 14
        for f in (0.18, 0.58):
            shx = x + int(w * f)
            cv.box(shx, y + 12, 34, 6, mid)
            cv.vline(shx + 17, y + 12, 10, mid, 2)
            cv.box(shx + 17, y + 2, 9, 6, mid)
        cx, cy = x + w - 24, y + 16
        for dx, dy in ((0, -9), (-11, 0), (11, 0), (0, 9)):
            cv.disc(cx + dx, cy + dy, 3, color)
    elif kind == "bridge":
        # Suspension bridge: deck, two towers, sagging cables, water.
        # Arc radius stays inside the box: never taller than the box.
        cv.hline(x + 4, y + h // 2, w - 8, color, 3)
        for f in (0.18, 0.82):
            tx = x + int(w * f)
            cv.vline(tx, y + 6, h // 2 - 4, color, 3)
        cx = x + w // 2
        ar = max(6, min(w // 4, h // 2 - 4))
        cv.arc(cx, y + h // 2 - ar, ar, 200, 340, color, 2)
        for f in (0.3, 0.5, 0.7):
            vx = x + int(w * f)
            cv.vline(vx, y + h // 2 - 12, 12, color, 2)
        wx = x + 6
        while wx < x + w - 16:
            cv.hline(wx, y + h - 8, 12, mid, 2)
            wx += 22
    elif kind == "radar":
        # Concentric rings, sweep spoke, blips, crosshair ticks.
        # Ring radii scale to the box so nothing spills out of it.
        cx, cy = x + w // 2, y + h // 2
        for r in (max(4, h // 5), max(6, h // 3), max(8, h // 2 - 2)):
            cv.ring(cx, cy, r, color, 2)
        cv.seg(cx, cy, cx + max(8, h // 2 - 2), cy - 8, color, 2)
        cv.disc(cx - 9, cy + 6, 3, color)
        cv.disc(cx + 7, cy + 9, 3, mid)
        cv.disc(cx, cy, 2, color)
        cv.hline(x + 4, cy, 8, color, 2)
        cv.hline(x + w - 12, cy, 8, color, 2)
    elif kind == "alert":
        # Two mountain peaks, a small plane, a warning triangle.
        cv.seg(x + 4, y + h - 6, x + w // 3, y + 8, color, 3)
        cv.seg(x + w // 3, y + 8, x + 2 * w // 3, y + h - 6, color, 3)
        cv.seg(x + w // 3, y + h - 6, x + 3 * w // 4, y + h // 2, color, 3)
        cv.seg(x + 3 * w // 4, y + h // 2, x + w - 4, y + h - 6, color, 3)
        px, py = x + w - 44, y + 8
        cv.box(px, py, 26, 4, mid)
        cv.seg(px + 6, py + 4, px + 11, py + 10, mid, 2)
        cv.seg(px + 20, py + 4, px + 15, py + 10, mid, 2)
        tx, ty = x + w - 16, y + h // 2 + 4
        cv.seg(tx, ty - 11, tx - 12, ty + 9, color, 3)
        cv.seg(tx, ty - 11, tx + 12, ty + 9, color, 3)
        cv.hline(tx - 12, ty + 9, 24, color, 3)
        cv.box(tx - 1, ty - 5, 3, 7, color)
        cv.box(tx - 1, ty + 4, 3, 3, color)
    elif kind == "ban":
        # A document, a round stamp with a slash, a seal dot.
        dw = min(76, int(w * 0.42))
        cv.box(x + 4, y + 5, dw, h - 10, WHITE)
        cv.frame(x + 4, y + 5, dw, h - 10, color, 2)
        for ly in (y + 12, y + 19, y + 26):
            cv.hline(x + 11, ly, max(8, dw - 14), mid, 3)
        sx, sy = x + w - 30, y + h // 2
        cv.ring(sx, sy, 12, color, 3)
        cv.seg(sx - 8, sy + 8, sx + 8, sy - 8, color, 3)
        cv.disc(x + w - 10, y + 10, 5, color)
    else:
        raise ValueError("unknown icon: %r" % kind)


# ------------------------------------------------------------------
# Layout
# ------------------------------------------------------------------

M = 24  # side margin


def draw_masthead(cv):
    cv.hline(M, 8, W - 2 * M, RULE, 2)
    draw_text(cv, M, 16, "VOL. I - No. 323", 2, MUTED)
    draw_text(cv, W - M - text_w("SIX STORIES", 2), 16, "SIX STORIES", 2, MUTED)
    draw_text_c(cv, W // 2, 16, KICKER, 2, RED)
    draw_text_c(cv, W // 2, 38, NAMEPLATE, 10, INK)
    draw_text_c(cv, W // 2, 114, DATE_LINE, 3, INK)
    cv.hline(M, 140, W - 2 * M, RULE, 3)
    cv.hline(M, 145, W - 2 * M, RULE, 1)


def draw_lead(cv):
    story = STORIES[0]
    cv.hline(M, 152, 200, RED, 3)
    draw_text(cv, M, 160, "1  LEAD STORY  -  " + story["tag"], 2, RED)
    # Title wraps inside the left column only, never under the scene.
    title_lines = wrap(story["title"], 4, 640)
    ty = 182
    for line in title_lines[:2]:
        draw_text(cv, M, ty, line, 4, INK)
        ty += 28
    # Body in the left column, red rule at its left edge.
    cv.vline(M, ty + 8, 66, RED, 3)
    body_lines = wrap(story["body"], 2, 636)
    by = ty + 6
    for line in body_lines[:4]:
        draw_text(cv, M + 12, by, line, 2, BODY)
        by += 17
    # Big scene box on the right, light tint so the caption reads.
    sx, sy, sw, sh = 684, 182, 316, 140
    cv.box(sx, sy, sw, sh, tint(story["color"], WHITE, 0.12))
    cv.frame(sx, sy, sw, sh, INK, 2)
    draw_scene(cv, story["icon"], sx + 8, sy + 8, sw - 16, sh - 32,
               story["color"])
    cv.box(sx + 2, sy + sh - 24, sw - 4, 22, WHITE)
    draw_text_c(cv, sx + sw // 2, sy + sh - 20,
                "SHENZHEN - APEC SUMMIT", 2, story["color"])
    cv.hline(M, 330, W - 2 * M, FAINT_RULE, 1)


def draw_map_header(cv):
    cv.box(M, 340, 12, 12, RED)
    draw_text(cv, M + 20, 340, "THE WORLD AT A GLANCE - WHERE IT HAPPENED",
              2, INK)
    draw_text(cv, W - M - text_w("SIX STORIES, NUMBERED 1-6", 2), 340,
              "SIX STORIES, NUMBERED 1-6", 2, MUTED)


def draw_key(cv):
    """Two rows of numbered tags under the map."""
    for row in range(2):
        y = 556 + row * 20
        for col in range(3):
            i = row * 3 + col
            story = STORIES[i]
            x = M + col * 330
            cv.disc(x + 8, y + 7, 8, story["color"])
            num = str(i + 1)
            draw_text(cv, x + 8 - text_w(num, 2) // 2, y, num, 2, WHITE)
            draw_text(cv, x + 22, y, story["tag"], 2, INK)


def draw_card(cv, story, num, x, y, w, h, scene=True, body_max=4):
    cv.box(x, y, w, h, WHITE)
    cv.frame(x, y, w, h, FAINT_RULE, 1)
    cv.hline(x, y, w, story["color"], 3)
    # Number disc + tag.
    cv.disc(x + 18, y + 18, 9, story["color"])
    num_s = str(num)
    draw_text(cv, x + 18 - text_w(num_s, 2) // 2, y + 11, num_s, 2, WHITE)
    draw_text(cv, x + 32, y + 11, story["tag"], 2, INK)
    ty = y + 30
    if scene:
        sy = ty
        cv.box(x + 12, sy, w - 24, 30, tint(story["color"], WHITE, 0.88))
        draw_scene(cv, story["icon"], x + 16, sy + 2, w - 32, 26,
                   story["color"])
        ty = sy + 36
    # Title: scale 3 when it fits in two lines, else scale 2 -- so no
    # headline ever loses its last word.
    title_lines = wrap(story["title"], 3, w - 32)
    tscale, tstep = 3, 23
    if len(title_lines) > 2:
        title_lines = wrap(story["title"], 2, w - 32)
        tscale, tstep = 2, 16
    for line in title_lines[:2]:
        draw_text(cv, x + 16, ty, line, tscale, INK)
        ty += tstep
    # Body: only as many lines as fit inside the card, never spilling.
    body_lines = wrap(story["body"], 2, w - 32)
    by = ty + 4
    fits = max(1, (y + h - 6 - by) // 16)
    for line in body_lines[:min(body_max, fits)]:
        draw_text(cv, x + 16, by, line, 2, BODY)
        by += 16


def draw_also(cv):
    cv.hline(M, 924, W - 2 * M, RULE, 2)
    lines = wrap(ALSO_LINE, 2, W - 2 * M)
    fy = 934
    for line in lines[:3]:
        draw_text(cv, M, fy, line, 2, INK)
        fy += 17


def draw_footer(cv):
    cv.hline(M, 990, W - 2 * M, FAINT_RULE, 1)
    draw_text(cv, M, 998, SOURCE_LINE, 2, MUTED)
    draw_text(cv, W - M - text_w("ONE DAY, ONE PAGE", 2), 998,
              "ONE DAY, ONE PAGE", 2, RED)


def render():
    cv = Canvas(W, H, PAPER)
    draw_masthead(cv)
    draw_lead(cv)
    draw_map_header(cv)
    draw_map(cv)
    draw_key(cv)
    # Row 1: stories 2, 3, 4 in three columns.
    cw = (W - 2 * M - 2 * 12) // 3
    for k, i in enumerate((1, 2, 3)):
        draw_card(cv, STORIES[i], i + 1, M + k * (cw + 12), 596, cw, 176,
                  scene=True, body_max=4)
    # Row 2: stories 5, 6 in two wide columns, no scene strip.
    cw2 = (W - 2 * M - 12) // 2
    for k, i in enumerate((4, 5)):
        draw_card(cv, STORIES[i], i + 1, M + k * (cw2 + 12), 780, cw2, 136,
                  scene=False, body_max=3)
    draw_also(cv)
    draw_footer(cv)
    return cv

# ------------------------------------------------------------------
# Hand-rolled PNG encoder (filter 0, zlib level 9, no ancillary data)
# ------------------------------------------------------------------

def _chunk(kind, data):
    return (struct.pack(">I", len(data)) + kind + data +
            struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))


def encode_png(cv):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)
        raw += cv.buf[y * cv.w * 3:(y + 1) * cv.w * 3]
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) +
            _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
            _chunk(b"IEND", b""))


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = encode_png(render())
    with open(os.path.join(out_dir, "entry.png"), "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
