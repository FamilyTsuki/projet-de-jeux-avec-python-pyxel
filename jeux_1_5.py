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
        self.last_exit_portal = None
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
        self.last_exit_portal = None
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
        if self.crossing_info is not None:
            return

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
        self.last_exit_portal = None

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

        if self.crossing_info is not None:
            jump_pressed = False

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
        if self.crossing_info is not None:
            pin = self.crossing_info["pin"]
            if pin.angle in (0, 180):
                self.vy = 0.0
            else:
                self.vx = 0.0
                self.vy += 0.4
                if self.vy > 12.0:
                    self.vy = 12.0
        else:
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

        if self.last_exit_portal is not None:
            p = self.last_exit_portal
            if abs((self.x + 8.0) - p.pos_x) > 16.0 or abs((self.y + 8.0) - p.pos_y) > 16.0:
                self.last_exit_portal = None

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

    def portaille(self):
        global t1, t2
        if not (t1.active and t2.active):
            self.crossing_info = None
            return

        if self.crossing_info is not None:
            pin = self.crossing_info["pin"]
            pout = self.crossing_info["pout"]
            lat = self.crossing_info["lat"]

            if pin.angle == 180:
                depth = (self.x + 16.0) - pin.pos_x
            elif pin.angle == 0:
                depth = pin.pos_x - self.x
            elif pin.angle == 270:
                depth = (self.y + 16.0) - pin.pos_y
            elif pin.angle == 90:
                depth = pin.pos_y - self.y
            else:
                depth = 0.0

            if depth >= 16.0:
                speed = math.hypot(self.vx, self.vy)
                if speed < 0.1:
                    speed = 0.1

                self.spawn_particles(pin.pos_x, pin.pos_y, 12 if pin == t1 else 9)

                if pout.angle == 0:
                    self.x = pout.pos_x + 1.0
                    self.y = pout.pos_y + lat - 8.0
                    self.vx = speed
                    self.vy = 0.0
                    self.dir = 1
                    self.en_saut = 0
                elif pout.angle == 180:
                    self.x = pout.pos_x - 17.0
                    self.y = pout.pos_y + lat - 8.0
                    self.vx = -speed
                    self.vy = 0.0
                    self.dir = -1
                    self.en_saut = 0
                elif pout.angle == 270:
                    self.x = pout.pos_x + lat - 8.0
                    self.y = pout.pos_y - 17.0
                    self.vx = 0.0
                    self.vy = -speed
                    self.en_saut = 0
                elif pout.angle == 90:
                    self.x = pout.pos_x + lat - 8.0
                    self.y = pout.pos_y + 1.0
                    self.vx = 0.0
                    self.vy = speed
                    self.en_saut = 0

                self.spawn_particles(pout.pos_x, pout.pos_y, 12 if pout == t1 else 9)
                self.teleport_cooldown = 12
                self.last_exit_portal = pout
                self.crossing_info = None

                try:
                    pyxel.play(3, 3)
                except Exception:
                    pass
                return

            elif depth <= 0.0:
                if pin.angle == 180:
                    self.x = pin.pos_x - 16.0
                elif pin.angle == 0:
                    self.x = pin.pos_x
                elif pin.angle == 270:
                    self.y = pin.pos_y - 16.0
                elif pin.angle == 90:
                    self.y = pin.pos_y
                self.crossing_info = None
                return

            else:
                self.crossing_info["depth"] = depth
                if pin.angle in (0, 180):
                    self.y = pin.pos_y + lat - 8.0
                    self.vy = 0.0
                    self.en_saut = 1
                else:
                    self.x = pin.pos_x + lat - 8.0
                    self.vx = 0.0
                return

        if self.teleport_cooldown > 0:
            return

        for pin, pout in ((t1, t2), (t2, t1)):
            if pin == self.last_exit_portal or not pin.active:
                continue

            if pin.angle == 180:
                lat = (self.y + 8.0) - pin.pos_y
                if abs(lat) <= 12.0 and self.vx > 0.0:
                    depth = (self.x + 16.0) - pin.pos_x
                    if 0.0 < depth < 16.0:
                        self.crossing_info = {"pin": pin, "pout": pout, "depth": depth, "lat": lat}
                        self.y = pin.pos_y + lat - 8.0
                        self.vy = 0.0
                        self.en_saut = 1
                        return
            elif pin.angle == 0:
                lat = (self.y + 8.0) - pin.pos_y
                if abs(lat) <= 12.0 and self.vx < 0.0:
                    depth = pin.pos_x - self.x
                    if 0.0 < depth < 16.0:
                        self.crossing_info = {"pin": pin, "pout": pout, "depth": depth, "lat": lat}
                        self.y = pin.pos_y + lat - 8.0
                        self.vy = 0.0
                        self.en_saut = 1
                        return
            elif pin.angle == 270:
                lat = (self.x + 8.0) - pin.pos_x
                if abs(lat) <= 8.0 and self.vy >= 0.0:
                    depth = (self.y + 16.0) - pin.pos_y
                    if 0.0 < depth < 16.0:
                        self.crossing_info = {"pin": pin, "pout": pout, "depth": depth, "lat": lat}
                        self.x = pin.pos_x + lat - 8.0
                        self.vx = 0.0
                        return
            elif pin.angle == 90:
                lat = (self.x + 8.0) - pin.pos_x
                if abs(lat) <= 8.0 and self.vy <= 0.0:
                    depth = pin.pos_y - self.y
                    if 0.0 < depth < 16.0:
                        self.crossing_info = {"pin": pin, "pout": pout, "depth": depth, "lat": lat}
                        self.x = pin.pos_x + lat - 8.0
                        self.vx = 0.0
                        return

    def colision(self):
        global t1, t2

        if self.crossing_info is not None:
            if self.y > 220.0:
                self.respawn()
            return

        if self.vy >= 0.0:
            for x1, x2, py in self.list_p:
                if x1 <= self.x + 8 <= x2:
                    if self.y + 16 >= py and (self.y + 16 - self.vy) <= py + 8:
                        in_floor = False
                        for p in (t1, t2):
                            if p.active and p.angle == 270 and abs(p.pos_y - py) < 6:
                                if p != self.last_exit_portal and self.teleport_cooldown == 0:
                                    if abs(p.pos_x - (self.x + 8)) <= 8:
                                        in_floor = True
                                        break
                        if not in_floor:
                            self.y = py - 16.0
                            self.vy = 0.0
                            self.en_saut = 1

        if self.x <= 0.0:
            in_portal = False
            for p in (t1, t2):
                if p.active and p.angle == 0 and abs(p.pos_x) < 6:
                    if p != self.last_exit_portal and abs((self.y + 8.0) - p.pos_y) <= 12.0:
                        in_portal = True
                        break
            if not in_portal:
                self.x = 0.0
                if self.vx < 0.0:
                    self.vx = 0.0

        if self.x + 16.0 >= 382.0:
            in_portal = False
            for p in (t1, t2):
                if p.active and p.angle == 180 and abs(p.pos_x - 382.0) < 6:
                    if p != self.last_exit_portal and abs((self.y + 8.0) - p.pos_y) <= 12.0:
                        in_portal = True
                        break
            if not in_portal:
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

        if p1.en_saut == 0:
            sprite_u = 48
        elif p1.is_moving:
            sprite_u = 0 if (pyxel.frame_count // 5) % 2 == 0 else 16
        else:
            sprite_u = 0

        sprite_w = 16 if p1.dir > 0 else -16

        if p1.crossing_info is not None:
            pin = p1.crossing_info["pin"]
            pout = p1.crossing_info["pout"]
            depth = p1.crossing_info["depth"]
            lat = p1.crossing_info["lat"]
            lat_clamped = min(6.0, max(-6.0, lat))

            if pin.angle == 180:
                pyxel.clip(0, 0, max(0, int(pin.pos_x)), 230)
            elif pin.angle == 0:
                pyxel.clip(max(0, int(pin.pos_x)), 0, 384, 230)
            elif pin.angle == 270:
                sy = int(pin.pos_y - self.cam_y)
                pyxel.clip(0, 0, 384, max(0, sy))
            elif pin.angle == 90:
                sy = int(pin.pos_y - self.cam_y)
                pyxel.clip(0, max(0, sy), 384, 230)

            pyxel.blt(p1.x, p1.y, 0, sprite_u, 32, sprite_w, 16, 7)

            if pout.angle == 0:
                pyxel.clip(max(0, int(pout.pos_x)), 0, 384, 230)
                pyxel.blt(pout.pos_x + depth - 16, pout.pos_y + lat_clamped - 8, 0, sprite_u, 32, 16, 16, 7)
            elif pout.angle == 180:
                pyxel.clip(0, 0, max(0, int(pout.pos_x)), 230)
                pyxel.blt(pout.pos_x - depth, pout.pos_y + lat_clamped - 8, 0, sprite_u, 32, -16, 16, 7)
            elif pout.angle == 270:
                sy = int(pout.pos_y - self.cam_y)
                pyxel.clip(0, 0, 384, max(0, sy))
                pyxel.blt(pout.pos_x + lat_clamped - 8, pout.pos_y - depth, 0, sprite_u, 32, sprite_w, 16, 7)
            elif pout.angle == 90:
                sy = int(pout.pos_y - self.cam_y)
                pyxel.clip(0, max(0, sy), 384, 230)
                pyxel.blt(pout.pos_x + lat_clamped - 8, pout.pos_y + depth - 16, 0, sprite_u, 32, sprite_w, 16, 7)

            pyxel.clip()
        else:
            pyxel.blt(p1.x, p1.y, 0, sprite_u, 32, sprite_w, 16, 7)

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
