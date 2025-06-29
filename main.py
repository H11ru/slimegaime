import pygame
import ctypes
import time
import random
import keyboard

# Constants for Windows API
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000

# Initialize Pygame and load the image
pygame.init()
enemy_orig = pygame.image.load("blue_slime.png")
SMALL_SIZE = (enemy_orig.get_width() // 2, enemy_orig.get_height() // 2)
enemy_size = enemy_orig.get_width() // 2, enemy_orig.get_height() // 2
pygame.display.set_caption("Transparent Enemy")

def get_mouse_position():
    pt = ctypes.wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

def get_screen_dimensions():
    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
screen = pygame.display.set_mode(get_screen_dimensions(), pygame.NOFRAME)
# Get HWND
hwnd = pygame.display.get_wm_info()['window']
# Make window always on top
HWND_TOPMOST = -1
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
import ctypes.wintypes

ctypes.windll.user32.SetWindowPos(hwnd, ctypes.wintypes.HWND(HWND_TOPMOST), 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)

MAGENTA_KEY = (73, 4, 84)  # RGB for #490454

# Set window to be layered and transparent using colorkey (NO WS_EX_TRANSPARENT)
ctypes.windll.user32.SetWindowLongW(
    hwnd, GWL_EXSTYLE,
    ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE) | WS_EX_LAYERED
)
colorkey = (MAGENTA_KEY[2] << 16) | (MAGENTA_KEY[1] << 8) | MAGENTA_KEY[0]
ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, colorkey, 0, 0x1)  # 0x1 == LWA_COLORKEY

def updatewindow(x, y, width, height):
    x = int(x)
    y = int(y)
    width = int(width)
    height = int(height)
    ctypes.windll.user32.MoveWindow(hwnd, x, y, width, height, True)

screen_dimensions = get_screen_dimensions()

player_pos = [300, 300]
player_speed = 7
player_radius = 25

projectiles = []
projectile_speed = 15
bullettimer = 0

def shoot_towards(target_x, target_y):
    dx = target_x - (player_pos[0] + player_radius)
    dy = target_y - (player_pos[1] + player_radius)
    vec = pygame.math.Vector2(dx, dy)
    if vec.length() > 0:
        vec = vec.normalize()
    else:
        vec = pygame.math.Vector2(0, 0)
    projectiles.append([
        player_pos[0] + player_radius, player_pos[1] + player_radius,
        vec.x * projectile_speed, vec.y * projectile_speed
    ])

# --- SLIME TYPES ---
SLIME_TYPES = {
    "blue": {
        "img": pygame.transform.smoothscale(pygame.image.load("blue_slime.png"), SMALL_SIZE),
        "pop_value": 1
    },
    "yellow": {
        "img": pygame.transform.smoothscale(pygame.image.load("yellow_slime.png"), SMALL_SIZE),
        "pop_value": 12
    },
    "red": {
        "img": pygame.transform.smoothscale(pygame.image.load("red_slime.png"), SMALL_SIZE),
        "pop_value": 50
    },
    "gold": {
        "img": pygame.transform.smoothscale(pygame.image.load("gold_slime.png"), SMALL_SIZE),
        "pop_value": 100
    }
}

for t in SLIME_TYPES.values():
    t["img"].set_colorkey(MAGENTA_KEY)

def spawn_slime():
    slime_type = random.choices(
        ["blue", "yellow", "red", "gold"],
        weights=[8, 5, 3, 1]
    )[0]
    edge = random.choice(['top', 'bottom', 'left', 'right'])
    if edge == 'top':
        sx = random.randint(0, screen_dimensions[0] - enemy_size[0])
        sy = -enemy_size[1]
    elif edge == 'bottom':
        sx = random.randint(0, screen_dimensions[0] - enemy_size[0])
        sy = screen_dimensions[1]
    elif edge == 'left':
        sx = -enemy_size[0]
        sy = random.randint(0, screen_dimensions[1] - enemy_size[1])
    elif edge == 'right':
        sx = screen_dimensions[0]
        sy = random.randint(0, screen_dimensions[1] - enemy_size[1])
    speed = random.uniform(3.5, 6.5)
    return {
        "type": slime_type,
        "pos": [sx, sy],
        "speed": speed,
        "target": pygame.math.Vector2(sx, sy),
        "uselesstimer": random.randint(30, 60),
        "dir": pygame.math.Vector2(random.uniform(-1,1), random.uniform(-1,1)).normalize()
    }

num_slimes = 50
slimetimer = 60
slimes = []
def shortest_vector_wrap(pos, target, screen_dimensions, buffer=50):
    w, h = screen_dimensions
    w += buffer * 2
    h += buffer * 2
    dx = (target[0] - pos[0])
    dy = (target[1] - pos[1])
    # Wrap X
    if abs(dx) > w / 2:
        if dx > 0:
            dx -= w
        else:
            dx += w
    # Wrap Y
    if abs(dy) > h / 2:
        if dy > 0:
            dy -= h
        else:
            dy += h
    return pygame.math.Vector2(dx, dy)

def slime_rect(slime):
    x, y = slime["pos"]
    return pygame.Rect(x, y, enemy_size[0], enemy_size[1])

def push_slimes(slimes):
    for i in range(len(slimes)):
        for j in range(i+1, len(slimes)):
            r1 = slime_rect(slimes[i])
            r2 = slime_rect(slimes[j])
            if r1.colliderect(r2):
                dx = r1.centerx - r2.centerx
                dy = r1.centery - r2.centery
                dist = max((dx**2 + dy**2)**0.5, 1)
                push = 2
                slimes[i]["pos"][0] += (dx/dist) * push
                slimes[i]["pos"][1] += (dy/dist) * push
                slimes[j]["pos"][0] -= (dx/dist) * push
                slimes[j]["pos"][1] -= (dy/dist) * push

pops = 0
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # --- GLOBAL PLAYER MOVEMENT ---
    player_vpos = [0, 0]
    if keyboard.is_pressed('w'):
        player_vpos[1] -= player_speed
    if keyboard.is_pressed('s'):
        player_vpos[1] += player_speed
    if keyboard.is_pressed('a'):
        player_vpos[0] -= player_speed
    if keyboard.is_pressed('d'):
        player_vpos[0] += player_speed
    player_vpos = pygame.math.Vector2(player_vpos)
    player_vpos = player_vpos.normalize() if player_vpos.length() > 0 else pygame.math.Vector2(0, 0)
    player_pos += player_vpos * player_speed

    # --- GLOBAL SHOOTING ---
    if keyboard.is_pressed('space') and bullettimer <= 0:
        # ALl slimes touching you pop
        for slime in slimes[:]:
            if slime_rect(slime).colliderect(pygame.Rect(player_pos[0], player_pos[1], player_radius * 2, player_radius * 2)):
                pops += SLIME_TYPES[slime["type"]]["pop_value"]
                slimes.remove(slime)

    # --- ENEMY AI ---
    for slime in slimes:
        stype = slime["type"]
        if stype == "blue" or stype == "gold":
            # --- BLUE: your current AI, sometimes pick player as target ---
            if slime["uselesstimer"] > 0:
                slime["uselesstimer"] -= 1
                continue
            distance_to_target = pygame.math.Vector2(slime["pos"]).distance_to(slime["target"])
            if distance_to_target < slime["speed"]:
                slime["pos"][0] = slime["target"].x
                slime["pos"][1] = slime["target"].y
                slime["uselesstimer"] = random.randint(30, 60)
                # Pick random target, sometimes near player
                if random.randint(1, 4) == 2:
                    slime["target"] = pygame.math.Vector2(
                        player_pos[0] + player_radius + random.randint(-15, 15),
                        player_pos[1] + player_radius + random.randint(-15, 15)
                    )
                else:
                    slime["target"] = pygame.math.Vector2(
                        random.randint(0, screen_dimensions[0]),
                        random.randint(0, screen_dimensions[1])
                    )
                continue
                        # Instead of:
            # vec = pygame.math.Vector2(slime["target"].x - slime["pos"][0], slime["target"].y - slime["pos"][1])
            # Use:
            vec = shortest_vector_wrap(slime["pos"], (slime["target"].x, slime["target"].y), screen_dimensions)
            if vec.length() > 0:
                vec = vec.normalize() * slime["speed"]
            else:
                vec = pygame.math.Vector2(0, 0)
            slime["pos"][0] += vec.x
            slime["pos"][1] += vec.y

        elif stype == "yellow":
            # --- YELLOW: random, never pick player, avoid player area ---
            if slime["uselesstimer"] > 0:
                slime["uselesstimer"] -= 1
                continue
            distance_to_target = pygame.math.Vector2(slime["pos"]).distance_to(slime["target"])
            if distance_to_target < slime["speed"]:
                slime["pos"][0] = slime["target"].x
                slime["pos"][1] = slime["target"].y
                slime["uselesstimer"] = random.randint(30, 60)
                # Pick random target NOT near player
                while True:
                    tx = random.randint(0, screen_dimensions[0])
                    ty = random.randint(0, screen_dimensions[1])
                    if pygame.math.Vector2(tx, ty).distance_to(player_pos) > player_radius + 60:
                        break
                slime["target"] = pygame.math.Vector2(tx, ty)
                continue
                        # Instead of:
            # vec = pygame.math.Vector2(slime["target"].x - slime["pos"][0], slime["target"].y - slime["pos"][1])
            # Use:
            vec = shortest_vector_wrap(slime["pos"], (slime["target"].x, slime["target"].y), screen_dimensions)
            if vec.length() > 0:
                vec = vec.normalize() * slime["speed"]
            else:
                vec = pygame.math.Vector2(0, 0)
            slime["pos"][0] += vec.x
            slime["pos"][1] += vec.y

        elif stype == "red":
            # --- RED: always >100 from player, if near, run away and ignore timer ---
            dist_to_player = pygame.math.Vector2(slime["pos"]).distance_to(player_pos)
            if dist_to_player < 150:
                # Run away, ignore uselesstimer
                dx = slime["pos"][0] - player_pos[0]
                dy = slime["pos"][1] - player_pos[1]
                away = pygame.math.Vector2(slime["pos"][0] + dx * 2, slime["pos"][1] + dy * 2)
                slime["target"] = away
                            # Instead of:
                # vec = pygame.math.Vector2(slime["target"].x - slime["pos"][0], slime["target"].y - slime["pos"][1])
                # Use:
                vec = shortest_vector_wrap(slime["pos"], (slime["target"].x, slime["target"].y), screen_dimensions)
                if vec.length() > 0:
                    vec = vec.normalize() * slime["speed"]
                else:
                    vec = pygame.math.Vector2(0, 0)
                slime["pos"][0] += vec.x 
                slime["pos"][1] += vec.y 
                continue
            if slime["uselesstimer"] > 0:
                slime["uselesstimer"] -= 1
                continue
            distance_to_target = pygame.math.Vector2(slime["pos"]).distance_to(slime["target"])
            if distance_to_target < slime["speed"]:
                slime["pos"][0] = slime["target"].x
                slime["pos"][1] = slime["target"].y
                slime["uselesstimer"] = random.randint(30, 60)
                # Pick a target >100 from player
                while True:
                    tx = random.randint(0, screen_dimensions[0])
                    ty = random.randint(0, screen_dimensions[1])
                    if pygame.math.Vector2(tx, ty).distance_to(player_pos) > 300:
                        break
                slime["target"] = pygame.math.Vector2(tx, ty)
                continue
            # Instead of:
            # vec = pygame.math.Vector2(slime["target"].x - slime["pos"][0], slime["target"].y - slime["pos"][1])
            # Use:
            vec = shortest_vector_wrap(slime["pos"], (slime["target"].x, slime["target"].y), screen_dimensions)
            if vec.length() > 0:
                vec = vec.normalize() * slime["speed"]
            else:
                vec = pygame.math.Vector2(0, 0)
            slime["pos"][0] += vec.x
            slime["pos"][1] += vec.y

    # --- SLIME PUSHING ---

    # Slime appear
    if slimetimer <= 0 and len(slimes) < num_slimes:
        slimes.append(spawn_slime())
        slimetimer = 60
    slimetimer -= 1

    # --- PROJECTILE COLLISION WITH SLIMES ---
    for slime in slimes:
        for proj in projectiles:
            r = slime_rect(slime)
            if r.collidepoint(proj[0], proj[1]):
                print("Slime destroyed!")
                pops += SLIME_TYPES[slime["type"]]["pop_value"]
                # Reset slime position
                edge = random.choice(['top', 'bottom', 'left', 'right'])
                if edge == 'top':
                    slime["pos"][0] = random.randint(0, screen_dimensions[0] - enemy_size[0])
                    slime["pos"][1] = -enemy_size[1]
                elif edge == 'bottom':
                    slime["pos"][0] = random.randint(0, screen_dimensions[0] - enemy_size[0])
                    slime["pos"][1] = screen_dimensions[1]
                elif edge == 'left':
                    slime["pos"][0] = -enemy_size[0]
                    slime["pos"][1] = random.randint(0, screen_dimensions[1] - enemy_size[1])
                elif edge == 'right':
                    slime["pos"][0] = screen_dimensions[0]
                    slime["pos"][1] = random.randint(0, screen_dimensions[1] - enemy_size[1])
                projectiles.remove(proj)
                break

    # --- PROJECTILE UPDATE ---
    for proj in projectiles:
        proj[0] += proj[2]
        proj[1] += proj[3]
    projectiles = [p for p in projectiles if 0 <= p[0] <= screen_dimensions[0] and 0 <= p[1] <= screen_dimensions[1]]

    # --- PLAYER WRAP ---
    player_pos[0] = ((player_pos[0] + 50) % (screen_dimensions[0] + 100)) - 50
    player_pos[1] = ((player_pos[1] + 50) % (screen_dimensions[1] + 100)) - 50

    # --- SLIME WRAP ---
    for slime in slimes:
        slime["pos"][0] = ((slime["pos"][0] + 50) % (screen_dimensions[0] + 100)) - 50
        slime["pos"][1] = ((slime["pos"][1] + 50) % (screen_dimensions[1] + 100)) - 50

    # --- DRAW EVERYTHING ---
    screen.fill(MAGENTA_KEY)
    temp = pygame.Surface(screen.get_size())
    temp.fill(MAGENTA_KEY)
    temp.set_colorkey(MAGENTA_KEY)
    for slime in slimes:
        slime_img = SLIME_TYPES[slime["type"]]["img"]
        temp.blit(slime_img, (int(slime["pos"][0]), int(slime["pos"][1])))
    screen.blit(temp, (0, 0))
    pygame.draw.circle(screen, (0, 200, 255), player_pos, player_radius)
    for proj in projectiles:
        pygame.draw.circle(screen, (255, 255, 0), (int(proj[0]), int(proj[1])), 8)
    # draw radiuses around the player
    #pygame.draw.circle(screen, (255, 0, 0), player_pos, 150, 1)
    #pygame.draw.circle(screen, (0, 255, 0), player_pos, 300, 1)

    # POps coutner
    font = pygame.font.Font(None, 46)
    textblack = font.render(f"Pops: {pops}", True, (0, 0, 0))
    textlblue = font.render(f"Pops: {pops}", True, (230, 230, 255))
    screen.blit(textblack, (10, 10))
    screen.blit(textblack, (10, 14))
    screen.blit(textblack, (14, 10))
    screen.blit(textblack, (14, 14))
    screen.blit(textlblue, (12, 12))
    pygame.display.update()
    time.sleep(0.02)

pygame.quit()