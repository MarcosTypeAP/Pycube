# Ursina
from ursina import (
    Entity,
    color,
    scene,
    mouse,
    destroy,
    Sequence,
    Func,
    curve,
    raycast,
    Vec3,
    Vec2,
    Tooltip,
    InputField,
    DirectionalLight,
    Ursina,
    window,
    application,
    camera,
    Text,
    text,
    Button,
    Panel,
)
from ursina.prefabs.first_person_controller import FirstPersonController
from ursina.prefabs.sky import Sky
from ursina.shaders import lit_with_shadows_shader

# Python
import threading
import time

# App
from client import Network


class Voxel(Entity):
    def __init__(self, position=(0, 0, 0)):
        super().__init__(
            parent=scene,
            model='cube',
            collider='box',
            texture='white_cube',
            color=color.gray,
            #  color=color.rgba(0,0,0,0.1),  # xray
            position=position,
            scale=1,
            shader=lit_with_shadows_shader
        )
        self.original_color = self.color
        self.destroying = False

    def input(self, key):
        global actions_buffer
        if self.hovered:
            if key == 'right mouse down':
                pos = self.position + mouse.normal
                if not self.get_voxel(pos):
                    Voxel.create(position=pos)
                    if network:
                        actions_buffer.append((1, pos))
            elif key == 'left mouse down':
                if network:
                    actions_buffer.append((0, self.position))
                self.destroy()

    def on_mouse_enter(self):
        self.color = self.color.tint(0.1)

    def on_mouse_exit(self):
        self.color = self.original_color

    def destroy(self, animation=True):
        if not animation:
            destroy(self)
        elif not self.destroying:
            self.destroying = True
            Sequence(
                Func(self.animate_scale, 0, duration=1, curve=curve.out_expo),
                0.1,
                Func(destroy, self)
            ).start()

    @staticmethod
    def create(position, animation=True):
        v = Voxel(position=position)
        if animation:
            v.scale = 0.5
            v.animate_scale(1, duration=0.4, curve=curve.out_expo)

    @staticmethod
    def get_voxel(pos):
        directions = (
            (0, 1, 0), (0, -1, 0),
            (1, 0, 0), (-1, 0, 0),
            (0, 0, 1), (0, 0, -1),
        )
        for direction in directions:
            hit = raycast(pos, direction=direction, distance=0.51)
            #  Entity(model='sphere', color=color.red, scale=(0.1), position=pos)
            if not hit.entity:
                return None
            if hit.entity.position == pos:
                return hit.entity


class FPCPlayer(FirstPersonController):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def update_wrapper(f):
        def wrapper(self):
            f(self)
            if self.y < -10:
                self.position = Vec3(0, 0.5, 0)
                self.rotation_y = 45
                self.camera_pivot.rotation_x = 0
        return wrapper

    update = update_wrapper(FirstPersonController.update)


class ConnectTextInput(InputField):
    def __init__(self, action, **kwargs):
        super().__init__(**kwargs)
        self.action = action
        self.input = self.input_wrapper(InputField.input)
        self.tooltip = Tooltip('Enter')

    def input_wrapper(self, f):
        def wrapper(key):
            f(self, key)
            if self.active and key == 'enter' and not network:
                self.active = False
                try:
                    addr, port = self.text.split(':')
                    self.text_color = color.white
                    self.action(addr, int(port))
                except ValueError:
                    self.text_color = color.red
        return wrapper


def connect_to_server(server_addr, server_port):
    global network
    print('connecting')
    network = Network(server_addr, server_port)
    network.connect()
    network_handler.start()


def input(key):
    if key == 'escape' and map_downloaded:
        if mouse.locked:
            mouse.locked = False
            player.mouse_sensitivity = Vec2(0, 0)
        else:
            mouse.locked = True
            player.mouse_sensitivity = MOUSE_SENSITIVITY


def handle_network():
    global player
    if network and network.connected and player:
        while True:
            if network.local:
                time.sleep(NETWORK_DELAY)
            wereThereActions = bool(actions_buffer)
            net_data = network.send_data(player.position, actions_buffer)
            if net_data:
                received_data_buffer.append(net_data)
            elif player_pool:
                for p in player_pool.values():
                    destroy(p)
                player_pool.clear()
            if wereThereActions:
                actions_buffer.clear()


def update():
    global player_pool, map_downloaded

    for net_data in received_data_buffer:
        connected_playes_id = []
        for data_type, data in net_data:

            if data_type == 0:  # player position
                uid = data[0]
                pos = data[1]
                if uid in player_pool:
                    player_pool[uid].animate_position(
                        value=pos, duration=NETWORK_DELAY + 0.01,
                        curve=curve.linear
                    )
                else:
                    player_pool[uid] = Entity(
                        model='cube', scale=Vec3(1, 2, 1),
                        position=pos, color=color.random_color(),
                        origin_y=-0.5, shader=lit_with_shadows_shader
                    )
                connected_playes_id.append(uid)

            elif data_type == 1:  # actions
                action_type = data[0]
                action_data = data[1]

                if action_type == 0:  # destroy block
                    voxel = Voxel.get_voxel(tuple(action_data))
                    if voxel:
                        voxel.destroy(animation=map_downloaded)

                elif action_type == 1:  # create block
                    voxel = Voxel.get_voxel(tuple(action_data))
                    if not voxel:
                        Voxel.create(
                            position=action_data, animation=map_downloaded
                        )

        disconnected_players_id = set(player_pool.keys()).difference(
            set(connected_playes_id)
        )

        for player_id in disconnected_players_id:
            destroy(player_pool[player_id])
            del player_pool[player_id]

        if not map_downloaded:
            map_downloaded = True
            start_shaders()
            disable_connect_menu()

    received_data_buffer.clear()


def start_shaders():
    pivot = Entity()
    DirectionalLight(
        parent=pivot, position=Vec3(10, 10, 10),
        shadows=True, rotation=Vec3(45, -45, 45),
        shadow_map_resolution=Vec2(8192, 8192)
    )


def start_game():
    global player, start_game_panel, network, sky

    destroy(start_game_panel)

    # Sky(texture='sky_sunset')
    sky = Sky()

    player = FPCPlayer(
        origin_y=-0.5, visible=False, y=0.5,
        mouse_sensitivity=MOUSE_SENSITIVITY,
    )
    player.camera_pivot.y -= 0.5


def multiplayer_setup():
    global connection_text_input

    connection_text_input = ConnectTextInput(
        default_value=DEFAULT_SERVER_ADDR,
        scale=(0.3, Text.size * 2),
        action=connect_to_server
    )
    connection_text_input.active = True

    start_game()
    enable_connect_menu()


def enable_connect_menu():
    player.disable()
    sky.disable()


def disable_connect_menu():
    player.enable()
    sky.enable()
    destroy(connection_text_input)


def singleplayer_setup():
    global map_downloaded

    for z in range(TERRAIN_WIDTH):
        for x in range(TERRAIN_WIDTH):
            for y in range(0, -3, -1):
                Voxel.create(position=(x, y, z), animation=False)

    map_downloaded = True

    start_shaders()
    start_game()


if __name__ == '__main__':
    app = Ursina()

    #  window.fullscreen = True
    #  window.size = window.fullscreen_size / 3
    window.size = window.fullscreen_size * 0.8
    #  window.exit_button.enabled = False
    window.vsync = True
    application.development_mode = False

    camera.fov = 100

    text.Text.size = 0.02

    MOUSE_SENSITIVITY = Vec2(50, 50)
    TERRAIN_WIDTH = 20
    NETWORK_DELAY = 0.07  # seconds
    DEFAULT_SERVER_ADDR = '127.0.0.1:8001'

    network = None
    player_pool = {}
    player = None
    actions_buffer = []
    received_data_buffer = []
    map_downloaded = False

    start_game_panel = Panel(color=color.rgba(0, 0, 0, 0))

    Button(
        parent=start_game_panel,
        text='singleplayer',
        scale=0.3,
        position=Vec2(-0.3, 0),
        on_click=singleplayer_setup
    )
    Button(
        parent=start_game_panel,
        text='multiplayer',
        scale=0.3,
        position=Vec2(0.3, 0),
        on_click=multiplayer_setup
    )

    network_handler = threading.Thread(target=handle_network, daemon=True)

    app.run()
