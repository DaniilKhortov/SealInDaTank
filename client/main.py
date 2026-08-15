from .network import create_room, get_available_rooms, waiting_to_start, join_game_request
from common.config import REDIS_HOST, REDIS_PORT
from enum import Enum
from .game_ui import GameRenderer
import json, pygame, redis, math
from common.models import Bullet, Explosion, Enemy, MuzzleFlash

# Клас Enum станів
class Status(Enum):
    DEFAULT = 1
    AWAIT = 2
    EXIT = 3
    
# Підключення клієнта до БД Redis, що запущено на окремій машині
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Визначення стану користувача клієнту
status = Status.DEFAULT


# Функція оновлення екрану графічного інтерфейсу користувача
def update_local_sprites(renderer, state):
    
    # Перевірка чи гравець живий. 
    # Якщо так, то передається позиція і стан корпусу, вежі до потоку
    # Якщо ні, то знищується танк гравців
    if state['hull']['alive']:
        renderer.player_hull.apply_state(state['hull']['pos'], state['hull']['angle'])
        renderer.player_turret.apply_state(state['turret']['offset'])
    else:
        renderer.player_hull.kill()
        renderer.player_turret.kill()
    
    # Припинення поведінки снарядів 
    for bullet in renderer.bullets_group:
        bullet.kill() 
    
    # Очищення снарядів  з групи 
    renderer.bullets_group.empty() 
    
    # Отримання нових даних про снаряди з сервера
    all_server_bullets = state['bullets'] + state['enemy_bullets']
    
    # Реєстрація даних про снаряди у клієнті
    for b_data in all_server_bullets:
            new_bullet = Bullet(b_data['pos'][0], b_data['pos'][1], b_data['angle'])
            renderer.bullets_group.add(new_bullet)
            renderer.all_sprites.add(new_bullet)

    # Очищення ворогів з групи та припинення їх поведінки        
    for e in renderer.enemies_group: 
        e.kill()
    renderer.enemies_group.empty()
        
        
    # Отримання нових даних про ворогів з сервера та реєстрація їх на клієнті 
    for e_data in state['enemies']:
        dummy_enemy = Enemy(e_data['pos'][0], e_data['pos'][1], renderer.enemy_img, None, [])
        dummy_enemy.angle = e_data['angle']
        dummy_enemy.image = pygame.transform.rotate(dummy_enemy.org_img, dummy_enemy.angle)
        renderer.enemies_group.add(dummy_enemy)
        renderer.all_sprites.add(dummy_enemy)
    
    # Обробка інформації при пострілі гравця та ефекту полумя дула
    if state.get('shot_event'):
        
        # Розрахунок позиції кінця дула
        total_angle = renderer.player_hull.angle + renderer.player_turret.offset_angle
        rad = math.radians(total_angle + 90)
        
        # Розміщення полумя дула
        t_pos = renderer.player_turret.rect.center
        flash_x = t_pos[0] + 95 * math.cos(-rad)
        flash_y = t_pos[1] + 95 * math.sin(-rad)

        # Створення ефекту полумя дула
        flash = MuzzleFlash(flash_x, flash_y, total_angle, renderer.flash_frames)
        renderer.all_sprites.add(flash) 
           
    # Обробка інформації про ефект вибуху 
    for exp_pos in state.get('explosions', []):
        renderer.all_sprites.add(Explosion(exp_pos, renderer.explosion_frames))
          
# Ігровий цикл та середовище циклу        
def run_game_loop(player_id, room_id, role):
    renderer = GameRenderer(role) # Рендер графічного інтерфейсу 
    running = True                # Стан циклу
    exit_timer = None             # Таймер виходу (треба для 5-секундної затримки)
    state_sub = r.pubsub(ignore_subscribe_messages=True) # Створення обєкту підписки 
    state_sub.subscribe(f"room:{room_id}:state") # Підписка на стан конкретної кімнати
    
    
    # Словник команд для різних ролей
    if role == "driver":
        key_map = {pygame.K_w: 'w', pygame.K_s: 's', pygame.K_a: 'a', pygame.K_d: 'd'}
    else:
        key_map = {pygame.K_f: 'left', pygame.K_g: 'right', pygame.K_SPACE: 'shoot'}
        
        
    # Головний цикл гри  
    while running:
        
         # Обробка виходу з вікна (Стандартний у pygame)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                running = False
            
            # Обробка натискання та відпускання клавіш
            # Це заощаджує на трафіку потоку
            if event.type in (pygame.KEYDOWN, pygame.KEYUP):
                
                if event.key in key_map:
                    
                    # 1 для KEYDOWN, 0 для KEYUP
                    val = 1 if event.type == pygame.KEYDOWN else 0
                    key_name = key_map[event.key]
                    
                    # Надсилання команди зміни стану кнопки 
                    r.xadd(f"room:{room_id}:commands", {
                        "player_id": player_id,
                        "key": key_name,
                        "value": val
                    }, maxlen=10)

        # Отримання команди і стану з серверу
        msg = state_sub.get_message()
        
        # Декодування повідомлення
        if msg:
            new_state = json.loads(msg['data'])
            update_local_sprites(renderer, new_state)
            
            # Якщо сервер зареєстрував поразку, то відбудиться 5-секундне очікування перед закриттям вікна клієнту
            if new_state.get('game_over') and exit_timer is None:
                exit_timer = pygame.time.get_ticks() + 5000
        
        # Вихід з циклу після 5-секундного очікування 
        if exit_timer and pygame.time.get_ticks() > exit_timer:
            running = False

        # Оновлення  рендеру спрайтів
        renderer.all_sprites.update()
        # Промальовка  спрайтів
        renderer.draw(renderer.player_hull, renderer.player_turret, renderer.all_sprites)
        # 60 тіків на секунду, що означає 60 кадр./с
        renderer.clock.tick(60)


# Меню
print("Welcome to tankCo-op!")
player_id = input("Enter name:")
while True:
    
    # Якщо гравець тільки зайшов, то потрапляє у меню
    if status == Status.DEFAULT:
        print(f"Choose option:\n1.Start game\n2.Join game\n3.Change name\n4.Quit\n")
        choice = input("Your choice:")
        match choice:
            # Створення кімнати
            case "1":
                room_id = create_room(player_id)
                if room_id:
                    print(f"Room {room_id} created!")
                    status = Status.AWAIT  
                    
            # Приєднання до кімнати       
            case "2":
                rooms = get_available_rooms()
                for i, room in enumerate(rooms):
                    print(f"[{i}] Room: {room['id']} (Awaiting gunner to {room['player1']})")
                    
                choice = int(input("Enter room id to join: "))
                target_room_id = rooms[choice]['id']
                join_game_request(player_id, target_room_id)
                status = Status.AWAIT
                
            # Зміна ідентифікатора   
            case "3":            
                player_id = input("Enter new name:") 
            
            # Вихід       
            case "4":
                status = "exit"
                break
            case _:
                print("invalid command")    
      
    # Гравець при переведені потрапляє у кімнату очікування   
    elif status == Status.AWAIT:
        game_data = waiting_to_start(player_id)
        if game_data:
            run_game_loop(player_id, game_data['room_id'], game_data['role'])
            break 
  
            

    