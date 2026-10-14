import math

import pyxel

SCREEN_WIDTH = 384
SCREEN_HEIGHT = 230
FPS = 30

GRAVITY = 0.4
MAX_FALL_SPEED = 12.0
JUMP_FORCE = -6.5
MOVE_ACCELERATION = 0.8
MAX_MOVE_SPEED = 4.0
GROUND_FRICTION = 0.75
AIR_FRICTION = 0.985
MIN_VELOCITY = 0.15

PLAYER_START_X = 100.0
PLAYER_START_Y = 80.0
FALL_LIMIT_Y = 220.0

PORTAL_COLORS = {
    1: (12, 6, 7),
    2: (9, 10, 7),
}

PLATFORMS = (
    (0, 382, 100),
    (32, 64, 68),
)

SURFACES = (
    {"type": "vertical", "coord": 0.0, "min_span": -920.0, "max_span": 100.0, "angle": 0},
    {"type": "vertical", "coord": 382.0, "min_span": -920.0, "max_span": 100.0, "angle": 180},
    {"type": "horizontal", "coord": 100.0, "min_span": 0.0, "max_span": 382.0, "angle": 270},
    {"type": "horizontal", "coord": 68.0, "min_span": 32.0, "max_span": 64.0, "angle": 270},
    {"type": "horizontal", "coord": -900.0, "min_span": 0.0, "max_span": 382.0, "angle": 90},
)


class Portail:
    def __init__(self, x=0, y=0, angle=0, active=False):
        self.pos_x = x
        self.pos_y = y
        self.angle = angle
        self.active = active

    def set_pos(self, x, y):
        self.pos_x = x
        self.pos_y = y

    def set_angle(self, angle):
        self.angle = angle

    def get_pos_x(self):
        return self.pos_x

    def get_pos_y(self):
        return self.pos_y

    def get_angle(self):
        return self.angle

    def draw(self, portal_id):
        if not self.active:
            return

        color_outer, color_inner, color_core = PORTAL_COLORS.get(
            portal_id, (9, 10, 7)
        )
        pulse = (pyxel.frame_count // 4) % 2
        portal_x = int(self.pos_x)
        portal_y = int(self.pos_y)

        if self.angle in (0, 180):
            pyxel.rect(portal_x - 3, portal_y - 14, 6, 28, color_outer)
            pyxel.rect(
                portal_x - 2,
                portal_y - 12 + pulse,
                4,
                24 - pulse * 2,
                color_inner,
            )
            pyxel.rect(portal_x - 1, portal_y - 8, 2, 16, color_core)
        else:
            pyxel.rect(portal_x - 14, portal_y - 3, 28, 6, color_outer)
            pyxel.rect(
                portal_x - 12 + pulse,
                portal_y - 2,
                24 - pulse * 2,
                4,
                color_inner,
            )
            pyxel.rect(portal_x - 8, portal_y - 1, 16, 2, color_core)


class Joueur:
    def __init__(self):
        self.x = PLAYER_START_X
        self.y = PLAYER_START_Y
        self.velocityX = 0.0
        self.velocityY = 0.0
        self.largeur = 16
        self.hauteur = 16
        self.direction = 1
        self.is_on_ground = True
        self.teleport_cooldown = 0
        self.shot_beams = []
        self.particles = []
        self.is_moving = False
        self.crossing_info = None
        self.liste_plateformes = list(PLATFORMS)

    def respawn(self):
        self.x = PLAYER_START_X
        self.y = PLAYER_START_Y
        self.velocityX = 0.0
        self.velocityY = 0.0
        self.is_on_ground = True
        self.teleport_cooldown = 0
        self.crossing_info = None

    def gerer_entrees(self):
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.recherche_mur("l")
        if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            self.recherche_mur("r")

        moving_left = (
            pyxel.btn(pyxel.KEY_Q)
            or pyxel.btn(pyxel.KEY_A)
            or pyxel.btn(pyxel.KEY_LEFT)
        )
        moving_right = pyxel.btn(pyxel.KEY_D) or pyxel.btn(pyxel.KEY_RIGHT)
        self.is_moving = moving_left or moving_right

        if moving_right and not moving_left:
            self.velocityX = min(self.velocityX + MOVE_ACCELERATION, MAX_MOVE_SPEED)
            self.direction = 1
        elif moving_left and not moving_right:
            self.velocityX = max(self.velocityX - MOVE_ACCELERATION, -MAX_MOVE_SPEED)
            self.direction = -1

        jump_pressed = (
            pyxel.btnp(pyxel.KEY_Z)
            or pyxel.btnp(pyxel.KEY_W)
            or pyxel.btnp(pyxel.KEY_UP)
            or pyxel.btnp(pyxel.KEY_SPACE)
        )

        if self.crossing_info is not None:
            jump_pressed = False

        if jump_pressed and self.is_on_ground:
            self.velocityY = JUMP_FORCE
            self.is_on_ground = False
            try:
                pyxel.play(2, 4)
            except BaseException:
                pass

        if pyxel.btnp(pyxel.KEY_R):
            self.respawn()

    def raycast_surfaces(self, target_mouse_x, target_mouse_y):
        origin_x = self.x + 8.0
        origin_y = self.y + 8.0
        delta_x = target_mouse_x - origin_x
        delta_y = target_mouse_y - origin_y
        distance = math.hypot(delta_x, delta_y)
        if distance < 1e-4:
            return None

        dir_x = delta_x / distance
        dir_y = delta_y / distance
        surface_hits = []

        for surface in SURFACES:
            if surface["type"] == "vertical":
                if (surface["angle"] == 0 and dir_x < -1e-4) or (surface["angle"] == 180 and dir_x > 1e-4):
                    ray_distance = (surface["coord"] - origin_x) / dir_x
                    hit_y = origin_y + ray_distance * dir_y
                    if ray_distance > 0 and surface["min_span"] <= hit_y <= surface["max_span"]:
                        surface_hits.append((ray_distance, surface["coord"], hit_y, surface["angle"]))
            else:
                if (surface["angle"] == 270 and dir_y > 1e-4) or (surface["angle"] == 90 and dir_y < -1e-4):
                    ray_distance = (surface["coord"] - origin_y) / dir_y
                    hit_x = origin_x + ray_distance * dir_x
                    if ray_distance > 0 and surface["min_span"] <= hit_x <= surface["max_span"]:
                        surface_hits.append((ray_distance, hit_x, surface["coord"], surface["angle"]))

        if not surface_hits:
            return None

        surface_hits.sort(key=lambda hit: hit[0])
        return surface_hits[0]

    def recherche_mur(self, portal_side):
        if self.crossing_info is not None:
            return

        is_left = portal_side == "l"
        portal = Portal1 if is_left else Portal2
        portal_id = 1 if is_left else 2
        beam_color = 12 if is_left else 9

        camera_y = getattr(Jeux, "current_camera_y", -100.0)
        target_mouse_x = pyxel.mouse_x
        target_mouse_y = pyxel.mouse_y + camera_y

        hit = self.raycast_surfaces(target_mouse_x, target_mouse_y)
        if hit is None:
            return

        _, hit_x, hit_y, surface_angle = hit

        if surface_angle in (0, 180):
            hit_y = max(-880.0, min(86.0, hit_y))
        else:
            hit_x = max(16.0, min(366.0, hit_x))

        portal.set_pos(hit_x, hit_y)
        portal.set_angle(surface_angle)
        portal.active = True

        self.shot_beams.append(
            {
                "x1": self.x + 8.0,
                "y1": self.y + 8.0,
                "x2": portal.pos_x,
                "y2": portal.pos_y,
                "color": beam_color,
                "time": 4,
            }
        )

        try:
            pyxel.play(1, portal_id)
        except BaseException:
            pass

    def appliquer_modificateurs_vitesse(self):
        if self.crossing_info is not None:
            portal_entry = self.crossing_info["portal_entry"]
            if portal_entry.angle in (0, 180):
                self.velocityY = 0.0
                if not self.is_moving:
                    self.velocityX *= GROUND_FRICTION
                    if abs(self.velocityX) < MIN_VELOCITY:
                        self.velocityX = 0.0
            else:
                self.velocityX = 0.0
        else:
            self.velocityY += GRAVITY
            if self.velocityY > MAX_FALL_SPEED:
                self.velocityY = MAX_FALL_SPEED

            if self.is_on_ground:
                if not self.is_moving:
                    self.velocityX *= GROUND_FRICTION
                    if abs(self.velocityX) < MIN_VELOCITY:
                        self.velocityX = 0.0
            else:
                self.velocityX *= AIR_FRICTION

        if self.teleport_cooldown > 0:
            self.teleport_cooldown -= 1

        self.shot_beams = [beam for beam in self.shot_beams if beam["time"] > 0]
        for beam in self.shot_beams:
            beam["time"] -= 1

        for particle in self.particles:
            particle["x"] += particle["velocityX"]
            particle["y"] += particle["velocityY"]
            particle["life"] -= 1
        self.particles = [
            particle for particle in self.particles if particle["life"] > 0
        ]

    def appliquer_deplacement(self):
        self.x += self.velocityX
        self.y += self.velocityY

    def spawn_particles(self, x, y, color):
        for index in range(8):
            angle = (pyxel.frame_count * 23 + index * 45) % 360
            radians = math.radians(angle)
            speed = 1.0 + (index % 3) * 0.8
            self.particles.append(
                {
                    "x": x,
                    "y": y,
                    "velocityX": math.cos(radians) * speed,
                    "velocityY": math.sin(radians) * speed,
                    "color": color,
                    "life": 12,
                }
            )

    def calculer_profondeur_portail(self, portal):
        if portal.angle == 180:
            return (self.x + 16.0) - portal.pos_x
        if portal.angle == 0:
            return portal.pos_x - self.x
        if portal.angle == 270:
            return (self.y + 16.0) - portal.pos_y
        if portal.angle == 90:
            return portal.pos_y - self.y
        return 0.0

    def verifier_entree_portail(self, portal_entry, portal_exit):
        if portal_entry.angle in (0, 180):
            lateral_offset = (self.y + 8.0) - portal_entry.pos_y
            if abs(lateral_offset) > 12.0:
                return None
            if portal_entry.angle == 180 and self.velocityX <= 0.0:
                return None
            if portal_entry.angle == 0 and self.velocityX >= 0.0:
                return None
        else:
            lateral_offset = (self.x + 8.0) - portal_entry.pos_x
            if abs(lateral_offset) > 8.0:
                return None
            if portal_entry.angle == 270 and self.velocityY < 0.0:
                return None
            if portal_entry.angle == 90 and self.velocityY > 0.0:
                return None

        entry_depth = self.calculer_profondeur_portail(portal_entry)
        if 0.0 < entry_depth < 16.0:
            return {
                "portal_entry": portal_entry,
                "portal_exit": portal_exit,
                "entry_depth": entry_depth,
                "lateral_offset": lateral_offset,
            }
        return None

    def teleporter_sortie(self, portal_entry, portal_exit, lateral_offset, exit_speed):
        self.spawn_particles(
            portal_entry.pos_x,
            portal_entry.pos_y,
            12 if portal_entry == Portal1 else 9,
        )

        if portal_exit.angle == 0:
            self.x = portal_exit.pos_x + 1.0
            self.y = portal_exit.pos_y + lateral_offset - 8.0
            self.velocityX = exit_speed
            self.velocityY = 0.0
            self.direction = 1
            self.is_on_ground = False
        elif portal_exit.angle == 180:
            self.x = portal_exit.pos_x - 17.0
            self.y = portal_exit.pos_y + lateral_offset - 8.0
            self.velocityX = -exit_speed
            self.velocityY = 0.0
            self.direction = -1
            self.is_on_ground = False
        elif portal_exit.angle == 270:
            self.x = portal_exit.pos_x + lateral_offset - 8.0
            if exit_speed < 1.0:
                self.y = portal_exit.pos_y - 16.0
                self.velocityX = 0.0
                self.velocityY = 0.0
                self.is_on_ground = True
            else:
                self.y = portal_exit.pos_y - 16.0
                self.velocityX = 0.0
                self.velocityY = -exit_speed
                self.is_on_ground = False
        elif portal_exit.angle == 90:
            self.x = portal_exit.pos_x + lateral_offset - 8.0
            self.y = portal_exit.pos_y + 1.0
            self.velocityX = 0.0
            self.velocityY = exit_speed
            self.is_on_ground = False

        self.spawn_particles(
            portal_exit.pos_x,
            portal_exit.pos_y,
            12 if portal_exit == Portal1 else 9,
        )
        self.teleport_cooldown = (
            15 if (portal_exit.angle == 270 and exit_speed < 1.0) else 3
        )
        self.crossing_info = None

        try:
            pyxel.play(3, 3)
        except BaseException:
            pass

    def annuler_traversee(self, portal_entry):
        if portal_entry.angle == 180:
            self.x = portal_entry.pos_x - 16.0
        elif portal_entry.angle == 0:
            self.x = portal_entry.pos_x
        elif portal_entry.angle == 270:
            self.y = portal_entry.pos_y - 16.0
        elif portal_entry.angle == 90:
            self.y = portal_entry.pos_y
        self.crossing_info = None

    def gerer_portails(self, portal_1=None, portal_2=None):
        p1 = portal_1 if portal_1 is not None else Portal1
        p2 = portal_2 if portal_2 is not None else Portal2

        if not (p1.active and p2.active):
            self.crossing_info = None
            return

        if self.crossing_info is not None:
            portal_entry = self.crossing_info["portal_entry"]
            portal_exit = self.crossing_info["portal_exit"]
            lateral_offset = self.crossing_info["lateral_offset"]

            entry_depth = self.calculer_profondeur_portail(portal_entry)

            if entry_depth >= 16.0:
                exit_speed = max(math.hypot(self.velocityX, self.velocityY), 0.1)
                self.teleporter_sortie(
                    portal_entry, portal_exit, lateral_offset, exit_speed
                )
                return

            if entry_depth <= 0.0:
                self.annuler_traversee(portal_entry)
                return

            self.crossing_info["entry_depth"] = entry_depth
            if portal_entry.angle in (0, 180):
                self.y = portal_entry.pos_y + lateral_offset - 8.0
                self.velocityY = 0.0
                self.is_on_ground = True
            else:
                self.x = portal_entry.pos_x + lateral_offset - 8.0
                self.velocityX = 0.0
            return

        if self.teleport_cooldown > 0:
            return

        for portal_entry, portal_exit in ((p1, p2), (p2, p1)):
            if not portal_entry.active or not portal_exit.active:
                continue
            crossing = self.verifier_entree_portail(portal_entry, portal_exit)
            if crossing is not None:
                self.crossing_info = crossing
                if portal_entry.angle in (0, 180):
                    self.y = portal_entry.pos_y + crossing["lateral_offset"] - 8.0
                    self.velocityY = 0.0
                    self.is_on_ground = True
                else:
                    self.x = portal_entry.pos_x + crossing["lateral_offset"] - 8.0
                    self.velocityX = 0.0
                return

    def gerer_collisions(self, portal_1=None, portal_2=None):
        portals = (
            portal_1 if portal_1 is not None else Portal1,
            portal_2 if portal_2 is not None else Portal2,
        )

        if self.crossing_info is not None:
            if self.y > FALL_LIMIT_Y:
                self.respawn()
            return

        if self.velocityY >= 0.0:
            for x_min, x_max, platform_y in self.liste_plateformes:
                if x_min <= self.x + 8.0 <= x_max:
                    if (
                        self.y + 16.0 >= platform_y
                        and (self.y + 16.0 - self.velocityY) <= platform_y + 8.0
                    ):
                        is_over_portal_floor = False
                        for portal in portals:
                            if (
                                portal.active
                                and portal.angle == 270
                                and abs(portal.pos_y - platform_y) < 6
                            ):
                                if self.teleport_cooldown == 0:
                                    if abs(portal.pos_x - (self.x + 8.0)) <= 8:
                                        is_over_portal_floor = True
                                        break
                        if not is_over_portal_floor:
                            self.y = platform_y - 16.0
                            self.velocityY = 0.0
                            self.is_on_ground = True

        if self.x <= 0.0:
            is_in_portal_wall = any(
                portal.active
                and portal.angle == 0
                and abs(portal.pos_x) < 6
                and abs((self.y + 8.0) - portal.pos_y) <= 12.0
                for portal in portals
            )
            if not is_in_portal_wall:
                self.x = 0.0
                if self.velocityX < 0.0:
                    self.velocityX = 0.0

        if self.x + 16.0 >= 382.0:
            is_in_portal_wall = any(
                portal.active
                and portal.angle == 180
                and abs(portal.pos_x - 382.0) < 6
                and abs((self.y + 8.0) - portal.pos_y) <= 12.0
                for portal in portals
            )
            if not is_in_portal_wall:
                self.x = 382.0 - 16.0
                if self.velocityX > 0.0:
                    self.velocityX = 0.0

        if self.y > FALL_LIMIT_Y:
            self.respawn()

    def appliquer_clip_portail(self, portal, camera_y):
        portal_x = int(portal.pos_x)
        screen_y = int(portal.pos_y - camera_y)
        if portal.angle == 0:
            pyxel.clip(max(0, portal_x), 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        elif portal.angle == 180:
            pyxel.clip(0, 0, max(0, portal_x), SCREEN_HEIGHT)
        elif portal.angle == 270:
            pyxel.clip(0, 0, SCREEN_WIDTH, max(0, screen_y))
        elif portal.angle == 90:
            pyxel.clip(0, max(0, screen_y), SCREEN_WIDTH, SCREEN_HEIGHT)

    def calculer_coordonnees_sprite_sortie(
        self, portal_exit, depth, lateral_clamped, sprite_w
    ):
        if portal_exit.angle == 0:
            return (
                portal_exit.pos_x + depth - 16.0,
                portal_exit.pos_y + lateral_clamped - 8.0,
                16,
            )
        if portal_exit.angle == 180:
            return (
                portal_exit.pos_x - depth,
                portal_exit.pos_y + lateral_clamped - 8.0,
                -16,
            )
        if portal_exit.angle == 270:
            return (
                portal_exit.pos_x + lateral_clamped - 8.0,
                portal_exit.pos_y - depth,
                sprite_w,
            )
        if portal_exit.angle == 90:
            return (
                portal_exit.pos_x + lateral_clamped - 8.0,
                portal_exit.pos_y + depth - 16.0,
                sprite_w,
            )
        return self.x, self.y, sprite_w

    def afficher_joueur(self, jeux):
        """draw player start"""
        if not self.is_on_ground:
            sprite_u = 48
        elif self.is_moving:
            sprite_u = 0 if (pyxel.frame_count // 5) % 2 == 0 else 16
        else:
            sprite_u = 0

        sprite_w = 16 if self.direction > 0 else -16

        if self.crossing_info is None:
            pyxel.blt(self.x, self.y, 0, sprite_u, 32, sprite_w, 16, 7)
            return

        portal_entry = self.crossing_info["portal_entry"]
        portal_exit = self.crossing_info["portal_exit"]
        entry_depth = self.crossing_info["entry_depth"]
        lateral_clamped = min(6.0, max(-6.0, self.crossing_info["lateral_offset"]))

        self.appliquer_clip_portail(portal_entry, jeux.camera_y)
        pyxel.blt(self.x, self.y, 0, sprite_u, 32, sprite_w, 16, 7)

        exit_x, exit_y, exit_sprite_w = self.calculer_coordonnees_sprite_sortie(
            portal_exit, entry_depth, lateral_clamped, sprite_w
        )
        self.appliquer_clip_portail(portal_exit, jeux.camera_y)
        pyxel.blt(exit_x, exit_y, 0, sprite_u, 32, exit_sprite_w, 16, 7)
        pyxel.clip()

    commande = gerer_entrees
    aplicationModifierToVelocity = appliquer_modificateurs_vitesse
    portaille = gerer_portails
    colision = gerer_collisions
    aplicationVelocityToCoordonate = appliquer_deplacement
    drawPlayer = afficher_joueur


class Jeux:
    current_camera_y = -100.0
    current_cam_y = -100.0

    def __init__(self):
        pyxel.init(
            SCREEN_WIDTH, SCREEN_HEIGHT, title="Portal 2D - Nuit du Code", fps=FPS
        )
        pyxel.load("my_resource.pyxres")
        self.init_audio()

        global Player, Portal1, Portal2
        Portal1 = Portail(120, 100, 270, True)
        Portal2 = Portail(382, 40, 180, True)
        Player = Joueur()

        self.camera_y = -100.0

        pyxel.run(self.update, self.draw)

    def init_audio(self):
        try:
            pyxel.sounds[1].set("c3g3c4", "t", "7", "v", 3)
            pyxel.sounds[2].set("e3b3e4", "t", "7", "v", 3)
            pyxel.sounds[3].set("g2c3e3g3", "s", "7", "f", 3)
            pyxel.sounds[4].set("c3e3g3", "s", "6", "f", 4)
        except BaseException:
            pass

    def update(self):
        global Player, Portal1, Portal2
        Player.gerer_entrees()
        Player.appliquer_modificateurs_vitesse()
        Player.gerer_portails(Portal1, Portal2)
        Player.gerer_collisions(Portal1, Portal2)
        Player.appliquer_deplacement()

    def update_camera(self):
        target_camera_y = Player.y - 120.0
        clamped_camera_y = min(-100.0, max(-820.0, target_camera_y))
        self.camera_y += (clamped_camera_y - self.camera_y) * 0.15
        Jeux.current_camera_y = self.camera_y
        Jeux.current_cam_y = self.camera_y
        pyxel.camera(0, self.camera_y)

    def draw(self):
        global Player, Portal1, Portal2
        pyxel.cls(0)

        self.update_camera()

        pyxel.bltm(0, -924, 0, 0, 0, 416, 1032)

        for beam in Player.shot_beams:
            pyxel.line(beam["x1"], beam["y1"], beam["x2"], beam["y2"], beam["color"])

        for particle in Player.particles:
            pyxel.pset(particle["x"], particle["y"], particle["color"])

        Portal1.draw(1)
        Portal2.draw(2)

        Player.afficher_joueur(self)
        pyxel.camera()

        draw_mouse(pyxel.mouse_x, pyxel.mouse_y, Portal1, Portal2)


def draw_mouse(mouse_x, mouse_y, portal_1=None, portal_2=None):
    p1 = portal_1 if portal_1 is not None else Portal1
    p2 = portal_2 if portal_2 is not None else Portal2
    pyxel.circb(mouse_x, mouse_y, 4, 7)
    pyxel.pset(mouse_x - 2, mouse_y, 12 if p1.active else 5)
    pyxel.pset(mouse_x + 2, mouse_y, 9 if p2.active else 4)
    pyxel.pset(mouse_x, mouse_y, 7)


drawMouse = draw_mouse

global Portal1, Portal2, Player
Portal1 = Portail(120, 100, 270, True)
Portal2 = Portail(382, 40, 180, True)
Player = Joueur()

if __name__ == "__main__":
    Jeux()
