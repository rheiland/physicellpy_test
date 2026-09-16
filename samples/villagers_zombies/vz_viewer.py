"""Standalone VTK client that streams cell positions + type from vz_stream.py
and renders them live as colored spheres (0 = villager, 1 = zombie).

Run vz_stream.py first, then this script.
"""

import os
import socket
import struct
import sys

import numpy as np

try:
    import vtk
    from vtk.util import numpy_support
except ImportError:
    sys.exit("vtk is required to run this viewer. Install it with: pip install vtk")

HOST = '127.0.0.1'
PORT = 56790
RECV_TIMEOUT = 30.0  # seconds to wait for a frame before giving up
TIMER_INTERVAL_MS = 30
ZOMBIE_TEXTURE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "silly_zombie.png")

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

    # Villagers and zombies need different glyph geometry (sphere vs.
    # textured quad), so each type gets its own points/polydata/glyph/actor
    # -- a single vtkGlyph3D can only stamp one fixed source shape per input.

    # --- Villagers: spheres, solid color, scaled by radius ---
    villager_points = vtk.vtkPoints()
    villager_radius = vtk.vtkFloatArray()
    villager_radius.SetName("Radius")
    villager_polydata = vtk.vtkPolyData()
    villager_polydata.SetPoints(villager_points)
    villager_polydata.GetPointData().SetScalars(villager_radius)

    sphere_source = vtk.vtkSphereSource()
    sphere_source.SetRadius(1.0)  # unit sphere; actual size comes from glyph scaling
    sphere_source.SetThetaResolution(12)
    sphere_source.SetPhiResolution(12)

    villager_glyph = vtk.vtkGlyph3D()
    villager_glyph.SetSourceConnection(sphere_source.GetOutputPort())
    villager_glyph.SetInputData(villager_polydata)
    villager_glyph.SetScaleModeToScaleByScalar()
    villager_glyph.SetScaleFactor(1.0)

    villager_mapper = vtk.vtkPolyDataMapper()
    villager_mapper.SetInputConnection(villager_glyph.GetOutputPort())
    villager_mapper.ScalarVisibilityOff()

    villager_actor = vtk.vtkActor()
    villager_actor.SetMapper(villager_mapper)
    villager_actor.GetProperty().SetColor(*TYPE_COLORS[0])

    # --- Zombies: flat quads textured with a zombie image, scaled by radius ---
    zombie_points = vtk.vtkPoints()
    zombie_radius = vtk.vtkFloatArray()
    zombie_radius.SetName("Radius")
    zombie_polydata = vtk.vtkPolyData()
    zombie_polydata.SetPoints(zombie_points)
    zombie_polydata.GetPointData().SetScalars(zombie_radius)

    plane_source = vtk.vtkPlaneSource()
    plane_source.SetOrigin(-0.5, -0.5, 0.0)
    plane_source.SetPoint1(0.5, -0.5, 0.0)
    plane_source.SetPoint2(-0.5, 0.5, 0.0)

    plane_tcoords = vtk.vtkTextureMapToPlane()
    plane_tcoords.SetInputConnection(plane_source.GetOutputPort())

    zombie_glyph = vtk.vtkGlyph3D()
    zombie_glyph.SetSourceConnection(plane_tcoords.GetOutputPort())
    zombie_glyph.SetInputData(zombie_polydata)
    zombie_glyph.SetScaleModeToScaleByScalar()
    zombie_glyph.SetScaleFactor(4.0)  # plane spans [-0.5, 0.5] -> full size = 2x diameter
    # zombie_glyph.SetScaleFactor(1.0)  # plane spans [-0.5, 0.5] -> full size = 2x diameter

    zombie_mapper = vtk.vtkPolyDataMapper()
    zombie_mapper.SetInputConnection(zombie_glyph.GetOutputPort())
    zombie_mapper.ScalarVisibilityOff()

    zombie_reader = vtk.vtkPNGReader()
    zombie_reader.SetFileName(ZOMBIE_TEXTURE_PATH)
    zombie_texture = vtk.vtkTexture()
    zombie_texture.SetInputConnection(zombie_reader.GetOutputPort())
    zombie_texture.InterpolateOn()

    zombie_actor = vtk.vtkActor()
    zombie_actor.SetMapper(zombie_mapper)
    zombie_actor.SetTexture(zombie_texture)

    time_actor = vtk.vtkTextActor()
    time_actor.GetTextProperty().SetJustificationToCentered()
    time_actor.GetTextProperty().SetVerticalJustificationToTop()
    time_actor.GetTextProperty().SetFontSize(36)
    time_actor.GetTextProperty().SetColor(0.0, 0.0, 0.0)
    time_actor.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
    time_actor.GetPositionCoordinate().SetValue(0.5, 0.97)
    time_actor.SetInput("Press 'g' to start simulation")

    renderer = vtk.vtkRenderer()
    renderer.SetViewport(0.0, 0.28, 1.0, 1.0)
    renderer.AddActor(villager_actor)
    renderer.AddActor(zombie_actor)
    renderer.AddActor2D(time_actor)
    renderer.SetBackground(1.0, 1.0, 1.0)

    # Live time series of per-type cell counts, plotted in a strip below
    # the 3D view. History is kept as plain Python lists -- the counts are
    # derived from the CellType scalars already arriving each frame.
    count_history = {'time': [], 'villagers': [], 'zombies': []}

    count_table = vtk.vtkTable()
    for col_name in ('Time', 'Villagers', 'Zombies'):
        col = vtk.vtkFloatArray()
        col.SetName(col_name)
        count_table.AddColumn(col)

    chart = vtk.vtkChartXY()
    for axis_id in (vtk.vtkAxis.BOTTOM, vtk.vtkAxis.LEFT):
        axis = chart.GetAxis(axis_id)
        axis.SetGridVisible(False)
        axis.GetLabelProperties().SetColor(0.0, 0.0, 0.0)
        axis.GetLabelProperties().SetFontSize(20)
        axis.GetTitleProperties().SetColor(0.0, 0.0, 0.0)
    chart.GetAxis(vtk.vtkAxis.BOTTOM).SetTitle("Time (min)")
    chart.GetAxis(vtk.vtkAxis.BOTTOM).SetLabelsVisible(True)
    chart.GetAxis(vtk.vtkAxis.LEFT).SetTitle("Cell count")

    villager_plot = chart.AddPlot(vtk.vtkChart.LINE)
    villager_plot.SetInputData(count_table, 0, 1)
    villager_plot.SetColor(*(int(c * 255) for c in TYPE_COLORS[0]))
    villager_plot.SetWidth(4.0)

    zombie_plot = chart.AddPlot(vtk.vtkChart.LINE)
    zombie_plot.SetInputData(count_table, 0, 2)
    zombie_plot.SetColor(*(int(c * 255) for c in TYPE_COLORS[1]))
    zombie_plot.SetWidth(4.0)

    chart_scene = vtk.vtkContextScene()
    chart_scene.AddItem(chart)
    chart_actor = vtk.vtkContextActor()
    chart_actor.SetScene(chart_scene)

    chart_renderer = vtk.vtkRenderer()
    chart_renderer.SetViewport(0.0, 0.0, 1.0, 0.28)
    chart_renderer.SetBackground(1.0, 1.0, 1.0)
    chart_renderer.AddActor(chart_actor)
    # vtkPlotLine logs an error if asked to draw a line through <2 points;
    # hide the chart until the second data point arrives.
    chart_actor.SetVisibility(False)

    render_window = vtk.vtkRenderWindow()
    render_window.AddRenderer(renderer)
    render_window.AddRenderer(chart_renderer)
    render_window.SetSize(800, 900)
    render_window.SetWindowName("Villagers vs Zombies - Live")

    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(render_window)
    interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())

    state = {'frame_seen': False, 'timer_id': None}

    def update(obj, event):
        try:
            num_points, current_time, raw_positions, raw_types, raw_radii = client.read_frame()
        except (socket.timeout, ConnectionError, OSError) as exc:
            print(f"Stream ended: {exc}")
            interactor.DestroyTimer(state['timer_id'])
            time_actor.SetInput(time_actor.GetInput() + "  (simulation ended)")
            render_window.Render()
            return

        time_actor.SetInput(f"t = {current_time:.1f} min")

        pos_array = np.frombuffer(raw_positions, dtype=np.float32).reshape(num_points, 3)
        types_np = np.frombuffer(raw_types, dtype=np.float32)
        radii_np = np.frombuffer(raw_radii, dtype=np.float32)

        def update_group(polydata, points_obj, mask):
            vtk_pts = numpy_support.numpy_to_vtk(pos_array[mask], deep=True, array_type=vtk.VTK_FLOAT)
            points_obj.SetData(vtk_pts)
            vtk_radii = numpy_support.numpy_to_vtk(radii_np[mask], deep=True, array_type=vtk.VTK_FLOAT)
            vtk_radii.SetName("Radius")
            polydata.GetPointData().SetScalars(vtk_radii)
            polydata.Modified()

        update_group(villager_polydata, villager_points, types_np == 0)
        update_group(zombie_polydata, zombie_points, types_np == 1)

        count_history['time'].append(current_time)
        count_history['villagers'].append(int(np.count_nonzero(types_np == 0)))
        count_history['zombies'].append(int(np.count_nonzero(types_np == 1)))

        row = len(count_history['time']) - 1
        count_table.SetNumberOfRows(row + 1)
        count_table.SetValue(row, 0, count_history['time'][row])
        count_table.SetValue(row, 1, count_history['villagers'][row])
        count_table.SetValue(row, 2, count_history['zombies'][row])
        count_table.Modified()
        chart.RecalculateBounds()
        if row + 1 >= 2:
            chart_actor.SetVisibility(True)

        if not state['frame_seen']:
            state['frame_seen'] = True
            renderer.ResetCamera()

        render_window.Render()

    def on_keypress(obj, event):
        if obj.GetKeySym().lower() != 'g':
            return
        interactor.RemoveObserver(keypress_tag[0])
        time_actor.SetInput("t = 0.0 min")
        client.sock.sendall(b'g')
        state['timer_id'] = interactor.CreateRepeatingTimer(TIMER_INTERVAL_MS)
        interactor.AddObserver('TimerEvent', update)

    keypress_tag = [None]
    keypress_tag[0] = interactor.AddObserver('KeyPressEvent', on_keypress)

    interactor.Initialize()
    render_window.Render()

    try:
        interactor.Start()
    finally:
        client.close()


if __name__ == '__main__':
    main()
