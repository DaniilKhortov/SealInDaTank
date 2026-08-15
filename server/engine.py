import pygame, time, random
from common.models import Hull, Turret, Enemy

class GameEngine:
    def __init__(self):
        
        # Вікно без вмісту
        pygame.display.set_mode((1, 1), pygame.NOFRAME)
        
        # Створення груп спрайтів
        self.all_sprites = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.enemy_bullets = pygame.sprite.Group()
        
        # Створення спрайтів (але без зображення)
        dummy_img = pygame.Surface((58, 110))
        self.dummy_enemy_img = pygame.Surface((52, 159))
        self.hull = Hull(dummy_img)
        self.turret = Turret(self.hull, dummy_img, [])
        self.all_sprites.add(self.hull, self.turret)
        self.just_shot = False # Дозвіл на постріл 
        self.last_spawn = time.time() # Час останнього спавну ворога
        self.explosions_this_frame = [] # Список координат вибухів для клієнта
        self.game_over = False     # Стан програшу
        self.death_time = None   # Таймер для 5-секундного очкування при поразці
        
    def update(self, commands):
        self.explosions_this_frame = []
        now = time.time()
        
        # Перевірка на програш
        if self.game_over: 
            return
        
        
        # Спавн ворога у випадковому місці кожні 10 секунд
        if now - self.last_spawn > 10:
            self.last_spawn = now
            
            enemy = Enemy(random.randint(100, 1180), random.randint(100, 620), self.dummy_enemy_img, self.hull, [])
            self.enemies.add(enemy)
            self.all_sprites.add(enemy)
            
        # Оновлення положення гравця
        self.hull.update(commands['w'], commands['s'], commands['a'], commands['d'], self.enemies)
        self.turret.update(commands['left'], commands['right'])
        self.just_shot = False

        # Реєстрація пострілу 
        if commands['shoot']:
            
            if self.turret.shoot(self.all_sprites, self.bullets, is_server=True):
                self.just_shot = True
        
        # Оновлення положення снарядів          
        self.bullets.update(pygame.Rect(0, 0, 1280, 720)) 
        # Оновлення положення ворогів
        self.enemies.update(is_server=True)
        
        # Дозвіл на постріл ворога
        for enemy in self.enemies:
            if getattr(enemy, 'should_shoot', False):
                enemy.shoot(self.all_sprites, self.enemy_bullets, is_server=True)
                enemy.should_shoot = False
        
        # Межі для видалення снарядів
        bounds = pygame.Rect(0, 0, 1280, 720)
        self.bullets.update(bounds)
        self.enemy_bullets.update(bounds)
        
        # Реєстрація ураження снарядом у ворога
        hits = pygame.sprite.groupcollide(self.enemies, self.bullets, True, True)
        for enemy_hit in hits:
            self.explosions_this_frame.append(enemy_hit.rect.center)

       # Реєстрація ураження снарядом у гравця з запуском таймеру очікування
        if pygame.sprite.spritecollide(self.hull, self.enemy_bullets, True):
            self.explosions_this_frame.append(self.hull.rect.center)
            self.game_over = True 
            self.death_time = now 
            
   # Отримання команд стану гри     
    def get_state(self):
            state = {
                "hull": {
                    "pos": self.hull.rect.center,
                    "angle": self.hull.angle,
                    "alive": not self.game_over
                },
                "turret": {
                    "offset": self.turret.offset_angle
                },
                "enemies": [
                    {"pos": e.rect.center, "angle": e.angle} for e in self.enemies
                ],
                "bullets": [
                    {"pos": b.rect.center, "angle": b.angle} for b in self.bullets
                ],
                "shot_event": self.just_shot, 
                "turret_pos": self.turret.rect.center,
                "enemy_bullets": [{"pos": b.rect.center, "angle": b.angle} for b in self.enemy_bullets],
                "explosions": self.explosions_this_frame,
                "game_over": self.game_over
            }
            return state

