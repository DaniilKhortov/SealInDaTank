import math, pygame, time

# Спрайт корпусу гравця
class Hull(pygame.sprite.Sprite):
    def __init__(self, image):
        super().__init__()
        #Завантаження зображення й положення
        self.org_img = image
        self.image = image
        self.rect = self.image.get_rect(center=(640, 360))
        
        #Параметри
        self.velocity = 0          # v
        self.max_speed = 3         # max v
        self.accel = 0.1           # a
        self.friction = 0.1        # f(p)
        self.angle = 0             # Кут відносно вертикалі
        self.rotate_speed = 2      # Обертова швидкість
        self.mask = pygame.mask.from_surface(self.image)
          
    def update(self, cmd_w=None, cmd_s=None, cmd_a=None, cmd_d=None, obstacle_group=None):
        
        
        # Кастиль для уникнення багу ініціалізації на клієнті
        if cmd_w is None:
            return
        
        #Пересування
        if cmd_a:
            self.angle += self.rotate_speed
        if cmd_d:
            self.angle -= self.rotate_speed
        
        #Обертання
        if cmd_w:
            self.velocity += self.accel
        elif cmd_s:
            self.velocity -= self.accel
        else:
            #Тертя
            if abs(self.velocity) > 0.1:
                self.velocity *= 0.95 
            else:
                self.velocity = 0
        
        #Задання v
        self.velocity = max(-self.max_speed, min(self.velocity, self.max_speed))

        #Задання положення корпусу
        rad = math.radians(self.angle + 90)
        self.rect.centerx += self.velocity * math.cos(-rad)
        self.rect.centery += self.velocity * math.sin(-rad)

        
        old_center = self.rect.center 
        
        # Застосування обернення на спрайті 
        self.image = pygame.transform.rotate(self.org_img, self.angle)
        
        # Застосування переміщення на спрайті 
        self.rect = self.image.get_rect(center=old_center) 
        
        # Колайдер
        if pygame.sprite.spritecollideany(self, obstacle_group):
            self.rect.center = old_center
            self.velocity = 0
            
        self.mask = pygame.mask.from_surface(self.image)
        
    # Застосування переміщення на спрайті при обробці пвідомлення з сервера
    def apply_state(self, pos, angle):
        self.rect.center = pos
        self.angle = angle
        self.image = pygame.transform.rotate(self.org_img, self.angle)
        self.rect = self.image.get_rect(center=self.rect.center)

# Спрайт башти гравця 
class Turret(pygame.sprite.Sprite):
    def __init__(self, hull, image, flash_frames):
        super().__init__()
        
        #Завантаження зображення й положення
        self.org_img = image
        self.image = self.org_img
        self.rect = self.image.get_rect()
        
        #Привязка до корпусу
        self.hull = hull
    
        self.offset_angle = 0                           #Кут відносно корпусу
        self.rotate_speed = 2                           # Обертова швидкість 
        self.img_offset = pygame.math.Vector2(0, 15)    # Вектор напрямку башти
        self.flash_frames = flash_frames                # Ефект полумя з дула 
        self.last_shot = 0                              # Час останнього пострілу (для перезарядки)
        self.reload_time = 3.0                          # Час перезарядки 
        
        

    
    # Постріл
    # Якщо відбувся, то повертає True
    # Якщо не може відбутися через перезаряядку, то False
    # Це економить трафік потоку, оскільки клієнт може надіслати команду раз в певний проміжок часу
    def shoot(self, all_sprites, bullets_group, is_server=False):
        
        
        now = time.time()
        # Перевірка перезарядки
        if now - self.last_shot > self.reload_time:
            self.last_shot = now
        
            # Визначення спрямування башти
            total_angle = self.hull.angle + self.offset_angle
            rad = math.radians(total_angle + 90)
            
            # Визначення положення кінця дула
            barrel_end_x = self.rect.centerx + 95 * math.cos(-rad)
            barrel_end_y = self.rect.centery + 95 * math.sin(-rad)
            
            # Створення снаряду
            bullet = Bullet(barrel_end_x, barrel_end_y, total_angle)
            bullets_group.add(bullet)
            all_sprites.add(bullet)
            
            # Створення спалаху але для клієнта
            if not is_server and self.flash_frames:
                flash = MuzzleFlash(barrel_end_x, barrel_end_y, total_angle, self.flash_frames)
                all_sprites.add(flash)
                
                
            return True
        return False
            
            
    def update(self, cmd_left=None, cmd_right=None):
        if cmd_left is None:
            return
        
        # Тригери на командах
        # Додають швидкість обертання
        if cmd_left:
            self.offset_angle += self.rotate_speed
        if cmd_right:
            self.offset_angle -= self.rotate_speed           
        
        #Визначення кута відносно вертикалі
        total_angle = self.hull.angle + self.offset_angle
   
        # Застосування оберту на спрайті
        self.image = pygame.transform.rotate(self.org_img, total_angle)
        rotated_offset = self.img_offset.rotate(-total_angle)
        
        # Змінення позиції спрайту (адже башта зміщена відносно корпусу трохи назад)
        self.rect = self.image.get_rect(center=self.hull.rect.center - rotated_offset)      
     
    # Застосування переміщення на спрайті при обробці пвідомлення з сервера  
    def apply_state(self, offset_angle):
        self.offset_angle = offset_angle
        total_angle = self.hull.angle + self.offset_angle
        self.image = pygame.transform.rotate(self.org_img, total_angle)
        rotated_offset = self.img_offset.rotate(-total_angle)
        self.rect = self.image.get_rect(center=self.hull.rect.center - rotated_offset)
        
                    
# Спрайт снаряду  
class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, angle):
        super().__init__()

        # Створення спрайту (він малюється, а не імпортується з зображення)
        self.image = pygame.Surface((2, 10), pygame.SRCALPHA)
        self.image.fill((255, 165, 0))
        self.image = pygame.transform.rotate(self.image, angle)
        self.rect = self.image.get_rect(center=(x, y))
        
        
        self.angle = angle # Кут відносно вертикалі
        self.speed = 20    # Швидкість польоту
        rad = math.radians(self.angle + 90)
        
        # Цільова позиція
        self.dx = math.cos(-rad) * self.speed 
        self.dy = math.sin(-rad) * self.speed

    def update(self, bounds_rect=None): 
        if bounds_rect is None:
            return
        self.rect.x += self.dx
        self.rect.y += self.dy
        if bounds_rect and not bounds_rect.colliderect(self.rect):
            self.kill()        

# Спрайт ефекту полумя з дула       
class MuzzleFlash(pygame.sprite.Sprite):
    def __init__(self, x, y, angle, frames):
        super().__init__()
        self.frames = frames # Імпорт розгортки
        self.current_frame = 0 # Початковий кадр
        self.image = pygame.transform.rotate(self.frames[self.current_frame], angle) # Обертання зображення за напрямком башти та задання зображення
        self.rect = self.image.get_rect(center=(x, y)) # Розміщення спрайту
        self.angle = angle # Кут відносно вертикалі
        self.animation_speed = 1  # Швидкість анімації

    def update(self):
        # Прокрутка анімації. При вичерпані кадрів самоусувається
        self.current_frame += self.animation_speed
        if self.current_frame >= len(self.frames):
            self.kill() 
        else:
            raw_image = self.frames[int(self.current_frame)]
            self.image = pygame.transform.rotate(raw_image, self.angle)
            self.rect = self.image.get_rect(center=self.rect.center)
  
#Спрайт ефекту вибуху при уражені
class Explosion(pygame.sprite.Sprite):
    def __init__(self, center, frames):
        super().__init__()
        self.frames = frames # Імпорт розгортки
        self.current_frame = 0 # Початковий кадр
        self.image = self.frames[self.current_frame] # задання зображення
        self.rect = self.image.get_rect(center=center) # Розміщення спрайту
        self.animation_speed = 0.8  # Швидкість анімації

    def update(self):
        # Прокрутка анімації. При вичерпані кадрів самоусувається
        self.current_frame += self.animation_speed
        if self.current_frame >= len(self.frames):
            self.kill() 
        else:
            self.image = self.frames[int(self.current_frame)]
            self.rect = self.image.get_rect(center=self.rect.center)  
  
            
# Чпрайт ворожого танку        
class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, image, player, flash_frames):
        super().__init__()
        
        # Імпорт зображення
        self.org_img = image 
        self.image = self.org_img
        self.rect = self.image.get_rect(center=(x, y))
        
        # Ціль ураження
        self.player = player
        
        #Ефект постріу (поки зламано)
        self.flash_frames = flash_frames
        
        
        self.angle = 0 #Кут відносно вертикалі 
        self.speed = 2 #Швидкість руху
    
        self.last_action = 0 # Час останньої дії
        
        self.action_cooldown = 3.0   # Перезарядка дії
        self.last_shot = 0 # Час останнього пострілу
        self.reload_time = 2.0 # Перезарядка пострілу
        
        self.moving = False # Дозвіл на пересування
        self.target_dist = 0 # Похибка для пострілу
        self.mask = pygame.mask.from_surface(self.image) # Маска колізії
        self.should_shoot = False # Дозвіл на постріл

    def update(self, is_server=False):
        if not is_server: 
            return
        now = time.time()

        # ШІ ворога
        
        #Ініціалізація дії
        if now - self.last_action > self.action_cooldown:
            
            # Визначення обертання на гравця
            self.last_action = now
            self.rotate_to_player()
            self.moving = True
            self.target_dist = 100 

        # Пересування
        if self.moving and self.target_dist > 0:
            rad = math.radians(self.angle + 30)
            dx = math.cos(-rad) * self.speed
            dy = math.sin(-rad) * self.speed
            self.rect.x += dx
            self.rect.y += dy
            self.target_dist -= self.speed
        else:
            self.moving = False

        # Перевірка чи гравець у зоні ураження
        self.check_line_of_sight(now)

        # Обертання спрайту 
        old_center = self.rect.center
        self.image = pygame.transform.rotate(self.org_img, self.angle)
        self.rect = self.image.get_rect(center=old_center)
        self.mask = pygame.mask.from_surface(self.image)

    # Функція обертання на гравця
    def rotate_to_player(self):
        # Обрахунок кута
        dx = self.player.rect.centerx - self.rect.centerx
        dy = self.player.rect.centery - self.rect.centery
        target_angle = math.degrees(math.atan2(-dy, dx)) - 90
        
        # Оберт до 30 градусів
        angle_diff = (target_angle - self.angle + 180) % 360 - 180
        angle_diff = max(-30, min(30, angle_diff))
        self.angle += angle_diff

    # Перевірка чи гравець у зоні ураження
    def check_line_of_sight(self, now):
        
        # Створення вектору вогню
        dx = self.player.rect.centerx - self.rect.centerx
        dy = self.player.rect.centery - self.rect.centery
        target_angle = math.degrees(math.atan2(-dy, dx)) - 90
        if abs((target_angle - self.angle + 180) % 360 - 180) < 10:
                    if now - self.last_shot > self.reload_time:
                        
                        # Дозвіл на постріл
                        self.should_shoot = True 
                        
                        self.last_shot = now
                        
                        
    # Створення снаряду ворога, що летить за вектором
    def shoot(self, all_sprites, enemy_bullets, is_server=True):
        rad = math.radians(self.angle + 90)
        barrel_end_x = self.rect.centerx + 100 * math.cos(-rad)
        barrel_end_y = self.rect.centery + 100 * math.sin(-rad)
        bullet = Bullet(barrel_end_x, barrel_end_y, self.angle)
        all_sprites.add(bullet)
        enemy_bullets.add(bullet)     