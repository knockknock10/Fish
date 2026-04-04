# ═══════════════════════════════════════════════════════════════
#  GILBERT v4.0  —  fish.py
#  GilbertFish: movement, CV detection, capture, storage, HUD
# ═══════════════════════════════════════════════════════════════

import pygame
import math
import random
from config import (
    WIDTH, HEIGHT, FPS,
    FISH_SIZE, FISH_CAPACITY,
    FISH_SPEED_SEARCH, FISH_SPEED_TARGET,
    FISH_TURN_RATE, FISH_DETECT_RADIUS, BOUNDARY_MARGIN,
    FISH_BODY, FISH_DARK, FISH_BELLY, FISH_ACCENT, FISH_STRIPE,
    FISH_EYE, FISH_PUPIL, FISH_MOUTH, FIN_COL, TAIL_COL,
    HUD_BG, HUD_TEXT, HUD_ACCENT, HUD_WARN, CV_GREEN,
)
from particles import Particle

# ─────────────────────────────────────────────────────────────
#  FONT HELPERS  (module-level, initialised once)
# ─────────────────────────────────────────────────────────────
_fonts_ready = False
FONT_SM = FONT_MD = FONT_LG = FONT_TI = None

def _init_fonts():
    global _fonts_ready, FONT_SM, FONT_MD, FONT_LG, FONT_TI
    if _fonts_ready:
        return
    try:
        FONT_SM = pygame.font.SysFont("consolas", 13)
        FONT_MD = pygame.font.SysFont("consolas", 15, bold=True)
        FONT_LG = pygame.font.SysFont("consolas", 21, bold=True)
        FONT_TI = pygame.font.SysFont("consolas", 11)
    except Exception:
        FONT_SM = pygame.font.Font(None, 14)
        FONT_MD = pygame.font.Font(None, 17)
        FONT_LG = pygame.font.Font(None, 23)
        FONT_TI = pygame.font.Font(None, 12)
    _fonts_ready = True


def _txt(surf, text, font, col, x, y):
    surf.blit(font.render(text, True, (0,0,0)), (x+1, y+1))
    surf.blit(font.render(text, True, col), (x, y))


# ─────────────────────────────────────────────────────────────
#  FULL-ALERT BANNER
# ─────────────────────────────────────────────────────────────
class FullAlert:
    """Animated 'STORAGE FULL' warning banner."""
    def __init__(self):
        self.timer    = 0          # counts up while fish is FULL
        self.flash_t  = 0.0

    def update(self, is_full: bool, dt: float):
        if is_full:
            self.timer  += 1
            self.flash_t += dt
        else:
            self.timer   = 0
            self.flash_t = 0.0

    def draw(self, surf):
        if self.timer == 0:
            return
        _init_fonts()
        # pulsing alpha
        alpha = int(180 + 70 * math.sin(self.flash_t * 5))
        alpha = max(0, min(255, alpha))

        bw, bh = 520, 52
        bx     = WIDTH//2 - bw//2
        by     = 22

        bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
        pygame.draw.rect(bg, (8, 18, 36, min(220, alpha)), (0,0,bw,bh), border_radius=10)
        pygame.draw.rect(bg, (255, 80, 40, min(200, alpha)), (0,0,bw,bh), 2, border_radius=10)
        surf.blit(bg, (bx, by))

        line1 = FONT_LG.render("⚠  STORAGE FULL  —  CAPACITY REACHED", True, (255, 110, 60))
        line2 = FONT_TI.render("Fish surfacing to standby mode  •  throw more plastic to resume", True, (200,180,160))
        surf.blit(line1, (WIDTH//2 - line1.get_width()//2, by+5))
        surf.blit(line2, (WIDTH//2 - line2.get_width()//2, by+30))


# ─────────────────────────────────────────────────────────────
#  GILBERT FISH
# ─────────────────────────────────────────────────────────────
class GilbertFish:

    # ── sizes pulled from config ──
    FS       = FISH_SIZE
    INTAKE_R = max(26, FISH_SIZE // 3)   # wider mouth capture zone
    DETECT_R = FISH_DETECT_RADIUS
    DOT_THRESH = -0.20         # ~100° half-cone — wider so fish keeps sight during turns

    def __init__(self, river_y: int):
        _init_fonts()
        self.river_y  = river_y
        self.river_h  = HEIGHT - river_y

        # position
        self.x = float(WIDTH // 2)
        self.y = float(river_y + self.river_h // 2)

        # ── ANGLE SYSTEM (THE FIX) ──────────────────────────
        # angle      = current heading (radians, pygame coords: right=0, down=π/2)
        # want_angle = where we WANT to go (set by logic each frame)
        # We lerp angle → want_angle by FISH_TURN_RATE per frame.
        # This prevents the spinning bug caused by rapid tgt_angle flips.
        self.angle      = 0.0
        self.want_angle = 0.0

        self.speed    = FISH_SPEED_SEARCH
        self.mode     = "SEARCH"   # SEARCH | TARGET | SURFACE | FULL_IDLE
        self.target   = None       # Plastic | None

        self.storage   : list = []
        self.particles : list[Particle] = []
        self.target_fail = 0      # frames spent chasing current target

        # animation phases
        self.tail_ph  = 0.0
        self.fin_ph   = 0.0
        self.cap_flash= 0
        self.depth_off= 0.0
        self.depth_dir= 1

        # wander
        self.wander_cd = 0

        # stats
        self.total_cap = 0
        self.session_t = 0

        # CV readouts
        self.cv_scanned  = 0
        self.cv_detected = 0
        self.cv_lock     = False

        # FULL behaviour
        self.full_alert = FullAlert()
        self._surface_target_y = river_y + 30   # y to rise to when FULL

    # ── FORWARD VISION CONE ──────────────────────────────────
    def _detect(self, plastics):
        fx = math.cos(self.angle)
        fy = math.sin(self.angle)
        best, best_d = None, 1e9
        self.cv_scanned  = 0
        self.cv_detected = 0

        for p in plastics:
            if p.captured or not p.alive:
                continue
            self.cv_scanned += 1
            dx   = p.x - self.x
            dy   = p.y - self.y
            dist = math.hypot(dx, dy)
            if dist > self.DETECT_R:
                continue
            dot = (dx*fx + dy*fy) / (dist + 1e-6)
            if dot < self.DOT_THRESH:
                continue
            self.cv_detected += 1
            p.detected = True
            if dist < best_d:
                best_d = dist
                best   = p

        self.cv_lock = best is not None
        return best

    # ── SMOOTH ANGLE UPDATE ───────────────────────────────────
    def _turn_toward(self, target_angle: float):
        """Nudge self.angle toward target_angle using FISH_TURN_RATE.
        Uses shortest path (handles the ±π wraparound).
        This is the core fix for the mad-spinning bug."""
        diff        = (target_angle - self.angle + math.pi) % (2*math.pi) - math.pi
        self.angle += diff * FISH_TURN_RATE
        # keep angle in [0, 2π)
        self.angle %= (2 * math.pi)

    # ── BOUNDARY PUSH ────────────────────────────────────────
    def _apply_boundary(self):
        """
        Hard steering away from walls. Directly overwrites want_angle
        with increasing authority the closer we get to a wall.
        This BEATS target-chase so the fish never pins to a wall.
        """
        margin = BOUNDARY_MARGIN
        x, y   = self.x, self.y
        top    = self.river_y + self.FS * 0.7
        bot    = HEIGHT       - self.FS * 0.7

        # Compute per-wall urgency (0 = outside margin, 1 = at wall)
        push_r = max(0.0, (margin - x)           / margin)   # need to go right
        push_l = max(0.0, (x - (WIDTH - margin)) / margin)   # need to go left
        push_d = max(0.0, (top - y)              / margin)   # need to go down
        push_u = max(0.0, (y - bot)              / margin)   # need to go up

        strongest = max(push_r, push_l, push_d, push_u)
        if strongest <= 0:
            return   # nowhere near a wall

        # Build escape vector by summing wall pushes
        ex, ey = 0.0, 0.0
        if push_r > 0: ex += push_r
        if push_l > 0: ex -= push_l
        if push_d > 0: ey += push_d
        if push_u > 0: ey -= push_u

        escape_angle = math.atan2(ey, ex)

        # Blend strength: soft at margin edge, FULL takeover near wall
        blend = min(strongest * 3.0, 1.0)
        diff  = (escape_angle - self.want_angle + math.pi) % (2*math.pi) - math.pi
        self.want_angle += diff * blend

        # At extreme closeness raise turn rate temporarily
        if strongest > 0.6:
            self._turn_toward(self.want_angle)   # extra turn step

    # ── CAPTURE ATTEMPT ──────────────────────────────────────
    def _try_capture(self, plastic):
        mx        = self.x + math.cos(self.angle) * self.FS * 0.82
        my        = self.y + math.sin(self.angle) * self.FS * 0.82
        mouth_d   = math.hypot(plastic.x - mx,      plastic.y - my)
        body_d    = math.hypot(plastic.x - self.x,  plastic.y - self.y)
        if mouth_d < self.INTAKE_R or body_d < self.FS * 0.55:
            plastic.captured = True
            plastic.alive    = False
            self.storage.append(plastic)
            self.total_cap  += 1
            self.cap_flash   = 22
            for _ in range(26):
                self.particles.append(Particle(mx, my, "burst"))
            self.target      = None
            self.target_fail = 0
            self.mode        = "SEARCH"
            self.speed       = FISH_SPEED_SEARCH

    # ── WANDER ───────────────────────────────────────────────
    def _wander(self):
        self.wander_cd -= 1
        if self.wander_cd <= 0:
            # centre bias keeps fish in mid-river, not stuck at edges
            cx_bias = (WIDTH / 2 - self.x) * 0.0012
            cy_bias = (self.river_y + self.river_h / 2 - self.y) * 0.0012
            self.want_angle = (self.angle
                               + random.uniform(-0.75, 0.75)
                               + cx_bias + cy_bias)
            self.wander_cd = random.randint(55, 120)
        self.speed = FISH_SPEED_SEARCH

    # ── MAIN UPDATE ──────────────────────────────────────────
    def update(self, plastics, dt: float, t: float):
        self.session_t += 1
        self.tail_ph   += 0.18
        self.fin_ph    += 0.12

        # depth oscillation (gentle bobbing)
        self.depth_off += 0.007 * self.depth_dir
        if abs(self.depth_off) > 5:
            self.depth_dir *= -1

        # ── FULL check ─────────────────────────────────────
        is_full = len(self.storage) >= FISH_CAPACITY
        self.full_alert.update(is_full, dt)

        if is_full and self.mode not in ("SURFACE", "FULL_IDLE"):
            self.target      = None
            self.target_fail = 0
            self.mode        = "SURFACE"

        # ── MODE FSM ───────────────────────────────────────
        if self.mode == "SEARCH":
            found = self._detect(plastics)
            if found:
                self.target      = found
                self.target_fail = 0
                self.mode        = "TARGET"
                self.speed       = FISH_SPEED_TARGET
            else:
                self._wander()

        elif self.mode == "TARGET":
            # ── Target gone? → back to SEARCH ──────────────
            if self.target is None or self.target.captured or not self.target.alive:
                self.target      = None
                self.target_fail = 0
                self.mode        = "SEARCH"
                self.speed       = FISH_SPEED_SEARCH

            else:
                dx   = self.target.x - self.x
                dy   = self.target.y - self.y
                dist = math.hypot(dx, dy)

                # ── GIVE-UP TIMER ─────────────────────────
                # If we've been chasing the same piece too long without
                # capturing (e.g. near-wall orbit), abandon and pick next.
                self.target_fail += 1
                if self.target_fail > 300:       # ~5 seconds at 60fps
                    self.target.detected = False
                    self.target      = None
                    self.target_fail = 0
                    self.mode        = "SEARCH"
                    self.speed       = FISH_SPEED_SEARCH
                else:
                    # Steer toward plastic
                    self.want_angle = math.atan2(dy, dx)

                    # Slow down as we get very close (prevent overshooting)
                    if dist < self.FS * 1.5:
                        self.speed = max(0.8, FISH_SPEED_TARGET * (dist / (self.FS * 1.5)))
                    else:
                        self.speed = FISH_SPEED_TARGET

                    # Pull plastic toward mouth
                    mx  = self.x + math.cos(self.angle) * self.FS * 0.82
                    my  = self.y + math.sin(self.angle) * self.FS * 0.82
                    pdx = self.target.x - mx
                    pdy = self.target.y - my
                    pd  = math.hypot(pdx, pdy)
                    if pd < self.FS * 3.5:
                        pull = 0.60 * (1 - pd / (self.FS * 3.5 + 1))
                        self.target.attract_vx += (-pdx / (pd + 1)) * pull
                        self.target.attract_vy += (-pdy / (pd + 1)) * pull

                    # Try to eat it
                    self._try_capture(self.target)

                    # Keep detection overlay live
                    self._detect(plastics)

        elif self.mode == "SURFACE":
            self._detect(plastics)
            target_y = self._surface_target_y
            dy       = target_y - self.y
            if abs(dy) > 4:
                self.want_angle = math.atan2(dy, math.cos(self.angle) * 4)
                self.speed      = FISH_SPEED_SEARCH * 0.8
            else:
                self.y     = float(target_y)
                self.speed = 0.5
                self.wander_cd -= 1
                if self.wander_cd <= 0:
                    self.want_angle = random.choice([0.0, math.pi])
                    self.wander_cd  = random.randint(90, 180)
                self.mode = "FULL_IDLE"

        elif self.mode == "FULL_IDLE":
            self._detect(plastics)
            self.speed = 0.6
            self.wander_cd -= 1
            if self.wander_cd <= 0:
                self.want_angle = random.choice([0.0, math.pi])
                self.wander_cd  = random.randint(90, 200)
            if self.y > self._surface_target_y + 10:
                self.want_angle = math.atan2(-1, math.cos(self.angle))

        # ── BOUNDARY — applied AFTER mode logic so walls always win ──
        self._apply_boundary()

        # ── SMOOTH TURN toward want_angle ─────────────────
        self._turn_toward(self.want_angle)

        # ── MOVE ──────────────────────────────────────────
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed + self.depth_off * 0.03

        # Hard clamp as absolute last resort
        self.x = max(self.FS * 0.7, min(WIDTH  - self.FS * 0.7, self.x))
        self.y = max(self.river_y + 20, min(HEIGHT - 20, self.y))

        # ── BUBBLES ───────────────────────────────────────
        if random.random() < 0.22:
            self.particles.append(Particle(
                self.x - math.cos(self.angle)*self.FS*0.88,
                self.y - math.sin(self.angle)*self.FS*0.88,
                "bubble"
            ))

        # ── PARTICLE CLEANUP ──────────────────────────────
        self.particles = [p for p in self.particles if p.life > 0]
        for p in self.particles:
            p.update()

        if self.cap_flash > 0:
            self.cap_flash -= 1

    # ── DRAW FISH ─────────────────────────────────────────────
    def draw(self, surf):
        for p in self.particles:
            p.draw(surf)

        fs  = self.FS
        ang = self.angle
        ca, sa   = math.cos(ang), math.sin(ang)
        px, py   = int(self.x), int(self.y)
        pa       = ang + math.pi/2
        cpa, spa = math.cos(pa), math.sin(pa)

        # ── TAIL ──────────────────────────────────────────
        sw    = math.sin(self.tail_ph) * 0.42
        tb_bx = px - ca * fs*0.56
        tb_by = py - sa * fs*0.56
        sa2   = ang + math.pi + sw
        ttx   = tb_bx + math.cos(sa2)*fs*0.68
        tty   = tb_by + math.sin(sa2)*fs*0.68
        t1    = (ttx + math.cos(sa2+0.46)*fs*0.57, tty + math.sin(sa2+0.46)*fs*0.57)
        t2    = (ttx + math.cos(sa2-0.46)*fs*0.57, tty + math.sin(sa2-0.46)*fs*0.57)
        ub    = (tb_bx+cpa*fs*0.35, tb_by+spa*fs*0.35)
        lb    = (tb_bx-cpa*fs*0.35, tb_by-spa*fs*0.35)
        ts    = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(ts, (*TAIL_COL,224), [ub, lb, t2, (ttx,tty), t1])
        pygame.draw.polygon(ts, (*FISH_ACCENT,68), [ub,(ttx,tty),t1])
        surf.blit(ts, (0,0))

        # ── DORSAL FIN ────────────────────────────────────
        ds  = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        d1  = (px-ca*fs*0.11+cpa*fs*0.35, py-sa*fs*0.11+spa*fs*0.35)
        d2  = (px+ca*fs*0.25+cpa*fs*0.34, py+sa*fs*0.25+spa*fs*0.34)
        dt2 = (px+ca*fs*0.05+cpa*fs*0.69, py+sa*fs*0.05+spa*fs*0.69)
        pygame.draw.polygon(ds, (*FIN_COL,182), [d1,d2,dt2])
        pygame.draw.polygon(ds, (*FISH_ACCENT,52), [d1,d2,dt2], 2)
        surf.blit(ds, (0,0))

        # ── PECTORAL FINS ─────────────────────────────────
        ff  = math.sin(self.fin_ph*1.3)*0.21
        ps2 = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for sign in (1,-1):
            fa  = ang + sign*(math.pi/2+ff)
            fp  = (px+ca*fs*0.13+cpa*sign*fs*0.25,
                   py+sa*fs*0.13+spa*sign*fs*0.25)
            fpt = (fp[0]+math.cos(fa)*fs*0.43,
                   fp[1]+math.sin(fa)*fs*0.43)
            fpb = (fp[0]-ca*fs*0.29, fp[1]-sa*fs*0.29)
            pygame.draw.polygon(ps2, (*FIN_COL,170), [fp,fpt,fpb])
        surf.blit(ps2, (0,0))

        # ── BODY ──────────────────────────────────────────
        bw = fs*2; bh = int(fs*0.68)
        bs = pygame.Surface((bw+20, bh+20), pygame.SRCALPHA)
        bx2= bw//2+10; by2= bh//2+10
        # shadow
        pygame.draw.ellipse(bs,(0,28,58,50),(bx2-bw//2+5,by2-bh//2+7,bw,bh))
        # base
        pygame.draw.ellipse(bs,FISH_DARK,(bx2-bw//2,by2-bh//2,bw,bh))
        # top sheen
        sh = pygame.Surface((bw,bh), pygame.SRCALPHA)
        for i in range(bh//2):
            a2 = int(88*(1-i/(bh//2+1)))
            pygame.draw.line(sh,(*FISH_ACCENT,a2),(0,i),(bw,i))
        bs.blit(sh,(bx2-bw//2,by2-bh//2),special_flags=pygame.BLEND_RGBA_ADD)
        # belly
        pygame.draw.ellipse(bs,FISH_BELLY,(bx2-bw//2+12,by2,bw-24,bh//3))
        # stripes
        for i in range(3):
            sx2 = bx2-bw//2+bw*(i+1)//4
            pygame.draw.line(bs,(*FISH_STRIPE,90),(sx2,by2-bh//2+6),(sx2,by2+bh//2-6),1)
        pygame.draw.line(bs,(*FISH_ACCENT,42),(bx2-bw//2+5,by2),(bx2+bw//2-5,by2),1)
        # capture flash
        if self.cap_flash > 0:
            fa3 = int(172*self.cap_flash/22)
            pygame.draw.ellipse(bs,(0,255,200,fa3),(bx2-bw//2,by2-bh//2,bw,bh),3)
        # stored waste dots
        n = len(self.storage)
        for i in range(min(n, FISH_CAPACITY)):
            di_x = bx2-bw//4+(i%6)*(bw//7+2)
            di_y = by2+bh//5+(i//6)*8
            # dots pulse orange→red when full
            dot_col = (255,60,40,215) if n>=FISH_CAPACITY else (255,155,36,210)
            pygame.draw.circle(bs, dot_col, (int(di_x),int(di_y)), 3)
        br = pygame.transform.rotate(bs,-math.degrees(ang))
        surf.blit(br, br.get_rect(center=(px,py)))

        # ── HEAD / SNOUT ──────────────────────────────────
        hs  = pygame.Surface((fs*2+4,fs*2+4), pygame.SRCALPHA)
        hc  = fs+2
        snout = [
            (hc+fs*0.74, hc),
            (hc+fs*0.36, hc-fs*0.30),
            (hc+fs*0.28, hc-fs*0.17),
            (hc+fs*0.28, hc+fs*0.17),
            (hc+fs*0.36, hc+fs*0.30),
        ]
        pygame.draw.polygon(hs, FISH_BODY, snout)
        pygame.draw.polygon(hs, FISH_ACCENT, snout,1)
        mo = [
            (hc+fs*0.74, hc+fs*0.05),
            (hc+fs*0.56, hc+fs*0.14),
            (hc+fs*0.55, hc-fs*0.04),
        ]
        pygame.draw.polygon(hs, FISH_MOUTH, mo)
        ex_ = int(hc+fs*0.44); ey_ = int(hc-fs*0.11)
        pygame.draw.circle(hs,FISH_EYE,(ex_,ey_),9)
        pygame.draw.circle(hs,FISH_PUPIL,(ex_+1,ey_-1),3)
        pygame.draw.circle(hs,(95,195,255,165),(ex_+2,ey_-2),2)
        hr = pygame.transform.rotate(hs,-math.degrees(ang))
        surf.blit(hr, hr.get_rect(center=(px,py)))

    # ── CV / DEBUG OVERLAY ─────────────────────────────────────
    def draw_debug(self, surf, t: float):
        _init_fonts()
        ang = self.angle
        px, py = int(self.x), int(self.y)
        fs     = self.FS

        # detection cone fill
        cone_a = math.acos(max(-1.0,min(1.0, self.DOT_THRESH)))
        steps  = 48
        pts    = [(px,py)]
        for i in range(steps+1):
            a = ang - cone_a + (2*cone_a*i/steps)
            pts.append((px+math.cos(a)*self.DETECT_R,
                        py+math.sin(a)*self.DETECT_R))
        col = (0,255,120) if self.cv_lock else (0,200,150)
        cone_s = pygame.Surface((WIDTH,HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(cone_s, (*col,14), pts)
        pygame.draw.lines(cone_s, (*col,50), False, pts[1:], 1)
        # animated sweep
        for i in range(4):
            sa3 = ang - cone_a + (2*cone_a*(i*0.25 + (t*0.4 % 0.25)))
            ex3 = px+math.cos(sa3)*self.DETECT_R
            ey3 = py+math.sin(sa3)*self.DETECT_R
            pygame.draw.line(cone_s,(*col,28),(px,py),(int(ex3),int(ey3)),1)
        surf.blit(cone_s,(0,0))

        # intake circle
        mx3 = px+int(math.cos(ang)*fs*0.82)
        my3 = py+int(math.sin(ang)*fs*0.82)
        pulse = int(4*math.sin(t*7))
        in_s  = pygame.Surface((WIDTH,HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(in_s,(255,60,60,62),(mx3,my3),self.INTAKE_R+pulse)
        pygame.draw.circle(in_s,(255,60,60,182),(mx3,my3),self.INTAKE_R+pulse,2)
        surf.blit(in_s,(0,0))

        # horizontal scan line
        scan_y = self.river_y + int((t*55) % self.river_h)
        ss     = pygame.Surface((WIDTH,2), pygame.SRCALPHA)
        ss.fill((0,255,120,11))
        surf.blit(ss,(0,scan_y))

        # CV readout panel (top-right)
        cpw,cph = 222,92
        cp = pygame.Surface((cpw,cph), pygame.SRCALPHA)
        pygame.draw.rect(cp,(4,14,28,212),(0,0,cpw,cph),border_radius=8)
        pygame.draw.rect(cp,(0,255,120,58),(0,0,cpw,cph),1,border_radius=8)
        surf.blit(cp,(WIDTH-cpw-14,14))
        lx = WIDTH-cpw-2
        _txt(surf,"COMPUTER VISION",    FONT_TI,(0,255,120),lx,20)
        _txt(surf,f"SCAN  RADIUS : {self.DETECT_R}px",FONT_TI,(120,220,180),lx,34)
        _txt(surf,f"OBJECTS SEEN : {self.cv_scanned}",  FONT_TI,(120,220,180),lx,46)
        _txt(surf,f"IN CONE      : {self.cv_detected}",  FONT_TI,(120,220,180),lx,58)
        lk_col = (0,255,120) if self.cv_lock else (120,120,120)
        _txt(surf,f"TARGET LOCK  : {'YES' if self.cv_lock else 'NO'}",
             FONT_TI,lk_col,lx,70)
        _txt(surf,f"INTAKE ZONE  : {self.INTAKE_R}px",  FONT_TI,(120,220,180),lx,82)

    # ── HUD ────────────────────────────────────────────────────
    def draw_hud(self, surf, alive_count: int, t: float):
        _init_fonts()
        # ── background panel ─────────────────────────────
        pw, ph = 316, 252
        hud = pygame.Surface((pw,ph), pygame.SRCALPHA)
        pygame.draw.rect(hud,(*HUD_BG,212),(0,0,pw,ph),border_radius=12)
        pygame.draw.rect(hud,(*HUD_ACCENT,82),(0,0,pw,ph),1,border_radius=12)
        surf.blit(hud,(14,14))

        lx,ly = 26,22
        _txt(surf,"GILBERT  v4.0",         FONT_LG,HUD_ACCENT,lx,ly)
        _txt(surf,"BIO-ROBOTIC FISH SYSTEM",FONT_SM,(112,192,172),lx,ly+26)
        pygame.draw.line(surf,(*HUD_ACCENT,72),(lx,ly+43),(lx+282,ly+43),1)

        ly += 55
        mc = {"SEARCH":(92,215,172),"TARGET":(252,196,38),
              "SURFACE":(80,160,255),"FULL_IDLE":(255,95,68)
              }.get(self.mode,(192,192,192))
        _txt(surf,f"MODE     : {self.mode}",      FONT_MD,mc,      lx,ly)
        ly+=22
        _txt(surf,f"STORAGE  : {len(self.storage)}/{FISH_CAPACITY}", FONT_MD,HUD_TEXT,lx,ly)
        ly+=22
        _txt(surf,f"CAPTURED : {self.total_cap}", FONT_MD,HUD_TEXT,lx,ly)
        ly+=22
        _txt(surf,f"FLOATING : {alive_count}",    FONT_MD,HUD_TEXT,lx,ly)
        ly+=22
        _txt(surf,f"SPEED    : {self.speed:.1f} m/s",FONT_MD,HUD_TEXT,lx,ly)
        ly+=22
        mi=(self.session_t//(FPS*60)); se=(self.session_t//FPS)%60
        _txt(surf,f"RUNTIME  : {mi:02d}:{se:02d}",FONT_MD,HUD_TEXT,lx,ly)

        ly+=30
        _txt(surf,"STORAGE CAPACITY",FONT_TI,(112,192,172),lx,ly)
        ly+=14
        bw=282
        pygame.draw.rect(surf,(18,48,78),(lx,ly,bw,11),border_radius=5)
        fw = int(bw*len(self.storage)/max(1,FISH_CAPACITY))
        fc = (252,95,68) if len(self.storage)>=FISH_CAPACITY else HUD_ACCENT
        if fw>0:
            pygame.draw.rect(surf,fc,(lx,ly,fw,11),border_radius=5)
        pygame.draw.rect(surf,(*HUD_ACCENT,92),(lx,ly,bw,11),1,border_radius=5)

        # target tracking box
        if self.target and not self.target.captured:
            tx2,ty2 = int(self.target.x),int(self.target.y)
            ts2 = pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
            r2  = int(15+4*math.sin(t*5))
            for dx2,dy2 in [(-1,-1),(1,-1),(1,1),(-1,1)]:
                sx2=tx2+dx2*r2; sy2=ty2+dy2*r2
                pygame.draw.line(ts2,(252,196,38,218),(sx2,sy2),(sx2-dx2*8,sy2),2)
                pygame.draw.line(ts2,(252,196,38,218),(sx2,sy2),(sx2,sy2-dy2*8),2)
            pygame.draw.circle(ts2,(252,196,38,55),(tx2,ty2),r2,1)
            surf.blit(ts2,(0,0))

        # bottom watermark
        wm = FONT_SM.render(
            "GILBERT | Environmental Robotics  [ CLICK RIVER → throw plastic ]",
            True,(52,112,92))
        surf.blit(wm,(WIDTH//2-wm.get_width()//2,HEIGHT-22))