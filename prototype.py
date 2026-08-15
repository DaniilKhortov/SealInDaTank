# Example file showing a basic pygame "game loop"
import pygame
import math
import random

# pygame setup
pygame.init()
screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()
FOG_COLOR = (10, 10, 15, 230)
HULL_VISION_LENGTH = 300
HULL_VISION_ANGLE = 45
TURRET_VISION_RADIUS = 150
TURRET_CONE_LENGTH = 600
TURRET_CONE_ANGLE = 35



def load_sprite_sheet(filename, cols, rows, scale, angle):
    sheet = pygame.image.load(filename).convert_alpha()
    w = sheet.get_width() // cols
    h = sheet.get_height() // rows
    
    #Frame size
    diagonal = int(math.sqrt(w**2 + h**2)) 
    
    frames = []
    for y in range(rows):
        for x in range(cols):
            # cutting image
            raw_frame = sheet.subsurface(pygame.Rect(x * w, y * h, w, h))
            
            # creating surface
            temp_surface = pygame.Surface((diagonal, diagonal), pygame.SRCALPHA)
            
            # displaying image on surface
            temp_surface.blit(raw_frame, (diagonal//2 - w//2, diagonal//2 - h//2))
            
            # transformation of surface
            new_size = (int(diagonal * scale), int(diagonal * scale))
            temp_surface = pygame.transform.rotate(temp_surface, angle)
            final_frame = pygame.transform.smoothscale(temp_surface, new_size)
            
            frames.append(final_frame)
    return frames

#Function to display fog of war
def draw_fog(screen, player_hull, player_turret):
    
# 1. Створюємо поверхню туману

    # Creating fog
    fog_surf = pygame.Surface((1280, 720), pygame.SRCALPHA)
    fog_surf.fill(FOG_COLOR)

    # Vision of hull
    hull_angle_rad = math.radians(player_hull.angle + 90)
    p_center = player_hull.rect.center
    
    h_left = hull_angle_rad - math.radians(HULL_VISION_ANGLE / 2)
    h_right = hull_angle_rad + math.radians(HULL_VISION_ANGLE / 2)
    
    h_p2 = (p_center[0] + HULL_VISION_LENGTH * math.cos(-h_left), 
            p_center[1] + HULL_VISION_LENGTH * math.sin(-h_left))
    h_p3 = (p_center[0] + HULL_VISION_LENGTH * math.cos(-h_right), 
            p_center[1] + HULL_VISION_LENGTH * math.sin(-h_right))
    
    pygame.draw.polygon(fog_surf, (0, 0, 0, 0), [p_center, h_p2, h_p3])

    # vision of aim
    turret_total_angle = player_hull.angle + player_turret.offset_angle
    turret_angle_rad = math.radians(turret_total_angle + 90)
    
    t_left = turret_angle_rad - math.radians(TURRET_CONE_ANGLE / 2)
    t_right = turret_angle_rad + math.radians(TURRET_CONE_ANGLE / 2)
    
    t_p2 = (p_center[0] + TURRET_CONE_LENGTH * math.cos(-t_left), 
            p_center[1] + TURRET_CONE_LENGTH * math.sin(-t_left))
    t_p3 = (p_center[0] + TURRET_CONE_LENGTH * math.cos(-t_right), 
            p_center[1] + TURRET_CONE_LENGTH * math.sin(-t_right))
    
    pygame.draw.polygon(fog_surf, (0, 0, 0, 0), [p_center, t_p2, t_p3])

    # vision of turret`s tower
    pygame.draw.circle(fog_surf, (0, 0, 0, 0), p_center, TURRET_VISION_RADIUS)

    # applying fog of war
    screen.blit(fog_surf, (0, 0))
    
    
bg = pygame.image.load("assets/bg.png")
hull_img_org = pygame.image.load("assets/hull_small_2.png")
turret_img_org = pygame.image.load("assets/turret_small.png")
flash_frames = load_sprite_sheet("assets/shoot.png", 7, 4, 0.1, 90)
raw_explosion = load_sprite_sheet("assets/exp.png", 4, 4, 2.0, 0)
explosion_frames = raw_explosion[::-1] + raw_explosion





# Hull Sprite for player tank
class Hull(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.org_img = hull_img_org
        self.image = hull_img_org
        self.rect = self.image.get_rect()
        self.rect.center = (640, 360)
        self.velocity = 0          # v
        self.max_speed = 3         # max v
        self.accel = 0.1           # a
        self.friction = 0.1        # f(p)
        self.angle = 0             # angle
        self.rotate_speed = 2      # angle_v
        self.mask = pygame.mask.from_surface(self.image)
        
    #Movement & rotation    
    def update(self):
        
        # Triggers of buttons        
        keys = pygame.key.get_pressed()
        
        #Movement
        if keys[pygame.K_a]:
            self.angle += self.rotate_speed
        if keys[pygame.K_d]:
            self.angle -= self.rotate_speed
        
        #Rotation
        if keys[pygame.K_w]:
            self.velocity += self.accel
        elif keys[pygame.K_s]:
            self.velocity -= self.accel
        else:
            #Friction
            if abs(self.velocity) > 0.1:
                self.velocity *= 0.95 
            else:
                self.velocity = 0
        
        #Setting v
        self.velocity = max(-self.max_speed, min(self.velocity, self.max_speed))

        # Setting angle
        rad = math.radians(self.angle + 90)
        self.rect.centerx += self.velocity * math.cos(-rad)
        self.rect.centery += self.velocity * math.sin(-rad)

        
        old_center = self.rect.center 
        # Performing rotation of sprite
        self.image = pygame.transform.rotate(self.org_img, self.angle)
        
        # Changing position of sprite
        self.rect = self.image.get_rect(center=old_center) 
        
        old_pos = self.rect.topleft
        if pygame.sprite.spritecollideany(self, enemies):
            self.rect.topleft = old_pos # Повертаємо назад, якщо врізалися
            self.velocity = 0 
            
        self.mask = pygame.mask.from_surface(self.image)

# Turret Sprite for player tank   
class Turret(pygame.sprite.Sprite):
    def __init__(self, hull, flash_frames):
        super().__init__()
        self.org_img = turret_img_org
        self.image = self.org_img
        self.rect = self.image.get_rect()
        self.hull = hull
        self.offset_angle = 0  #angle
        self.rotate_speed = 2  # angle_v 
        self.img_offset = pygame.math.Vector2(0, 15)
        self.flash_frames = flash_frames
        self.last_shot = 0
        self.reload_time = 3000
        
        
    def update(self):
        keys = pygame.key.get_pressed()
        
        # Triggers of buttons 
        if keys[pygame.K_f]:
            self.offset_angle += self.rotate_speed
        if keys[pygame.K_g]:
            self.offset_angle -= self.rotate_speed
        
        #Defining total angle
        total_angle = self.hull.angle + self.offset_angle
   
        # Performing rotation of sprite
        self.image = pygame.transform.rotate(self.org_img, total_angle)
        rotated_offset = self.img_offset.rotate(-total_angle)
        
        # Changing position of sprite
        self.rect = self.image.get_rect(center=self.hull.rect.center - rotated_offset)      
    
    # Shooting
    def shoot(self, all_sprites, bullets_group):
        now = pygame.time.get_ticks()
        
        #Defining if gun is reloading
        if now - self.last_shot > self.reload_time:
            self.last_shot = now
            
            # Defining gun angle
            total_angle = self.hull.angle + self.offset_angle
            rad = math.radians(total_angle + 90)
            
            barrel_end_x = self.rect.centerx + 95 * math.cos(-rad)
            barrel_end_y = self.rect.centery + 95 * math.sin(-rad)
            
            # Performing shot
            bullet = Bullet(barrel_end_x, barrel_end_y, total_angle)
            flash = MuzzleFlash(barrel_end_x, barrel_end_y, total_angle, self.flash_frames)
            
            all_sprites.add(bullet, flash)
            bullets_group.add(bullet)
            
# Bullet projectile    
class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle):
        super().__init__()

        # Creating Sprite
        self.image = pygame.Surface((2, 10), pygame.SRCALPHA)
        self.image.fill((255, 165, 0))
        self.image = pygame.transform.rotate(self.image, angle)
        self.rect = self.image.get_rect(center=(x, y))
        
        # Vector of movement
        self.angle = angle
        self.speed = 20      
        rad = math.radians(self.angle + 90)
        self.dx = math.cos(-rad) * self.speed
        self.dy = math.sin(-rad) * self.speed

    def update(self):
        self.rect.x += self.dx
        self.rect.y += self.dy
        
        # Deleting bullet
        if not screen.get_rect().colliderect(self.rect):
            self.kill()        

# Muzzle Flash Effect        
class MuzzleFlash(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, frames):
        super().__init__()
        self.frames = frames
        self.current_frame = 0
        self.image = pygame.transform.rotate(self.frames[self.current_frame], angle)
        self.rect = self.image.get_rect(center=(x, y))
        self.angle = angle
        self.animation_speed = 1 

    def update(self):
        self.current_frame += self.animation_speed
        if self.current_frame >= len(self.frames):
            self.kill() 
        else:
            raw_image = self.frames[int(self.current_frame)]
            self.image = pygame.transform.rotate(raw_image, self.angle)
            self.rect = self.image.get_rect(center=self.rect.center)
  
#Explosion on death 
class Explosion(pygame.sprite.Sprite):
    def __init__(self, center, frames):
        super().__init__()
        self.frames = frames
        self.current_frame = 0
        self.image = self.frames[self.current_frame]
        self.rect = self.image.get_rect(center=center)
        self.animation_speed = 0.8 

    def update(self):
        self.current_frame += self.animation_speed
        if self.current_frame >= len(self.frames):
            self.kill() 
        else:
            self.image = self.frames[int(self.current_frame)]
            self.rect = self.image.get_rect(center=self.rect.center)  
  
            
# Sprite of enemy tank        
class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, player, flash_frames):
        super().__init__()
        self.org_img = pygame.image.load("assets/tank_enemy_small.png").convert_alpha()
        self.image = self.org_img
        self.rect = self.image.get_rect(center=(x, y))
        
        self.player = player
        self.flash_frames = flash_frames
        
        self.angle = 0
        self.speed = 2
        
        # Timers 
        self.last_action = pygame.time.get_ticks()
        self.action_cooldown = 3000  
        self.last_shot = 0
        self.reload_time = 2000
        
        self.moving = False
        self.target_dist = 0
        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        now = pygame.time.get_ticks()

        # AI
        
        #Action init
        if now - self.last_action > self.action_cooldown:
            self.last_action = now
            self.rotate_to_player()
            self.moving = True
            self.target_dist = 100 

        # Movement 
        if self.moving and self.target_dist > 0:
            rad = math.radians(self.angle + 30)
            dx = math.cos(-rad) * self.speed
            dy = math.sin(-rad) * self.speed
            self.rect.x += dx
            self.rect.y += dy
            self.target_dist -= self.speed
        else:
            self.moving = False

        # Checking if player is in the line of sight
        self.check_line_of_sight(now)

        # rotation
        old_center = self.rect.center
        self.image = pygame.transform.rotate(self.org_img, self.angle)
        self.rect = self.image.get_rect(center=old_center)
        self.mask = pygame.mask.from_surface(self.image)

    # Rotates enemy towards player
    def rotate_to_player(self):
        # Calc angle
        dx = self.player.rect.centerx - self.rect.centerx
        dy = self.player.rect.centery - self.rect.centery
        target_angle = math.degrees(math.atan2(-dy, dx)) - 90
        
        # Measurement up to 90
        angle_diff = (target_angle - self.angle + 180) % 360 - 180
        angle_diff = max(-90, min(90, angle_diff))
        self.angle += angle_diff

    # Checks if player is visible
    def check_line_of_sight(self, now):
        dx = self.player.rect.centerx - self.rect.centerx
        dy = self.player.rect.centery - self.rect.centery
        target_angle = math.degrees(math.atan2(-dy, dx)) - 90
        
        if abs((target_angle - self.angle + 180) % 360 - 180) < 10:
            if now - self.last_shot > self.reload_time:
                self.shoot()
                self.last_shot = now
    # creating projectile of enemy bulet
    def shoot(self):
        rad = math.radians(self.angle + 90)
        barrel_end_x = self.rect.centerx + 100 * math.cos(-rad)
        barrel_end_y = self.rect.centery + 100 * math.sin(-rad)
        
        bullet = Bullet(barrel_end_x, barrel_end_y, self.angle)
        flash = MuzzleFlash(barrel_end_x, barrel_end_y, self.angle, self.flash_frames)
        

        all_sprites.add(bullet, flash)
        enemy_bullets.add(bullet)        
        
            
            
all_sprites = pygame.sprite.Group()
enemies = pygame.sprite.Group()
bullets = pygame.sprite.Group()
enemy_bullets = pygame.sprite.Group()

player_hull = Hull()
player_turret = Turret(player_hull, flash_frames)
all_sprites.add(player_hull, player_turret)


game_over_timer = None
last_action = 0

running = True
while running:
    
    #spawn logic
    now = pygame.time.get_ticks()
    if game_over_timer is None:
        if now - last_action > 5000:
            last_action = now
            enemy = Enemy(random.randint(100, 1180), random.randint(100, 620), player_hull, flash_frames)
            all_sprites.add(enemy)
            enemies.add(enemy)

    all_sprites.update()

    #destruction logic
    hits = pygame.sprite.groupcollide(enemies, bullets, True, True)
    for enemy_hit in hits:
        exp = Explosion(enemy_hit.rect.center, explosion_frames)
        all_sprites.add(exp)
        
        
        
        
    #game over logic    
    if game_over_timer is None:
        player_hit = pygame.sprite.spritecollide(player_hull, enemy_bullets, True)
        if player_hit:
            exp = Explosion(player_hull.rect.center, explosion_frames)
            all_sprites.add(exp)
            print("Game Over!")
            # Замість running = False, ставимо таймер на 2 секунди (2000 мс)
            game_over_timer = now + 2000 
            # Ховаємо танк гравця, щоб він "зник" у вибуху
            player_hull.kill()
            player_turret.kill()  
    
    if game_over_timer and now > game_over_timer:
        running = False
    
    # poll for events
    # pygame.QUIT event means the user clicked X to close your window
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE: 
                player_turret.shoot(all_sprites, bullets)
                


    # Background display
    screen.blit(bg, (0, 0))  
    
    # Drawing sprites
    all_sprites.draw(screen) 
    
    # Applying fog of war
    if player_hull.alive():
        draw_fog(screen, player_hull, player_turret)
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()