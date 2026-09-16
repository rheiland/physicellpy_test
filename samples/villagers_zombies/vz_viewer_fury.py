"""FURY (GPU billboard-impostor sphere) client that streams cell positions,
type, and radius from vz_stream.py and renders them live.

FURY 2.0 draws these spheres as camera-facing shader impostors: each pixel's
sphere normal is reconstructed per-fragment, so the silhouette and shading
look like real spheres rather than faceted polygons -- but this is still
rasterization, not true path-traced ray tracing (which would need VTK's
OSPRay backend, CPU-only on macOS and too slow to re-trace every frame of a
live simulation).

Run vz_stream.py first, then this script; click the window and press 'g' to
start the simulation once connected.
"""

import socket
import struct

import numpy as np
try:
    from fury import actor, window
except ImportError:
    sys.exit("fury is required to run this viewer. Install it with: pip install fury")

HOST = '127.0.0.1'
PORT = 56790
RECV_TIMEOUT = 30.0  # seconds to wait for a frame before giving up
POLL_INTERVAL = 0.03  # seconds between stream polls

TYPE_COLORS = {
    0: (0.2, 0.6, 1.0),  # villager
    1: (0.8, 0.1, 0.1),  # zombie
}


def recv_exact(sock, num_bytes):
    buf = b""
    while len(buf) < num_bytes:
        chunk = sock.recv(num_bytes - len(buf))
        if not chunk:
            raise ConnectionError("Server closed the connection")
        buf += chunk
    return buf


class StreamClient:
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(RECV_TIMEOUT)
        print(f"Connecting to {host}:{port}...")
        self.sock.connect((host, port))
        print("Connected.")

    def read_frame(self):
        header = recv_exact(self.sock, 8)
        num_points, current_time = struct.unpack('!If', header)
        positions = recv_exact(self.sock, num_points * 3 * 4)
        types = recv_exact(self.sock, num_points * 4)
        radii = recv_exact(self.sock, num_points * 4)
        return num_points, current_time, positions, types, radii

    def close(self):
        self.sock.close()


def main():
    client = StreamClient(HOST, PORT)

    scene = window.Scene(background=(1, 1, 1, 1))
    camera = window.PerspectiveCamera()

    # ShowManager's default light is attached to the camera, so for a
    # straight-down view its direction nearly matches the view direction --
    # every sphere gets lit dead-on and shows almost no shading gradient,
    # looking flat. An off-axis light gives each sphere a visible light/dark
    # side despite the top-down view.
    key_light = window.DirectionalLight(color="#ffffff", intensity=3.0)
    key_light.local.position = (300, 300, 600)
    scene.add(key_light)
    scene.add(window.AmbientLight(intensity=0.3))

    show_manager = window.ShowManager(
        scene=scene,
        camera=camera,
        title="Villagers vs Zombies - FURY (press 'g' to start)",
        size=(800, 800),
    )

    state = {'cell_actor': None, 'frame_seen': False, 'sent_go': False}

    def poll_stream():
        try:
            num_points, current_time, raw_positions, raw_types, raw_radii = client.read_frame()
        except (socket.timeout, ConnectionError, OSError) as exc:
            print(f"Stream ended: {exc}")
            show_manager.cancel_callback("poll_stream")
            return

        pos = np.frombuffer(raw_positions, dtype=np.float32).reshape(num_points, 3)
        types_np = np.frombuffer(raw_types, dtype=np.float32)
        radii_np = np.frombuffer(raw_radii, dtype=np.float32)

        is_villager = (types_np == 0)[:, None]
        colors = np.where(
            is_villager,
            np.array(TYPE_COLORS[0], dtype=np.float32),
            np.array(TYPE_COLORS[1], dtype=np.float32),
        )

        # FURY has no in-place "move these points" update for billboard
        # impostors, so each frame swaps in a freshly built sphere actor.
        new_actor = actor.sphere(centers=pos, colors=colors, radii=radii_np, impostor=True)
        if state['cell_actor'] is not None:
            scene.remove(state['cell_actor'])
        scene.add(new_actor)
        state['cell_actor'] = new_actor

        n_villagers = int(np.count_nonzero(types_np == 0))
        n_zombies = int(np.count_nonzero(types_np == 1))
        print(f"t = {current_time:7.1f} min | villagers = {n_villagers} | zombies = {n_zombies}")

        if not state['frame_seen']:
            state['frame_seen'] = True
            camera.show_object(new_actor, view_dir=(0, 0, -1), up=(0, 1, 0))

        show_manager.render()

    def on_key_down(event):
        if state['sent_go'] or getattr(event, 'key', '').lower() != 'g':
            return
        state['sent_go'] = True
        client.sock.sendall(b'g')
        print("Go signal sent -- simulation starting.")
        show_manager.register_callback(poll_stream, POLL_INTERVAL, True, "poll_stream")

    show_manager.renderer.add_event_handler(on_key_down, window.EventType.KEY_DOWN)

    print("Click the render window and press 'g' to start the simulation.")

    try:
        show_manager.start()
    finally:
        client.close()


if __name__ == '__main__':
    main()
