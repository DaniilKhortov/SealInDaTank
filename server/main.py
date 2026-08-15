import redis
import json
import uuid
import time
import threading
from common.config import REDIS_HOST, REDIS_PORT
from .engine import GameEngine


# Підключення додатку до Redis
# можна звичайно і імпортувати зі спільного файлу, але часу обмаль
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)



active_games = {} # Кімнати
last_ids = {}  # Ідентифікатори кімнат
current_inputs = {}  # Поточні команди


# Рушій обчислення взаємодії спрайтів
def run_physics_loop():
    while True:
        # При відсутності ігор сервер сповільнюється
        if not active_games:
            time.sleep(0.5)
            continue
        
        # Зчитування станів кімнат
        for room_id, engine in list(active_games.items()):
            now = time.time()
            
             # Дії при завершені гри
            if engine.game_over and engine.death_time and (now - engine.death_time > 5):
                print(f"[#] Game Over in {room_id}. Cleaning up...")
                
                # Видалення потоку
                r.delete(f"room:{room_id}:commands")
                
                # Зняття з таблиці активних кімнат поточної кімнати
                r.srem("active_rooms_list", room_id)
                
                # Видалення даних кімнати
                r.delete(f"game_rooms:{room_id}")
                
                # Видалення зі списку ігор
                del active_games[room_id]
                if room_id in current_inputs:
                    del current_inputs[room_id]
                continue
            
            # Створення звичайної команди 
            if room_id not in current_inputs:
                current_inputs[room_id] = {"w":0, "s":0, "a":0, "d":0, "left":0, "right":0, "shoot":0}

            # Зчитування нових команд
            start_id = last_ids.get(room_id, "0-0")
            
            # Зчитання команди
            events = r.xread({f"room:{room_id}:commands": start_id}, count=10)
            if events:
                for _, msgs in events:
                    for m_id, data in msgs:
                        key = data.get('key')
                        val = int(data.get('value', 0))
                        if key in current_inputs[room_id]:
                            current_inputs[room_id][key] = val
                        
                        last_ids[room_id] = m_id

            engine.update(current_inputs[room_id])

            # Створення пубдікації стану           
            state = engine.get_state()
            r.publish(f"room:{room_id}:state", json.dumps(state))
            
            # Обробка пострілу
            if current_inputs[room_id]['shoot'] == 1:
                 current_inputs[room_id]['shoot'] = 0

        # Частота ноновлення
        time.sleep(0.01)
        
def start_server():
    print("Server online")
    last_id = '$'  

    while True:
        # Читання записту зі стріму 
        events = r.xread({"global:requests": last_id}, block=5000)
        
        if not events:
            continue

        # Обробка запиту
        for stream, messages in events:
            for msg_id, data in messages:
                process_request(data)
                last_id = msg_id  

# Обробка запиту
def process_request(data):
    action = data.get("action")
    player_id = data.get("player_id")
    reply_channel = data.get("reply_to") 

    # Реакція на створення кімнати
    if action == "create_room":
        
        # Генерація коду кімнати
        room_id = f"room_{uuid.uuid4().hex[:6]}"
        
        # Збереження кімнати
        room_data = {
            "status": "waiting",
            "player1": player_id,
            "player2": "",
            "created_at": "timestamp_here"
        }
        r.hset(f"game_rooms:{room_id}", mapping=room_data)
        
        # Додавання в список активних кімнат
        r.sadd("active_rooms_list", room_id)

        print(f"[*] Creted room {room_id} for player {player_id}")

        # Відправка відповіді клієнту
        response = {
            "status": "success",
            "room_id": room_id,
        }
        r.publish(reply_channel, json.dumps(response))
    elif action == "join_room":    
        process_join_request(data)
        
# Функція доєднання до кімнати    
def process_join_request(data):
    room_id = data.get("room_id")
    new_player_id = data.get("player_id")
    reply_channel = data.get("reply_to")
    
    room_key = f"game_rooms:{room_id}"

    if not r.exists(room_key):
        send_response(reply_channel, "error", "Room not found")
        return

    current_p1 = r.hget(room_key, "player1")
    current_p2 = r.hget(room_key, "player2")

    if new_player_id == current_p1:
        send_response(reply_channel, "error", "You already enroled here!")
        return
        
    if current_p2 != "":
        send_response(reply_channel, "error", "Room is full!")
        return


    r.hset(room_key, "player2", new_player_id)
    r.hset(room_key, "status", "active")

    active_games[room_id] = GameEngine() 

    print(f"[+] Player {new_player_id} joined to {room_id}. Game started!")

    join_response = {
        "status": "success",
        "room_id": room_id,
        "role": "gunner"
    }
    r.publish(reply_channel, json.dumps(join_response))

    p1_inbox = f"client:{current_p1}:inbox"
    notification = {
        "status": "start_game",
        "room_id": room_id,
        "role": "driver"
    }
    r.publish(p1_inbox, json.dumps(notification))

def send_response(channel, status, message):
    r.publish(channel, json.dumps({"status": status, "message": message}))        

if __name__ == "__main__":
    try:
        threading.Thread(target=run_physics_loop, daemon=True).start()
        start_server()
    except KeyboardInterrupt:
        print("\nServer killed!.")