# pycube
<img src="https://i.ibb.co/H45zQ4F/pycube.png">
Pycube is a very basic cube game with singleplayer/multiplayer-online, written in python.

Usage
-----

First you need to clone the repository or [download it](https://github.com/MarcosTypeAP/pycube-multiplayer-online/archive/refs/heads/main.zip), and then install python's dependencies.

```bash
git clone https://github.com/MarcosTypeAP/pycube-multiplayer-online.git
cd pycube-multiplayer-online/
python3 -m pip install -Ur requirements.txt
```

To execute the game just run `python3 main.py` and then select `singleplayer` in the game UI.

### Multiplayer

To play multiplayer, follow the next steps:
- Start the server with `python3 server.py` in other console
- Start the game with `python3 main.py`
- Select `multiplayer` in the game UI
- If the server isn't running locally, change the local IP for the server IP on your local network or a public one
- Press Enter to connect
