from __future__ import annotations

import importlib
import argparse
import base64
from pathlib import Path
import urllib.request
import numpy as np
import json
import webbrowser
from typing import Any, Iterable, Mapping, Sequence


def _optional_import(module: str) -> Any:
    try:
        return importlib.import_module(module)
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            f"Optional dependency '{module}' is required for this visualization method. "
            "Install it (e.g. `pip install matplotlib pandas plotly`) and try again."
        ) from exc


def _image_to_data_uri(path: str | Path) -> str:
    image_path = Path(path)
    content = image_path.read_bytes()
    encoded = base64.b64encode(content).decode('ascii')
    suffix = image_path.suffix.lower().lstrip('.')
    mime = 'png' if suffix not in {'png', 'jpg', 'jpeg', 'webp'} else suffix
    if mime == 'jpg':
        mime = 'jpeg'
    return f"data:image/{mime};base64,{encoded}"


def _as_int_bounds(bounds: Sequence[int]) -> tuple[int, int, int, int]:
    if len(bounds) != 4:
        raise ValueError('bounds must be 4 integers: x_min y_min x_max y_max')
    x_min, y_min, x_max, y_max = (int(bounds[0]), int(bounds[1]), int(bounds[2]), int(bounds[3]))
    if x_max <= x_min or y_max <= y_min:
        raise ValueError('invalid bounds: require x_max>x_min and y_max>y_min')
    return x_min, y_min, x_max, y_max


def _download_if_missing(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    tmp = dest.with_suffix(dest.suffix + '.tmp')
    if tmp.exists():
        try:
            tmp.unlink()
        except Exception:
            pass
    urllib.request.urlretrieve(url, tmp)  # noqa: S310
    tmp.replace(dest)
    return dest


def _tibiamaps_floor_image_url(floor: int) -> str:
    return f"https://tibiamaps.github.io/tibia-map-data/floor-{floor:02d}-map.png"


def _tibiamaps_bounds_url() -> str:
    return "https://tibiamaps.github.io/tibia-map-data/bounds.json"


def _tibiamaps_bounds_to_world(bounds_json: Mapping[str, Any]) -> tuple[int, int, int, int]:
    # bounds.json is in Tibia world coordinates (sqm), aligned to 256-sqm tile origins.
    # xMax/yMax represent the last tile origin included; convert to an exclusive upper bound
    # by adding 256, so that (x_max - x_min) == width and (y_max - y_min) == height.
    x_min = int(bounds_json['xMin'])
    x_max_inclusive_tile_origin = int(bounds_json['xMax'])
    y_min = int(bounds_json['yMin'])
    y_max_inclusive_tile_origin = int(bounds_json['yMax'])
    x_max = x_max_inclusive_tile_origin + 256
    y_max = y_max_inclusive_tile_origin + 256
    return x_min, y_min, x_max, y_max


def _parse_int_list(arg: str) -> list[int]:
    parts = [p.strip() for p in arg.replace(';', ',').split(',') if p.strip()]
    out: list[int] = []
    for part in parts:
        out.append(int(part))
    return out


def _apply_point_modifications(
    data: Sequence[Mapping[str, Any]],
    *,
    shift: tuple[int, int] | None = None,
    snap: int | None = None,
    only_z: int | None = None,
    dedupe: bool = False,
) -> list[dict[str, Any]]:
    """Apply simple, safe modifications to waypoint coordinates.

    - shift: (dx, dy) added to X/Y.
    - snap: grid size for rounding X/Y to nearest multiple.
    - only_z: only modify points at this floor.
    - dedupe: removes consecutive duplicates, but only when the *entire step* is identical.
    """

    dx, dy = shift if shift else (0, 0)
    grid = int(snap) if snap is not None else 0
    if grid < 0:
        raise ValueError('snap must be >= 0')

    out: list[dict[str, Any]] = []
    prev_step: dict[str, Any] | None = None

    for step in data:
        # Clone to avoid mutating the input mapping.
        new_step: dict[str, Any] = dict(step)
        coord = step.get('coordinate')
        if isinstance(coord, (list, tuple)) and len(coord) >= 3:
            x, y, z = int(coord[0]), int(coord[1]), int(coord[2])
            if only_z is None or z == only_z:
                x += dx
                y += dy
                if grid and grid > 1:
                    x = int(round(x / grid) * grid)
                    y = int(round(y / grid) * grid)
            new_step['coordinate'] = [x, y, z]

        if dedupe and prev_step is not None and new_step == prev_step:
            continue
        out.append(new_step)
        prev_step = new_step

    return out


def _validate_floor_transitions(data: Sequence[Mapping[str, Any]]) -> list[str]:
    warnings: list[str] = []

    def _get_coord(step: Mapping[str, Any]) -> tuple[int, int, int] | None:
        coord = step.get('coordinate')
        if not (isinstance(coord, (list, tuple)) and len(coord) >= 3):
            return None
        try:
            return (int(coord[0]), int(coord[1]), int(coord[2]))
        except (TypeError, ValueError):
            return None

    expected_dz_by_type: dict[str, int] = {
        'moveDown': 1,
        'moveUp': -1,
        'useRope': -1,
        'useLadder': -1,
        'useHole': 1,
    }

    for i in range(len(data) - 1):
        step = data[i]
        nxt = data[i + 1]
        c1 = _get_coord(step)
        c2 = _get_coord(nxt)
        if c1 is None or c2 is None:
            continue
        z1 = c1[2]
        z2 = c2[2]
        wtype = str(step.get('type', ''))
        dz = z2 - z1

        if wtype in expected_dz_by_type:
            expected_dz = expected_dz_by_type[wtype]
            if dz != expected_dz:
                warnings.append(
                    f"step[{i}] type={wtype} at z={z1} -> next z={z2} (dz={dz}); expected dz={expected_dz}"
                )
            continue

        if z1 != z2:
            warnings.append(
                f"step[{i}] type={wtype or '<missing>'} changes floor z={z1} -> z={z2} (dz={dz}) without an explicit transition action"
            )

    return warnings


def _audit_move_directions(
    data: Sequence[Mapping[str, Any]],
    *,
    fix: bool = False,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Audit (and optionally fix) moveUp/moveDown directions.

    We infer direction from the previous *same-floor* adjacent step (prev -> current).
    This matches the typical route where you walk up to the stair/hole tile and then
    press the same direction again to transition floors.
    """

    def _get_coord(step: Mapping[str, Any]) -> tuple[int, int, int] | None:
        coord = step.get('coordinate')
        if not (isinstance(coord, (list, tuple)) and len(coord) >= 3):
            return None
        try:
            return (int(coord[0]), int(coord[1]), int(coord[2]))
        except (TypeError, ValueError):
            return None

    def _infer_from_prev(i: int) -> str | None:
        c = _get_coord(data[i])
        if c is None:
            return None
        x, y, z = c
        for j in range(i - 1, -1, -1):
            pc = _get_coord(data[j])
            if pc is None:
                continue
            px, py, pz = pc
            if pz != z:
                continue
            dx = x - px
            dy = y - py
            if dx == 0 and dy == -1:
                return 'north'
            if dx == 0 and dy == 1:
                return 'south'
            if dx == 1 and dy == 0:
                return 'east'
            if dx == -1 and dy == 0:
                return 'west'
            # Keep searching until we find an adjacent same-floor step.
        return None

    warnings: list[str] = []
    out: list[dict[str, Any]] = [dict(step) for step in data]

    for i, step in enumerate(out):
        wtype = str(step.get('type', ''))
        if wtype not in {'moveDown', 'moveUp'}:
            continue
        inferred = _infer_from_prev(i)
        coord = _get_coord(step)
        opts = step.get('options')
        direction: str | None
        if isinstance(opts, dict):
            direction = opts.get('direction')
        else:
            direction = None

        if inferred is None:
            warnings.append(
                f"step[{i}] type={wtype} coord={coord} direction={direction}: cannot infer direction (no adjacent same-floor prev step)"
            )
            continue

        if direction is None:
            warnings.append(f"step[{i}] type={wtype}: missing options.direction; inferred={inferred}")
            if fix:
                if not isinstance(opts, dict):
                    opts = {}
                    step['options'] = opts
                opts['direction'] = inferred
            continue

        if str(direction) != inferred:
            warnings.append(f"step[{i}] type={wtype}: direction={direction} but inferred={inferred}")
            if fix:
                if not isinstance(opts, dict):
                    opts = {}
                    step['options'] = opts
                opts['direction'] = inferred

    return warnings, out

class WaypointsVisualizer:
    def __init__(self, data: str | Sequence[Mapping[str, Any]]):
        """
        Initialize the visualizer with the JSON data (list of dictionaries) or a filename to load the data from.
        """
        if isinstance(data, str):
            # Load from file if a string (filename) is provided
            with open(data, 'r') as f:
                self.data = json.load(f)
        else:
            self.data = data
        self.x: list[int] = []
        self.y: list[int] = []
        self.z: list[int] = []
        self.types: list[str] = []  # To differentiate walk and singleMove
        self.directions: list[str | None] = []  # To store directions if present
        self._extract_coordinates()

    def _extract_coordinates(self) -> None:
        """
        Extract all coordinates from the data, including ignored ones, as they form part of the path.
        """
        for step in self.data:
            coord = step['coordinate']
            self.x.append(coord[0])
            self.y.append(coord[1])
            self.z.append(coord[2])
            self.types.append(step['type'])
            self.directions.append(step.get('options', {}).get('direction', None))

    def visualize_2d(self) -> None:
        """
        Visualize the path in 2D, with color representing the Z coordinate.
        """
        plt = _optional_import('matplotlib.pyplot')
        plt.figure(figsize=(10, 8))
        scatter = plt.scatter(self.x, self.y, c=self.z, cmap='viridis', s=50)
        plt.plot(self.x, self.y, 'k-', alpha=0.5)  # Connect points with a line
        plt.colorbar(scatter, label='Z Coordinate')
        plt.xlabel('X')
        plt.ylabel('Y')
        plt.title('2D Path Visualization')
        plt.grid(True)
        
        # Annotate points with type and direction if available
        for i in range(len(self.x)):
            label = self.types[i]
            if self.directions[i]:
                label += f' ({self.directions[i]})'
            plt.annotate(label, (self.x[i], self.y[i]), textcoords="offset points", xytext=(0,10), ha='center', fontsize=8)
        
        plt.show()

    def visualize_3d(self) -> None:
        """
        Visualize the path in 3D.
        """
        plt = _optional_import('matplotlib.pyplot')
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        scatter = ax.scatter(self.x, self.y, self.z, c=self.z, cmap='viridis', s=50)
        ax.plot(self.x, self.y, self.z, 'k-', alpha=0.5)  # Connect points with a line
        fig.colorbar(scatter, ax=ax, label='Z Coordinate (color redundant)')
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.set_title('3D Path Visualization')
        
        # Annotate points with type and direction if available
        for i in range(len(self.x)):
            label = self.types[i]
            if self.directions[i]:
                label += f' ({self.directions[i]})'
            ax.text(self.x[i], self.y[i], self.z[i], label, fontsize=8)
        
        plt.show()

    def animate_2d(self) -> None:
        """
        Animate the path in 2D, showing the progression over time.
        """
        if not self.x:
            print("No data to animate.")
            return

        plt = _optional_import('matplotlib.pyplot')
        animation = _optional_import('matplotlib.animation')
        FuncAnimation = animation.FuncAnimation

        fig, ax = plt.subplots(figsize=(10, 8))
        ax.set_xlim(min(self.x) - 10, max(self.x) + 10)
        ax.set_ylim(min(self.y) - 10, max(self.y) + 10)
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_title('Animated 2D Path')
        ax.grid(True)

        line, = ax.plot([], [], 'k-', alpha=0.5)
        scatter = ax.scatter([], [], c=[], cmap='viridis', s=50)
        
        # Dummy colorbar to be updated later
        cbar = plt.colorbar(scatter, ax=ax, label='Z Coordinate')

        def init() -> tuple[Any, Any]:
            line.set_data([], [])
            scatter.set_offsets(np.empty((0, 2)))
            scatter.set_array(np.array([]))
            return line, scatter

        def update(frame: int) -> tuple[Any, Any]:
            line.set_data(self.x[:frame + 1], self.y[:frame + 1])
            offsets = np.c_[self.x[:frame + 1], self.y[:frame + 1]]
            scatter.set_offsets(offsets)
            scatter.set_array(np.array(self.z[:frame + 1]))
            # Update colorbar if needed
            if frame == 0:
                cbar.update_normal(scatter)
            return line, scatter

        ani = FuncAnimation(fig, update, frames=len(self.x), init_func=init, blit=True, interval=200)
        
        plt.show()

    def animate_3d(self) -> None:
        """
        Animate the path in 3D, showing the progression over time.
        """
        if not self.x:
            print("No data to animate.")
            return

        plt = _optional_import('matplotlib.pyplot')
        animation = _optional_import('matplotlib.animation')
        FuncAnimation = animation.FuncAnimation

        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        ax.set_xlim(min(self.x) - 10, max(self.x) + 10)
        ax.set_ylim(min(self.y) - 10, max(self.y) + 10)
        ax.set_zlim(min(self.z) - 1, max(self.z) + 1)
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        ax.set_title('Animated 3D Path')

        line, = ax.plot([], [], [], 'k-', alpha=0.5)
        scatter = ax.scatter([], [], [], c=[], cmap='viridis', s=50)
        
        # Dummy colorbar to be updated later
        cbar = fig.colorbar(scatter, ax=ax, label='Z Coordinate')

        def init() -> tuple[Any, Any]:
            line.set_data([], [])
            line.set_3d_properties([])
            scatter._offsets3d = ([], [], [])
            scatter.set_array(np.array([]))
            return line, scatter

        def update(frame: int) -> tuple[Any, Any]:
            line.set_data(self.x[:frame + 1], self.y[:frame + 1])
            line.set_3d_properties(self.z[:frame + 1])
            scatter._offsets3d = (self.x[:frame + 1], self.y[:frame + 1], self.z[:frame + 1])
            scatter.set_array(np.array(self.z[:frame + 1]))
            # Update colorbar if needed
            if frame == 0:
                cbar.update_normal(scatter)
            return line, scatter

        ani = FuncAnimation(fig, update, frames=len(self.x), init_func=init, blit=True, interval=200)
        
        plt.show()

    def visualize_2d_plotly(self) -> None:
        """
        Interactive 2D visualization using Plotly.
        """
        if not self.x:
            print("No data to visualize.")
            return

        pd = _optional_import('pandas')
        px = _optional_import('plotly.express')
        go = _optional_import('plotly.graph_objects')

        df = pd.DataFrame({
            'x': self.x,
            'y': self.y,
            'z': self.z,
            'type': self.types,
            'direction': [d if d else '' for d in self.directions]
        })

        fig = px.scatter(df, x='x', y='y', color='z',
                         hover_data=['type', 'direction'],
                         title='Interactive 2D Path Visualization')

        fig.add_trace(go.Scatter(x=df['x'], y=df['y'], mode='lines', line=dict(color='black', width=2), opacity=0.5))

        fig.show()

    def visualize_2d_plotly_on_map(
        self,
        *,
        map_image: str,
        bounds: tuple[int, int, int, int],
        only_z: int | None = None,
        out_html: str | None = None,
        open_browser: bool = True,
        title: str | None = None,
    ) -> None:
        """Plot 2D waypoints on top of a map image.

        Notes:
        - This expects a *locally provided* map image.
        - bounds are world-coordinate extents of the image: (x_min, y_min, x_max, y_max).
        - If only_z is provided, data is filtered to that floor.
        """

        if not self.x:
            print('No data to visualize.')
            return

        pd = _optional_import('pandas')
        go = _optional_import('plotly.graph_objects')

        x_min, y_min, x_max, y_max = bounds
        df = pd.DataFrame(
            {
                'x': self.x,
                'y': self.y,
                'z': self.z,
                'type': self.types,
                'direction': [d if d else '' for d in self.directions],
            }
        )

        if only_z is not None:
            df = df[df['z'] == only_z]
            if df.empty:
                print(f'No points for z={only_z}.')
                return

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df['x'],
                y=df['y'],
                mode='markers+lines',
                line=dict(color='black', width=2),
                marker=dict(size=8, color=df['z'], colorscale='Viridis', showscale=True),
                customdata=np.stack([df['type'], df['direction'], df['z']], axis=-1),
                hovertemplate='x=%{x}<br>y=%{y}<br>z=%{customdata[2]}<br>%{customdata[0]} %{customdata[1]}<extra></extra>',
            )
        )

        fig.update_layout(
            title=title or 'Waypoints on Map',
            xaxis=dict(range=[x_min, x_max], title='X'),
            yaxis=dict(range=[y_min, y_max], title='Y', autorange='reversed', scaleanchor='x', scaleratio=1),
            margin=dict(l=20, r=20, t=60, b=20),
        )

        fig.add_layout_image(
            dict(
                source=_image_to_data_uri(map_image),
                xref='x',
                yref='y',
                x=x_min,
                y=y_min,
                sizex=(x_max - x_min),
                sizey=(y_max - y_min),
                xanchor='left',
                yanchor='top',
                sizing='stretch',
                opacity=1.0,
                layer='below',
            )
        )

        if out_html:
                        # Ctrl+click on a point opens TibiaMaps at that coordinate in a new tab.
                        # This is intentionally injected post-render so we don't depend on Plotly's internal div id.
                        ctrl_click_js = r"""
(function(){
    function fenrilBindCtrlClickOpen(gd) {
        if (!gd || gd.__fenril_ctrl_open_bound) return;
        gd.__fenril_ctrl_open_bound = true;

        gd.on('plotly_click', function(data) {
            try {
                var ev = data && data.event;
                if (!ev || !(ev.ctrlKey || ev.metaKey)) return;

                var pt = data && data.points && data.points[0];
                if (!pt) return;

                var x = Math.round(Number(pt.x));
                var y = Math.round(Number(pt.y));
                var z = null;
                if (pt.customdata && pt.customdata.length >= 3) z = Math.round(Number(pt.customdata[2]));
                if (!Number.isFinite(x) || !Number.isFinite(y)) return;
                if (!Number.isFinite(z)) z = 7;

                // TibiaMaps supports linking via hash: #x,y,z:zoom
                var url = 'https://tibiamaps.io/map#' + x + ',' + y + ',' + z + ':2';
                window.open(url, '_blank', 'noopener');
            } catch (e) {
                // Ignore
            }
        });
    }

    function fenrilBindAllPlots() {
        var plots = document.querySelectorAll('.js-plotly-plot');
        for (var i = 0; i < plots.length; i++) fenrilBindCtrlClickOpen(plots[i]);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fenrilBindAllPlots);
    } else {
        fenrilBindAllPlots();
    }
})();
""".strip()

                        out_path = Path(out_html)
                        html = fig.to_html(full_html=True, include_plotlyjs=True)
                        if '</body>' in html:
                                html = html.replace(
                                        '</body>',
                                        f'<script type="text/javascript">\n{ctrl_click_js}\n</script>\n</body>',
                                        1,
                                )
                        else:
                                html = html + f'\n<script type="text/javascript">\n{ctrl_click_js}\n</script>\n'

                        out_path.write_text(html, encoding='utf-8')
                        if open_browser:
                                webbrowser.open(out_path.resolve().as_uri())
        else:
            fig.show()

    def edit_points_matplotlib_on_tibiamaps(
        self,
        *,
        floor: int,
        cache_dir: str | Path = '.cache/tibiamaps',
        pad: int = 250,
        nudge_step: float = 1.0,
        only_selected_floor: bool = True,
        export_path: str | Path | None = None,
    ) -> list[dict[str, Any]]:
        """Interactive editor: drag points on top of TibiaMaps floor image.

        Controls:
        - Left click near a point: select
        - Drag with left mouse: move selected point
        - Arrow keys: nudge selected point (base = --edit-step, Shift = x10, Ctrl = x5)
        - `[` / `]` (or PageUp/PageDown): switch to previous/next floor
        - `d`: delete selected point
        - `a`: add new point at mouse position (insert after selected)
        - `u`: undo last edit
        - `s`: save to --export (if provided)
        - `q`: quit

        Returns a modified copy of the underlying waypoint list.
        """

        if not self.x:
            print('No data to edit.')
            return list(self.data)

        plt = _optional_import('matplotlib.pyplot')
        mpimg = _optional_import('matplotlib.image')

        cache_dir_path = Path(cache_dir)
        bounds_path = _download_if_missing(_tibiamaps_bounds_url(), cache_dir_path / 'bounds.json')
        with bounds_path.open('r', encoding='utf-8') as f:
            bounds_json = json.load(f)
        x_min, y_min, x_max, y_max = _tibiamaps_bounds_to_world(bounds_json)

        def _load_floor_image(f: int) -> Any:
            floor_path = _download_if_missing(
                _tibiamaps_floor_image_url(int(f)),
                cache_dir_path / f'floor-{int(f):02d}-map.png',
            )
            return mpimg.imread(str(floor_path))

        # Work on a deep-ish copy.
        data: list[dict[str, Any]] = [dict(step) for step in self.data]

        # Floors that exist in this pilotscript (based on current data, not only the original self.z).
        floors_with_points: list[int] = sorted(
            {
                int(coord[2])
                for step in data
                for coord in [step.get('coordinate')]
                if isinstance(coord, (list, tuple)) and len(coord) >= 3
            }
        )
        if not floors_with_points:
            print('No waypoint Z floors found.')
            return data

        current_floor: int = int(floor)
        if current_floor not in floors_with_points:
            current_floor = floors_with_points[0]

        def _rebuild_editables() -> tuple[list[int], list[float], list[float]]:
            editable_indices_local: list[int] = []
            xs_local: list[float] = []
            ys_local: list[float] = []
            for idx, step in enumerate(data):
                coord = step.get('coordinate')
                if not (isinstance(coord, (list, tuple)) and len(coord) >= 3):
                    continue
                x, y, z = int(coord[0]), int(coord[1]), int(coord[2])
                if only_selected_floor and z != int(current_floor):
                    continue
                editable_indices_local.append(idx)
                xs_local.append(float(x))
                ys_local.append(float(y))
            return editable_indices_local, xs_local, ys_local

        editable_indices, xs, ys = _rebuild_editables()

        if not editable_indices:
            # If the requested floor has no points, try a floor that does.
            for candidate in floors_with_points:
                current_floor = int(candidate)
                editable_indices, xs, ys = _rebuild_editables()
                if editable_indices:
                    break
        if not editable_indices:
            print('No editable points found in this pilotscript.')
            return data

        fig, ax = plt.subplots(figsize=(12, 9))
        ax.set_title(
            f"Drag waypoints on TibiaMaps floor {int(current_floor):02d} (z={current_floor}). "
            "Press 's' to print-save hint, 'q' to quit"
        )

        # Try to make the window visible/focused on Windows (TkAgg).
        try:  # pragma: no cover
            manager = plt.get_current_fig_manager()
            window = getattr(manager, 'window', None)
            if window is not None:
                try:
                    window.state('zoomed')
                except Exception:
                    pass
                try:
                    window.lift()
                    window.focus_force()
                except Exception:
                    pass
                try:
                    window.attributes('-topmost', True)
                    window.update()
                    window.attributes('-topmost', False)
                except Exception:
                    pass
        except Exception:
            pass

        # Draw background map. Y axis is inverted to match Tibia coordinate direction.
        bg_img = _load_floor_image(int(current_floor))
        bg = ax.imshow(bg_img, extent=(x_min, x_max, y_max, y_min), interpolation='nearest', zorder=0)

        # Hide axes/ticks (no border scales).
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

        # Plot path (in order) and points.
        path_line, = ax.plot(xs, ys, color='black', alpha=0.6, linewidth=2, zorder=2)
        scat = ax.scatter(xs, ys, s=42, c='red', alpha=0.9, zorder=3, marker='s')
        selected = ax.scatter([xs[0]], [ys[0]], s=160, facecolors='none', edgecolors='yellow', linewidths=2, zorder=4, marker='s')

        point_labels: list[Any] = []

        def _rebuild_point_labels() -> None:
            nonlocal point_labels
            for t in point_labels:
                try:
                    t.remove()
                except Exception:
                    pass
            point_labels = []
            for i, (px, py) in enumerate(zip(xs, ys)):
                point_labels.append(
                    ax.text(
                        px,
                        py,
                        str(i),
                        fontsize=8,
                        color='white',
                        ha='left',
                        va='bottom',
                        zorder=5,
                        bbox=dict(facecolor='black', alpha=0.55, edgecolor='none', pad=1.5),
                    )
                )

        def _infer_direction_for_step_index(step_index: int) -> str | None:
            coord = data[step_index].get('coordinate')
            if not (isinstance(coord, (list, tuple)) and len(coord) >= 3):
                return None
            x, y, z = int(coord[0]), int(coord[1]), int(coord[2])

            def _dir_from(prev: Any) -> str | None:
                if not (isinstance(prev, (list, tuple)) and len(prev) >= 3):
                    return None
                px, py, pz = int(prev[0]), int(prev[1]), int(prev[2])
                if pz != z:
                    return None
                dx = x - px
                dy = y - py
                if dx == 0 and dy == -1:
                    return 'north'
                if dx == 0 and dy == 1:
                    return 'south'
                if dx == 1 and dy == 0:
                    return 'east'
                if dx == -1 and dy == 0:
                    return 'west'
                return None

            # Prefer previous same-floor coordinate.
            for j in range(step_index - 1, -1, -1):
                prev = data[j].get('coordinate')
                d = _dir_from(prev)
                if d is not None:
                    return d
            # Fallback: try next same-floor coordinate.
            for j in range(step_index + 1, len(data)):
                nxt = data[j].get('coordinate')
                if not (isinstance(nxt, (list, tuple)) and len(nxt) >= 3):
                    continue
                nx, ny, nz = int(nxt[0]), int(nxt[1]), int(nxt[2])
                if nz != z:
                    continue
                dx = nx - x
                dy = ny - y
                # Direction to move from this tile towards the next.
                if dx == 0 and dy == -1:
                    return 'north'
                if dx == 0 and dy == 1:
                    return 'south'
                if dx == 1 and dy == 0:
                    return 'east'
                if dx == -1 and dy == 0:
                    return 'west'
                break
            return None

        def _set_waypoint_type(step_index: int, waypoint_type: str) -> None:
            # Keep coordinate as-is; just change action type + required options.
            data[step_index]['type'] = waypoint_type
            opts = data[step_index].get('options')
            if not isinstance(opts, dict):
                opts = {}
                data[step_index]['options'] = opts

            if waypoint_type in {'moveDown', 'moveUp', 'singleMove', 'rightClickDirection'}:
                if 'direction' not in opts:
                    inferred = _infer_direction_for_step_index(step_index)
                    opts['direction'] = inferred if inferred is not None else 'north'

        label = ax.text(
            0.01,
            0.99,
            '',
            transform=ax.transAxes,
            ha='left',
            va='top',
            fontsize=10,
            bbox=dict(facecolor='white', alpha=0.75, edgecolor='none'),
        )

        # Zoom to points (+pad).
        xmin_p, xmax_p = min(xs), max(xs)
        ymin_p, ymax_p = min(ys), max(ys)
        initial_xlim = (xmin_p - pad, xmax_p + pad)
        initial_ylim = (ymax_p + pad, ymin_p - pad)
        ax.set_xlim(*initial_xlim)
        ax.set_ylim(*initial_ylim)

        selected_i: int = 0
        dragging: bool = False
        last_mouse: tuple[float, float] = (xs[0], ys[0])
        history: list[str] = []

        def _set_floor(new_floor: int) -> None:
            nonlocal current_floor, editable_indices, xs, ys, selected_i, last_mouse, bg
            if int(new_floor) == int(current_floor):
                return
            if int(new_floor) not in floors_with_points:
                return
            current_floor = int(new_floor)
            # Swap background image
            try:
                bg.set_data(_load_floor_image(int(current_floor)))
            except Exception:
                # Fallback: recreate image artist
                try:
                    bg.remove()
                except Exception:
                    pass
                new_bg = ax.imshow(
                    _load_floor_image(int(current_floor)),
                    extent=(x_min, x_max, y_max, y_min),
                    interpolation='nearest',
                    zorder=0,
                )
                bg = new_bg

            editable_indices, xs, ys = _rebuild_editables()
            if not editable_indices:
                # Keep floor change even if no points; just don't crash.
                xs = [float('nan')]
                ys = [float('nan')]
            selected_i = 0
            last_mouse = (xs[0], ys[0])
            ax.set_title(
                f"Drag waypoints on TibiaMaps floor {int(current_floor):02d} (z={current_floor}). "
                "Press 's' to print-save hint, 'q' to quit"
            )
            _rebuild_point_labels()
            _refresh()

        def _push_history() -> None:
            # Store a JSON snapshot for a simple undo stack.
            history.append(json.dumps(data, ensure_ascii=False, separators=(',', ':')))
            # Cap history to avoid unbounded memory growth.
            if len(history) > 50:
                history[:] = history[-50:]

        def _undo() -> None:
            if not history:
                return
            snapshot = history.pop()
            restored = json.loads(snapshot)
            data.clear()
            data.extend(restored)

        def _save() -> None:
            if not export_path:
                print('No export path provided. Run with --export <file>.')
                return
            path = Path(export_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print(f'Saved: {path}')

        def _refresh() -> None:
            path_line.set_data(xs, ys)
            scat.set_offsets(np.c_[xs, ys])
            i = int(selected_i)
            selected.set_offsets(np.array([[xs[i], ys[i]]], dtype=float))
            if len(point_labels) != len(xs):
                _rebuild_point_labels()
            for j, t in enumerate(point_labels):
                t.set_position((xs[j], ys[j]))
            step_index = editable_indices[i]
            coord = data[step_index].get('coordinate')
            wtype = data[step_index].get('type')
            wopts = data[step_index].get('options')
            label.set_text(
                f"floor: z={current_floor} | selected: i={i} step_index={step_index} type={wtype} options={wopts}\n"
                f"coord={coord}\n"
                f"drag: move | arrows: nudge (step={nudge_step:g}) | [ ]: floor | 1..7: action | h/j/k/l: dir | a: add | d: delete | u: undo | s: save | q: quit"
            )
            fig.canvas.draw_idle()

        def _nearest_point_index(x: float, y: float) -> int | None:
            # Find nearest in data coordinates; use a tolerance relative to zoom.
            x0, x1 = ax.get_xlim()
            y0, y1 = ax.get_ylim()
            tol = max(abs(x1 - x0), abs(y1 - y0)) * 0.01
            best_i: int | None = None
            best_d2 = float('inf')
            for i, (px, py) in enumerate(zip(xs, ys)):
                d2 = (px - x) ** 2 + (py - y) ** 2
                if d2 < best_d2:
                    best_d2 = d2
                    best_i = i
            if best_i is None:
                return None
            return best_i if best_d2 <= tol * tol else None

        def on_press(event: Any) -> None:
            nonlocal selected_i, dragging, last_mouse
            if event.inaxes != ax:
                return
            if event.button != 1:
                return
            if event.xdata is None or event.ydata is None:
                return
            last_mouse = (float(event.xdata), float(event.ydata))
            nearest = _nearest_point_index(float(event.xdata), float(event.ydata))
            if nearest is None:
                return
            selected_i = int(nearest)
            dragging = True
            _refresh()

        def on_release(event: Any) -> None:
            nonlocal dragging
            if event.button != 1:
                return
            dragging = False

        def on_move(event: Any) -> None:
            nonlocal last_mouse
            if event.inaxes == ax and event.xdata is not None and event.ydata is not None:
                last_mouse = (float(event.xdata), float(event.ydata))
            if not dragging:
                return
            if event.inaxes != ax:
                return
            if event.xdata is None or event.ydata is None:
                return
            _push_history()
            i = int(selected_i)
            xs[i] = float(event.xdata)
            ys[i] = float(event.ydata)
            # Write back to data as integers.
            step_index = editable_indices[i]
            coord = data[step_index].get('coordinate')
            if isinstance(coord, (list, tuple)) and len(coord) >= 3:
                data[step_index]['coordinate'] = [int(round(xs[i])), int(round(ys[i])), int(coord[2])]
            _refresh()

        def on_key(event: Any) -> None:
            nonlocal selected_i, editable_indices, xs, ys
            key = str(getattr(event, 'key', '')).lower()
            if key == 'q':
                plt.close(fig)
                return
            if key in {'[', 'pageup', 'prior'}:
                idx = floors_with_points.index(int(current_floor))
                if idx > 0:
                    _set_floor(floors_with_points[idx - 1])
                return
            if key in {']', 'pagedown', 'next'}:
                idx = floors_with_points.index(int(current_floor))
                if idx < len(floors_with_points) - 1:
                    _set_floor(floors_with_points[idx + 1])
                return
            if key in {'+', '=', 'plus'}:
                _zoom_at(None, None, 1 / 1.2)
                return
            if key in {'-', '_', 'minus'}:
                _zoom_at(None, None, 1.2)
                return
            if key == '0':
                ax.set_xlim(*initial_xlim)
                ax.set_ylim(*initial_ylim)
                fig.canvas.draw_idle()
                return
            if key == 'm':
                ax.set_xlim(x_min, x_max)
                ax.set_ylim(y_max, y_min)
                fig.canvas.draw_idle()
                return
            if key == 's':
                _save()
                return
            if key == 'u':
                _undo()
                editable_indices, xs, ys = _rebuild_editables()
                selected_i = min(int(selected_i), max(0, len(xs) - 1))
                _refresh()
                return

            # Action/type editing for the selected step.
            if key in {'1', '2', '3', '4', '5', '6', '7'}:
                if not editable_indices:
                    return
                i = int(selected_i)
                step_index = editable_indices[i]
                mapping = {
                    '1': 'walk',
                    '2': 'moveDown',
                    '3': 'moveUp',
                    '4': 'useLadder',
                    '5': 'useRope',
                    '6': 'useShovel',
                    '7': 'rightClickUse',
                }
                _push_history()
                _set_waypoint_type(step_index, mapping[key])
                _refresh()
                return

            # Direction editing (vim keys): h=west, j=south, k=north, l=east.
            if key in {'h', 'j', 'k', 'l'}:
                if not editable_indices:
                    return
                i = int(selected_i)
                step_index = editable_indices[i]
                direction_map = {'h': 'west', 'j': 'south', 'k': 'north', 'l': 'east'}
                direction = direction_map[key]
                _push_history()
                opts = data[step_index].get('options')
                if not isinstance(opts, dict):
                    opts = {}
                    data[step_index]['options'] = opts
                opts['direction'] = direction
                # If current type needs direction but is missing, keep it as-is; user can set type with 2/3.
                _refresh()
                return

            # Nudge with arrows.
            if key in {'left', 'right', 'up', 'down'}:
                # base step comes from --edit-step; modifiers apply multipliers.
                step_size = float(nudge_step)
                if getattr(event, 'shift', False):
                    step_size *= 10.0
                if getattr(event, 'control', False) or getattr(event, 'ctrl', False):
                    step_size *= 5.0
                dx = dy = 0.0
                if key == 'left':
                    dx = -step_size
                elif key == 'right':
                    dx = step_size
                elif key == 'up':
                    dy = -step_size
                elif key == 'down':
                    dy = step_size
                _push_history()
                i = int(selected_i)
                xs[i] += dx
                ys[i] += dy
                step_index = editable_indices[i]
                coord = data[step_index].get('coordinate')
                if isinstance(coord, (list, tuple)) and len(coord) >= 3:
                    data[step_index]['coordinate'] = [int(round(xs[i])), int(round(ys[i])), int(coord[2])]
                _refresh()
                return

            # Delete selected point.
            if key == 'd':
                if not editable_indices:
                    return
                _push_history()
                i = int(selected_i)
                step_index = editable_indices[i]
                data.pop(step_index)
                editable_indices, xs, ys = _rebuild_editables()
                if not editable_indices:
                    plt.close(fig)
                    return
                selected_i = min(i, len(xs) - 1)
                _refresh()
                return

            # Add a point at last mouse position (insert after selected).
            if key == 'a':
                if not editable_indices:
                    return
                mx, my = last_mouse
                i = int(selected_i)
                step_index = editable_indices[i]
                coord = data[step_index].get('coordinate')
                if not (isinstance(coord, (list, tuple)) and len(coord) >= 3):
                    return
                _push_history()
                new_step = {
                    'type': data[step_index].get('type', 'walk'),
                    'coordinate': [int(round(mx)), int(round(my)), int(coord[2])],
                    'options': dict(data[step_index].get('options', {})),
                }
                data.insert(step_index + 1, new_step)
                editable_indices, xs, ys = _rebuild_editables()
                # Select the inserted point (which should be next among editables).
                selected_i = min(i + 1, len(xs) - 1)
                _refresh()
                return

        def _zoom_at(x: float | None, y: float | None, scale: float) -> None:
            # scale < 1 => zoom in, scale > 1 => zoom out
            x0, x1 = ax.get_xlim()
            y0, y1 = ax.get_ylim()
            if x is None or y is None:
                x = (x0 + x1) / 2
                y = (y0 + y1) / 2
            new_x0 = x - (x - x0) * scale
            new_x1 = x + (x1 - x) * scale
            new_y0 = y - (y - y0) * scale
            new_y1 = y + (y1 - y) * scale
            ax.set_xlim(new_x0, new_x1)
            ax.set_ylim(new_y0, new_y1)
            fig.canvas.draw_idle()

        def on_scroll(event: Any) -> None:
            if event.inaxes != ax:
                return
            # Matplotlib uses 'up'/'down' for wheel on some backends.
            direction = str(getattr(event, 'button', '')).lower()
            if direction == 'up':
                scale = 1 / 1.2
            elif direction == 'down':
                scale = 1.2
            else:
                # Fallback: use step if present
                step = float(getattr(event, 'step', 0.0) or 0.0)
                scale = 1 / 1.2 if step > 0 else 1.2
            _zoom_at(getattr(event, 'xdata', None), getattr(event, 'ydata', None), scale)

        fig.canvas.mpl_connect('button_press_event', on_press)
        fig.canvas.mpl_connect('button_release_event', on_release)
        fig.canvas.mpl_connect('motion_notify_event', on_move)
        fig.canvas.mpl_connect('key_press_event', on_key)
        fig.canvas.mpl_connect('scroll_event', on_scroll)

        _rebuild_point_labels()
        _refresh()
        plt.show()
        return data

    def visualize_3d_plotly(self) -> None:
        """
        Interactive 3D visualization using Plotly.
        """
        if not self.x:
            print("No data to visualize.")
            return

        pd = _optional_import('pandas')
        px = _optional_import('plotly.express')
        go = _optional_import('plotly.graph_objects')

        df = pd.DataFrame({
            'x': self.x,
            'y': self.y,
            'z': self.z,
            'type': self.types,
            'direction': [d if d else '' for d in self.directions]
        })

        fig = px.scatter_3d(df, x='x', y='y', z='z', color='z',
                            hover_data=['type', 'direction'],
                            title='Interactive 3D Path Visualization')

        fig.add_trace(go.Scatter3d(x=df['x'], y=df['y'], z=df['z'], mode='lines', line=dict(color='black', width=2), opacity=0.5))

        fig.show()

    def animate_2d_plotly(self) -> None:
        """
        Animated 2D visualization using Plotly, showing progression over steps.
        """
        if not self.x:
            print("No data to animate.")
            return

        go = _optional_import('plotly.graph_objects')

        # Create cumulative data for each frame
        frames = []
        for i in range(1, len(self.x) + 1):
            frame_data = {
                'x': self.x[:i],
                'y': self.y[:i],
                'z': self.z[:i],
                'type': self.types[:i],
                'direction': [d if d else '' for d in self.directions[:i]]
            }
            frames.append(go.Frame(data=[
                go.Scatter(x=frame_data['x'], y=frame_data['y'], mode='markers', marker=dict(color=frame_data['z'], colorscale='viridis'), name='Points'),
                go.Scatter(x=frame_data['x'], y=frame_data['y'], mode='lines', line=dict(color='black', width=2), opacity=0.5, name='Path')
            ], name=str(i)))

        # Initial figure
        fig = go.Figure(
            data=[
                go.Scatter(x=[self.x[0]], y=[self.y[0]], mode='markers', marker=dict(color=[self.z[0]], colorscale='viridis')),
                go.Scatter(x=[self.x[0]], y=[self.y[0]], mode='lines', line=dict(color='black', width=2), opacity=0.5)
            ],
            layout=go.Layout(
                title='Animated 2D Path Visualization',
                xaxis=dict(range=[min(self.x) - 10, max(self.x) + 10]),
                yaxis=dict(range=[min(self.y) - 10, max(self.y) + 10]),
                updatemenus=[dict(type='buttons', showactive=False, buttons=[dict(label='Play', method='animate', args=[None, dict(frame=dict(duration=200, redraw=True), fromcurrent=True)])])]
            ),
            frames=frames
        )

        fig.show()

    def animate_3d_plotly(self) -> None:
        """
        Animated 3D visualization using Plotly, showing progression over steps.
        """
        if not self.x:
            print("No data to animate.")
            return

        go = _optional_import('plotly.graph_objects')

        # Create cumulative data for each frame
        frames = []
        for i in range(1, len(self.x) + 1):
            frame_data = {
                'x': self.x[:i],
                'y': self.y[:i],
                'z': self.z[:i],
                'color': self.z[:i],
                'type': self.types[:i],
                'direction': [d if d else '' for d in self.directions[:i]]
            }
            frames.append(go.Frame(data=[
                go.Scatter3d(x=frame_data['x'], y=frame_data['y'], z=frame_data['z'], mode='markers', marker=dict(color=frame_data['color'], colorscale='viridis')),
                go.Scatter3d(x=frame_data['x'], y=frame_data['y'], z=frame_data['z'], mode='lines', line=dict(color='black', width=2), opacity=0.5)
            ], name=str(i)))

        # Initial figure
        fig = go.Figure(
            data=[
                go.Scatter3d(x=[self.x[0]], y=[self.y[0]], z=[self.z[0]], mode='markers', marker=dict(color=[self.z[0]], colorscale='viridis')),
                go.Scatter3d(x=[self.x[0]], y=[self.y[0]], z=[self.z[0]], mode='lines', line=dict(color='black', width=2), opacity=0.5)
            ],
            layout=go.Layout(
                title='Animated 3D Path Visualization',
                scene=dict(
                    xaxis=dict(range=[min(self.x) - 10, max(self.x) + 10]),
                    yaxis=dict(range=[min(self.y) - 10, max(self.y) + 10]),
                    zaxis=dict(range=[min(self.z) - 1, max(self.z) + 1])
                ),
                updatemenus=[dict(type='buttons', showactive=False, buttons=[dict(label='Play', method='animate', args=[None, dict(frame=dict(duration=200, redraw=True), fromcurrent=True)])])]
            ),
            frames=frames
        )

        fig.show()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Visualize Fenril waypoints JSON (.pilotscript).')
    parser.add_argument('file', nargs='?', default='waypoints.pilotscript', help='Path to .pilotscript file (default: waypoints.pilotscript)')
    parser.add_argument(
        '--method',
        default='visualize_2d_plotly',
        help='WaypointsVisualizer method to run (default: visualize_2d_plotly)',
    )
    parser.add_argument('--map-image', help='Overlay on a local map image (single floor)')
    parser.add_argument('--map-z', type=int, help='When using --map-image, filter to this Z floor')
    parser.add_argument(
        '--map-bounds',
        nargs=4,
        type=int,
        metavar=('X_MIN', 'Y_MIN', 'X_MAX', 'Y_MAX'),
        help='World bounds covered by the map image',
    )
    parser.add_argument('--map-dir', help='Directory containing per-floor images (e.g. map_z7.png, map_z8.png, ...)')
    parser.add_argument('--map-pattern', default='map_z{z}.png', help='Filename pattern inside --map-dir (default: map_z{z}.png)')
    parser.add_argument('--out', help='Output HTML path (single map) or output directory (per-floor)')
    parser.add_argument('--no-open', action='store_true', help="Don't auto-open the generated HTML")
    parser.add_argument('--tibiamaps-floor', type=int, help='Download tibia-map-data floor-XX-map.png locally and overlay (requires Plotly)')
    parser.add_argument(
        '--tibiamaps-floors',
        help="Generate overlays for multiple floors. Use 'auto' to use all z values from the pilotscript, or a comma list like '7,8,9'.",
    )
    parser.add_argument('--tibiamaps-cache-dir', default='.cache/tibiamaps', help='Cache directory for downloaded TibiaMaps assets')

    # Waypoint modifications (optional)
    parser.add_argument('--shift', nargs=2, type=int, metavar=('DX', 'DY'), help='Shift all waypoint X/Y by DX,DY')
    parser.add_argument('--shift-z', type=int, help='Apply --shift/--snap only to this Z floor')
    parser.add_argument('--snap', type=int, help='Snap waypoint X/Y to nearest multiple of N (grid)')
    parser.add_argument('--dedupe', action='store_true', help='Drop consecutive duplicate steps (only if step dicts are identical)')
    parser.add_argument('--export', help='Write modified waypoints JSON to this file path')
    parser.add_argument(
        '--validate-transitions',
        action='store_true',
        help='Print warnings for suspicious Z-floor transitions between consecutive steps',
    )
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Run --validate-transitions and exit (no visualization)',
    )
    parser.add_argument(
        '--audit-directions',
        action='store_true',
        help='Audit moveDown/moveUp options.direction (infers from previous adjacent step)',
    )
    parser.add_argument(
        '--fix-directions',
        action='store_true',
        help='With --audit-directions: update moveDown/moveUp options.direction when inference is available',
    )
    parser.add_argument('--edit-tibiamaps-floor', type=int, help='Interactive edit: drag points on TibiaMaps floor (Matplotlib GUI)')
    parser.add_argument('--edit-pad', type=int, default=250, help='Padding (world coords) around waypoints when editing')
    parser.add_argument('--edit-step', type=float, default=1.0, help='Arrow-key nudge base step (default: 1). Shift=×10, Ctrl=×5')

    args = parser.parse_args()

    # Load and optionally modify waypoints before visualization.
    base_visualizer = WaypointsVisualizer(args.file)

    # Interactive edit mode (Matplotlib): must run before other transforms.
    if args.edit_tibiamaps_floor is not None:
        if args.validate_only:
            raise SystemExit('--validate-only cannot be used with --edit-tibiamaps-floor')
        edited = base_visualizer.edit_points_matplotlib_on_tibiamaps(
            floor=int(args.edit_tibiamaps_floor),
            cache_dir=args.tibiamaps_cache_dir,
            pad=int(args.edit_pad),
            nudge_step=float(args.edit_step),
            only_selected_floor=True,
        )
        if not args.export:
            raise SystemExit('Use --export <file> to save edited waypoints.')
        export_path = Path(args.export)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        if args.validate_transitions:
            warnings = _validate_floor_transitions(edited)
            if warnings:
                print('Floor transition warnings:')
                for w in warnings:
                    print(f' - {w}')
            else:
                print('No suspicious floor transitions found.')
        export_path.write_text(json.dumps(edited, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        raise SystemExit(0)

    modified_data = base_visualizer.data
    if args.shift or args.snap or args.dedupe:
        shift = (int(args.shift[0]), int(args.shift[1])) if args.shift else None
        modified_data = _apply_point_modifications(
            base_visualizer.data,
            shift=shift,
            snap=args.snap,
            only_z=args.shift_z,
            dedupe=bool(args.dedupe),
        )

    if args.validate_transitions:
        warnings = _validate_floor_transitions(modified_data)
        if warnings:
            print('Floor transition warnings:')
            for w in warnings:
                print(f' - {w}')
        else:
            print('No suspicious floor transitions found.')

    if args.audit_directions or args.fix_directions:
        audit_warnings, audited = _audit_move_directions(modified_data, fix=bool(args.fix_directions))
        if audit_warnings:
            print('Direction audit:')
            for w in audit_warnings:
                print(f' - {w}')
        else:
            print('Direction audit: no issues found.')
        if args.fix_directions:
            modified_data = audited

    if args.validate_only:
        raise SystemExit(0)
    if args.export:
        export_path = Path(args.export)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_text(json.dumps(modified_data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    visualizer = WaypointsVisualizer(modified_data)

    # TibiaMaps (tibia-map-data) overlay mode (local cached download) - multiple floors
    if args.tibiamaps_floors:
        floors: list[int]
        if args.tibiamaps_floors.strip().lower() == 'auto':
            floors = sorted(set(int(z) for z in visualizer.z))
        else:
            floors = sorted(set(_parse_int_list(args.tibiamaps_floors)))

        cache_dir = Path(args.tibiamaps_cache_dir)
        bounds_path = _download_if_missing(_tibiamaps_bounds_url(), cache_dir / 'bounds.json')
        with bounds_path.open('r', encoding='utf-8') as f:
            bounds_json = json.load(f)
        world_bounds = _tibiamaps_bounds_to_world(bounds_json)

        out_dir = Path(args.out) if args.out else Path.cwd()
        out_dir.mkdir(parents=True, exist_ok=True)

        opened = False
        for floor in floors:
            floor_url = _tibiamaps_floor_image_url(floor)
            floor_path = _download_if_missing(floor_url, cache_dir / f'floor-{floor:02d}-map.png')
            out_html = str(out_dir / f'waypoints_z{floor}_tibiamaps.html')
            visualizer.visualize_2d_plotly_on_map(
                map_image=str(floor_path),
                bounds=world_bounds,
                only_z=floor,
                out_html=out_html,
                open_browser=(not args.no_open and not opened),
                title=f'Waypoints on TibiaMaps floor {floor:02d} (z={floor})',
            )
            opened = True

        raise SystemExit(0)

    # TibiaMaps (tibia-map-data) overlay mode (local cached download)
    if args.tibiamaps_floor is not None:
        floor = int(args.tibiamaps_floor)
        cache_dir = Path(args.tibiamaps_cache_dir)
        bounds_path = _download_if_missing(_tibiamaps_bounds_url(), cache_dir / 'bounds.json')
        with bounds_path.open('r', encoding='utf-8') as f:
            bounds_json = json.load(f)
        world_bounds = _tibiamaps_bounds_to_world(bounds_json)

        floor_url = _tibiamaps_floor_image_url(floor)
        floor_path = _download_if_missing(floor_url, cache_dir / f'floor-{floor:02d}-map.png')

        out_html = args.out
        if not out_html:
            out_html = f'waypoints_z{floor}_tibiamaps.html'

        visualizer.visualize_2d_plotly_on_map(
            map_image=str(floor_path),
            bounds=world_bounds,
            only_z=floor,
            out_html=out_html,
            open_browser=not args.no_open,
            title=f'Waypoints on TibiaMaps floor {floor:02d} (z={floor})',
        )
        raise SystemExit(0)

    # Map overlay mode (single image)
    if args.map_image:
        if not args.map_bounds:
            raise SystemExit('--map-bounds is required when using --map-image')
        bounds = _as_int_bounds(args.map_bounds)
        out_html = args.out
        visualizer.visualize_2d_plotly_on_map(
            map_image=args.map_image,
            bounds=bounds,
            only_z=args.map_z,
            out_html=out_html,
            open_browser=not args.no_open,
            title=f'Waypoints on Map (z={args.map_z})' if args.map_z is not None else 'Waypoints on Map',
        )
        raise SystemExit(0)

    # Map overlay mode (per-floor images)
    if args.map_dir:
        if not args.map_bounds:
            raise SystemExit('--map-bounds is required when using --map-dir')
        bounds = _as_int_bounds(args.map_bounds)
        out_dir = Path(args.out) if args.out else Path.cwd()
        out_dir.mkdir(parents=True, exist_ok=True)

        for z in sorted(set(visualizer.z)):
            image_path = Path(args.map_dir) / args.map_pattern.format(z=z)
            if not image_path.exists():
                print(f'Skipping z={z}: missing map image {image_path}')
                continue
            out_html = str(out_dir / f'waypoints_z{z}.html')
            visualizer.visualize_2d_plotly_on_map(
                map_image=str(image_path),
                bounds=bounds,
                only_z=z,
                out_html=out_html,
                open_browser=(not args.no_open and z == sorted(set(visualizer.z))[0]),
                title=f'Waypoints on Map (z={z})',
            )
        raise SystemExit(0)

    method = getattr(visualizer, args.method, None)
    if method is None or not callable(method):
        raise SystemExit(f"Unknown/invalid method: {args.method}")
    method()