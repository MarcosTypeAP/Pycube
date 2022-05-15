import socket
import threading
import time
import sys


def client_thread(conn, addr):
    global player_pool
    if player_pool:
        client_id = max(player_pool.keys()) + 1
    else:
        client_id = 0
    client_id_encoded = str(client_id).encode('utf-8')
    conn.sendall(client_id_encoded)
    got_actions_index = 0
    player_pool[client_id] = b''
    print(f'Client ID sent ({client_id})')

    while not stop_threads:
        try:
            # Data sample:  b'1,1,1:0,2,2,2:1,3,3,3!'
            msg = conn.recv(BUFFER_SIZE)

            if not msg:
                break

            while msg[-1] != 33:  # not msg.endswith(b'!')  33 = !
                msg += conn.recv(BUFFER_SIZE)

            msg = msg[:-1]  # removes last b'!'

            if b':' in msg:
                pos, actions = msg.split(b':', 1)
                player_pool[client_id] = client_id_encoded + b':' + pos
                map_actions[0] += b':' + actions
                map_actions[1] += 1 + len(actions)
            else:
                player_pool[client_id] = client_id_encoded + b':' + msg

            reply = b''
            for uid, data in player_pool.items():
                if uid != client_id and data:
                    #  print(uid, data)
                    reply += data + b';'

            reply += map_actions[0][got_actions_index + 1:]  # skip fist b':'
            got_actions_index = map_actions[1]

            reply += b'!'
            conn.sendall(reply)
            #  print('msg:', msg)
            #  print(player_pool)
            #  print(map_actions[0])
            #  print('reply:', reply)
            #  print('/'*80)

        except ConnectionResetError:
            break

    del player_pool[client_id]
    print(f'Client Disconnected ({client_id})')


def remove_block_actions_redundancy():  # not tested
    global map_actions

    if not map_actions[0]:
        return

    actions = map_actions[0].split(b':')[1:]
    actions = list(set(actions))

    buffer = {}

    for action in actions:
        act_type, pos = action.split(b',', 1)
        if pos in buffer:
            del buffer[pos]
        else:
            buffer[pos] = act_type

    map_actions[0] = b''.join([
        b':' + act_type + b',' + pos
        for pos, act_type in buffer.items()
    ])
    map_actions[1] = len(map_actions[0])


def map_actions_handler_thread():
    while True:
        time.sleep(5)
        remove_block_actions_redundancy()


def main():
    while True:
        conn, addr = s.accept()
        t = threading.Thread(
            target=client_thread, args=(conn, addr), daemon=True
        )
        thread_pool.append(t)
        #  remove_block_actions_redundancy()
        t.start()
        print('New Client')


if __name__ == '__main__':
    SERVER_ADDR = ''  # 0.0.0.0
    SERVER_PORT = 8001
    BUFFER_SIZE = 2048
    MAP_WIDTH = 20
    MAP_HEIGHT = 3
    map_actions = [b'', 0]  # actions, len(actions)
    player_pool = {}
    thread_pool = []

    stop_threads = False

    for z in range(MAP_WIDTH):
        for x in range(MAP_WIDTH):
            for y in range(0, -MAP_HEIGHT, -1):
                # make_block,x,y,z
                map_actions[0] += f':1,{x},{y},{z}'.encode('utf-8')

    map_actions[1] = len(map_actions[0])

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((SERVER_ADDR, SERVER_PORT))
    s.listen(4)
    print('Server started')

    try:
        main()
    except KeyboardInterrupt:
        stop_threads = True
        for thread in thread_pool:
            while thread.is_alive():
                pass
        sys.exit(1)
