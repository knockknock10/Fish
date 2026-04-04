# ═══════════════════════════════════════════════════════════════
#  GILBERT v4.0  —  config.py
#  All tunable parameters in one place.
#  Change values here; nothing else needs editing.
# ═══════════════════════════════════════════════════════════════

# ── WINDOW ──────────────────────────────────────────────────────
WIDTH  = 1280
HEIGHT = 720
FPS    = 60

# ── RIVER LAYOUT ────────────────────────────────────────────────
# RIVER_Y = top edge of water.  0.42 means water starts 42% down.
RIVER_TOP_RATIO = 0.42          # ← move river up/down (0.3 – 0.6)

# ── FISH ────────────────────────────────────────────────────────
FISH_SIZE     = 90              # ← half-body length px  (60–130)
FISH_CAPACITY = 12              # ← storage slots before FULL

FISH_SPEED_SEARCH = 1.4         # ← wander speed (px/frame)
FISH_SPEED_TARGET = 2.4         # ← chase speed  (px/frame)

# Turning smoothness: LOWER = smoother but slower turns (0.02–0.08)
FISH_TURN_RATE    = 0.035       # ← KEY FIX: was 0.065 → caused spinning

# Vision cone range (pixels)
FISH_DETECT_RADIUS = 260        # ← detection distance

# How many px from edge the fish starts curving back
BOUNDARY_MARGIN    = 110        # ← turn-back zone width

# ── PLASTIC ─────────────────────────────────────────────────────
PLASTIC_SIZE_MIN  = 8           # ← smallest piece radius
PLASTIC_SIZE_MAX  = 18          # ← largest piece radius
INITIAL_PLASTICS  = 16          # ← pieces at startup

# ── COLORS ──────────────────────────────────────────────────────
SKY_TOP    = (14,  22,  42)
SKY_BOT    = (35,  62,  98)
BANK_TOP   = (68,  54,  34)
BANK_MID   = (54,  44,  24)
GRASS1     = (48,  84,  34)
GRASS2     = (36,  72,  24)
STONE1     = (80,  72,  60)
STONE2     = (64,  58,  48)

WATER_DEEP  = ( 6,  40,  72)
WATER_SURF  = (16,  84, 135)

FISH_BODY   = (28, 175, 155)
FISH_DARK   = (18, 128, 112)
FISH_BELLY  = (175,228, 208)
FISH_ACCENT = (  0,218, 196)
FISH_STRIPE = ( 10, 95,  85)
FISH_EYE    = ( 15, 15,  25)
FISH_PUPIL  = (255,255, 255)
FISH_MOUTH  = (195, 72,  52)
FIN_COL     = ( 18,155, 135)
TAIL_COL    = ( 12,120, 102)

PLASTIC_COLS = [
    (238,  72,  50),
    (238, 196,  38),
    ( 52, 172, 238),
    (215,  52, 215),
    ( 52, 215,  72),
    (252, 132,  14),
]

HUD_BG     = (  6,  18,  36)
HUD_TEXT   = (155, 235, 215)
HUD_ACCENT = (  0, 218, 196)
HUD_WARN   = (255, 155,  38)

CV_GREEN   = (  0, 255, 100)
CV_AMBER   = (255, 200,  40)
CV_RED     = (255,  60,  60)
