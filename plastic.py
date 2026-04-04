# ═══════════════════════════════════════════════════════════════
#  GILBERT v4.0  —  plastic.py
#  Plastic (floating waste) + ThrownPlastic (arc animation)
# ═══════════════════════════════════════════════════════════════

import pygame
import math
import random
from config import (
    WIDTH, HEIGHT, PLASTIC_COLS,
    PLASTIC_SIZE_MIN, PLASTIC_SIZE_MAX,
)

# River boundary — set after pygame init via set_river_y()
_RIVER_Y = 300


def set_river_y(ry: int):
    global _RIVER_Y
    _RIVER_Y = ry


# ─────────────────────────────────────────────────────────────
#  SHARED SHAPE RENDERER
# ─────────────────────────────────────────────────────────────
def draw_plastic_shape(surf, x, y, size, shape, color, angle):
    """Draw a plastic item at (x,y) with given rotation angle."""
    pad = size * 4 + 4
    s   = pygame.Surface((pad, pad), pygame.SRCALPHA)
    cx  = cy = pad // 2

    if shape == "bottle":
        pts = [
            (cx,           cy - size),
            (cx + size//2, cy - size//3),
            (cx + size//2, cy + size),
            (cx - size//2, cy + size),
            (cx - size//2, cy - size//3),
        ]
        pygame.draw.polygon(s, color, pts)
        pygame.draw.polygon(s, (255,255,255,55), pts, 1)
        pygame.draw.rect(s, (*color[:3],180),
                         (cx-size//4, cy-size-4, size//2, 5))
        pygame.draw.line(s,(255,255,255,70),
                         (cx-size//4,cy-size+2),(cx-size//4,cy),1)

    elif shape == "bag":
        pygame.draw.ellipse(s, color,
                            (cx-size, cy-size//2, size*2, size))
        pygame.draw.ellipse(s,(255,255,255,48),
                            (cx-size, cy-size//2, size*2, size),1)
        pygame.draw.line(s, color, (cx,cy-size//2),(cx,cy-size),2)

    elif shape == "fragment":
        rng = random.Random(int(size*100))   # deterministic shape
        pts = [(cx + math.cos(i*math.tau/5)*size*rng.uniform(0.55,1.0),
                cy + math.sin(i*math.tau/5)*size*rng.uniform(0.55,1.0))
               for i in range(5)]
        pygame.draw.polygon(s, color, pts)
        pygame.draw.polygon(s,(255,255,255,55), pts,1)

    else:  # cap
        pygame.draw.circle(s, color, (cx,cy), size)
        pygame.draw.circle(s,(255,255,255,75),(cx,cy),size,2)
        pygame.draw.circle(s,(*color[:3],115),
                           (cx-size//3,cy-size//3),max(2,size//3))

    rs = pygame.transform.rotate(s, math.degrees(angle))
    surf.blit(rs, rs.get_rect(center=(int(x),int(y))))


# ─────────────────────────────────────────────────────────────
#  FLOATING PLASTIC
# ─────────────────────────────────────────────────────────────
class Plastic:
    def __init__(self, x=None, y=None):
        ry = _RIVER_Y
        self.x    = float(x) if x is not None else random.uniform(60, WIDTH-60)
        self.y    = float(y) if y is not None else random.uniform(ry+20, HEIGHT-20)
        self.vx          = random.uniform(-0.35, -0.08)   # gentle downstream
        self.vy          = 0.0
        self.wave_offset = random.uniform(0, math.tau)
        self.wave_amp    = random.uniform(0.25, 0.70)
        self.wave_freq   = random.uniform(1.0, 2.2)
        self.size        = random.randint(PLASTIC_SIZE_MIN, PLASTIC_SIZE_MAX)
        self.shape       = random.choice(["bottle","bag","fragment","cap"])
        self.color       = random.choice(PLASTIC_COLS)
        self.angle       = random.uniform(0, math.tau)
        self.spin        = random.uniform(-0.012, 0.012)
        self.captured    = False
        self.attract_vx  = 0.0
        self.attract_vy  = 0.0
        self.alive       = True
        self.detected    = False    # flagged by fish CV each frame

    def update(self, t):
        if self.captured:
            return
        self.vy  = math.sin(t * self.wave_freq + self.wave_offset) * self.wave_amp
        self.x  += self.vx + self.attract_vx
        self.y  += self.vy + self.attract_vy
        self.angle += self.spin
        self.attract_vx *= 0.84
        self.attract_vy *= 0.84
        # wrap left → right
        if self.x < -40:
            self.x = WIDTH + 30
        ry = _RIVER_Y
        self.x = max(18, min(WIDTH-18, self.x))
        self.y = max(ry+10, min(HEIGHT-10, self.y))

    def draw(self, surf):
        if not self.alive:
            return
        draw_plastic_shape(surf, self.x, self.y,
                           self.size, self.shape, self.color, self.angle)
        # CV detection corner-tick overlay
        if self.detected:
            r  = self.size + 7
            ms = pygame.Surface((r*4, r*4), pygame.SRCALPHA)
            c  = r*2
            for dx, dy in [(-1,-1),(1,-1),(1,1),(-1,1)]:
                sx, sy = c+dx*r, c+dy*r
                pygame.draw.line(ms,(0,255,100,200),(sx,sy),(sx-dx*7,sy),2)
                pygame.draw.line(ms,(0,255,100,200),(sx,sy),(sx,sy-dy*7),2)
            surf.blit(ms, ms.get_rect(center=(int(self.x),int(self.y))))
            self.detected = False


# ─────────────────────────────────────────────────────────────
#  THROWN PLASTIC  (arc animation before landing)
# ─────────────────────────────────────────────────────────────
class ThrownPlastic:
    def __init__(self, target_x, target_y):
        ry = _RIVER_Y
        self.tx       = float(target_x)
        self.ty       = float(max(ry+20, min(HEIGHT-18, target_y)))
        self.start_x  = target_x + random.uniform(-45, 45)
        self.start_y  = ry - random.uniform(55, 125)
        self.progress = 0.0
        self.speed    = random.uniform(0.022, 0.038)
        self.arc_h    = random.uniform(65, 125)
        self.shape    = random.choice(["bottle","bag","fragment","cap"])
        self.color    = random.choice(PLASTIC_COLS)
        self.size     = random.randint(PLASTIC_SIZE_MIN, PLASTIC_SIZE_MAX)
        self.angle    = 0.0
        self.spin     = random.uniform(0.07, 0.20)
        self.done     = False
        self.splashed = False

    def update(self):
        self.progress = min(1.0, self.progress + self.speed)
        self.angle   += self.spin
        if self.progress >= 1.0:
            self.done = True

    @property
    def pos(self):
        p  = self.progress
        mx = (self.start_x + self.tx) / 2
        my = min(self.start_y, self.ty) - self.arc_h
        x  = (1-p)**2*self.start_x + 2*(1-p)*p*mx + p**2*self.tx
        y  = (1-p)**2*self.start_y + 2*(1-p)*p*my + p**2*self.ty
        return x, y

    def draw(self, surf):
        x, y = self.pos
        ry   = _RIVER_Y
        # soft shadow when over water
        if y > ry:
            shd = pygame.Surface((self.size*3, 5), pygame.SRCALPHA)
            shd.fill((0,20,40,55))
            surf.blit(shd, (int(x)-self.size, int(y)+3))
        draw_plastic_shape(surf, x, y,
                           self.size, self.shape, self.color, self.angle)
