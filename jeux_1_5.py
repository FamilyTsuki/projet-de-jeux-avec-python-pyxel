import json
import math
import os
import time

import pyxel

SCREEN_WIDTH = 384
SCREEN_HEIGHT = 230
FPS = 60
PHYSICS_HZ = 30
PHYSICS_STEP = 1.0 / PHYSICS_HZ
MAX_STEPS_PER_FRAME = 5

GRAVITY = 0.4
MAX_FALL_SPEED = 20.0
JUMP_FORCE = -6.5
MOVE_ACCELERATION = 0.8
MAX_MOVE_SPEED = 4.0
GROUND_FRICTION = 0.75
AIR_FRICTION = 0.985
MIN_VELOCITY = 0.15
COYOTE_FRAMES = 4
JUMP_CUT = 0.45
CROSSING_MIN_SPEED = 2.0
PORTAL_HALF = 14.0
PORTAL_SLIDE = 40.0

PLAYER_SIZE = 16
PLAYER_START_X = 24.0
PLAYER_START_Y = 84.0

PORTAL_COLORS = {
    1: (12, 6, 7),
    2: (9, 10, 7),
}


NIVEAU_FICHIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "niveau.json")

LEVEL_TOP = -100.0
LEVEL_BOTTOM = 140.0
BLOCKS = ()
GRATES = ()
HAZARDS = ()
GOAL = (0, 0, 0, 0)
HINTS = ()
PLATFORMS = ()


def charger_niveau(chemin=NIVEAU_FICHIER):
    global LEVEL_TOP, LEVEL_BOTTOM, BLOCKS, GRATES, HAZARDS, GOAL, HINTS
    global PLATFORMS, PLAYER_START_X, PLAYER_START_Y

    with open(chemin, encoding="utf-8") as fichier:
        data = json.load(fichier)

    BLOCKS = tuple(
        (int(x), int(y), int(w), int(h), bool(p))
        for x, y, w, h, p in data.get("blocks", [])
    )
    GRATES = tuple((int(x), int(y), int(w)) for x, y, w in data.get("grates", []))
    HAZARDS = tuple(
        (int(x), int(y), int(w), int(h)) for x, y, w, h in data.get("hazards", [])
    )
    GOAL = tuple(int(v) for v in data.get("goal", (0, 0, 0, 0)))
    HINTS = tuple(
        (int(x), int(y), str(texte), int(couleur))
        for x, y, texte, couleur in data.get("hints", [])
    )
    PLAYER_START_X, PLAYER_START_Y = (float(v) for v in data.get("start", (24, 84)))
    PLATFORMS = tuple((gx, gx + gw, gy) for gx, gy, gw in GRATES)

    hauts = [b[1] for b in BLOCKS] + [g[1] for g in GRATES] + [GOAL[1]]
    bas = [b[1] + b[3] for b in BLOCKS] + [PLAYER_START_Y + 16.0]
    LEVEL_TOP = float(min(hauts)) if hauts else -100.0
    LEVEL_BOTTOM = float(max(bas)) if bas else 140.0


charger_niveau()


def tick_anim():
    return int(time.perf_counter() * PHYSICS_HZ)


def plus_proche(distance, block, best):
    if best is None:
        return True
    if abs(distance - best[0]) < 1e-6:
        return block[4] and not best[4][4]
    return distance < best[0]


def point_dans_bloc(px, py):
    for bx, by, bw, bh, _ in BLOCKS:
        if bx < px < bx + bw and by < py < by + bh:
            return True
    return False


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

        color_outer, color_inner, color_core = PORTAL_COLORS.get(portal_id, (9, 10, 7))
        pulse = (tick_anim() // 4) % 2
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
        self.largeur = PLAYER_SIZE
        self.hauteur = PLAYER_SIZE
        self.direction = 1
        self.is_on_ground = True
        self.coyote = 0
        self.saut_en_cours = False
        self.teleport_cooldown = 0
        self.shot_beams = []
        self.particles = []
        self.is_moving = False
        self.crossing_info = None
        self.liste_plateformes = list(PLATFORMS)
        self.meilleure_hauteur = 0
        self.chutes = 0
        self.debut_chute = None
        self.gagne = False

    def respawn(self):
        self.x = PLAYER_START_X
        self.y = PLAYER_START_Y
        self.velocityX = 0.0
        self.velocityY = 0.0
        self.is_on_ground = True
        self.teleport_cooldown = 0
        self.crossing_info = None

    def gerer_tirs(self):
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.recherche_mur("l")
        if pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            self.recherche_mur("r")

    def gerer_entrees(self, jump_pressed=None):
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

        if jump_pressed is None:
            jump_pressed = saut_appuye()

        if self.crossing_info is not None:
            jump_pressed = False

        if jump_pressed and (self.is_on_ground or self.coyote > 0):
            self.velocityY = JUMP_FORCE
            self.is_on_ground = False
            self.coyote = 0
            self.saut_en_cours = True

        if self.saut_en_cours:
            if self.velocityY >= 0.0 or self.crossing_info is not None:
                self.saut_en_cours = False
            elif not saut_maintenu():
                self.velocityY *= JUMP_CUT
                self.saut_en_cours = False
            try:
                pyxel.play(2, 4)
            except BaseException:
                pass

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
        best = None

        for block in BLOCKS:
            bx, by, bw, bh, _ = block
            if abs(dir_x) > 1e-4:
                if dir_x > 0:
                    face_x, angle = bx, 180
                else:
                    face_x, angle = bx + bw, 0
                ray_distance = (face_x - origin_x) / dir_x
                hit_y = origin_y + ray_distance * dir_y
                if ray_distance > 0 and by <= hit_y <= by + bh:
                    if plus_proche(ray_distance, block, best):
                        best = (ray_distance, float(face_x), hit_y, angle, block)
            if abs(dir_y) > 1e-4:
                if dir_y > 0:
                    face_y, angle = by, 270
                else:
                    face_y, angle = by + bh, 90
                ray_distance = (face_y - origin_y) / dir_y
                hit_x = origin_x + ray_distance * dir_x
                if ray_distance > 0 and bx <= hit_x <= bx + bw:
                    if plus_proche(ray_distance, block, best):
                        best = (ray_distance, hit_x, float(face_y), angle, block)

        return best

    def calculer_position_portail(self, hit, portal):
        _, hit_x, hit_y, angle, block = hit
        bx, by, bw, bh, portalable = block
        if not portalable:
            return None

        vertical = angle in (0, 180)
        if vertical:
            mini, maxi, vise = by + PORTAL_HALF, by + bh - PORTAL_HALF, hit_y
        else:
            mini, maxi, vise = bx + PORTAL_HALF, bx + bw - PORTAL_HALF, hit_x
        if mini > maxi:
            return None
        depart = max(mini, min(maxi, vise))

        other = Portal2 if portal is Portal1 else Portal1
        face = hit_x if vertical else hit_y

        def place_libre(centre):
            if vertical:
                x0 = face if angle == 0 else face - 2.0
                zone = (x0, centre - PORTAL_HALF, 2.0, 2 * PORTAL_HALF)
            else:
                y0 = face - 2.0 if angle == 270 else face
                zone = (centre - PORTAL_HALF, y0, 2 * PORTAL_HALF, 2.0)
            zx, zy, zw, zh = zone
            for ox, oy, ow, oh, _ in BLOCKS:
                if zx < ox + ow and zx + zw > ox and zy < oy + oh and zy + zh > oy:
                    return False
            if other.active and other.angle == angle:
                if vertical:
                    meme_face = abs(other.pos_x - face) < 1
                    distance = abs(other.pos_y - centre)
                else:
                    meme_face = abs(other.pos_y - face) < 1
                    distance = abs(other.pos_x - centre)
                if meme_face and distance < 2 * PORTAL_HALF:
                    return False
            return True

        for decalage in range(int(PORTAL_SLIDE) + 1):
            for centre in (depart - decalage, depart + decalage):
                if mini <= centre <= maxi and place_libre(centre):
                    if vertical:
                        return hit_x, centre, angle
                    return centre, hit_y, angle
        return None

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

        placement = self.calculer_position_portail(hit, portal)
        if placement is None:
            self.shot_beams.append(
                {
                    "x1": self.x + 8.0,
                    "y1": self.y + 8.0,
                    "x2": hit[1],
                    "y2": hit[2],
                    "color": 13,
                    "time": 4,
                }
            )
            self.spawn_particles(hit[1], hit[2], 13)
            return

        hit_x, hit_y, surface_angle = placement
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
            crossing_speed = max(self.crossing_info["entry_speed"], CROSSING_MIN_SPEED)
            if portal_entry.angle in (0, 180):
                self.velocityY = 0.0
                if abs(self.velocityX) <= MAX_MOVE_SPEED and not self.is_moving:
                    self.velocityX = 0.0
            else:
                self.velocityX = 0.0
                if portal_entry.angle == 270:
                    self.velocityY = crossing_speed
                else:
                    self.velocityY = -crossing_speed
        else:
            self.velocityY += GRAVITY
            self.velocityY = min(self.velocityY, MAX_FALL_SPEED)

            if self.is_on_ground:
                if not self.is_moving:
                    self.velocityX *= GROUND_FRICTION
                    if abs(self.velocityX) < MIN_VELOCITY:
                        self.velocityX = 0.0
            else:
                self.velocityX *= AIR_FRICTION

        if self.teleport_cooldown > 0:
            self.teleport_cooldown -= 1
        if self.coyote > 0:
            self.coyote -= 1

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
        pass

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
                "entry_speed": abs(
                    self.velocityX if portal_entry.angle in (0, 180) else self.velocityY
                ),
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
        self.saut_en_cours = False
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
                if portal_entry.angle in (0, 180):
                    exit_speed = max(abs(self.velocityX), 0.1)
                else:
                    exit_speed = max(self.crossing_info["entry_speed"], 0.1)
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

    @staticmethod
    def chevauche(x, y, block):
        bx, by, bw, bh = block[0], block[1], block[2], block[3]
        return x < bx + bw and x + 16.0 > bx and y < by + bh and y + 16.0 > by

    def portail_ouvert(self, angle, coord, centre, portals):
        if self.teleport_cooldown > 0:
            return False
        if not all(portal.active for portal in portals):
            return False
        for portal in portals:
            if portal.angle != angle:
                continue
            if angle in (0, 180):
                if (
                    abs(portal.pos_x - coord) < 1.0
                    and abs(centre - portal.pos_y) <= 12.0
                ):
                    return True
            elif abs(portal.pos_y - coord) < 1.0 and abs(centre - portal.pos_x) <= 8.0:
                return True
        return False

    def depenetrer(self, portals):
        for block in BLOCKS:
            if not self.chevauche(self.x, self.y, block):
                continue
            bx, by, bw, bh = block[0], block[1], block[2], block[3]
            options = (
                ((self.y + 16.0) - by, 270, by, self.x + 8.0),
                ((by + bh) - self.y, 90, by + bh, self.x + 8.0),
                ((self.x + 16.0) - bx, 180, bx, self.y + 8.0),
                ((bx + bw) - self.x, 0, bx + bw, self.y + 8.0),
            )
            depth, angle, coord, centre = min(options, key=lambda option: option[0])
            if self.portail_ouvert(angle, coord, centre, portals):
                continue
            if angle == 270:
                self.y = by - 16.0
                self.velocityY = min(self.velocityY, 0.0)
            elif angle == 90:
                self.y = by + bh
                self.velocityY = max(self.velocityY, 0.0)
            elif angle == 180:
                self.x = bx - 16.0
                self.velocityX = min(self.velocityX, 0.0)
            else:
                self.x = bx + bw
                self.velocityX = max(self.velocityX, 0.0)

    def gerer_collisions(self, portal_1=None, portal_2=None):
        portals = (
            portal_1 if portal_1 is not None else Portal1,
            portal_2 if portal_2 is not None else Portal2,
        )

        if self.crossing_info is not None:
            self.x += self.velocityX
            self.y += self.velocityY
            return

        self.depenetrer(portals)

        old_x = self.x
        self.x += self.velocityX
        for block in BLOCKS:
            if not self.chevauche(self.x, self.y, block):
                continue
            if self.chevauche(old_x, self.y, block):
                continue
            bx, bw = block[0], block[2]
            if self.velocityX > 0:
                if self.portail_ouvert(180, bx, self.y + 8.0, portals):
                    continue
                self.x = bx - 16.0
                self.velocityX = 0.0
            elif self.velocityX < 0:
                if self.portail_ouvert(0, bx + bw, self.y + 8.0, portals):
                    continue
                self.x = bx + bw
                self.velocityX = 0.0

        old_y = self.y
        velocity_y = self.velocityY
        self.y += velocity_y
        landed = False
        for block in BLOCKS:
            if not self.chevauche(self.x, self.y, block):
                continue
            if self.chevauche(self.x, old_y, block):
                continue
            by, bh = block[1], block[3]
            if velocity_y > 0:
                if self.portail_ouvert(270, by, self.x + 8.0, portals):
                    continue
                self.y = by - 16.0
                self.velocityY = 0.0
                landed = True
            elif velocity_y < 0:
                if self.portail_ouvert(90, by + bh, self.x + 8.0, portals):
                    continue
                self.y = by + bh
                self.velocityY = 0.0

        if velocity_y > 0 and not landed:
            centre_x = self.x + 8.0
            for grate_x, grate_y, grate_w in GRATES:
                if (
                    grate_x <= centre_x <= grate_x + grate_w
                    and old_y + 16.0 <= grate_y + 0.01
                    and self.y + 16.0 >= grate_y
                ):
                    self.y = grate_y - 16.0
                    self.velocityY = 0.0
                    landed = True
                    break

        self.is_on_ground = landed
        if landed:
            self.coyote = COYOTE_FRAMES

        if self.y > LEVEL_BOTTOM + 100.0:
            self.respawn()

    def gerer_niveau(self):
        if self.crossing_info is not None:
            self.debut_chute = None
            return

        for hazard in HAZARDS:
            if self.chevauche(self.x, self.y, hazard):
                self.spawn_particles(self.x + 8.0, self.y + 8.0, 11)
                self.chutes += 1
                self.respawn()
                return

        hauteur = int((PLAYER_START_Y - self.y) // 8)
        self.meilleure_hauteur = max(self.meilleure_hauteur, hauteur)

        if self.is_on_ground:
            if self.debut_chute is not None and self.y - self.debut_chute > 120.0:
                self.chutes += 1
            self.debut_chute = None
        elif self.velocityY > 0 and self.debut_chute is None:
            self.debut_chute = self.y
        elif self.velocityY <= 0:
            self.debut_chute = None

        if not self.gagne and self.chevauche(self.x, self.y, GOAL):
            self.gagne = True
            self.spawn_particles(self.x + 8.0, self.y + 8.0, 10)

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
        if not self.is_on_ground:
            sprite_u = 48
        elif self.is_moving:
            sprite_u = 0 if (tick_anim() // 5) % 2 == 0 else 16
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


def saut_maintenu():
    return (
        pyxel.btn(pyxel.KEY_Z)
        or pyxel.btn(pyxel.KEY_W)
        or pyxel.btn(pyxel.KEY_UP)
        or pyxel.btn(pyxel.KEY_SPACE)
    )


def saut_appuye():
    return (
        pyxel.btnp(pyxel.KEY_Z)
        or pyxel.btnp(pyxel.KEY_W)
        or pyxel.btnp(pyxel.KEY_UP)
        or pyxel.btnp(pyxel.KEY_SPACE)
    )


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
        Portal1 = Portail()
        Portal2 = Portail()
        Player = Joueur()

        self.camera_y = self.cible_camera(Player.y + 8.0)
        self.frames = 0
        self.accumulateur = 0.0
        self.dernier_temps = time.perf_counter()
        self.saut_tampon = False
        self.prev_x = Player.x
        self.prev_y = Player.y

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

        if pyxel.btnp(pyxel.KEY_F5):
            try:
                charger_niveau()
                Portal1.active = False
                Portal2.active = False
                Player.crossing_info = None
            except (OSError, ValueError) as erreur:
                print("niveau.json invalide :", erreur)

        Player.gerer_tirs()
        if saut_appuye():
            self.saut_tampon = True

        maintenant = time.perf_counter()
        self.accumulateur += min(maintenant - self.dernier_temps, 0.25)
        self.dernier_temps = maintenant

        pas = 0
        while self.accumulateur >= PHYSICS_STEP and pas < MAX_STEPS_PER_FRAME:
            self.prev_x = Player.x
            self.prev_y = Player.y
            Player.gerer_entrees(self.saut_tampon)
            self.saut_tampon = False
            Player.gerer_portails(Portal1, Portal2)
            Player.appliquer_modificateurs_vitesse()
            Player.gerer_collisions(Portal1, Portal2)
            Player.gerer_niveau()
            if not Player.gagne:
                self.frames += 1
            self.accumulateur -= PHYSICS_STEP
            pas += 1
        if pas == MAX_STEPS_PER_FRAME:
            self.accumulateur = 0.0

    def cible_camera(self, centre_y):
        haut = LEVEL_TOP - 16.0
        bas = max(haut, LEVEL_BOTTOM - SCREEN_HEIGHT)
        return min(bas, max(haut, centre_y - SCREEN_HEIGHT / 2))

    def centre_suivi(self, joueur):
        crossing = joueur.crossing_info
        if crossing is not None and crossing["entry_depth"] >= PLAYER_SIZE / 2:
            lateral = min(6.0, max(-6.0, crossing["lateral_offset"]))
            _, sortie_y, _ = joueur.calculer_coordonnees_sprite_sortie(
                crossing["portal_exit"], crossing["entry_depth"], lateral, 16
            )
            return sortie_y + PLAYER_SIZE / 2
        return joueur.y + PLAYER_SIZE / 2

    def update_camera(self, joueur):
        cible = self.cible_camera(self.centre_suivi(joueur))
        if abs(cible - self.camera_y) > SCREEN_HEIGHT:
            self.camera_y = cible
        else:
            self.camera_y += (cible - self.camera_y) * 0.12
        Jeux.current_camera_y = self.camera_y
        Jeux.current_cam_y = self.camera_y
        pyxel.camera(0, self.camera_y)

    def draw(self):
        global Player, Portal1, Portal2
        pyxel.cls(0)

        vrai_x, vrai_y = Player.x, Player.y
        alpha = min(1.0, self.accumulateur / PHYSICS_STEP)
        if abs(vrai_x - self.prev_x) + abs(vrai_y - self.prev_y) < 24.0:
            Player.x = self.prev_x + (vrai_x - self.prev_x) * alpha
            Player.y = self.prev_y + (vrai_y - self.prev_y) * alpha

        self.update_camera(Player)

        draw_background(self.camera_y)
        draw_level(self.camera_y, Player)

        for beam in Player.shot_beams:
            pyxel.line(beam["x1"], beam["y1"], beam["x2"], beam["y2"], beam["color"])

        for particle in Player.particles:
            pyxel.pset(particle["x"], particle["y"], particle["color"])

        Portal1.draw(1)
        Portal2.draw(2)

        Player.afficher_joueur(self)
        Player.x, Player.y = vrai_x, vrai_y
        pyxel.camera()

        draw_hud(self.frames, Player)
        draw_mouse(pyxel.mouse_x, pyxel.mouse_y, Portal1, Portal2)


def draw_mouse(mouse_x, mouse_y, portal_1=None, portal_2=None):
    p1 = portal_1 if portal_1 is not None else Portal1
    p2 = portal_2 if portal_2 is not None else Portal2
    pyxel.circb(mouse_x, mouse_y, 4, 7)
    pyxel.pset(mouse_x - 2, mouse_y, 12 if p1.active else 5)
    pyxel.pset(mouse_x + 2, mouse_y, 9 if p2.active else 4)
    pyxel.pset(mouse_x, mouse_y, 7)


def draw_background(camera_y=-100.0):
    first_row = int((84 - (camera_y + SCREEN_HEIGHT)) // 16)
    last_row = int((84 - camera_y) // 16) + 1
    for x in range(24):
        for y in range(first_row, last_row + 1):
            if y % 2 == 1:
                rotate = 90 * (x % 2)
            else:
                rotate = 270 - 90 * (x % 2)
            tile_u = ((x + y) % 4) * 16
            tile_v = (((x + y) // 4) % 2) * 16

            pyxel.blt(
                x * 16,
                -y * 16 + 84,
                1,
                tile_u,
                tile_v,
                16,
                16,
                colkey=None,
                rotate=rotate,
            )


def draw_block(bx, by, bw, bh, portalable):
    if portalable:
        pyxel.rect(bx, by, bw, bh, 6)
        for gx in range(bx, bx + bw, 16):
            pyxel.line(gx, by, gx, by + bh - 1, 12)
        for gy in range(by, by + bh, 16):
            pyxel.line(bx, gy, bx + bw - 1, gy, 12)
        pyxel.rectb(bx, by, bw, bh, 5)
    else:
        pyxel.rect(bx, by, bw, bh, 5)
        for gx in range(bx, bx + bw, 16):
            pyxel.line(gx, by, gx, by + bh - 1, 13)
        for gy in range(by, by + bh, 16):
            pyxel.line(bx, gy, bx + bw - 1, gy, 13)
        pyxel.rectb(bx, by, bw, bh, 0)


def draw_level(camera_y, joueur):
    top = camera_y - 16
    bottom = camera_y + SCREEN_HEIGHT + 16

    for block in sorted(BLOCKS, key=lambda b: b[4]):
        bx, by, bw, bh, portalable = block
        if by + bh < top or by > bottom:
            continue
        draw_block(bx, by, bw, bh, portalable)

    for gx, gy, gw in GRATES:
        if gy < top or gy > bottom:
            continue
        pyxel.rect(gx, gy, gw, 3, 4)
        for px in range(gx + 2, gx + gw - 1, 4):
            pyxel.pset(px, gy + 1, 15)
        pyxel.line(gx, gy + 3, gx + gw - 1, gy + 3, 0)

    for hx, hy, hw, hh in HAZARDS:
        if hy + hh < top or hy > bottom:
            continue
        pyxel.rect(hx, hy, hw, hh, 11)
        pyxel.line(hx, hy, hx + hw - 1, hy, 3)
        for bubble in range(hx + 6, hx + hw - 4, 23):
            bubble_y = hy - 1 - ((tick_anim() // 6 + bubble) % 3)
            pyxel.pset(bubble, bubble_y, 11)

    gx, gy, gw, gh = GOAL
    if top < gy < bottom:
        glow = 10 if (tick_anim() // 8) % 2 == 0 else 9
        pyxel.rectb(gx, gy, gw, gh, glow)
        pyxel.rect(gx + 3, gy + 3, gw - 6, gh - 6, 1)
        pyxel.rect(gx + 6, gy + 6, gw - 12, gh - 9, glow)

    for hint_x, hint_y, text, color in HINTS:
        if hint_y < top or hint_y > bottom:
            continue
        pyxel.rect(hint_x - 3, hint_y - 2, len(text) * 4 + 5, 9, 1)
        pyxel.rectb(hint_x - 3, hint_y - 2, len(text) * 4 + 5, 9, 0)
        pyxel.text(hint_x, hint_y, text, color)


def draw_hud(frames, joueur):
    seconds = frames // PHYSICS_HZ
    timer = f"{seconds // 60:02d}:{seconds % 60:02d}"
    hauteur = max(0, int((PLAYER_START_Y - joueur.y) // 8))
    texte = f"{hauteur}m  max {joueur.meilleure_hauteur}m  {timer}"
    largeur = len(texte) * 4 + 8
    pyxel.rect(6, 6, largeur, 13, 0)
    pyxel.rectb(6, 6, largeur, 13, 5)
    pyxel.text(10, 10, texte, 7)

    if joueur.gagne:
        pyxel.rect(102, 90, 180, 40, 0)
        pyxel.rectb(102, 90, 180, 40, 10)
        pyxel.text(160, 98, "NIVEAU TERMINE !", 10)
        pyxel.text(130, 110, f"Temps {timer}   Chutes {joueur.chutes}", 7)


drawMouse = draw_mouse

global Portal1, Portal2, Player
Portal1 = Portail()
Portal2 = Portail()
Player = Joueur()

if __name__ == "__main__":
    Jeux()
