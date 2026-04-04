#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════
#  GILBERT v4.0  —  main.py
#  Run this file to start the simulation.
#
#  Controls:
#    LEFT CLICK  → throw plastic into river
#    D           → toggle CV / debug overlay
#    R           → reset everything
#    ESC         → quit
# ═══════════════════════════════════════════════════════════════

import pygame
import math
import random
import sys

# ── LOCAL MODULES ───────────────────────────────────────────
from config      import WIDTH, HEIGHT, FPS, RIVER_TOP_RATIO, INITIAL_PLASTICS
from environment import draw_environment
from plastic     import Plastic, ThrownPlastic, set_river_y
from particles   import SplashParticle, Ripple
from fish        import GilbertFish

# ── PYGAME INIT ─────────────────────────────────────────────
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(
    "GILBERT v4.0 – Bio-Inspired Robotic Fish | Environmental AI System")
clock = pygame.time.Clock()

# ── RIVER GEOMETRY ──────────────────────────────────────────
RIVER_Y = int(HEIGHT * RIVER_TOP_RATIO)
set_river_y(RIVER_Y)     # tell plastic module where the river starts

# ── FONT for controls bar ────────────────────────────────────
try:
    FONT_SM = pygame.font.SysFont("consolas", 13)
except Exception:
    FONT_SM = pygame.font.Font(None, 14)

# ────────────────────────────────────────────────────────────
def make_wave_offsets():
    return [random.uniform(0, math.tau) for _ in range(6)]


def reset_sim():
    plastics     = [Plastic() for _ in range(INITIAL_PLASTICS)]
    thrown       = []
    splashes     = []
    ripples      = []
    fish         = GilbertFish(RIVER_Y)
    wave_offsets = make_wave_offsets()
    return plastics, thrown, splashes, ripples, fish, wave_offsets


# ────────────────────────────────────────────────────────────
def main():
    plastics, thrown, splashes, ripples, fish, wave_offsets = reset_sim()

    t          = 0.0
    running    = True
    show_debug = True
    respawn_cd = 0

    while running:
        dt = clock.tick(FPS) / 1000.0
        t += dt

        # ── EVENTS ──────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_d:
                    show_debug = not show_debug
                elif event.key == pygame.K_r:
                    (plastics, thrown, splashes,
                     ripples, fish, wave_offsets) = reset_sim()
                    t = 0.0

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                # clamp landing to river bounds
                land_x = max(22, min(WIDTH-22, mx))
                land_y = max(RIVER_Y+22, min(HEIGHT-20, my))
                thrown.append(ThrownPlastic(land_x, land_y))

        # ── UPDATE THROWN ARCS ──────────────────────────
        for th in thrown[:]:
            th.update()
            if th.done and not th.splashed:
                th.splashed = True
                lx, ly = th.tx, th.ty
                for _ in range(random.randint(10,18)):
                    splashes.append(SplashParticle(lx, ly))
                for _ in range(3):
                    ripples.append(Ripple(lx+random.uniform(-6,6),
                                         ly+random.uniform(-4,4)))
                plastics.append(Plastic(lx, ly))
                thrown.remove(th)

        # ── UPDATE SPLASHES / RIPPLES ────────────────────
        splashes = [s for s in splashes if s.life > 0]
        for s in splashes:
            s.update()
        ripples = [r for r in ripples if r.life > 0]
        for r in ripples:
            r.update()

        # ── RESPAWN if river almost empty ────────────────
        alive_count = sum(1 for p in plastics if p.alive and not p.captured)
        if alive_count < 5:
            respawn_cd += 1
            if respawn_cd > 90:
                plastics.append(Plastic())
                respawn_cd = 0

        # ── UPDATE PLASTICS + FISH ───────────────────────
        for p in plastics:
            p.update(t)
        fish.update(plastics, dt, t)

        # ── DRAW ────────────────────────────────────────
        draw_environment(screen, t, wave_offsets, RIVER_Y)

        for r in ripples:
            r.draw(screen)
        for s in splashes:
            s.draw(screen)
        for th in thrown:
            th.draw(screen)
        for p in plastics:
            p.draw(screen)

        if show_debug:
            fish.draw_debug(screen, t)

        fish.draw(screen)
        fish.draw_hud(screen, alive_count, t)

        # ── FULL ALERT BANNER ────────────────────────────
        fish.full_alert.draw(screen)

        # ── CONTROLS BAR ────────────────────────────────
        hint = FONT_SM.render(
            "  CLICK → throw plastic    [D] CV overlay    [R] reset    [ESC] quit  ",
            True, (72, 132, 112))
        hw  = hint.get_width()
        hbg = pygame.Surface((hw+8, 18), pygame.SRCALPHA)
        hbg.fill((4, 14, 28, 155))
        screen.blit(hbg, (WIDTH//2-hw//2-4, HEIGHT-19))
        screen.blit(hint, (WIDTH//2-hw//2,  HEIGHT-18))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
