# ═══════════════════════════════════════════════════════════════
#  GILBERT v4.0  —  environment.py
#  River background: sky, hills, trees, bank, water, waves
# ═══════════════════════════════════════════════════════════════

import pygame
import math
import random
from config import (
    WIDTH, HEIGHT,
    SKY_TOP, SKY_BOT,
    BANK_TOP, BANK_MID, GRASS1, GRASS2, STONE1, STONE2,
    WATER_DEEP, WATER_SURF,
)

_tree_cache: dict = {}
_built = False


def _build_tree_cache():
    global _tree_cache, _built
    for tx in range(0, WIDTH, 34):
        rng = random.Random(tx * 31 + 7)
        _tree_cache[tx] = {
            "h":   rng.randint(28, 60),
            "cw":  rng.randint(24, 38),
            "ch":  rng.randint(18, 28),
            "col": (rng.randint(16,26), rng.randint(44,70), rng.randint(18,36)),
        }
    _built = True


def draw_environment(surf, t: float, wave_offsets: list, river_y: int):
    global _built
    if not _built:
        _build_tree_cache()

    river_h = HEIGHT - river_y

    # ── PRE-BAKED static layer (sky + land) ───────────────────
    # Sky gradient
    for y in range(river_y):
        ratio = y / river_y
        c = (
            int(SKY_TOP[0] + (SKY_BOT[0]-SKY_TOP[0])*ratio),
            int(SKY_TOP[1] + (SKY_BOT[1]-SKY_TOP[1])*ratio),
            int(SKY_TOP[2] + (SKY_BOT[2]-SKY_TOP[2])*ratio),
        )
        pygame.draw.line(surf, c, (0, y), (WIDTH, y))

    # Rolling hill silhouette (3 overlapping sine frequencies = organic)
    hill_pts = [(0, river_y)]
    for hx in range(0, WIDTH+6, 6):
        hy = river_y - 20 - int(
            14*math.sin(hx*0.0085 + 0.4) +
             9*math.sin(hx*0.018  + 1.1) +
             5*math.sin(hx*0.036  + 2.0)
        )
        hill_pts.append((hx, hy))
    hill_pts.append((WIDTH, river_y))
    pygame.draw.polygon(surf, (20, 48, 30), hill_pts)

    # Trees
    for tx, td in _tree_cache.items():
        # trunk
        pygame.draw.rect(surf, (26, 20, 12),
                         (tx + td["cw"]//2-2, river_y - td["h"], 4, td["h"]))
        # canopy dark
        pygame.draw.ellipse(surf, td["col"],
                            (tx, river_y-td["h"]-td["ch"], td["cw"], td["ch"]))
        # canopy highlight
        hc = (td["col"][0]+8, td["col"][1]+12, td["col"][2]+6)
        pygame.draw.ellipse(surf, hc,
                            (tx+3, river_y-td["h"]-td["ch"]+3,
                             td["cw"]-6, td["ch"]//2))

    # Riverbank pebbles (deterministic random so no flicker)
    for i in range(0, WIDTH, 20):
        rng = random.Random(i*19+5)
        sx  = i + rng.randint(0,16)
        sy  = river_y - rng.randint(2, 7)
        sw  = rng.randint(5, 13)
        sh  = rng.randint(3, 7)
        col = STONE1 if rng.random() > 0.5 else STONE2
        pygame.draw.ellipse(surf, col, (sx, sy, sw, sh))

    # Bank strips
    pygame.draw.rect(surf, BANK_TOP, (0, river_y-5,  WIDTH, 9))
    pygame.draw.rect(surf, GRASS1,   (0, river_y-16, WIDTH, 13))
    pygame.draw.rect(surf, GRASS2,   (0, river_y-27, WIDTH, 13))

    # ── WATER BODY (gradient) ─────────────────────────────────
    for y in range(river_y, HEIGHT):
        ratio = (y - river_y) / river_h
        # darker at bottom (depth illusion)
        c = (
            int(WATER_DEEP[0] + (WATER_SURF[0]-WATER_DEEP[0])*(1-ratio)*0.65),
            int(WATER_DEEP[1] + (WATER_SURF[1]-WATER_DEEP[1])*(1-ratio)*0.65),
            int(WATER_DEEP[2] + (WATER_SURF[2]-WATER_DEEP[2])*(1-ratio)*0.65),
        )
        pygame.draw.line(surf, c, (0, y), (WIDTH, y))

    # ── ANIMATED WAVE LINES ───────────────────────────────────
    ws = pygame.Surface((WIDTH, river_h), pygame.SRCALPHA)
    wave_defs = [
        # (y_fraction, scroll_speed, amplitude, color+alpha, line_width)
        (0.06, 0.50, 3.8, (75,175,235,38), 1),
        (0.14, 0.82, 4.6, (75,175,235,30), 1),
        (0.25, 1.10, 5.2, (75,175,235,24), 1),
        (0.37, 0.62, 4.0, (75,175,235,20), 1),
        (0.51, 0.92, 4.9, (75,175,235,16), 1),
        (0.66, 0.72, 3.5, (75,175,235,12), 1),
    ]
    for i, (frac, spd, amp, col, thick) in enumerate(wave_defs):
        base = river_h * frac
        pts  = []
        for x in range(0, WIDTH+4, 3):
            wy = (base
                  + math.sin(x*0.010 + t*spd + wave_offsets[i]) * amp
                  + math.sin(x*0.018 + t*spd*0.6 + wave_offsets[i]*1.3) * amp*0.38)
            pts.append((x, wy))
        if len(pts) >= 2:
            pygame.draw.lines(ws, col, False, pts, thick)

    # Light shimmer streaks (drift with time)
    for i in range(9):
        sx  = (int(t*36*((i%4)+1)) + i*137) % WIDTH
        sy  = int(river_h*0.04 + (i*51) % int(river_h*0.36))
        sw2 = 30 + (i*13)%42
        shim = pygame.Surface((sw2, 2), pygame.SRCALPHA)
        shim.fill((195, 228, 255, 26))
        ws.blit(shim, (sx, sy))

    surf.blit(ws, (0, river_y))

    # Bottom bank edge
    pygame.draw.rect(surf, BANK_MID, (0, HEIGHT-5, WIDTH, 5))
