import socket


class Network:

    def __init__(self, server_addr, server_port):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_addr = server_addr
        self.server_port = server_port
        self.BUFFER_SIZE = 2048
        self.connected = False
        self.id = None
        local_addrs = ('127.0.0.1', 'localhost')
        self.local = True if server_addr in local_addrs else False

    def connect(self):
        if not self.connected:
            self.client.connect((self.server_addr, self.server_port))
            res = self.client.recv(64)
            self.id = int(res.decode('utf-8'))
            self.connected = True

    def serialize_data(self, x, y, z, actions):
        """
        Data sample: b'1,1,1:1,2,2,2'
        [  1,1,1 : 1,2,2,2  ]
        1,1,1    x,y,z : user position
        1,2,2,2  type,data : action
        # <type> 1 = create block
        # <data> 2,2,2 = block position x,y,z
        """
        data = '{},{},{}'.format(
            round(x, 3), round(y, 3), round(z, 3)
        )
        for action in actions:
            if action[0] in (0, 1):  # destroy, create blocks actions
                data += ':{},{},{},{}'.format(action[0], *action[1])
        data += '!'
        return data.encode('utf-8')

    def send_data(self, pos, actions):
        if self.connected:
            data = self.serialize_data(*pos, actions)
            self.client.sendall(data)
            res = self.client.recv(self.BUFFER_SIZE)
            while res[-1] != 33:  # ( not msg.endswith(b'!') )  33 = !
                res += self.client.recv(self.BUFFER_SIZE)
            if res == b'!':  # there're no users
                return ()
            return self.parse_data_generator(res)

    def parse_data_generator(self, data):
        """
        Data sample: b'0:1,1,1;2:4,4,4;1,2,2,2:0,1,1,1:0,2,2,2!'
        [  0 : 1,1,1 ; 1,2,2,2 : 0,3,3,3 !  ] OR [  0 : 1,1,1 ; ! ]
        0        n : user ID
        1,1,1    x,y,z : user position
        1,2,2,2  type,data : action
        # <type> 1 = create block
        # <data> 2,2,2 = block position x,y,z
        """
        *users_data, actions = data[:-1].split(b';')  # removes last b'!'
        for user_data in users_data:
            uid, position = user_data.split(b':')
            yield (
                0,  # player position tuple()
                (
                    int(uid),
                    [
                        float(axis)
                        for axis in position.split(b',')
                    ]
                )
            )
        if not actions:
            return
        for action in actions.split(b':'):
            action_type, *data = action.split(b',')
            yield (
                1,  # actions tuple()
                (
                    int(action_type),
                    [
                        float(axis) for axis in data
                    ]
                )
            )
