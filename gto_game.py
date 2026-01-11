import pygame as pg
import math, json, os, random, time

W, H = 1000, 600
FPS = 60
FONT_NAME = "arial"

DATA_FILE = "gto_progress.json"
METERS_TO_PX = 20

# звук выхода по крестику / Esc
EXIT_SOUND_FILE = "pobeda_budet_za_nami.ogg"

# масштаб спрайта игрока (ты раньше просил ×1.5)
ACTOR_SCALE = 1.5
BASE_ACTOR_H = 44
ACTOR_H = int(BASE_ACTOR_H * ACTOR_SCALE)


def play_exit_sound_and_quit():
    """Проиграть pobeda_budet_za_nami.ogg и выйти из игры."""
    try:
        if pg.mixer.get_init():
            try:
                pg.mixer.music.stop()
            except Exception:
                pass
            if os.path.exists(EXIT_SOUND_FILE):
                try:
                    snd = pg.mixer.Sound(EXIT_SOUND_FILE)
                    ch = snd.play()
                    start = time.time()
                    # даём звуку сыграть (до 6 сек)
                    while ch.get_busy() and (time.time() - start) < 6.0:
                        pg.time.delay(50)
                except Exception:
                    pass
    except Exception:
        pass
    pg.quit()
    raise SystemExit


# -------- Нормативы --------
NORMS = {
    "BGTO": {
        "events": [
            {
                "key": "rifle25",
                "title": "Стрельба (малокалиберная винтовка, 25 м, мишень №6, лёжа)",
                "target_type": "score",
                "pass_score": 35,
                "excellent_score": 45,
                "practice_shots": 3,
                "scoring_shots": 5
            },
            {"key": "longjump",   "title": "Прыжок в длину",    "target_type": "dist",
             "pass_meters": 3.80,   "excellent_meters": 4.50},
            {"key": "grenade500", "title": "Граната 500 г",     "target_type": "dist",
             "pass_meters": 25.0,   "excellent_meters": 33.0},
        ],
        "badge": "Значок БГТО"
    },
    "GTO1": {
        "events": [
            # ВАЖНО: именно здесь будет 3 попытки (см. ниже в play_level)
            {"key": "sprint100",  "title": "Бег 100 м",         "target_type": "time",
             "pass_seconds": 13.6,  "excellent_seconds": 12.4},
            {"key": "obstacle150","title": "Полоса препятствий 150 м","target_type": "time",
             "pass_seconds": 95.0,   "excellent_seconds": 90.0},
            {"key": "grenade700", "title": "Граната 700 г",     "target_type": "dist",
             "pass_meters": 37.0,    "excellent_meters": 50.0},
        ],
        "badge": "Значок ГТО 1"
    },
    "GTO2": {
        "events": [
            {"key": "hurdles110", "title": "Барьеры 110 м",     "target_type": "time",
             "pass_seconds": 21.0,   "excellent_seconds": 19.0},
            {"key": "javelin800", "title": "Копьё 800 г",       "target_type": "dist",
             "pass_meters": 34.0,    "excellent_meters": 40.0},
            {"key": "run1500",    "title": "Бег 1500 м",        "target_type": "time",
             "pass_seconds": 310.0,  "excellent_seconds": 290.0},
        ],
        "badge": "Значок ГТО 2"
    }
}

# музыка по этапам
EVENT_MUSIC = {
    "rifle25":   "01_Vintovkа.ogg",
    "longjump":  "02_Vzveytes_kostrami_siniye_nochi.ogg",
    "grenade500":"03_A_nu_ka_pesnyu_nam_propoj_veselyi_veter.ogg",
    "sprint100": "04_Tri_tankista.ogg",
    "obstacle150":"05_aviamarsh.ogg",
    "grenade700":"06_Marsh_enthusiastov.ogg",
    "hurdles110":"07_proshal3.ogg",
    "javelin800":"08_zavvoina.ogg",
    "run1500":   "09_katyusha.ogg",
}
GLOBAL_BG = "00_Sportivnyi_marsh.ogg"


# ----- утилиты загрузки и рисования -----
def remove_bg_near_color(img: pg.Surface, key_rgb, tol: int = 22) -> pg.Surface:
    w, h = img.get_size()
    out = pg.Surface((w, h), pg.SRCALPHA)
    try:
        src = img.convert_alpha()
    except Exception:
        src = img.convert()
    kr, kg, kb = key_rgb
    for y in range(h):
        for x in range(w):
            r, g, b, *rest = src.get_at((x, y))
            a = rest[0] if rest else 255
            if a < 255:
                out.set_at((x, y), (r, g, b, a))
                continue
            if (abs(r-kr) <= tol) and (abs(g-kg) <= tol) and (abs(b-kb) <= tol):
                out.set_at((x, y), (r, g, b, 0))
            else:
                out.set_at((x, y), (r, g, b, 255))
    return out


def make_transparent_from_corner(img: pg.Surface, tol: int = 22) -> pg.Surface:
    try:
        corner = img.get_at((0, 0))[:3]
    except Exception:
        return img
    return remove_bg_near_color(img, corner, tol)


def _maybe_apply_white_colorkey(img: pg.Surface) -> pg.Surface:
    try:
        if img.get_flags() & pg.SRCALPHA:
            return img
        tl = img.get_at((0, 0))[:3]
        if sum(tl) / 3 >= 250:
            img = img.convert()
            img.set_colorkey(tl)
            return img
    except Exception:
        pass
    return img


def load_progress():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_progress(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def time_to_str(sec):
    m = int(sec // 60)
    s = sec - m * 60
    return f"{m}:{s:05.2f}" if m else f"{s:0.2f} c"


def load_image_any(basename: str):
    for ext in (".png", ".jpg", ".jpeg"):
        path = basename + ext
        if os.path.exists(path):
            try:
                img = pg.image.load(path)
                try:
                    img = img.convert_alpha()
                except Exception:
                    img = img.convert()
                img = _maybe_apply_white_colorkey(img)
                return img
            except Exception:
                try:
                    img = pg.image.load(path).convert()
                    img = _maybe_apply_white_colorkey(img)
                    return img
                except Exception:
                    pass
    return None


def load_badge_image(basename: str):
    img = load_image_any(basename)
    if img is not None and basename.lower() == "gto2":
        try:
            img = make_transparent_from_corner(img, tol=26)
        except Exception:
            pass
        return img
    if img is not None:
        return img
    surf = pg.Surface((120, 120), pg.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    pg.draw.circle(surf, (200, 200, 200), (60, 60), 56)
    pg.draw.circle(surf, (150, 150, 150), (60, 60), 56, 6)
    return surf


def make_actor_placeholder(target_h=ACTOR_H):
    s = pg.Surface((int(28*ACTOR_SCALE), target_h), pg.SRCALPHA)
    pg.draw.rect(s, (30, 160, 30), pg.Rect(4, 4, int(20*ACTOR_SCALE), target_h-8), border_radius=4)
    pg.draw.rect(s, (0, 90, 0), pg.Rect(4, 4, int(20*ACTOR_SCALE), target_h-8), 2, border_radius=4)
    return s


def load_actor_sprite(target_h=ACTOR_H):
    img = load_image_any("sprite")
    if img is None:
        return make_actor_placeholder(target_h)
    iw, ih = img.get_size()
    scale = target_h / max(1, ih)
    w = max(12, int(iw * scale))
    h = target_h
    return pg.transform.smoothscale(img, (w, h))


def blit_actor(surface, actor_img, x, y, camera_x=0):
    if actor_img is None:
        return
    rect = actor_img.get_rect(midbottom=(int(x) - int(camera_x), int(y)))
    surface.blit(actor_img, rect)


def dim_image_preserve_alpha(img: pg.Surface, gray=(120,120,120), alpha_factor=0.70) -> pg.Surface:
    out = pg.Surface(img.get_size(), pg.SRCALPHA)
    out.blit(img, (0, 0))
    r, g, b = gray
    out.fill((r, g, b, int(255 * alpha_factor)), special_flags=pg.BLEND_RGBA_MULT)
    return out


# ----- базовый класс мини-игр -----
class BaseGame:
    def __init__(self, screen, font, actor_img=None):
        self.screen = screen
        self.font = font
        self.actor_img = actor_img
        self.done = False
        self.result = None
        self.title = ""
        self.help = ""

    def draw_text(self, text, x, y, size=28, color=(20,20,20), center=False, surf=None):
        if surf is None:
            surf = self.screen
        f = pg.font.SysFont(FONT_NAME, size)
        img = f.render(text, True, color)
        rect = img.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        surf.blit(img, rect)

    def run(self):
        raise NotImplementedError


# ----- бег -----
class SprintGame(BaseGame):
    """
    Спринты и барьерный бег.
    Для БЕГА 100 М: добавлена "тапающая" логика — чем чаще →, тем быстрее.
    Есть поддержка нескольких попыток (attempts_total).
    """
    def __init__(self, screen, font, dist_m=60, hurdles=False, actor_img=None, attempts_total=1):
        super().__init__(screen, font, actor_img)
        self.dist_m = dist_m
        self.hurdles = bool(hurdles)
        self.attempts_total = max(1, attempts_total)

        if not self.hurdles and self.dist_m == 100:
            self.title = "Бег 100 м (тапай →)"
            self.help = "Как можно чаще нажимайте → — чаще = быстрее. Esc — выход."
        else:
            self.title = f"Бег {'с барьерами ' if self.hurdles else ''}{dist_m} м"
            base_help = "→ — бежать" if not self.hurdles else "→ — бежать | Space — ПРЫЖОК над барьером"
            if self.attempts_total > 1:
                base_help += f"  •  Попытки: {self.attempts_total}, засчитывается лучший результат"
            self.help = base_help

        self.track_len = int(dist_m * METERS_TO_PX)

        self.base_max_speed = 4.0 if not self.hurdles else 3.6
        self.base_accel = 0.06
        self.friction = 0.02

        if self.hurdles:
            self.base_max_speed *= (1.6 * 0.9)
            self.base_accel     *= (1.6 * 0.9)

        self.vy = 0.0
        self.g = 1200.0 if self.hurdles else 0.0
        self.jump_vel = 420.0 if self.hurdles else 0.0

        self._clock = pg.time.Clock()

    def _inter_attempt_card(self, attempt_idx, best_time):
        t = 0
        show = 1.2
        while t < show:
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    play_exit_sound_and_quit()
            self.screen.fill((255,255,255))
            pg.draw.rect(self.screen, (235,240,250), pg.Rect(W//2-300, H//2-110, 600, 220), border_radius=16)
            self.draw_text(f"Попытка {attempt_idx} завершена", W//2, H//2-30, 28, (20,60,140), True)
            if best_time is not None:
                self.draw_text(f"Текущий лучший: {time_to_str(best_time)}", W//2, H//2+14, 24, (40,40,40), True)
            pg.display.flip()
            self._clock.tick(FPS)
            t += 1.0/FPS

    def _run_single(self):
        self.speed = 0.0
        self.max_speed = self.base_max_speed
        self.accel = self.base_accel
        self.player_x = 50.0
        self.ground_y = H//2
        self.player_y = float(self.ground_y)
        self.camera = 0
        self.time = 0.0

        # барьеры, если нужно
        self.barriers = []
        if self.hurdles:
            n = 10 if self.dist_m >= 110 else 8
            gap = int(self.track_len/(n+1))
            first_x = 120
            # --- увеличенные интервалы для 110 м с барьерами ---
            if self.dist_m == 110:
                gap = int(gap * 1.5)
                first_x = int(first_x * 1.5)
            for i in range(n):
                bx = first_x + i * gap
                if bx > self.track_len + 40:
                    break
                self.barriers.append(pg.Rect(bx, self.ground_y-45, 14, 40))

        # флаги для "тапающего" спринта
        is_tap_sprint = (not self.hurdles) and (self.dist_m == 100)
        tap_impulse = 0.55
        hold_accel = 0.02
        tap_max_speed = 5.2

        clock = pg.time.Clock()
        want_jump = False
        finished = False
        while not finished and not self.done:
            dt = clock.tick(FPS)/1000.0
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    play_exit_sound_and_quit()
                if e.type == pg.KEYDOWN:
                    if e.key == pg.K_ESCAPE:
                        self.done = True
                        return None
                    if self.hurdles and e.key == pg.K_SPACE:
                        want_jump = True
                    if is_tap_sprint and e.key == pg.K_RIGHT:
                        # каждый тап ускоряет
                        self.speed = min(tap_max_speed, self.speed + tap_impulse)

            keys = pg.key.get_pressed()
            if is_tap_sprint:
                if keys[pg.K_RIGHT]:
                    self.speed = min(tap_max_speed, self.speed + hold_accel)
            else:
                if keys[pg.K_RIGHT]:
                    self.speed = min(self.max_speed, self.speed + self.accel)

            # трение
            self.speed = max(0, self.speed - self.friction)

            self.player_x += self.speed
            self.time += dt
            self.camera = max(0, int(self.player_x) - 200)

            # прыжок над барьером
            if self.hurdles:
                on_ground = (abs(self.player_y - self.ground_y) < 0.5) and (self.vy == 0.0)
                if want_jump and on_ground:
                    self.vy = -self.jump_vel
                want_jump = False

                if not on_ground or self.vy < 0:
                    self.vy += self.g * dt
                    self.player_y += self.vy * dt
                    if self.player_y >= self.ground_y:
                        self.player_y = float(self.ground_y)
                        self.vy = 0.0

            # финиш
            if self.player_x >= self.track_len + 50:
                finished = True

            # столкновения с барьерами (в экранных координатах)
            if self.hurdles:
                player_rect = pg.Rect(int(self.player_x), int(self.player_y)-20, 20, 40)
                for b in self.barriers:
                    br = b.move(-self.camera, 0)
                    if br.colliderect(player_rect):
                        feet_y = player_rect.bottom
                        if feet_y <= br.top + 1:
                            continue
                        self.speed *= 0.25

            # рисуем
            self.screen.fill((240,240,240))
            pg.draw.rect(self.screen, (220,200,150), pg.Rect(0, self.ground_y-30, W, 60))
            # старт
            pg.draw.line(self.screen, (0,0,0), (50-self.camera, self.ground_y-30), (50-self.camera, self.ground_y+30), 3)
            # финиш
            pg.draw.line(self.screen, (0,0,0), (self.track_len+50-self.camera, self.ground_y-30), (self.track_len+50-self.camera, self.ground_y+30), 3)

            if self.hurdles:
                for b in self.barriers:
                    br = b.move(-self.camera, 0)
                    pg.draw.rect(self.screen, (180,30,30), br)

            blit_actor(self.screen, self.actor_img, self.player_x, self.player_y, self.camera)

            self.draw_text(self.title, 20, 20, 28)
            self.draw_text(self.help, 20, 52, 22)
            self.draw_text(f"Время: {time_to_str(self.time)}", 20, 86, 24)
            if self.hurdles:
                self.draw_text("Совет: жмите Space ЧУТЬ ДО барьера.", 20, 116, 20, (80,80,80))
            elif is_tap_sprint:
                self.draw_text("Чаще жмите →, чтобы ускориться", 20, 116, 20, (80,80,80))
            pg.display.flip()

        return self.time

    def run(self):
        best_time = None
        for attempt in range(1, self.attempts_total + 1):
            t = self._run_single()
            if self.done:
                self.result = None
                return self.result
            if t is not None:
                best_time = t if (best_time is None or t < best_time) else best_time
            if attempt < self.attempts_total:
                self._inter_attempt_card(attempt, best_time)
        self.result = best_time
        return self.result


# ----- прыжки / метания -----
class ThrowJumpGame(BaseGame):
    def __init__(self, screen, font, mode="longjump", name="Прыжок в длину", actor_img=None):
        super().__init__(screen, font, actor_img)
        self.mode = mode
        self.title = name

        self.angle = 35
        self.power_rate = 0.015
        self.angle_step = 1
        self.max_speed = 3.2
        self.meter_scale = 10.0
        self.v_base = 4.5
        self.v_speed_k = 0.7
        self.v_power_k = 8.5
        self.g = 0.42
        self.help = "→ → → — разбег; Space — удерживать силу; ↑/↓ — угол; отпустить Space — попытка"

        if self.mode == "longjump":
            self.angle = 20
            self.power_rate = 0.018
            self.max_speed = 3.2
            self.meter_scale = 18.0
            self.v_base = 2.0
            self.v_speed_k = 0.9
            self.v_power_k = 2.2
            self.g = 0.50
            self.help = "→ → → — разбег; Space — удерживать силу; ↑/↓ — угол (10–30°); отпустите Space — прыжок"
        elif "grenade" in self.mode:
            self.angle = 0
            self.power_rate = 0.010
            self.max_speed = 2.6
            self.meter_scale = 5.0
            self.v_base = 3.5
            self.v_speed_k = 0.6
            self.v_power_k = 9.0
            self.g = 0.42
            self.help = "→ — разбег; удерживайте Space для силы; ↑/↓ — угол; отпустите Space — бросок"
        elif "javelin" in self.mode:
            self.angle = 20
            self.power_rate = 0.012
            self.max_speed = 3.0
            self.meter_scale = 4.0
            self.v_base = 4.0
            self.v_speed_k = 0.65
            self.v_power_k = 9.5
            self.g = 0.42

        self.state = "run"
        self.obj = {"x":120, "y":H-120, "vx":0, "vy":0}

        self.best_dist = 0.0
        self.runway_len_px = 500
        self.run_progress = 0.0
        self.speed = 0.0
        self.accel = 0.08
        self.friction = 0.03

        self.cooldown = 0.0
        self.attempts = 0
        self.max_attempts = 3

        self.grenade_img_raw = load_image_any("grenade2") or load_image_any("grenade")
        self.grenade_scale = 1.3
        self.grenade_base_size = (22, 12)

        self.spear_img_raw = load_image_any("spear2")
        self.spear_scale = 1.3

        self.javelin_len = 28

    def _rotated_blit(self, surf, img: pg.Surface, ang_deg: float, center_xy):
        rot = pg.transform.rotate(img, ang_deg)
        rect = rot.get_rect(center=(int(center_xy[0]), int(center_xy[1])))
        surf.blit(rot, rect)

    def _draw_grenade(self, x, y, vx=0.0, vy=0.0):
        ang_deg = -math.degrees(math.atan2(vy, vx if abs(vx) > 1e-3 else 1e-3))
        if self.grenade_img_raw:
            target_w = int(self.grenade_base_size[0] * self.grenade_scale)
            target_h = int(self.grenade_base_size[1] * self.grenade_scale)
            img = pg.transform.smoothscale(self.grenade_img_raw, (target_w, target_h))
            self._rotated_blit(self.screen, img, ang_deg, (x, y))
        else:
            body = pg.Surface((int(24*self.grenade_scale), int(14*self.grenade_scale)), pg.SRCALPHA)
            pg.draw.ellipse(body, (30,100,30), (2, 1, body.get_width()-4, body.get_height()-2))
            pg.draw.rect(body, (70,70,70), (int(body.get_width()*0.67), 2, int(body.get_width()*0.25), 4))
            body = pg.transform.rotate(body, ang_deg)
            rect = body.get_rect(center=(int(x), int(y)))
            self.screen.blit(body, rect)

    def _draw_javelin(self, x, y, vx=0.0, vy=0.0):
        ang = math.atan2(vy, vx if abs(vx) > 1e-3 else 1e-3)
        ang_deg = -math.degrees(ang)
        if self.spear_img_raw:
            iw, ih = self.spear_img_raw.get_size()
            img = pg.transform.smoothscale(self.spear_img_raw, (int(iw*self.spear_scale), int(ih*self.spear_scale)))
            self._rotated_blit(self.screen, img, ang_deg, (x, y))
        else:
            dx = math.cos(ang) * (self.javelin_len/2)
            dy = math.sin(ang) * (self.javelin_len/2)
            x1, y1 = int(x - dx), int(y - dy)
            x2, y2 = int(x + dx), int(y + dy)
            pg.draw.line(self.screen, (80,80,80), (x1,y1), (x2,y2), 2)
            pg.draw.polygon(self.screen, (120,120,120),
                            [(x2,y2),
                             (x2-6*math.cos(ang)-3*math.sin(ang), y2-6*math.sin(ang)+3*math.cos(ang)),
                             (x2-6*math.cos(ang)+3*math.sin(ang), y2-6*math.sin(ang)-3*math.cos(ang))])

    def _draw_sprite(self, x, y):
        vx, vy = self.obj["vx"], self.obj["vy"]
        if self.mode == "longjump":
            blit_actor(self.screen, self.actor_img, x, y)
        elif "grenade" in self.mode:
            self._draw_grenade(x, y, vx, vy)
        elif "javelin" in self.mode:
            self._draw_javelin(x, y, vx, vy)
        else:
            pg.draw.circle(self.screen, (40,40,120), (int(x), int(y)), 8)

    def run(self):
        clock = pg.time.Clock()
        while not self.done:
            dt = clock.tick(FPS)/1000.0
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    play_exit_sound_and_quit()
                if e.type == pg.KEYDOWN and e.key == pg.K_ESCAPE:
                    self.done = True
                    self.result = None
                if self.state == "aim" and e.type == pg.KEYUP and e.key == pg.K_SPACE:
                    if self.mode == "longjump":
                        self.angle = max(10, min(30, self.angle))
                    ang = math.radians(self.angle)
                    v = self.v_base + self.speed*self.v_speed_k + self.power*self.v_power_k
                    self.obj["vx"] = v*math.cos(ang)
                    self.obj["vy"] = -v*math.sin(ang)
                    self.state = "fly"

            keys = pg.key.get_pressed()
            if self.state == "run":
                if keys[pg.K_RIGHT]:
                    self.speed = min(self.max_speed, self.speed + self.accel)
                else:
                    self.speed = max(0, self.speed - self.friction)
                self.run_progress += self.speed
                if self.run_progress >= self.runway_len_px and keys[pg.K_SPACE]:
                    self.state = "aim"
                    self.power = 0.0
            elif self.state == "aim":
                if keys[pg.K_UP]:
                    self.angle = min(70, self.angle+self.angle_step)
                if keys[pg.K_DOWN]:
                    self.angle = max(0,  self.angle-self.angle_step)
                if keys[pg.K_SPACE]:
                    self.power = min(1.0, getattr(self, 'power', 0) + self.power_rate)
            elif self.state == "fly":
                self.obj["x"] += self.obj["vx"]
                self.obj["y"] += self.obj["vy"]
                self.obj["vy"] += self.g
                ground = H-120
                if self.obj["y"] >= ground:
                    self.obj["y"] = ground
                    dist_px = max(0.0, self.obj["x"] - 120)
                    dist_m = dist_px / self.meter_scale
                    if self.mode == "longjump":
                        dist_m = min(dist_m, 5.8)
                    self.best_dist = max(self.best_dist, dist_m)
                    self.attempts += 1
                    self.cooldown = 1.0
                    self.state = "cooldown"
            elif self.state == "cooldown":
                self.cooldown -= dt
                if self.cooldown <= 0:
                    if self.attempts < self.max_attempts:
                        self.state = "run"
                        self.run_progress = 0.0
                        self.speed = 0.0
                        self.obj = {"x":120, "y":H-120, "vx":0, "vy":0}
                    else:
                        self.done = True
                        self.result = round(self.best_dist, 2)

            # отрисовка
            self.screen.fill((235,245,250))
            pg.draw.rect(self.screen, (200,200,200), pg.Rect(100, H-170, self.runway_len_px, 6))
            pg.draw.rect(self.screen, (60,160,220), pg.Rect(100, H-170, max(0,int(self.run_progress)), 6))
            pg.draw.rect(self.screen, (210,190,140), pg.Rect(0, H-110, W, 110))
            pg.draw.line(self.screen, (0,0,0), (120, H-160), (120, H), 3)

            if self.state in ("aim","fly"):
                self._draw_sprite(self.obj["x"], self.obj["y"])

            self.draw_text(self.title, 20, 20, 28)
            self.draw_text(self.help, 20, 52, 22)
            if self.state == "run":
                self.draw_text(f"Разбег: {int(self.run_progress)}/{self.runway_len_px} px | скорость {self.speed:0.1f}", 20, 86, 24)
            if self.state == "aim":
                self.draw_text(f"Угол: {self.angle}° | Сила: {int(self.power*100)}%", 20, 86, 24)
            if self.attempts > 0:
                self.draw_text(f"Лучшая дальность: {self.best_dist:0.2f} м  |  Попытки: {self.attempts}/3", 20, 120, 24)
            if self.state == "cooldown":
                self.draw_text(f"Пауза между попытками…", 20, 150, 22, color=(80,80,80))
            pg.display.flip()
        return self.result


# ----- стрельба -----
class ShootingGame(BaseGame):
    def __init__(self, screen, font, practice_shots=3, scoring_shots=5):
        super().__init__(screen, font)
        self.title = "Стрельба (25 м, мишень №6, лёжа)"
        self.help = "Мышь — прицел • ЛКМ — выстрел • 3 пробных + 5 зачётных • 3 попытки • Esc — назад"
        self.max_attempts = 3
        self.attempt_idx = 0
        self.practice_shots_per_try = practice_shots
        self.scoring_shots_per_try = scoring_shots
        self.practice_left = self.practice_shots_per_try
        self.scoring_left = self.scoring_shots_per_try
        self.total_scored_current = 0
        self.best_total = None
        self.shots = []
        self.target_center = (W//2 + 220, H//2)
        self.target_radius = 70
        self.ring_count = 10
        self.ring_step = self.target_radius / self.ring_count
        self.breath_ax = 6.0
        self.breath_ay = 4.0
        self.breath_freq = 0.8
        self.phase = 0.0
        self._roll_new_wind()
        self.trigger_jitter = 2.0

    def _roll_new_wind(self):
        self.wind_strength = random.uniform(0.2, 1.0)
        self.wind_dir = random.choice([-1, 1])
        self.wind_px = self.wind_dir * (6.0 + 4.0 * self.wind_strength)

    def _score_for_point(self, x, y):
        cx, cy = self.target_center
        d = math.hypot(x - cx, y - cy)
        ring = int(d // self.ring_step)
        score = max(0, 10 - ring)
        return score

    def _draw_target(self):
        cx, cy = self.target_center
        pg.draw.circle(self.screen, (248,248,248), (cx, cy), self.target_radius+12)
        for i in range(self.ring_count, 0, -1):
            rad = int(i * self.ring_step)
            col = (220,220,220) if i % 2 == 0 else (240,240,240)
            pg.draw.circle(self.screen, col, (cx, cy), rad)
        pg.draw.circle(self.screen, (0,0,0), (cx, cy), int(self.ring_step*0.7), 1)
        pg.draw.circle(self.screen, (30,30,30), (cx, cy), int(4*self.ring_step), 2)

    def _draw_crosshair(self, pos):
        x, y = pos
        pg.draw.circle(self.screen, (20,20,20), (x, y), 8, 1)
        pg.draw.line(self.screen, (20,20,20), (x-14, y), (x-2, y), 2)
        pg.draw.line(self.screen, (20,20,20), (x+2, y), (x+14, y), 2)
        pg.draw.line(self.screen, (20,20,20), (x, y-14), (x, y-2), 2)
        pg.draw.line(self.screen, (20,20,20), (x, y+2), (x, y+14), 2)

    def _apply_breath_to_mouse(self, mx, my, dt):
        self.phase += 2 * math.pi * self.breath_freq * dt
        bx = self.breath_ax * math.sin(self.phase)
        by = self.breath_ay * math.sin(self.phase * 0.9 + 1.3)
        return mx + bx, my + by

    def _wind_label(self):
        arrow = "→" if self.wind_dir > 0 else "←"
        bars = int(1 + round(self.wind_strength * 4))
        return arrow + " " + "▮" * bars

    def _reset_attempt(self):
        self.practice_left = self.practice_shots_per_try
        self.scoring_left = self.scoring_shots_per_try
        self.total_scored_current = 0
        self.shots = []
        self.phase = 0.0
        self._roll_new_wind()

    def run(self):
        clock = pg.time.Clock()
        self._reset_attempt()
        while not self.done:
            dt = clock.tick(FPS)/1000.0
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    play_exit_sound_and_quit()
                if e.type == pg.KEYDOWN and e.key == pg.K_ESCAPE:
                    self.done = True
                    self.result = None
                if e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
                    mx, my = pg.mouse.get_pos()
                    ax, ay = self._apply_breath_to_mouse(mx, my, 0)
                    jx = random.uniform(-self.trigger_jitter, self.trigger_jitter)
                    jy = random.uniform(-self.trigger_jitter, self.trigger_jitter)
                    sx = ax + jx + self.wind_px
                    sy = ay + jy
                    sc = self._score_for_point(sx, sy)
                    is_practice = self.practice_left > 0
                    if is_practice:
                        self.practice_left -= 1
                    else:
                        if self.scoring_left > 0:
                            self.scoring_left -= 1
                            self.total_scored_current += sc
                    self.shots.append((sx, sy, sc, is_practice))
                    if self.scoring_left == 0:
                        if (self.best_total is None) or (self.total_scored_current > self.best_total):
                            self.best_total = self.total_scored_current
                        self.attempt_idx += 1
                        if self.attempt_idx >= self.max_attempts:
                            self.done = True
                            self.result = self.best_total if self.best_total is not None else 0
                        else:
                            self._inter_attempt_card()
                            self._reset_attempt()

            self.screen.fill((245,245,250))
            pg.draw.rect(self.screen, (235,240,250), pg.Rect(20, 20, 420, H-40), border_radius=12)
            self._draw_target()
            mx, my = pg.mouse.get_pos()
            ax, ay = self._apply_breath_to_mouse(mx, my, dt)
            self._draw_crosshair((int(ax), int(ay)))
            for (x, y, sc, is_pr) in self.shots:
                clr = (140,140,140) if is_pr else (200,30,30)
                pg.draw.circle(self.screen, clr, (int(x), int(y)), 4)
                if not is_pr:
                    f = pg.font.SysFont(FONT_NAME, 16)
                    img = f.render(str(sc), True, (60,60,60))
                    self.screen.blit(img, (int(x)+6, int(y)-6))
            wind_label = self._wind_label()
            self.draw_text("Ветер:", 30, 30, 22, (20,30,60))
            self.draw_text(wind_label, 130, 30, 22, (20,30,60))
            base_x, base_y = 320, 46
            pg.draw.line(self.screen, (60,80,130), (base_x-60, base_y), (base_x+60, base_y), 3)
            tip_x = base_x + int(50 * self.wind_dir * (0.4 + 0.6*self.wind_strength))
            pg.draw.polygon(self.screen, (60,80,130),
                            [(tip_x, base_y),
                             (tip_x - 8*self.wind_dir, base_y - 6),
                             (tip_x - 8*self.wind_dir, base_y + 6)])
            self.draw_text(self.title, 30, 70, 24, (20,30,60))
            self.draw_text("Управление: мышь — прицеливание; ЛКМ — выстрел.", 30, 100, 18, (60,60,60))
            self.draw_text("На попытку: 3 пробных + 5 зачётных; всего 3 попытки. В зачёт идёт лучший результат.", 30, 124, 18, (60,60,60))
            self.draw_text(f"Попытка: {self.attempt_idx+1}/{self.max_attempts}", 30, 160, 22)
            self.draw_text(f"Пробных осталось: {self.practice_left}", 30, 188, 22)
            self.draw_text(f"Зачётных осталось: {self.scoring_left}", 30, 216, 22)
            self.draw_text(f"Счёт этой попытки: {self.total_scored_current} / 50", 30, 246, 22, (20,100,40))
            bt = self.best_total if self.best_total is not None else 0
            self.draw_text(f"Лучший из предыдущих: {bt} / 50", 30, 274, 20, (70,70,70))
            self.draw_text("Esc — назад", 230, H-36, 18, (90,90,90), True)
            pg.display.flip()
        return self.result

    def _inter_attempt_card(self):
        t = 0
        show = 1.2
        while t < show:
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    play_exit_sound_and_quit()
            self.screen.fill((255,255,255))
            pg.draw.rect(self.screen, (235,240,250), pg.Rect(W//2-300, H//2-110, 600, 220), border_radius=16)
            self.draw_text(f"Попытка {self.attempt_idx}/{self.max_attempts} завершена", W//2, H//2-30, 28, (20,60,140), True)
            self.draw_text(f"Счёт попытки: {self.total_scored_current} / 50", W//2, H//2+10, 24, (40,40,40), True)
            best = self.best_total if self.best_total is not None else 0
            self.draw_text(f"Текущий лучший: {best} / 50", W//2, H//2+44, 22, (60,60,60), True)
            pg.display.flip()
            pg.time.Clock().tick(FPS)
            t += 1.0/FPS


# ----- полоса препятствий -----
class ObstacleGame(BaseGame):
    """
    Полоса препятствий 150 м.
    Проверка столкновений в мировых координатах — нет прежнего "залипания".
    """
    def __init__(self, screen, font, dist_m=150, actor_img=None, attempts_total=1):
        super().__init__(screen, font, actor_img)
        self.title = "Полоса препятствий 150 м"
        self.base_help = "→ — бежать | Space — ПРЫЖОК"
        self.attempts_total = max(1, attempts_total)
        self.help = self.base_help + (f"  •  Попытки: {self.attempts_total}, засчитывается лучший результат"
                                      if self.attempts_total > 1 else "")
        self.dist_m = dist_m
        self.track_len = int(dist_m * METERS_TO_PX)
        self.ground_y = H//2
        self._clock = pg.time.Clock()
        self.obs = []
        n = 12
        gap = self.track_len/(n+1)
        kinds = ["log","fence","palisade","ditch"]
        for i in range(n):
            kind = kinds[i % len(kinds)]
            px = 200 + int((i+1)*gap)
            if kind == "ditch":
                rect = pg.Rect(px, self.ground_y - 8, 28, 6)
            elif kind == "palisade":
                rect = pg.Rect(px, self.ground_y - 55, 22, 50)
            elif kind == "fence":
                rect = pg.Rect(px, self.ground_y - 40, 22, 35)
            else:
                rect = pg.Rect(px, self.ground_y - 28, 26, 20)
            self.obs.append({"rect": rect, "kind": kind})

    def _inter_attempt_card(self, attempt_idx, best_time):
        t = 0
        show = 1.2
        while t < show:
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    play_exit_sound_and_quit()
            self.screen.fill((255,255,255))
            pg.draw.rect(self.screen, (235,240,250), pg.Rect(W//2-300, H//2-110, 600, 220), border_radius=16)
            self.draw_text(f"Попытка {attempt_idx} завершена", W//2, H//2-30, 28, (20,60,140), True)
            if best_time is not None:
                self.draw_text(f"Текущий лучший: {time_to_str(best_time)}", W//2, H//2+14, 24, (40,40,40), True)
            pg.display.flip()
            self._clock.tick(FPS)
            t += 1.0/FPS

    def _run_single(self):
        self.player_x = 50.0
        self.player_y = float(self.ground_y)
        self.camera = 0
        self.speed = 0.0
        self.max_speed = 3.8
        self.accel = 0.06
        self.friction = 0.02
        self.vy = 0.0
        self.g = 1200.0
        self.jump_vel = 420.0
        self.time = 0.0
        clock = pg.time.Clock()
        want_jump = False
        while True and not self.done:
            dt = clock.tick(FPS)/1000.0
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    play_exit_sound_and_quit()
                if e.type == pg.KEYDOWN:
                    if e.key == pg.K_ESCAPE:
                        self.done = True
                        return None
                    elif e.key == pg.K_SPACE:
                        want_jump = True
            keys = pg.key.get_pressed()
            if keys[pg.K_RIGHT]:
                self.speed = min(self.max_speed, self.speed + self.accel)
            else:
                self.speed = max(0.0, self.speed - self.friction)
            self.player_x += self.speed
            self.time += dt
            self.camera = max(0, int(self.player_x)-200)
            on_ground = (abs(self.player_y - self.ground_y) < 0.5) and (self.vy == 0.0)
            if want_jump and on_ground:
                self.vy = -self.jump_vel
            want_jump = False
            if not on_ground or self.vy < 0:
                self.vy += self.g * dt
                self.player_y += self.vy * dt
                if self.player_y >= self.ground_y:
                    self.player_y = float(self.ground_y)
                    self.vy = 0.0
            if self.player_x >= self.track_len+50:
                return self.time

            player_rect_world = pg.Rect(int(self.player_x) - 10,
                                        int(self.player_y) - 40,
                                        20, 40)
            for o in self.obs:
                if player_rect_world.colliderect(o["rect"]):
                    self.speed *= 0.40

            self.screen.fill((245,240,235))
            pg.draw.rect(self.screen, (220,200,150), pg.Rect(0, self.ground_y-30, W, 60))
            pg.draw.line(self.screen, (0,0,0), (50-self.camera, self.ground_y-30), (50-self.camera, self.ground_y+30), 3)
            pg.draw.line(self.screen, (0,0,0), (self.track_len+50-self.camera, self.ground_y-30), (self.track_len+50-self.camera, self.ground_y+30), 3)
            for o in self.obs:
                r = o["rect"].move(-self.camera,0)
                color = {"log":(120,70,30),"ditch":(30,120,180),"fence":(180,30,30),"palisade":(100,60,20)}[o["kind"]]
                pg.draw.rect(self.screen, color, r)
            blit_actor(self.screen, self.actor_img, self.player_x, self.player_y, self.camera)
            self.draw_text(self.title, 20, 20, 28)
            self.draw_text(self.help, 20, 52, 22)
            self.draw_text(f"Время: {time_to_str(self.time)}", 20, 86, 24)
            self.draw_text("Подсказка: жмите Space перед препятствием — прыжок стал настоящим.", 20, 116, 20, (70,70,70))
            pg.display.flip()

    def run(self):
        best_time = None
        for attempt in range(1, self.attempts_total + 1):
            t = self._run_single()
            if self.done:
                self.result = None
                return self.result
            if t is not None:
                best_time = t if (best_time is None or t < best_time) else best_time
            if attempt < self.attempts_total:
                self._inter_attempt_card(attempt, best_time)
        self.result = best_time
        return self.result


# ----- длинный бег -----
class LongRunGame(BaseGame):
    def __init__(self, screen, font, dist_m=1500, actor_img=None):
        super().__init__(screen, font, actor_img)
        self.title = f"Бег {dist_m} м"
        self.help = "Короткими нажатиями → держите индикатор в зелёной зоне"
        self.dist_m = dist_m
        self.progress = 0.0
        self.pace = 0.0
        self.time = 0.0
        target_h = ACTOR_H

        def _scale(img, h=target_h):
            if img is None:
                return None
            iw, ih = img.get_size()
            sc = h / max(1, ih)
            return pg.transform.smoothscale(img, (max(12, int(iw * sc)), h))

        self.sprite_q12 = _scale(load_image_any("sprite1")) or actor_img
        self.sprite_q34 = _scale(load_image_any("sprite")) or actor_img

    def run(self):
        clock = pg.time.Clock()
        cx, cy = W//2, H//2
        rx, ry = int(W*0.35), int(H*0.25)
        while not self.done:
            dt = clock.tick(FPS)/1000.0
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    play_exit_sound_and_quit()
                if e.type == pg.KEYDOWN and e.key == pg.K_ESCAPE:
                    self.done = True
                    self.result = None

            keys = pg.key.get_pressed()
            if keys[pg.K_RIGHT]:
                self.pace = min(1.0, self.pace + 0.025)
            else:
                self.pace = max(0.0, self.pace - 0.010)

            low, high = 0.45, 0.70
            base_speed = 1.8 + (self.pace * 2.8)
            in_green = (low <= self.pace <= high)
            speed = base_speed * (4.0 if in_green else 1.0)
            self.progress += speed * dt
            self.time += dt

            if self.progress >= self.dist_m:
                self.done = True
                self.result = self.time

            self.screen.fill((250,250,255))
            pg.draw.ellipse(self.screen, (230,210,160), pg.Rect(cx-rx, cy-ry, rx*2, ry*2), 40)

            frac = (self.progress % self.dist_m) / self.dist_m
            theta = 2 * math.pi * frac
            px = cx + rx * math.cos(theta)
            py = cy + ry * math.sin(theta) + ACTOR_H//2
            active_sprite = self.sprite_q12 if frac < 0.50 else self.sprite_q34
            blit_actor(self.screen, active_sprite, px, py)

            bar_x, bar_y, bar_w, bar_h = int(W*0.30), int(H*0.86), int(W*0.40), 20
            pg.draw.rect(self.screen, (200,200,200), (bar_x, bar_y, bar_w, bar_h))
            gz1 = bar_x + int(bar_w*0.45)
            gz2 = bar_x + int(bar_w*0.70)
            pg.draw.rect(self.screen, (170,220,170), (gz1, bar_y, gz2-gz1, bar_h))
            knob = bar_x + int(bar_w*self.pace)
            pg.draw.rect(self.screen, (30,120,200), (knob-6, bar_y-4, 12, bar_h+8))

            if in_green:
                self.draw_text("Скорость x4 (зелёная зона)", 20, 146, 20, (30,120,30))

            self.draw_text(self.title, 20, 20, 28)
            self.draw_text(self.help, 20, 52, 22)
            self.draw_text(f"Пройдено: {int(self.progress)} м из {self.dist_m} м", 20, 86, 24)
            self.draw_text(f"Время: {time_to_str(self.time)}", 20, 116, 24)
            pg.display.flip()
        return self.result


# -------- оценка результатов --------
def evaluate_event(event_def, value):
    t = event_def["target_type"]
    if value is None:
        return "нет результата", "Попробуйте снова"
    if t == "time":
        if value <= event_def["excellent_seconds"]:
            return "отлично", f"{time_to_str(value)} (≤ {time_to_str(event_def['excellent_seconds'])})"
        elif value <= event_def["pass_seconds"]:
            return "сдано", f"{time_to_str(value)} (≤ {time_to_str(event_def['pass_seconds'])})"
        else:
            return "не сдано", f"{time_to_str(value)} (> {time_to_str(event_def['pass_seconds'])})"
    elif t == "dist":
        if value >= event_def["excellent_meters"]:
            return "отлично", f"{value:.2f} м (≥ {event_def['excellent_meters']:.2f} м)"
        elif value >= event_def["pass_meters"]:
            return "сдано", f"{value:.2f} м (≥ {event_def['pass_meters']:.2f} м)"
        else:
            return "не сдано", f"{value:.2f} м (< {event_def['pass_meters']:.2f} м)"
    elif t == "score":
        if value >= event_def["excellent_score"]:
            return "отлично", f"{int(value)} оч. (≥ {event_def['excellent_score']})"
        elif value >= event_def["pass_score"]:
            return "сдано", f"{int(value)} оч. (≥ {event_def['pass_score']})"
        else:
            return "не сдано", f"{int(value)} оч. (< {event_def['pass_score']})"
    else:
        return "неизв. тип", "—"


# -------- главное приложение --------
class App:
    def __init__(self):
        pg.init()
        # полный экран
        info = pg.display.Info()
        global W, H
        W, H = info.current_w, info.current_h
        try:
            self.screen = pg.display.set_mode((W, H), pg.FULLSCREEN)
        except Exception:
            self.screen = pg.display.set_mode((W, H))
        pg.display.set_caption("ГТО — секретное оружие СССР")
        self.clock = pg.time.Clock()
        self.font = pg.font.SysFont(FONT_NAME, 24)
        self.progress = load_progress()
        self.badges = {
            "BGTO": load_badge_image("bgto"),
            "GTO1": load_badge_image("gto1"),
            "GTO2": load_badge_image("gto2"),
        }
        self.actor_img = load_actor_sprite(ACTOR_H)
        self.snd_click = None
        self.snd_failure = None
        self.snd_applause = None
        self.snd_achievement = None
        self.snd_failure2 = None
        self.bg_track = GLOBAL_BG

        # салют
        self.snd_fireworks = None
        self.fireworks_active = False
        self.fireworks_timer = 0.0
        self.fireworks_particles = []
        self.fireworks_played_once = False

        # аудио
        try:
            pg.mixer.init()
            for name in ("click.ogg", "click.wav", "menu_click.ogg", "menu_click.wav"):
                if os.path.exists(name):
                    try:
                        self.snd_click = pg.mixer.Sound(name)
                        break
                    except Exception:
                        pass

            def _load_first_sound(cands):
                for n in cands:
                    if os.path.exists(n):
                        try:
                            return pg.mixer.Sound(n)
                        except Exception:
                            pass
                return None

            self.snd_failure = _load_first_sound(["failure.ogg", "failure.wav"])
            self.snd_applause = _load_first_sound(["applause.ogg", "aplause.ogg", "applause.wav", "aplause.wav"])
            self.snd_achievement = _load_first_sound(["achievement.ogg", "achievement.wav"])
            self.snd_failure2 = _load_first_sound(["failure2.ogg", "failure2.wav"])

            # салют
            if os.path.exists("fireworks.ogg"):
                try:
                    self.snd_fireworks = pg.mixer.Sound("fireworks.ogg")
                except Exception:
                    self.snd_fireworks = None

            # основная музыка
            if os.path.exists("radio.ogg"):
                try:
                    pg.mixer.music.load("radio.ogg")
                    pg.mixer.music.set_volume(0.45)
                    pg.mixer.music.play(loops=0, fade_ms=600)
                    if os.path.exists(self.bg_track):
                        try:
                            pg.mixer.music.queue(self.bg_track)
                        except Exception:
                            pass
                except Exception:
                    self._start_bg_music()
            else:
                self._start_bg_music()
        except Exception:
            self.snd_click = None

    # салют при 3х значках
    def start_fireworks(self, duration=4.5):
        self.fireworks_active = True
        self.fireworks_timer = duration
        self.fireworks_particles = []
        self.fireworks_played_once = False
        for _ in range(4):
            self._spawn_firework_burst()

    def _spawn_firework_burst(self):
        x = random.randint(int(W*0.18), int(W*0.82))
        y = random.randint(int(H*0.10), int(H*0.45))
        count = random.randint(16, 28)
        colors = [
            (255, 80, 80), (255, 160, 60), (255, 255, 90),
            (140, 220, 140), (130, 190, 255), (220, 130, 255)
        ]
        for _ in range(count):
            ang = random.uniform(0, 2*math.pi)
            spd = random.uniform(80, 210)
            vx = math.cos(ang) * spd
            vy = math.sin(ang) * spd
            life = random.uniform(0.8, 1.6)
            col = random.choice(colors)
            self.fireworks_particles.append({
                "x": x,
                "y": y,
                "vx": vx,
                "vy": vy,
                "life": life,
                "max_life": life,
                "color": col
            })

    def _update_fireworks(self, dt):
        if not self.fireworks_active:
            return
        self.fireworks_timer -= dt
        if self.fireworks_timer <= 0:
            self.fireworks_active = False
            self.fireworks_particles.clear()
            return

        if random.random() < 0.03:
            self._spawn_firework_burst()

        g = 85.0
        for p in self.fireworks_particles:
            p["life"] -= dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += g * dt

        self.fireworks_particles = [p for p in self.fireworks_particles if p["life"] > 0]

    def _draw_fireworks(self, surface):
        if not self.fireworks_active:
            return
        for p in self.fireworks_particles:
            alpha = max(0, min(255, int(255 * (p["life"] / p["max_life"]))))
            col = (*p["color"], alpha)
            pg.draw.circle(surface, col, (int(p["x"]), int(p["y"])), 3)
        overlay = pg.Surface((W, H), pg.SRCALPHA)
        overlay.fill((20, 20, 40, 35))
        surface.blit(overlay, (0, 0))

        if (not self.fireworks_played_once) and self.snd_fireworks:
            try:
                self.snd_fireworks.play()
            except Exception:
                pass
            self.fireworks_played_once = True

    def _start_bg_music(self, fade_ms=600):
        try:
            if not pg.mixer.get_init():
                return
            if not os.path.exists(self.bg_track):
                return
            pg.mixer.music.load(self.bg_track)
            pg.mixer.music.set_volume(0.45)
            pg.mixer.music.play(loops=-1, fade_ms=fade_ms)
        except Exception:
            pass

    def _ensure_bg_loop_if_idle(self):
        try:
            if pg.mixer.get_init() and not pg.mixer.music.get_busy():
                self._start_bg_music()
        except Exception:
            pass

    def _play_event_music(self, ev_key, fade_ms=350, volume=0.55):
        fname = EVENT_MUSIC.get(ev_key)
        if not fname:
            return
        if not pg.mixer.get_init():
            return
        if not os.path.exists(fname):
            return
        try:
            pg.mixer.music.load(fname)
            pg.mixer.music.set_volume(volume)
            pg.mixer.music.play(loops=-1, fade_ms=fade_ms)
        except Exception:
            pass

    def _fadeout_music(self, ms=400):
        try:
            if pg.mixer.get_init():
                pg.mixer.music.fadeout(ms)
        except Exception:
            pass

    def play_click(self):
        if self.snd_click:
            try:
                self.snd_click.play()
            except Exception:
                pass

    def play_sound(self, snd):
        if snd:
            try:
                snd.play()
            except Exception:
                pass

    def draw_text(self, text, x, y, size=28, color=(20,20,20), center=False, surf=None):
        if surf is None:
            surf = self.screen
        f = pg.font.SysFont(FONT_NAME, size)
        img = f.render(text, True, color)
        rect = img.get_rect()
        if center:
            rect.center = (x, y)
        else:
            rect.topleft = (x, y)
        surf.blit(img, rect)

    def draw_keycap(self, label, x, y, w=None, h=34, font_size=18, surf=None):
        if surf is None:
            surf = self.screen
        pad = 12
        f = pg.font.SysFont(FONT_NAME, font_size)
        txt = f.render(label, True, (20,20,20))
        tw, th = txt.get_size()
        if w is None:
            w = max(40, tw + pad*2)
        rect = pg.Rect(x, y, w, h)
        pg.draw.rect(surf, (245,245,245), rect, border_radius=8)
        pg.draw.rect(surf, (200,200,200), rect, 2, border_radius=8)
        surf.blit(txt, (x + (w - tw)//2, y + (h - th)//2))

    def _load_logo_surface(self):
        img = load_image_any("logo")
        if img is None:
            return None
        lw, lh = img.get_size()
        base_target_h = int(H * 0.20)
        target_h = max(90, base_target_h)
        target_h = int(target_h * 1.4)   # ×1.4 как ты просил в меню
        scale = target_h / max(1, lh)
        target_w = max(90, int(lw * scale))
        return pg.transform.smoothscale(img, (target_w, target_h))

    def menu(self):
        run = True
        sel = 0
        items = [
            "Начать: БГТО",
            "Продолжить: ГТО 1",
            "Продолжить: ГТО 2",
            "Результаты",
            "Справка",
            "Выход"
        ]
        logo = None
        try:
            logo = self._load_logo_surface()
        except Exception:
            logo = None
        badge_w = 135
        badge_h = 135
        base_line_h = 46
        min_line_h = 34
        menu_font_size = 28

        while run:
            dt = self.clock.tick(FPS)/1000.0
            self._ensure_bg_loop_if_idle()
            self._update_fireworks(dt)

            last_sel = sel
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    play_exit_sound_and_quit()
                if e.type == pg.KEYDOWN:
                    if e.key == pg.K_ESCAPE:
                        play_exit_sound_and_quit()
                    if e.key in (pg.K_DOWN, pg.K_s):
                        sel = (sel + 1) % len(items)
                    if e.key in (pg.K_UP, pg.K_w):
                        sel = (sel - 1) % len(items)
                    if e.key in (pg.K_RETURN, pg.K_SPACE):
                        if sel == 0:
                            self.play_level("BGTO")
                        elif sel == 1:
                            self.play_level("GTO1")
                        elif sel == 2:
                            self.play_level("GTO2")
                        elif sel == 3:
                            self.dashboard()
                        elif sel == 4:
                            self.help_screen()
                        elif sel == 5:
                            play_exit_sound_and_quit()

            self.screen.fill((250, 248, 240))
            if logo:
                logo_rect = logo.get_rect(midtop=(W // 2, 18))
                self.screen.blit(logo, logo_rect)
                menu_top_y = logo_rect.bottom + 14
            else:
                self.draw_text("ГТО", W//2, 24, 48, (180,40,40), True)
                menu_top_y = 24 + 48 + 14
                logo_rect = pg.Rect(W//2-50, 24, 100, 48)

            available_menu_h = H - menu_top_y - 240
            if available_menu_h < 0:
                available_menu_h = 0
            items_total = len(items)
            line_h = min(base_line_h, max(min_line_h, available_menu_h // items_total)) if items_total else base_line_h
            if line_h < base_line_h:
                menu_font_size = 26 if line_h >= 38 else 24

            mx, my = pg.mouse.get_pos()
            hover = None
            for i, it in enumerate(items):
                y_row = menu_top_y + i * line_h
                clr = (200,40,40) if i == sel else (30,30,30)
                self.draw_text(it, W//2, y_row, menu_font_size, clr, True)
                r = pg.Rect(W//2 - 300, y_row - line_h//2 + 6, 600, line_h - 8)
                if r.collidepoint(mx, my):
                    hover = i

            if hover is not None and hover != sel:
                sel = hover
                self.play_click()
            if hover is not None and pg.mouse.get_pressed()[0]:
                if sel == 0:
                    self.play_level("BGTO")
                elif sel == 1:
                    self.play_level("GTO1")
                elif sel == 2:
                    self.play_level("GTO2")
                elif sel == 3:
                    self.dashboard()
                elif sel == 4:
                    self.help_screen()
                elif sel == 5:
                    play_exit_sound_and_quit()

            # последняя строка меню
            last_menu_y = menu_top_y + (len(items) - 1) * line_h

            gap_from_logo = menu_top_y - logo_rect.bottom
            badges_top = last_menu_y + 3 * gap_from_logo
            badges_center_y = badges_top + badge_h // 2

            cx = W // 2
            dx = int(badge_w * 1.25)
            badge_positions = [
                (cx - dx, badges_center_y),
                (cx,       badges_center_y),
                (cx + dx,  badges_center_y)
            ]

            for (code, label), (bx, by) in zip(
                [("BGTO","БГТО"), ("GTO1","ГТО 1"), ("GTO2","ГТО 2")],
                badge_positions
            ):
                got = self.progress.get(code,{}).get("badge", False)
                img = pg.transform.smoothscale(self.badges[code], (badge_w, badge_h))
                if not got:
                    img = dim_image_preserve_alpha(img, gray=(120,120,120), alpha_factor=0.70)
                rect = img.get_rect(center=(bx, by))
                self.screen.blit(img, rect)
                self.draw_text(label, bx, rect.bottom + 18, 22, center=True)

            footer_y = badges_center_y + badge_h//2 + 18 + 32
            self.draw_text("↑/↓ — выбор • Enter — подтвердить • Esc — выход", W//2, footer_y, 20, (80,80,80), True)

            if self.fireworks_active:
                self._draw_fireworks(self.screen)

            if sel != last_sel and hover is None:
                self.play_click()
            pg.display.flip()

    def play_level(self, level_code):
        # было ли уже 3/3
        was_all = all(self.progress.get(c, {}).get("badge", False) for c in ("BGTO", "GTO1", "GTO2"))

        events = NORMS[level_code]["events"]
        results = {}
        for ev in events:
            self._play_event_music(ev["key"])
            # ---- здесь решаем, какую мини-игру запускать ----
            if ev["key"] in ("sprint60","sprint100"):
                # ВАЖНО: именно здесь мы делаем 3 попытки для ГТО 1 БЕГ 100 м
                if ev["key"] == "sprint100" and level_code == "GTO1":
                    g = SprintGame(self.screen, self.font, dist_m=100,
                                   hurdles=False, actor_img=self.actor_img,
                                   attempts_total=3)
                else:
                    g = SprintGame(self.screen, self.font, dist_m=60 if "60" in ev["key"] else 100,
                                   hurdles=False, actor_img=self.actor_img)
            elif ev["key"]=="hurdles110":
                # 3 попытки сдачи для барьеров ГТО 2
                g = SprintGame(self.screen, self.font, dist_m=110, hurdles=True,
                               actor_img=self.actor_img, attempts_total=3)
            elif ev["key"]=="longjump":
                g = ThrowJumpGame(self.screen, self.font, "longjump", "Прыжок в длину",
                                  actor_img=self.actor_img)
            elif ev["key"] in ("grenade500","grenade700"):
                name = "Граната 500 г" if "500" in ev["key"] else "Граната 700 г"
                g = ThrowJumpGame(self.screen, self.font, ev["key"], name,
                                  actor_img=self.actor_img)
            elif ev["key"]=="javelin800":
                g = ThrowJumpGame(self.screen, self.font, "javelin800", "Копьё 800 г",
                                  actor_img=self.actor_img)
            elif ev["key"]=="obstacle150":
                attempts = 3 if level_code == "GTO1" else 1
                g = ObstacleGame(self.screen, self.font, 150,
                                 actor_img=self.actor_img, attempts_total=attempts)
            elif ev["key"]=="run1500":
                g = LongRunGame(self.screen, self.font, 1500,
                                actor_img=self.actor_img)
            elif ev["key"]=="rifle25":
                g = ShootingGame(self.screen, self.font,
                                 practice_shots=ev.get("practice_shots",3),
                                 scoring_shots=ev.get("scoring_shots",5))
            else:
                self._fadeout_music(150)
                continue

            res = g.run()
            self._fadeout_music(350)
            results[ev["key"]] = res
            status, note = evaluate_event(ev, res)
            if status == "не сдано":
                self.play_sound(self.snd_failure)
            elif status in ("сдано", "отлично"):
                self.play_sound(self.snd_applause)
            self.brief_card(f"{ev['title']}: {status}", note)

        # посчитать, все ли 3/3
        passed = 0
        for ev_key, res in results.items():
            edef = next(d for d in events if d["key"] == ev_key)
            st, _ = evaluate_event(edef, res)
            if st in ("сдано","отлично"):
                passed += 1
        got_badge = (passed == len(events))

        self.progress.setdefault(level_code, {})
        self.progress[level_code]["results"] = results
        self.progress[level_code]["badge"] = bool(got_badge)
        save_progress(self.progress)

        title = f"{level_code}: {'Значок получен!' if got_badge else 'Пока без значка'}"
        msg = "Итог уровня: " + (f"{passed}/{len(events)} дисциплин — зачёт (все пройдены)"
                                 if got_badge else f"{passed}/{len(events)} дисциплин — недостаточно (нужны все 3/3)")
        if got_badge:
            self.play_sound(self.snd_achievement)
        else:
            self.play_sound(self.snd_failure2)
        self.brief_card(title, msg)
        self._ensure_bg_loop_if_idle()

        # если прямо сейчас впервые собраны ВСЕ 3 значка — салют
        now_all = all(self.progress.get(c, {}).get("badge", False) for c in ("BGTO", "GTO1", "GTO2"))
        if (not was_all) and now_all:
            self.start_fireworks()

    def brief_card(self, title, msg):
        t = 0
        while t < 1.6:
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    play_exit_sound_and_quit()
            self.screen.fill((255,255,255))
            pg.draw.rect(self.screen, (235,240,250), pg.Rect(W//2-300, H//2-100, 600, 200), border_radius=16)
            self.draw_text(title, W//2, H//2-34, 28, (20,60,140), True)
            self.draw_text(msg, W//2, H//2+12, 24, (40,40,40), True)
            pg.display.flip()
            self.clock.tick(FPS)
            t += 1.0/FPS

    def dashboard(self):
        viewing = True
        while viewing:
            self._ensure_bg_loop_if_idle()
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    play_exit_sound_and_quit()
                if e.type == pg.KEYDOWN and e.key in (pg.K_ESCAPE, pg.K_RETURN, pg.K_SPACE):
                    viewing = False
            self.screen.fill((248,250,252))
            self.draw_text("Результаты", W//2, 40, 34, (20,30,60), True)
            y = 90
            for code, name in [("BGTO","БГТО"), ("GTO1","ГТО 1"), ("GTO2","ГТО 2")]:
                badge = self.progress.get(code,{}).get("badge", False)
                color = (30,160,60) if badge else (160,160,160)
                pg.draw.circle(self.screen, color, (70, y+20), 14)
                self.draw_text(name, 100, y, 28)
                evs = NORMS[code]["events"]
                res = self.progress.get(code,{}).get("results",{})
                yy = y+36
                for ev in evs:
                    v = res.get(ev["key"])
                    t_ev = ev["target_type"]
                    if t_ev=="time" and v is not None:
                        val = time_to_str(v); passv = time_to_str(ev["pass_seconds"])
                    elif t_ev=="dist" and v is not None:
                        val = f"{v:.2f} м"; passv = f"{ev['pass_meters']:.2f} м"
                    elif t_ev=="score" and v is not None:
                        val = f"{int(v)} оч."; passv = f"{ev['pass_score']} оч."
                    else:
                        val = "—"; passv = "—"
                    st, _ = evaluate_event(ev, v)
                    self.draw_text(f"• {ev['title']}: {val}  | порог: {passv}  → {st}", 120, yy, 22)
                    yy += 28
                y = yy + 10
            self.draw_text("Esc/Enter — назад", W//2, H-30, 20, (80,80,80), True)
            pg.display.flip()
            self.clock.tick(FPS)

    def help_screen(self):
        viewing = True
        margin_x = 60
        top = 70
        view_h = H - 120
        view_rect = pg.Rect(margin_x, top, W - margin_x*2, view_h)
        content = pg.Surface((view_rect.width, 1600), pg.SRCALPHA)
        y = 0
        self.draw_text("Справка по управлению", view_rect.width//2, y+10, 32, (20,30,60), True, content)
        y += 50
        self.draw_text("Общие клавиши", 0, y, 26, (30,30,30), False, content); y += 36
        self.draw_keycap("→", 0, y, surf=content); self.draw_text("— бежать / набирать скорость", 60, y+2, 22, surf=content); y += 34
        self.draw_keycap("Space", 0, y, 100, surf=content); self.draw_text("— прыжок/бросок (в фазе Aim) / выполнить попытку", 110, y+2, 22, surf=content); y += 34
        self.draw_keycap("↑", 0, y, surf=content); self.draw_keycap("↓", 50, y, surf=content); self.draw_text("— изменить угол", 110, y+2, 22, surf=content); y += 44
        self.draw_text("Прокрутка: колесо мыши • ↑/↓ • PgUp/PgDn • Home/End", 0, y, 20, (90,90,90), False, content); y += 36
        self.draw_text("Беговые дисциплины", 0, y, 26, (30,30,30), False, content); y += 36
        self.draw_text("Спринт 100 м (тапающий):", 0, y, 22, surf=content); y += 26
        self.draw_keycap("→", 20, y, surf=content); self.draw_text("— жмите ЧАСТО, а не держите — будет быстрее", 80, y+2, 22, surf=content); y += 34
        self.draw_text("110 м с барьерами:", 0, y, 22, surf=content); y += 26
        self.draw_keycap("→", 20, y, surf=content); self.draw_keycap("Space", 70, y, 100, surf=content)
        self.draw_text("— бежать; Space для настоящего прыжка над барьером", 180, y+2, 22, surf=content); y += 34
        self.draw_text("Полоса препятствий 150 м:", 0, y, 22, surf=content); y += 26
        self.draw_keycap("→", 20, y, surf=content); self.draw_keycap("Space", 70, y, 100, surf=content)
        self.draw_text("— бежать; Space для прыжка • столкновение теперь без подтормаживания", 180, y+2, 22, surf=content); y += 34
        self.draw_text("Бег 1500 м:", 0, y, 22, surf=content); y += 26
        self.draw_keycap("→", 20, y, surf=content); self.draw_text("— короткими нажатиями держите индикатор в зелёной зоне", 80, y+2, 22, surf=content); y += 40
        self.draw_text("Технические дисциплины", 0, y, 26, (30,30,30), False, content); y += 36
        self.draw_text("Прыжок в длину и метания:", 0, y, 22, surf=content); y += 26
        self.draw_keycap("→", 20, y, surf=content); self.draw_text("— обязательный разбег до конца шкалы", 80, y+2, 22, surf=content); y += 34
        self.draw_keycap("Space", 20, y, 100, surf=content); self.draw_text("— удерживать для силы (медленнее для гранаты)", 130, y+2, 22, surf=content); y += 34
        self.draw_keycap("↑", 20, y, surf=content); self.draw_keycap("↓", 70, y, surf=content)
        self.draw_text("— угол: прыжок оптимален ~20–25°, граната ~35–45°", 130, y+2, 22, surf=content); y += 34
        self.draw_text("Отпустите Space — выполнить попытку. 3 попытки, считается лучшая.", 20, y, 22, surf=content); y += 40
        self.draw_text("Стрельба (25 м, мишень №6, лёжа)", 0, y, 26, (30,30,30), False, content); y += 36
        self.draw_text("• 3 попытки; в каждой 3 пробных + 5 зачётных. В зачёт идёт лучший результат.", 20, y, 22, surf=content); y += 28
        self.draw_text("• Дрожь при дыхании смещает прицел; ветер сносит пулю (виден индикатор).", 20, y, 22, surf=content); y += 28
        self.draw_text("• Оценка по сумме очков за 5 зачётных (макс. 50).", 20, y, 22, surf=content); y += 40
        content_h = y + 10
        if content_h != content.get_height():
            c2 = pg.Surface((view_rect.width, content_h), pg.SRCALPHA)
            c2.blit(content, (0,0))
            content = c2

        offset = 0
        max_offset = max(0, content_h - view_h)

        while viewing:
            self._ensure_bg_loop_if_idle()
            for e in pg.event.get():
                if e.type == pg.QUIT:
                    play_exit_sound_and_quit()
                if e.type == pg.KEYDOWN:
                    if e.key in (pg.K_ESCAPE, pg.K_RETURN, pg.K_SPACE):
                        viewing = False
                    elif e.key == pg.K_UP:
                        offset = max(0, offset - 30)
                    elif e.key == pg.K_DOWN:
                        offset = min(max_offset, offset + 30)
                    elif e.key == pg.K_PAGEUP:
                        offset = max(0, offset - view_h + 40)
                    elif e.key == pg.K_PAGEDOWN:
                        offset = min(max_offset, offset + view_h - 40)
                    elif e.key == pg.K_HOME:
                        offset = 0
                    elif e.key == pg.K_END:
                        offset = max_offset
                if e.type == pg.MOUSEWHEEL:
                    offset = min(max_offset, max(0, offset - e.y * 40))

            self.screen.fill((248,248,252))
            self.draw_text("Справка", W//2, 30, 34, (20,30,60), True)
            pg.draw.rect(self.screen, (235,238,245), view_rect, border_radius=12)
            self.screen.set_clip(view_rect)
            self.screen.blit(content, (view_rect.x, view_rect.y - offset))
            self.screen.set_clip(None)
            if max_offset > 0:
                bar_x = view_rect.right + 10
                bar_y = view_rect.y
                bar_w = 10
                bar_h = view_rect.height
                pg.draw.rect(self.screen, (225,225,230), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
                thumb_h = max(30, int(bar_h * (view_h / content_h)))
                thumb_y = bar_y + int((bar_h - thumb_h) * (offset / max_offset))
                pg.draw.rect(self.screen, (150,150,170), (bar_x, thumb_y, bar_w, thumb_h), border_radius=6)
            self.draw_text("Esc/Enter/Space — назад • Колесо/↑↓ • PgUp/PgDn • Home/End — прокрутка",
                           W//2, H-28, 20, (80,80,80), True)
            pg.display.flip()
            self.clock.tick(FPS)

    def run(self):
        self.menu()

if __name__ == "__main__":
    App().run()

