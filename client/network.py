import redis, json, time

from common.config import REDIS_HOST, REDIS_PORT

# Підключення клієнта до БД Redis, що запущено на окремій машині
# можна звичайно і імпортувати зі спільного файлу, але часу обмаль
pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
r = redis.Redis(connection_pool=pool)


# Створення кімнати
def create_room(player_id):
    
    # Підписання у потік inbox для заяв на створення кімнат 
    my_inbox = f"client:{player_id}:inbox"
    pubsub = r.pubsub()
    pubsub.subscribe(my_inbox)
    
    print(f"[*] Subscribed on channel {my_inbox}. Sending request...")
    
    # Запит на створення кімнати
    r.xadd("global:requests", {
        "action": "create_room",
        "player_id": player_id,
        "reply_to": my_inbox 
    })
    
    # Очікування відповіді
    for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            return data.get('room_id')
    

    
# Функція отримання списку кімнат
def get_available_rooms():
    # Отримання всі ID кімнат 
    room_ids = r.smembers("active_rooms_list")
    available = []
    
    for rid in room_ids:
        
        # Отримання даних усіх кімнат
        data = r.hgetall(f"game_rooms:{rid}")
        if data.get("player2") == "":
            available.append({
                "id": rid,
                "player1": data.get("player1")
            })
    return available

# Функція приєднання другого гравця до кімнати
def join_game_request(player_id, room_id):
    my_inbox = f"client:{player_id}:inbox"
    r.xadd("global:requests", {
        "action": "join_room",
        "player_id": player_id,
        "room_id": room_id,
        "reply_to": my_inbox 
    })

# Функція, що запускає залу очікування
def waiting_to_start(player_id):
    my_inbox = f"client:{player_id}:inbox"
    pubsub = r.pubsub()
    pubsub.subscribe(my_inbox)
    for i in range(1, 4):
        print(f"\rWaiting for player to join{'.'*i}", end="")  
        time.sleep(1)   
        print(" " * 3, end="", flush=True) 
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                if data.get("status") == "start_game" or data.get("status") == "success":
                    print("\nGAME STARTING!")
                    return data    