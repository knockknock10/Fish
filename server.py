import pygame
import cv2
import numpy as np
import time
import os
import random
import math
import threading
from flask import Flask, Response, request, jsonify
from flask_cors import CORS

# ────────────────────────────────────────────────────────────
#  GILBERT v6.5  —  ULTRA-FAST INTERACTIVE ENGINE
#  Background-Threaded Rendering | Instant Initial Frame
# ────────────────────────────────────────────────────────────

os.environ["SDL_VIDEODRIVER"] = "dummy"

from config      import WIDTH, HEIGHT, FPS, RIVER_TOP_RATIO, INITIAL_PLASTICS
from environment import draw_environment
from plastic     import Plastic, ThrownPlastic, set_river_y
from particles   import SplashParticle, Ripple
from fish        import GilbertFish

# --- OPTIMIZED CONFIG ---
STREAM_WIDTH, STREAM_HEIGHT = 960, 540
STREAM_FPS = 30
JPEG_QUALITY = 70

app = Flask(__name__)
CORS(app)

class HeadlessEngine:
    def __init__(self):
        pygame.init()
        self.sim_surface = pygame.Surface((WIDTH, HEIGHT))
        self.RIVER_Y = int(HEIGHT * RIVER_TOP_RATIO)
        set_river_y(self.RIVER_Y)
        self.lock = threading.Lock()
        self.latest_frame_bytes = None
        self.reset()
        
        # Start Background Worker
        self.is_running = True
        self.worker = threading.Thread(target=self._run_loop, daemon=True)
        self.worker.start()

    def reset(self):
        with self.lock:
            self.plastics = [Plastic() for _ in range(INITIAL_PLASTICS)]
            self.thrown, self.splashes, self.ripples = [], [], []
            self.fish = GilbertFish(self.RIVER_Y)
            self.wave_offsets = [random.uniform(0, math.tau) for _ in range(6)]
            self.t = 0.0
            self.respawn_cd = 0
            print("[*] Headless Engine Reset")

    def _run_loop(self):
        """Infinite internal update/render loop (Req #2)."""
        frame_time = 1.0 / STREAM_FPS
        dt = 1.0 / FPS # Internal sim at 60fps
        
        while self.is_running:
            loop_start = time.time()
            
            with self.lock:
                # 1. Update Sim
                self.t += dt
                for th in self.thrown[:]:
                    th.update()
                    if th.done and not th.splashed:
                        th.splashed = True
                        lx, ly = th.tx, th.ty
                        for _ in range(random.randint(10,18)): self.splashes.append(SplashParticle(lx, ly))
                        for _ in range(3): self.ripples.append(Ripple(lx+random.uniform(-6,6), ly+random.uniform(-4,4)))
                        self.plastics.append(Plastic(lx, ly))
                        self.thrown.remove(th)

                self.splashes = [s for s in self.splashes if s.life > 0]
                for s in self.splashes: s.update()
                self.ripples = [r for r in self.ripples if r.life > 0]
                for r in self.ripples: r.update()

                alive_count = sum(1 for p in self.plastics if p.alive and not p.captured)
                if alive_count < 5:
                    self.respawn_cd += 1
                    if self.respawn_cd > 90:
                        self.plastics.append(Plastic())
                        self.respawn_cd = 0

                for p in self.plastics: p.update(self.t)
                self.fish.update(self.plastics, dt, self.t)

                # 2. Render and JPEG (Req #1: Fish Visibility)
                draw_environment(self.sim_surface, self.t, self.wave_offsets, self.RIVER_Y)
                for r in self.ripples: r.draw(self.sim_surface)
                for p in self.plastics: p.draw(self.sim_surface) # Draw waste under fish
                for th in self.thrown: th.draw(self.sim_surface)
                for s in self.splashes: s.draw(self.sim_surface)
                
                # FISH MUST BE LAST (Req #1)
                self.fish.draw(self.sim_surface)
                self.fish.draw_debug(self.sim_surface, self.t)
                self.fish.draw_hud(self.sim_surface, alive_count, self.t)

                raw_data = pygame.surfarray.array3d(self.sim_surface)
                frame = np.transpose(raw_data, (1, 0, 2))
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                frame = cv2.resize(frame, (STREAM_WIDTH, STREAM_HEIGHT), interpolation=cv2.INTER_AREA)
                
                success, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
                if success:
                    self.latest_frame_bytes = buffer.tobytes()

            # Wait to maintain 30 FPS for the stream
            wait = frame_time - (time.time() - loop_start)
            if wait > 0: time.sleep(wait)

    def add_plastic(self, x_pct, y_pct):
        with self.lock:
            sim_x = int(x_pct * WIDTH)
            sim_y = int(y_pct * HEIGHT)
            self.thrown.append(ThrownPlastic(max(22, min(WIDTH-22, sim_x)), max(self.RIVER_Y+22, min(HEIGHT-20, sim_y))))

engine = HeadlessEngine()

def gen_frames():
    """Generator providing instant initial frame (Req #2)."""
    while True:
        if engine.latest_frame_bytes:
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + engine.latest_frame_bytes + b'\r\n')
        time.sleep(0.01)

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/reset')
def reset():
    engine.reset()
    return jsonify({"status": "reset"})

@app.route('/click', methods=['POST'])
def click():
    data = request.json
    engine.add_plastic(data.get('x', 0.5), data.get('y', 0.5))
    return jsonify({"status": "clik"})

@app.route('/set_capacity', methods=['POST'])
def set_capacity():
    val = request.json.get('capacity', 20)
    with engine.lock:
        engine.fish.max_capacity = int(val)
    return jsonify({"status": "updated", "new_capacity": engine.fish.max_capacity})

if __name__ == '__main__':
    print("[*] GILBERT v6.5 ACTIVATED (THREADED ENGINE)")
    app.run(host='0.0.0.0', port=5000, threaded=True)
