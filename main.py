import pygame
import random

import sys

# Initialize Pygame
pygame.init()

# Screen setup - open fullscreen and adapt to display size
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
# Use FULLSCREEN window so game fills entire screen
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("2D Shooting Game - Fullscreen")
clock = pygame.time.Clock()

# Load images
_bg = pygame.image.load("background.png")
# Force convert() to match display and avoid unexpected alpha blending
background_img = _bg.convert()
# Smooth-scale background to fullscreen size so it fills the display
background_img = pygame.transform.smoothscale(background_img, (WIDTH, HEIGHT))

player_img = pygame.image.load("spaceship.png")
# Scale player based on screen size so it looks reasonable at large resolutions
player_width = max(40, WIDTH // 20)
player_height = int(player_width * 0.8)
player_img = pygame.transform.scale(player_img, (player_width, player_height))

enemy_img = pygame.image.load("enemy.png")
enemy_img = pygame.transform.scale(enemy_img, (int(player_width * 0.9), int(player_height * 0.75)))

obstacle_img = pygame.image.load("obstacle.png")
obstacle_size = max(24, WIDTH // 60)
obstacle_img = pygame.transform.scale(obstacle_img, (obstacle_size, obstacle_size))

# Load sound effects
pew_sound = pygame.mixer.Sound("pew.wav")
retro_sound = pygame.mixer.Sound("retro_shoot.wav")
explosion_sound = pygame.mixer.Sound("explosion.wav")

# Set volume lower
pew_sound.set_volume(0.3)
retro_sound.set_volume(0.3)
explosion_sound.set_volume(0.3)

# Player setup
player_x = WIDTH // 2
player_y = HEIGHT - (player_height + 20)
player_speed = max(4, WIDTH // 300)

# Lives / health
max_lives = 3
lives = max_lives
# Score
score = 0

# Font for HUD
hud_font = pygame.font.SysFont(None, max(24, WIDTH // 50))

# Bullets
bullets = []
bullet_speed = max(6, HEIGHT // 80)
last_shot_time = 0
fire_delay = 300  # milliseconds

# Floating score popups
popups = []  # each: {'text': str, 'x': float, 'y': float, 'ttl': int}

# Power-ups
powerups = []  # each: {'type': 'double_shot'|'invisible', 'rect': pygame.Rect, 'ttl': int}
POWERUP_DURATION = 8000  # ms
POWERUP_SPAWN_CHANCE = 60  # 1 in N chance per obstacle spawn (smaller -> more frequent)

# Optional assets for powerups
try:
    double_icon = pygame.image.load('power_double.png').convert_alpha()
except Exception:
    double_icon = None
try:
    invis_icon = pygame.image.load('power_invis.png').convert_alpha()
except Exception:
    invis_icon = None

# Pickup sound
try:
    pickup_sound = pygame.mixer.Sound('pickup.wav')
    pickup_sound.set_volume(0.3)
except Exception:
    pickup_sound = None

# Pickup message popups
pickup_msgs = []  # each: {'text', 'x', 'y', 'alpha', 'ttl'}

# Active power-up states
double_shot_active = False
double_shot_ends = 0
invisible_active = False
invisible_ends = 0

# High score file
HIGH_SCORE_FILE = 'highscore.txt'
try:
    with open(HIGH_SCORE_FILE, 'r') as f:
        high_score = int(f.read().strip() or 0)
except Exception:
    high_score = 0

# Invulnerability after hit
invulnerable = False
invuln_time = 0
INVULN_DURATION = 1500  # ms

# Game over state flag
game_over = False

# Enemies (targets)
# Enemies (targets)
enemies = []
enemy_speed = max(1, HEIGHT // 600)

# Obstacles (asteroids)
obstacles = []  # Each: {'rect': pygame.Rect, 'hits': 0}
obstacle_speed = max(2, HEIGHT // 300)
# obstacle_size defined earlier from image scaling

# Spawn enemy
def spawn_enemy():
    # use enemy image size so bottom checks are accurate
    e_w, e_h = enemy_img.get_width(), enemy_img.get_height()
    x = random.randint(0, max(0, WIDTH - e_w))
    enemies.append(pygame.Rect(x, 0, e_w, e_h))

# Spawn asteroid obstacle
def spawn_obstacle():
    x = random.randint(0, WIDTH - obstacle_size)
    rect = pygame.Rect(x, 0, obstacle_size, obstacle_size)
    obstacles.append({'rect': rect})
    # small chance to spawn a powerup near the obstacle
    # increased chance to spawn a powerup so they appear more often
    if random.randint(1, POWERUP_SPAWN_CHANCE) == 1:
        ptype = random.choice(['double_shot', 'invisible'])
        pr = pygame.Rect(rect.x, rect.y, obstacle_size, obstacle_size)
        powerups.append({'type': ptype, 'rect': pr, 'ttl': 1200})

# Draw player
def draw_player(x, y):
    screen.blit(player_img, (x, y))

# Draw bullets
def draw_bullets(bullets):
    for bullet in bullets:
        pygame.draw.rect(screen, (255, 255, 0), bullet)

# Draw enemies
def draw_enemies(enemies):
    for enemy in enemies:
        screen.blit(enemy_img, (enemy.x, enemy.y))

# Draw image-based obstacles
def draw_obstacles(obstacles):
    for obs in obstacles:
        screen.blit(obstacle_img, (obs['rect'].x, obs['rect'].y))

def draw_lives(surface, lives, max_lives):
    """Draw lives as small red hearts (fallback to rectangles)."""
    # Draw hearts using a unicode heart glyph; filled hearts for remaining lives
    padding = 10
    heart_size = max(20, player_width // 3)
    heart_text = '♥'
    for i in range(max_lives):
        x = padding + i * (heart_size + 8)
        y = padding
        if i < lives:
            color = (220, 20, 60)  # filled heart (crimson)
        else:
            color = (150, 150, 150)  # greyed-out
        txt = hud_font.render(heart_text, True, color)
        # scale text surface to roughly heart_size
        surface.blit(txt, (x, y))

def draw_score(surface, score):
    txt = hud_font.render(f"Score: {score}", True, (255, 255, 255))
    # draw in top-right corner with padding
    padding = 10
    surface.blit(txt, (WIDTH - txt.get_width() - padding, padding))

def draw_high_score(surface, high_score):
    txt = hud_font.render(f"High: {high_score}", True, (200, 200, 100))
    padding = 10
    surface.blit(txt, (WIDTH - txt.get_width() - padding, padding + 30))

def draw_popups(surface, popups):
    # render floating text and update TTL
    for p in popups[:]:
        txt = hud_font.render(p['text'], True, (255, 255, 255))
        surface.blit(txt, (p['x'], p['y']))
        # float up and decay
        p['y'] -= 0.5
        p['ttl'] -= 1
        if p['ttl'] <= 0:
            popups.remove(p)

def draw_powerups(surface, powerups):
    for pu in powerups:
        if pu['type'] == 'double_shot' and double_icon:
            surface.blit(pygame.transform.scale(double_icon, (obstacle_size, obstacle_size)), (pu['rect'].x, pu['rect'].y))
        elif pu['type'] == 'invisible' and invis_icon:
            surface.blit(pygame.transform.scale(invis_icon, (obstacle_size, obstacle_size)), (pu['rect'].x, pu['rect'].y))
        else:
            color = (50, 200, 50) if pu['type'] == 'double_shot' else (100, 100, 255)
            pygame.draw.rect(surface, color, pu['rect'])

def draw_pickup_msgs(surface, msgs):
    for m in msgs[:]:
        # render with alpha by creating a temporary surface
        txt = hud_font.render(m['text'], True, (255, 255, 255))
        surf = pygame.Surface(txt.get_size(), pygame.SRCALPHA)
        surf.blit(txt, (0, 0))
        surf.set_alpha(m['alpha'])
        surface.blit(surf, (m['x'], m['y']))
        m['y'] -= 0.5
        m['alpha'] = max(0, m['alpha'] - 2)
        m['ttl'] -= 1
        if m['ttl'] <= 0 or m['alpha'] <= 0:
            msgs.remove(m)

def draw_powerup_timers(surface):
    padding = 10
    x = padding
    y = padding + 40
    if double_shot_active:
        remaining = max(0, (double_shot_ends - pygame.time.get_ticks()) // 1000)
        txt = hud_font.render(f"Double: {remaining}s", True, (200, 200, 255))
        surface.blit(txt, (x, y))
        y += txt.get_height() + 4
    if invisible_active:
        remaining = max(0, (invisible_ends - pygame.time.get_ticks()) // 1000)
        txt = hud_font.render(f"Invisible: {remaining}s", True, (200, 200, 255))
        surface.blit(txt, (x, y))

def show_game_over(surface, score, high_score):
    # dark overlay
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(180)
    overlay.fill((0, 0, 0))
    surface.blit(overlay, (0, 0))
    large = pygame.font.SysFont(None, max(48, WIDTH // 20))
    txt1 = large.render("Game Over", True, (255, 50, 50))
    txt2 = hud_font.render(f"Score: {score}", True, (255, 255, 255))
    txt3 = hud_font.render(f"High Score: {high_score}", True, (255, 255, 0))
    txt4 = hud_font.render("Press R to Restart or ESC to Quit", True, (200, 200, 200))
    surface.blit(txt1, ((WIDTH - txt1.get_width()) // 2, HEIGHT // 2 - 80))
    surface.blit(txt2, ((WIDTH - txt2.get_width()) // 2, HEIGHT // 2 - 20))
    surface.blit(txt3, ((WIDTH - txt3.get_width()) // 2, HEIGHT // 2 + 20))
    surface.blit(txt4, ((WIDTH - txt4.get_width()) // 2, HEIGHT // 2 + 80))

def sweep_bottom_clutter(enemies, obstacles, bullets, popups, margin=4):
    """Remove any sprites that have their bottom at or below HEIGHT - margin."""
    # enemies: list of pygame.Rect
    for e in enemies[:]:
        try:
            bottom = getattr(e, 'bottom', e.y + (e.height if hasattr(e, 'height') else 0))
        except Exception:
            bottom = e.y
        if bottom >= HEIGHT - margin:
            try:
                enemies.remove(e)
            except ValueError:
                pass
    for obs in obstacles[:]:
        try:
            if obs['rect'].bottom >= HEIGHT - margin:
                obstacles.remove(obs)
        except Exception:
            try:
                obstacles.remove(obs)
            except Exception:
                pass
    for b in bullets[:]:
        try:
            if b.y >= HEIGHT - margin:
                bullets.remove(b)
        except Exception:
            try:
                bullets.remove(b)
            except Exception:
                pass
    # popups are text, remove those near bottom
    for p in popups[:]:
        try:
            if p.get('y', 0) >= HEIGHT - margin:
                popups.remove(p)
        except Exception:
            try:
                popups.remove(p)
            except Exception:
                pass

# Game loop
running = True
while running:
    clock.tick(60)
    screen.blit(background_img, (0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        # Allow exiting fullscreen/quit with ESC key
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_c:
                # manual cleanup sweep (larger margin)
                sweep_bottom_clutter(enemies, obstacles, bullets, popups, margin=20)
            if game_over and event.key == pygame.K_r:
                # Restart the game
                # reset game state
                enemies.clear()
                obstacles.clear()
                bullets.clear()
                popups.clear()
                lives = max_lives
                score = 0
                invulnerable = False
                game_over = False

    # Movement
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT] and player_x > 0:
        player_x -= player_speed
    if keys[pygame.K_RIGHT] and player_x < WIDTH - player_width:
        player_x += player_speed

    # Fire with UP key and cooldown
    current_time = pygame.time.get_ticks()
    if keys[pygame.K_UP]:
        if current_time - last_shot_time > fire_delay:
            # Fire bullets (supports double shot)
            by = player_y
            if double_shot_active:
                bx1 = player_x + player_width // 4
                bx2 = player_x + (player_width * 3) // 4
                bullets.append(pygame.Rect(bx1, by, 4, 10))
                bullets.append(pygame.Rect(bx2, by, 4, 10))
            else:
                bx = player_x + player_width // 2 - 2
                bullets.append(pygame.Rect(bx, by, 4, 10))
            pew_sound.play()  # pew or retro
            last_shot_time = current_time

    # Move bullets
    for bullet in bullets[:]:
        bullet.y -= bullet_speed
        # remove bullets off top or stuck at bottom
        if bullet.y < 0 or bullet.y > HEIGHT:
            try:
                bullets.remove(bullet)
            except ValueError:
                pass

    # Move enemies
    for enemy in enemies[:]:
        enemy.y += enemy_speed
        # Remove enemies that move off-screen or get stuck at bottom
        try:
            if enemy.y > HEIGHT or getattr(enemy, 'bottom', enemy.y + enemy.height if hasattr(enemy, 'height') else enemy.y) >= HEIGHT - 2:
                enemies.remove(enemy)
        except Exception:
            # fallback remove by position
            if enemy.y > HEIGHT:
                try:
                    enemies.remove(enemy)
                except ValueError:
                    pass

    # Move obstacles
    for obs in obstacles[:]:
        obs['rect'].y += obstacle_speed
        # Remove obstacles that move off-screen or sit at bottom
        if obs['rect'].y > HEIGHT or obs['rect'].bottom >= HEIGHT - 2:
            try:
                obstacles.remove(obs)
            except ValueError:
                pass

    # Bullet hits enemy
    for enemy in enemies[:]:
        for bullet in bullets[:]:
            if enemy.colliderect(bullet):
                enemies.remove(enemy)
                bullets.remove(bullet)
                explosion_sound.play()
                score += 1
                # create a popup
                popups.append({'text': '+1', 'x': enemy.x, 'y': enemy.y, 'ttl': 60})
                break

    # Enemy hits player (touch) -> lose life unless invisible
    if not invisible_active:
        player_rect = pygame.Rect(player_x, player_y, player_width, player_height)
        for enemy in enemies[:]:
            if player_rect.colliderect(enemy):
                try:
                    enemies.remove(enemy)
                except ValueError:
                    pass
                lives -= 1
                explosion_sound.play()
                invulnerable = True
                invuln_time = pygame.time.get_ticks()
                if lives <= 0:
                    game_over = True
                    enemies.clear(); obstacles.clear(); bullets.clear(); popups.clear()
                break

    # Move powerups
    for pu in powerups[:]:
        pu['rect'].y += max(1, obstacle_speed // 2)
        pu['ttl'] -= 1
        if pu['rect'].y > HEIGHT or pu['ttl'] <= 0:
            try:
                powerups.remove(pu)
            except ValueError:
                pass

    # Player collects powerups
    player_rect = pygame.Rect(player_x, player_y, player_width, player_height)
    for pu in powerups[:]:
        if player_rect.colliderect(pu['rect']):
            if pu['type'] == 'double_shot':
                double_shot_active = True
                double_shot_ends = pygame.time.get_ticks() + POWERUP_DURATION
                # show pickup message and sound
                pickup_msgs.append({'text': 'Double Shot!', 'x': player_x, 'y': player_y - 20, 'alpha': 255, 'ttl': 80})
                if pickup_sound:
                    pickup_sound.play()
            elif pu['type'] == 'invisible':
                invisible_active = True
                invisible_ends = pygame.time.get_ticks() + POWERUP_DURATION
                pickup_msgs.append({'text': 'Invisible!', 'x': player_x, 'y': player_y - 20, 'alpha': 255, 'ttl': 80})
                if pickup_sound:
                    pickup_sound.play()
            try:
                powerups.remove(pu)
            except ValueError:
                pass

    # Bullet hits obstacle
    for obs in obstacles[:]:
        for bullet in bullets[:]:
            if obs['rect'].colliderect(bullet):
                bullets.remove(bullet)
                try:
                    obstacles.remove(obs)
                except ValueError:
                    pass
                explosion_sound.play()
                break

    # Player hits obstacle (respect invulnerability)
    player_rect = pygame.Rect(player_x, player_y, player_width, player_height)
    if not invulnerable:
        for obs in obstacles[:]:
            if player_rect.colliderect(obs['rect']):
                lives -= 1
                print(f"💥 You hit an obstacle! Lives left: {lives}")
                try:
                    obstacles.remove(obs)
                except ValueError:
                    pass
                explosion_sound.play()
                invulnerable = True
                invuln_time = pygame.time.get_ticks()
                if lives <= 0:
                    print("No lives left. Game Over.")
                    game_over = True
                    # clear bottom clutter immediately to reveal Game Over overlay
                    enemies.clear()
                    obstacles.clear()
                    bullets.clear()
                    popups.clear()
                break

    # Random spawn (disabled while game over)
    if not game_over:
        if random.randint(1, 40) == 1:
            spawn_enemy()
        if random.randint(1, 60) == 1:
            spawn_obstacle()

    # Update invulnerability
    if invulnerable:
        if pygame.time.get_ticks() - invuln_time > INVULN_DURATION:
            invulnerable = False

    # Update power-up timers
    if double_shot_active and pygame.time.get_ticks() > double_shot_ends:
        double_shot_active = False
    if invisible_active and pygame.time.get_ticks() > invisible_ends:
        invisible_active = False

    # Draw all
    # If invulnerable, blink the player
    if invulnerable and (pygame.time.get_ticks() // 150) % 2 == 0:
        # skip drawing player to create blink effect
        pass
    else:
        draw_player(player_x, player_y)
    draw_bullets(bullets)
    draw_enemies(enemies)
    draw_obstacles(obstacles)
    draw_powerups(screen, powerups)
    # Sweep any bottom-clutter that might have been missed
    sweep_bottom_clutter(enemies, obstacles, bullets, popups)
    # Draw HUD (lives)
    draw_lives(screen, lives, max_lives)
    draw_score(screen, score)
    draw_high_score(screen, high_score)
    draw_powerup_timers(screen)
    draw_popups(screen, popups)
    draw_pickup_msgs(screen, pickup_msgs)

    # If game over, show overlay and wait for restart/quit
    if game_over:
        # update high score if needed
        if score > high_score:
            high_score = score
            try:
                with open(HIGH_SCORE_FILE, 'w') as f:
                    f.write(str(high_score))
            except Exception:
                pass
        show_game_over(screen, score, high_score)

    pygame.display.flip()

# Quit
pygame.quit()
sys.exit()
