# ═══════════════════════════════════════════════════════════════
#  GILBERT v4.0  —  particles.py
#  SplashParticle, Particle (bubble/burst), Ripple
# ═══════════════════════════════════════════════════════════════

import pygame
import math
import random


class SplashParticle:
    """Water droplets thrown up when plastic hits the river."""
    def __init__(self, x, y):
        a   = random.uniform(-math.pi, 0)       # upward half-circle
        spd = random.uniform(2.0, 5.5)
        self.x, self.y   = float(x), float(y)
        self.vx           = math.cos(a) * spd
        self.vy           = math.sin(a) * spd
        self.r            = random.randint(2, 5)
        self.life         = random.randint(20, 45)
        self.max_life     = self.life
        self.col          = random.choice([(180,225,255),(120,190,240),(220,240,255)])

    def update(self):
        self.vy  += 0.22        # gravity pulls back down
        self.x   += self.vx
        self.y   += self.vy
        self.life -= 1

    def draw(self, surf):
        a = int(200 * self.life / self.max_life)
        s = pygame.Surface((self.r*2+2, self.r*2+2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.col, a), (self.r+1, self.r+1), self.r)
        surf.blit(s, (int(self.x)-self.r-1, int(self.y)-self.r-1))


class Particle:
    """Bubble trail or capture-burst particle."""
    def __init__(self, x, y, ptype="bubble"):
        self.x, self.y = float(x), float(y)
        self.ptype     = ptype
        if ptype == "bubble":
            self.vx   = random.uniform(-0.4, 0.4)
            self.vy   = random.uniform(-1.6, -0.5)
            self.r    = random.randint(2, 5)
            self.life = random.randint(28, 68)
            self.col  = (175, 225, 255)
        else:                           # capture burst
            a         = random.uniform(0, math.tau)
            spd       = random.uniform(1.4, 4.2)
            self.vx   = math.cos(a) * spd
            self.vy   = math.sin(a) * spd
            self.r    = random.randint(2, 6)
            self.life = random.randint(14, 32)
            self.col  = random.choice([(0,218,196),(95,255,225),(252,196,56)])
        self.max_life = self.life

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.ptype == "bubble":
            self.vy *= 0.978
        else:
            self.vy += 0.11
        self.life -= 1

    def draw(self, surf):
        a = int(255 * self.life / self.max_life)
        s = pygame.Surface((self.r*2+2, self.r*2+2), pygame.SRCALPHA)
        if self.ptype == "bubble":
            pygame.draw.circle(s, (*self.col, a), (self.r+1,self.r+1), self.r, 1)
        else:
            pygame.draw.circle(s, (*self.col, a), (self.r+1,self.r+1), self.r)
        surf.blit(s, (int(self.x)-self.r-1, int(self.y)-self.r-1))


class Ripple:
    """Expanding elliptical ring on water surface."""
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.r         = 4.0
        self.life      = 55
        self.max_life  = 55

    def update(self):
        self.r   += 2.2
        self.life -= 1

    def draw(self, surf):
        a  = int(160 * self.life / self.max_life)
        rw = int(self.r * 2)
        rh = max(2, int(self.r * 0.45))
        s  = pygame.Surface((rw+4, rh+4), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (120, 200, 240, a), (2, 2, rw, rh), 2)
        surf.blit(s, (int(self.x)-rw//2-2, int(self.y)-rh//2-2))
