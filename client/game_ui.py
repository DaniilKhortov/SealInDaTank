import pygame, math
from common.models import Hull, Turret

#Клас з інструментами для рендеру графічного інтерфейсу
class GameRenderer:
    def __init__(self, role):
        self.screen = pygame.display.set_mode((1280, 720)) #Розмір вікна
        self.role = role                                   #Роль гравця
        
        #Завантаження ресурсів
        self.bg = pygame.image.load("assets/bg.png")
        self.hull_img = pygame.image.load("assets/hull_small_2.png")
        self.enemy_img = pygame.image.load("assets/tank_enemy_small.png")
        self.turret_img = pygame.image.load("assets/turret_small.png")    
        self.flash_frames = self.load_sprite_sheet("assets/shoot.png", 7, 4, 0.1, 90)
        self.raw_explosion = self.load_sprite_sheet("assets/exp.png", 4, 4, 2.0, 0)
        self.explosion_frames = self.raw_explosion[::-1] + self.raw_explosion
        
        
        #Створення груп спрайтів
        self.all_sprites =  pygame.sprite.Group()
        self.bullets_group = pygame.sprite.Group() 
        self.enemies_group = pygame.sprite.Group() 
        
        #Створення танку гравців
        self.player_hull = Hull(self.hull_img)
        self.player_turret = Turret(self.player_hull, self.turret_img, self.flash_frames)
        self.all_sprites.add(self.player_hull, self.player_turret)
        
        self.clock = pygame.time.Clock()
        
    #Функція промальовки вікна, спрайтів та туману війни
    def draw(self, hull, turret, all_sprites):  
        self.screen.blit(self.bg, (0, 0))
        all_sprites.draw(self.screen)
        
        self.draw_fog(hull, turret)
        pygame.display.flip()
       
    #Функція промальовки туману війни та поля зору гравців 
    def draw_fog(self, player_hull, player_turret):
        
        #Створення туману
        fog_surf = pygame.Surface((1280, 720), pygame.SRCALPHA)
        fog_surf.fill((10, 10, 15, 230))
        
        ##Створення полю зору (алгоритм прорізу крізь шар туману)
        
        #Створення різного огляду для гравця-водія та гравця-башнера
        p_center = player_hull.rect.center
        if self.role == "driver":
            self._draw_cone(fog_surf, p_center, player_hull.angle + 90, 45, 300)
        else:
            pygame.draw.circle(fog_surf, (0, 0, 0, 0), p_center, 150)
            self._draw_cone(fog_surf, p_center, player_hull.angle + player_turret.offset_angle + 90, 35, 600)

        self.screen.blit(fog_surf, (0, 0))
    
    #Функція промальовки трикутника поля зору (Взято з ШІ)
    def _draw_cone(self, surf, center, angle, spread, length):
            left = math.radians(angle - spread/2)
            right = math.radians(angle + spread/2)
            p2 = (center[0] + length * math.cos(-left), center[1] + length * math.sin(-left))
            p3 = (center[0] + length * math.cos(-right), center[1] + length * math.sin(-right))
            pygame.draw.polygon(surf, (0, 0, 0, 0), [center, p2, p3])
    
    #Функція завантаження ефектів для їх анімації
    def load_sprite_sheet(self, filename, cols, rows, scale, angle):
        
        sheet = pygame.image.load(filename).convert_alpha() #Завантаження зображення
        w = sheet.get_width() // cols    #Поділ вертикальний
        h = sheet.get_height() // rows   #Поділ горизонтальний
        
        #Створення меж кадру
        diagonal = int(math.sqrt(w**2 + h**2)) 
        
        #Запис кадрів
        frames = []
        for y in range(rows):
            for x in range(cols):
                # Обрізка
                raw_frame = sheet.subsurface(pygame.Rect(x * w, y * h, w, h))
                
                # Створення шару кадру
                temp_surface = pygame.Surface((diagonal, diagonal), pygame.SRCALPHA)
                
                # Нанемення на кадр зображення
                temp_surface.blit(raw_frame, (diagonal//2 - w//2, diagonal//2 - h//2))
                
                # Трансформація кадру
                new_size = (int(diagonal * scale), int(diagonal * scale))
                temp_surface = pygame.transform.rotate(temp_surface, angle)
                final_frame = pygame.transform.smoothscale(temp_surface, new_size)
                
                frames.append(final_frame)
        return frames






