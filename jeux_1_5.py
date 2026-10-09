import math
import pyxel


class Portail:
    def __init__(self, x=0, y=0, g=0, active=False):
        self.pos_x = x
        self.pos_y = y
        self.angle = g
        self.active = active

    def set_pos(self, x, y):
        self.pos_x = x
        self.pos_y = y

    def set_angle(self, a):
        self.angle = a

    def get_pos_x(self):
        return self.pos_x

    def get_pos_y(self):
        return self.pos_y

    def get_angle(self):
        return self.angle

    def draw(self, portal_id):
        if not self.active:
            return

        if portal_id == 1:
            col_outer = 12
            col_inner = 6
            col_core = 7
        else:
            col_outer = 9
            col_inner = 10
            col_core = 7

        pulse = (pyxel.frame_count // 4) % 2

        if self.angle in (0, 180):
            x = int(self.pos_x)
            y = int(self.pos_y)
            pyxel.rect(x - 3, y - 14, 6, 28, col_outer)
            pyxel.rect(x - 2, y - 12 + pulse, 4, 24 - pulse * 2, col_inner)
            pyxel.rect(x - 1, y - 8, 2, 16, col_core)
        else:
            x = int(self.pos_x)
            y = int(self.pos_y)
            pyxel.rect(x - 14, y - 3, 28, 6, col_outer)
            pyxel.rect(x - 12 + pulse, y - 2, 24 - pulse * 2, 4, col_inner)
            pyxel.rect(x - 8, y - 1, 16, 2, col_core)


class Joueur:
    def __init__(self):
        self.x = 100.0
        self.y = 80.0
        self.vx = 0.0
        self.vy = 0.0
        self.w = 16
        self.h = 16
        self.dir = 1
        self.en_saut = 1
        self.tc = 0
        self.teleport_cooldown = 0
        self.shot_beams = []
        self.particles = []
        self.is_moving = False
        self.crossing_info = None

        self.co = {
            "1": [self.x, self.y + 16, 0.0, 0.0],
            "2": [self.x + 16, self.y + 16, 0.0, 0.0],
            "3": [self.x, self.y, 0.0, 0.0],
            "4": [self.x + 16, self.y, 0.0, 0.0],
        }
        self.tran = {"1": [1, 1], "2": [1, 1], "3": [1, 1], "4": [1, 1]}

        self.list_m = [[0, -1000, 1000], [382, -1000, 1000]]
        self.list_p = [[0, 382, 100], [32, 64, 68]]

    def respawn(self):
        self.x = 100.0
        self.y = 80.0
        self.vx = 0.0
        self.vy = 0.0
        self.en_saut = 1
        self.teleport_cooldown = 0
        self.crossing_info = None

    def vecteur(self):
        cam_y = getattr(Jeux, "current_cam_y", -100)
        px = self.x + 8
        py = self.y + 8
        mx = pyxel.mouse_x
        my = pyxel.mouse_y + cam_y
        dx = mx - px
        if abs(dx) < 1e-4:
            dx = 1e-4 if dx >= 0 else -1e-4
        return (my - py) / dx

    def raycast_surfaces(self, mx, my):
        px = self.x + 8
        py = self.y + 8
        dx = mx - px
        dy = my - py
        dist = math.hypot(dx, dy)
        if dist < 1e-4:
            return None

        ux = dx / dist
        uy = dy / dist
        hits = []

        if ux < -1e-4:
            t = (0.0 - px) / ux
            hy = py + t * uy
            if -920 <= hy <= 100 and t > 0:
                hits.append((t, 0.0, hy, 0))

        if ux > 1e-4:
            t = (382.0 - px) / ux
            hy = py + t * uy
            if -920 <= hy <= 100 and t > 0:
                hits.append((t, 382.0, hy, 180))

        if uy > 1e-4:
            t = (100.0 - py) / uy
            hx = px + t * ux
            if 0 <= hx <= 382 and t > 0:
                hits.append((t, hx, 100.0, 270))

        if uy > 1e-4:
            t = (68.0 - py) / uy
            hx = px + t * ux
            if 32 <= hx <= 64 and t > 0:
                hits.append((t, hx, 68.0, 270))

        if uy < -1e-4:
            t = (-900.0 - py) / uy
            hx = px + t * ux
            if 0 <= hx <= 382 and t > 0:
                hits.append((t, hx, -900.0, 90))

        if not hits:
            return None

        hits.sort(key=lambda h: h[0])
        return hits[0]

    def recherche_mur(self, s):
        p = t1 if s == "l" else t2
        portal_id = 1 if s == "l" else 2
        beam_color = 12 if s == "l" else 9

        cam_y = getattr(Jeux, "current_cam_y", -100)
        mx = pyxel.mouse_x
        my = pyxel.mouse_y + cam_y

        hit = self.raycast_surfaces(mx, my)
        if hit is None:
            return

        t, hx, hy, angle = hit

        if angle in (0, 180):
            hy = max(-880.0, min(86.0, hy))
            p.set_pos(hx, hy)
        else:
            hx = max(16.0, min(366.0, hx))
            p.set_pos(hx, hy)

        p.set_angle(angle)
        p.active = True

        self.shot_beams.append({
            "x1": self.x + 8,
            "y1": self.y + 8,
            "x2": p.pos_x,
            "y2": p.pos_y,
            "color": beam_color,
            "time": 4
        })

        try:
            pyxel.play(1, portal_id)
        except Exception:
            pass

    def recherche_plat(self):
        pass

    def commande(self):
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.recherche_mur("l")
        if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            self.recherche_mur("r")

        moving_left = pyxel.btn(pyxel.KEY_Q) or pyxel.btn(pyxel.KEY_A) or pyxel.btn(pyxel.KEY_LEFT)
        moving_right = pyxel.btn(pyxel.KEY_D) or pyxel.btn(pyxel.KEY_RIGHT)
        self.is_moving = moving_left or moving_right

        if moving_right and not moving_left:
            self.vx = min(self.vx + 0.8, 4.0)
            self.dir = 1
        elif moving_left and not moving_right:
            self.vx = max(self.vx - 0.8, -4.0)
            self.dir = -1

        jump_pressed = (
            pyxel.btnp(pyxel.KEY_Z) or
            pyxel.btnp(pyxel.KEY_W) or
            pyxel.btnp(pyxel.KEY_UP) or
            pyxel.btnp(pyxel.KEY_SPACE)
        )

        if jump_pressed and self.en_saut == 1:
            self.vy = -6.5
            self.en_saut = 0
            self.tc = pyxel.frame_count
            try:
                pyxel.play(2, 4)
            except Exception:
                pass

        if pyxel.btnp(pyxel.KEY_R):
            self.respawn()

    def actu1(self):
        self.vy += 0.4
        if self.vy > 12.0:
            self.vy = 12.0

        if self.en_saut == 1:
            if not self.is_moving:
                self.vx *= 0.75
                if abs(self.vx) < 0.15:
                    self.vx = 0.0
        else:
            self.vx *= 0.985

        if self.teleport_cooldown > 0:
            self.teleport_cooldown -= 1

        self.shot_beams = [b for b in self.shot_beams if b["time"] > 0]
        for b in self.shot_beams:
            b["time"] -= 1

        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1
        self.particles = [p for p in self.particles if p["life"] > 0]

    def set_tran(self, n, m):
        self.tran[n] = m

    def spawn_particles(self, x, y, color):
        for _ in range(8):
            angle = (pyxel.frame_count * 23 + _ * 45) % 360
            rad = math.radians(angle)
            speed = 1.0 + (_ % 3) * 0.8
            self.particles.append({
                "x": x,
                "y": y,
                "vx": math.cos(rad) * speed,
                "vy": math.sin(rad) * speed,
                "color": color,
                "life": 12
            })

    def check_portal_penetration(self, portal):
        if not portal.active:
            return 0.0, 0.0

        if portal.angle == 0:
            if not (portal.pos_y - 12 <= self.y + 8 <= portal.pos_y + 12):
                return 0.0, 0.0
            depth = portal.pos_x - self.x
            lat = (self.y + 8) - portal.pos_y
        elif portal.angle == 180:
            if not (portal.pos_y - 12 <= self.y + 8 <= portal.pos_y + 12):
                return 0.0, 0.0
            depth = (self.x + 16) - portal.pos_x
            lat = (self.y + 8) - portal.pos_y
        elif portal.angle == 270:
            if not (portal.pos_x - 10 <= self.x + 8 <= portal.pos_x + 10):
                return 0.0, 0.0
            depth = (self.y + 16) - portal.pos_y
            lat = (self.x + 8) - portal.pos_x
        elif portal.angle == 90:
            if not (portal.pos_x - 10 <= self.x + 8 <= portal.pos_x + 10):
                return 0.0, 0.0
            depth = portal.pos_y - self.y
            lat = (self.x + 8) - portal.pos_x
        else:
            return 0.0, 0.0

        return depth, lat

    def portaille(self):
        global t1, t2
        if not (t1.active and t2.active):
            self.crossing_info = None
            return

        if self.teleport_cooldown > 0:
            self.crossing_info = None
            return

        d1, lat1 = self.check_portal_penetration(t1)
        d2, lat2 = self.check_portal_penetration(t2)

        if d1 > 0:
            pin = t1
            pout = t2
            depth = d1
            lat = lat1
        elif d2 > 0:
            pin = t2
            pout = t1
            depth = d2
            lat = lat2
        else:
            self.crossing_info = None
            return

        if depth >= 16.0:
            speed = math.hypot(self.vx, self.vy)
            exit_speed = max(speed, 4.0)

            self.spawn_particles(pin.pos_x, pin.pos_y, 12 if pin == t1 else 9)

            if pout.angle == 0:
                self.x = pout.pos_x + 1.0
                self.y = pout.pos_y + lat - 8.0
                self.vx = exit_speed
                self.vy = 0.0
                self.en_saut = 0
            elif pout.angle == 180:
                self.x = pout.pos_x - 16.0 - 1.0
                self.y = pout.pos_y + lat - 8.0
                self.vx = -exit_speed
                self.vy = 0.0
                self.en_saut = 0
            elif pout.angle == 270:
                self.x = pout.pos_x + lat - 8.0
                self.y = pout.pos_y - 16.0 - 2.0
                self.vx = self.vx * 0.4
                self.vy = -max(exit_speed, 6.5)
                self.en_saut = 0
            elif pout.angle == 90:
                self.x = pout.pos_x + lat - 8.0
                self.y = pout.pos_y + 1.0
                self.vx = self.vx * 0.4
                self.vy = max(exit_speed, 3.5)
                self.en_saut = 0

            self.spawn_particles(pout.pos_x, pout.pos_y, 12 if pout == t1 else 9)
            self.teleport_cooldown = 8
            self.crossing_info = None

            try:
                pyxel.play(3, 3)
            except Exception:
                pass
        else:
            self.crossing_info = {
                "pin": pin,
                "pout": pout,
                "depth": depth,
                "lat": lat
            }

    def colision(self):
        global t1, t2

        if self.vy >= 0.0:
            for x1, x2, py in self.list_p:
                if x1 <= self.x + 8 <= x2:
                    if self.y + 16 >= py and (self.y + 16 - self.vy) <= py + 8:
                        in_floor = False
                        for p in (t1, t2):
                            if p.active and p.angle == 270 and abs(p.pos_y - py) < 6:
                                if abs(p.pos_x - (self.x + 8)) <= 10:
                                    in_floor = True
                                    break
                        if not in_floor:
                            self.y = py - 16.0
                            self.vy = 0.0
                            self.en_saut = 1

        if self.x <= 0.0:
            in_left = False
            for p in (t1, t2):
                if p.active and p.angle == 0 and abs(p.pos_x) < 6:
                    if abs(p.pos_y - (self.y + 8)) <= 12:
                        in_left = True
                        break
            if not in_left:
                self.x = 0.0
                if self.vx < 0.0:
                    self.vx = 0.0

        if self.x + 16.0 >= 382.0:
            in_right = False
            for p in (t1, t2):
                if p.active and p.angle == 180 and abs(p.pos_x - 382) < 6:
                    if abs(p.pos_y - (self.y + 8)) <= 12:
                        in_right = True
                        break
            if not in_right:
                self.x = 382.0 - 16.0
                if self.vx > 0.0:
                    self.vx = 0.0

        if self.y > 220.0:
            self.respawn()

    def actu2(self):
        self.x += self.vx
        self.y += self.vy

        self.co["1"] = [self.x, self.y + 16.0, self.vx, self.vy]
        self.co["2"] = [self.x + 16.0, self.y + 16.0, self.vx, self.vy]
        self.co["3"] = [self.x, self.y, self.vx, self.vy]
        self.co["4"] = [self.x + 16.0, self.y, self.vx, self.vy]


class Jeux:
    current_cam_y = -100

    def __init__(self):
        pyxel.init(384, 230, title="Portal 2D - Nuit du Code", fps=30)
        pyxel.load("my_resource.pyxres")

        try:
            pyxel.sounds[1].set("c3g3c4", "t", "7", "v", 3)
            pyxel.sounds[2].set("e3b3e4", "t", "7", "v", 3)
            pyxel.sounds[3].set("g2c3e3g3", "s", "7", "f", 3)
            pyxel.sounds[4].set("c3e3g3", "s", "6", "f", 4)
        except Exception:
            pass

        global p1, t1, t2
        t1 = Portail(120, 100, 270, True)
        t2 = Portail(382, 40, 180, True)
        p1 = Joueur()

        self.cam_y = -100.0
        self.show_help = True

        pyxel.run(self.update, self.draw)

    def update(self):
        global p1
        p1.commande()
        p1.actu1()
        p1.portaille()
        p1.colision()
        p1.actu2()

        if pyxel.btnp(pyxel.KEY_H):
            self.show_help = not self.show_help

    def draw_slice(self, portal, depth, lat, is_exit, col=10):
        d = min(16.0, max(0.0, depth))
        if d <= 0:
            return

        lat_clamped = min(6.0, max(-6.0, lat))

        if is_exit:
            if portal.angle == 0:
                x1, x2 = portal.pos_x, portal.pos_x + d
                y1, y2 = portal.pos_y + lat_clamped - 8, portal.pos_y + lat_clamped + 8
                pyxel.line(x2, y1, x2, y2, col)
                pyxel.line(x1, y1, x2, y1, col)
                pyxel.line(x1, y2, x2, y2, col)
            elif portal.angle == 180:
                x1, x2 = portal.pos_x - d, portal.pos_x
                y1, y2 = portal.pos_y + lat_clamped - 8, portal.pos_y + lat_clamped + 8
                pyxel.line(x1, y1, x1, y2, col)
                pyxel.line(x1, y1, x2, y1, col)
                pyxel.line(x1, y2, x2, y2, col)
            elif portal.angle == 270:
                x1, x2 = portal.pos_x + lat_clamped - 8, portal.pos_x + lat_clamped + 8
                y1, y2 = portal.pos_y - d, portal.pos_y
                pyxel.line(x1, y1, x2, y1, col)
                pyxel.line(x1, y1, x1, y2, col)
                pyxel.line(x2, y1, x2, y2, col)
            elif portal.angle == 90:
                x1, x2 = portal.pos_x + lat_clamped - 8, portal.pos_x + lat_clamped + 8
                y1, y2 = portal.pos_y, portal.pos_y + d
                pyxel.line(x1, y2, x2, y2, col)
                pyxel.line(x1, y1, x1, y2, col)
                pyxel.line(x2, y1, x2, y2, col)
        else:
            rem = 16.0 - d
            if portal.angle == 0:
                x1, x2 = portal.pos_x, portal.pos_x + rem
                y1, y2 = portal.pos_y + lat_clamped - 8, portal.pos_y + lat_clamped + 8
                pyxel.line(x2, y1, x2, y2, col)
                pyxel.line(x1, y1, x2, y1, col)
                pyxel.line(x1, y2, x2, y2, col)
            elif portal.angle == 180:
                x1, x2 = portal.pos_x - rem, portal.pos_x
                y1, y2 = portal.pos_y + lat_clamped - 8, portal.pos_y + lat_clamped + 8
                pyxel.line(x1, y1, x1, y2, col)
                pyxel.line(x1, y1, x2, y1, col)
                pyxel.line(x1, y2, x2, y2, col)
            elif portal.angle == 270:
                x1, x2 = portal.pos_x + lat_clamped - 8, portal.pos_x + lat_clamped + 8
                y1, y2 = portal.pos_y - rem, portal.pos_y
                pyxel.line(x1, y1, x2, y1, col)
                pyxel.line(x1, y1, x1, y2, col)
                pyxel.line(x2, y1, x2, y2, col)
            elif portal.angle == 90:
                x1, x2 = portal.pos_x + lat_clamped - 8, portal.pos_x + lat_clamped + 8
                y1, y2 = portal.pos_y, portal.pos_y + rem
                pyxel.line(x1, y2, x2, y2, col)
                pyxel.line(x1, y1, x1, y2, col)
                pyxel.line(x2, y1, x2, y2, col)

    def draw(self):
        global p1, t1, t2
        pyxel.cls(0)

        target_cam_y = p1.y - 120.0
        clamped_cam = min(-100.0, max(-820.0, target_cam_y))
        self.cam_y += (clamped_cam - self.cam_y) * 0.15
        Jeux.current_cam_y = self.cam_y
        pyxel.camera(0, self.cam_y)

        pyxel.bltm(0, -924, 0, 0, 0, 416, 1032)

        for beam in p1.shot_beams:
            pyxel.line(beam["x1"], beam["y1"], beam["x2"], beam["y2"], beam["color"])

        for pt in p1.particles:
            pyxel.pset(pt["x"], pt["y"], pt["color"])

        t1.draw(1)
        t2.draw(2)

        box_col = 10

        if p1.crossing_info is not None:
            pin = p1.crossing_info["pin"]
            pout = p1.crossing_info["pout"]
            depth = p1.crossing_info["depth"]
            lat = p1.crossing_info["lat"]
            self.draw_slice(pin, depth, lat, False, box_col)
            self.draw_slice(pout, depth, lat, True, box_col)
        else:
            pyxel.line(p1.co["1"][0], p1.co["1"][1], p1.co["2"][0], p1.co["2"][1], box_col)
            pyxel.line(p1.co["2"][0], p1.co["2"][1], p1.co["4"][0], p1.co["4"][1], box_col)
            pyxel.line(p1.co["4"][0], p1.co["4"][1], p1.co["3"][0], p1.co["3"][1], box_col)
            pyxel.line(p1.co["3"][0], p1.co["3"][1], p1.co["1"][0], p1.co["1"][1], box_col)

            cx = (p1.co["1"][0] + p1.co["2"][0]) / 2
            cy = (p1.co["1"][1] + p1.co["3"][1]) / 2
            pyxel.rect(cx - 1, cy - 1, 2, 2, 3)

            eye_x = p1.x + (11 if p1.dir > 0 else 3)
            eye_y = p1.y + 5
            pyxel.rect(eye_x, eye_y, 2, 2, 11)

        pyxel.camera()

        pyxel.rect(0, 0, 384, 13, 0)
        pyxel.line(0, 13, 384, 13, 5)

        pyxel.text(8, 4, "PORTAL 2D", 7)
        info_txt = f"X:{int(p1.x)} Y:{int(p1.y)} VX:{p1.vx:.1f} VY:{p1.vy:.1f}"
        pyxel.text(70, 4, info_txt, 6)

        p1_lbl = "P1: " + ("OK" if t1.active else "--")
        p2_lbl = "P2: " + ("OK" if t2.active else "--")
        pyxel.text(260, 4, p1_lbl, 12 if t1.active else 5)
        pyxel.text(320, 4, p2_lbl, 9 if t2.active else 4)

        if self.show_help:
            pyxel.rect(0, 218, 384, 12, 0)
            pyxel.line(0, 217, 384, 217, 5)
            pyxel.text(6, 221, "ZQSD/WASD: Deplacer | Clic G: P1 Bleu | Clic D: P2 Orange | R: Respawn | H: Aide", 7)

        mx = pyxel.mouse_x
        my = pyxel.mouse_y
        pyxel.circb(mx, my, 4, 7)
        pyxel.pset(mx - 2, my, 12 if t1.active else 5)
        pyxel.pset(mx + 2, my, 9 if t2.active else 4)
        pyxel.pset(mx, my, 7)


global t1, t2, p1
t1 = Portail(120, 100, 270, True)
t2 = Portail(382, 40, 180, True)
p1 = Joueur()

if __name__ == "__main__":
    Jeux()
