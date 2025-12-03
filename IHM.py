import socket
import datetime
from math import sqrt
from dash import Dash, dcc, html, Input, Output, State, callback_context
import plotly.graph_objs as go

# ==========================
# CONFIGURAÇÕES GERAIS
# ==========================
CLP_HOST = "localhost"
CLP_PORT = 65432
HIST_FILE = "historiador.txt"
STEP_XY = 0.5
STEP_Z = 0.3
MISSION_TOL = 0.25

SQUARES = {
    "Q1": {"x": -2.0, "y": -2.0, "z": 1.2},
    "Q2": {"x": 2.0, "y": -2.0, "z": 1.2},
    "Q3": {"x": 2.0, "y": 2.0, "z": 1.2},
    "Q4": {"x": -2.0, "y": 2.0, "z": 1.2},
}

# ==========================
# TCP CLIENT
# ==========================
def send_target_and_get_pos(target):
    msg = f"{target['x']:.3f},{target['y']:.3f},{target['z']:.3f}"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            s.connect((CLP_HOST, CLP_PORT))
            s.sendall(msg.encode("utf-8"))
            data = s.recv(1024)
        pos_str = data.decode("utf-8").strip()
        x_d, y_d, z_d = map(float, pos_str.split(","))
    except Exception as e:
        raise RuntimeError(f"Erro TCP: {e}")
    ts = datetime.datetime.now().isoformat()
    with open(HIST_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] Target <{msg}> → CLP <{pos_str}>\n")
    return x_d, y_d, z_d

# ==========================
# DASH APP
# ==========================
app = Dash(__name__)
app.title = "Supervisório Drone SDA"

store_target = dcc.Store(id="store-target", data={"x": 0.0, "y": 0.0, "z": 1.2})
store_drone = dcc.Store(id="store-drone", data={"x": 0.0, "y": 0.0, "z": 0.0})
store_path = dcc.Store(id="store-path", data={"x": [], "y": [], "z": []})
store_mission = dcc.Store(id="store-mission", data={"mode": "idle", "index": 0})
interval = dcc.Interval(id="interval-update", interval=500, n_intervals=0)

STYLE_BTN = {
    "width": "55px",
    "height": "50px",
    "font-size": "18px",
    "font-weight": "bold",
    "background-color": "#3498db",
    "color": "white",
    "border": "none",
    "border-radius": "8px",
    "cursor": "pointer",
    "transition": "all 0.15s ease-in-out",
    "box-shadow": "0px 3px 6px rgba(0,0,0,0.2)",
}

HOVER_SCRIPT = """
const style = document.createElement('style');
style.innerHTML = `
button:hover {
  filter: brightness(1.2);
  transform: scale(1.05);
}
button:active {
  filter: brightness(0.9);
  transform: scale(0.95);
}
`;
document.head.appendChild(style);
"""

# ==========================
# LAYOUT
# ==========================
app.layout = html.Div(
    style={
        "margin": "0",
        "padding": "0",
        "height": "90vh",
        "width": "100vw",
        "overflow": "hidden",
        "background-color": "#ecf0f1",
        "display": "flex",
        "flex-direction": "column",
        "font-family": "Segoe UI",
    },
    children=[
        html.Script(children=HOVER_SCRIPT),

        html.H2("Supervisório Drone SDA", style={
            "text-align": "center",
            "margin": "5px 0",
            "color": "#2c3e50",
        }),

        html.Div(
            style={
                "flex": "1",
                "display": "flex",
                "padding": "5px 10px 10px 10px",
                "gap": "10px",
                "height": "100%",
            },
            children=[
                # ========== PAINEL ESQUERDO ==========
                html.Div(
                    style={
                        "flex": "2",
                        "background": "white",
                        "border-radius": "10px",
                        "padding": "8px",
                        "display": "flex",
                        "flex-direction": "column",
                    },
                    children=[
                        dcc.Graph(
                            id="map-graph",
                            style={"flex": "1"},
                            config={"displayModeBar": True, "scrollZoom": True},
                        ),
                        html.Div(id="info-pos", style={
                            "text-align": "center",
                            "margin-top": "5px",
                            "font-size": "14px",
                            "color": "#2c3e50",
                            "background": "#f4f6f7",
                            "border-radius": "8px",
                            "padding": "5px",
                        }),
                    ],
                ),

                # ========== PAINEL DIREITO ==========
                html.Div(
                    style={
                        "flex": "1",
                        "background": "white",
                        "border-radius": "10px",
                        "padding": "10px",
                        "display": "flex",
                        "flex-direction": "column",
                        "justify-content": "space-between",
                    },
                    children=[
                        html.Div([
                            html.H4("🎮 Joystick / Target", style={
                                "text-align": "center", "color": "#34495e",
                            }),

                            html.Div(
                                style={"display": "flex", "justify-content": "center", "align-items": "center", "gap": "10px"},
                                children=[
                                    html.Button("←", id="btn-left", n_clicks=0, style=STYLE_BTN),
                                    html.Div(
                                        children=[
                                            html.Button("↑", id="btn-up", n_clicks=0, style=STYLE_BTN),
                                            html.Button("↓", id="btn-down", n_clicks=0, style=STYLE_BTN),
                                        ],
                                        style={"display": "flex", "flex-direction": "column", "gap": "6px"},
                                    ),
                                    html.Button("→", id="btn-right", n_clicks=0, style=STYLE_BTN),
                                    html.Div(
                                        children=[
                                            html.Button("Z+", id="btn-zup", n_clicks=0, style={**STYLE_BTN, "background-color": "#2ecc71"}),
                                            html.Button("Z-", id="btn-zdown", n_clicks=0, style={**STYLE_BTN, "background-color": "#e74c3c"}),
                                        ],
                                        style={"display": "flex", "flex-direction": "column", "gap": "6px"},
                                    ),
                                ],
                            ),

                            html.Div(
                                style={"display": "flex", "justify-content": "space-between", "margin-top": "10px", "gap": "5px"},
                                children=[
                                    dcc.Input(id="input-x", type="number", value=0.0, step=0.1,
                                              placeholder="X", style={"flex": "1", "border-radius": "6px", "padding": "5px"}),
                                    dcc.Input(id="input-y", type="number", value=0.0, step=0.1,
                                              placeholder="Y", style={"flex": "1", "border-radius": "6px", "padding": "5px"}),
                                    dcc.Input(id="input-z", type="number", value=1.2, step=0.1,
                                              placeholder="Z", style={"flex": "1", "border-radius": "6px", "padding": "5px"}),
                                    html.Button("📤", id="btn-send-target", n_clicks=0,
                                                style={**STYLE_BTN, "width": "55px", "background-color": "#27ae60"}),
                                ],
                            ),
                        ]),

                        html.Hr(),

                        html.Div([
                            html.H4("🗺️ Missões", style={"text-align": "center", "color": "#34495e"}),
                            html.Button("Percorrer todos os quadrados", id="btn-scan", n_clicks=0,
                                        style={**STYLE_BTN, "width": "100%", "background-color": "#9b59b6", "height": "40px"}),
                            dcc.Dropdown(
                                id="dropdown-square",
                                options=[{"label": f"{k} ({v['x']},{v['y']})", "value": k} for k, v in SQUARES.items()],
                                placeholder="Escolha um quadrado",
                                style={"width": "100%", "margin-top": "5px", "border-radius": "6px"},
                            ),
                            html.Button("Ir para quadrado", id="btn-goto-square", n_clicks=0,
                                        style={**STYLE_BTN, "width": "100%", "background-color": "#8e44ad", "height": "40px", "margin-top": "5px"}),
                        ]),
                    ],
                ),
            ],
        ),
        store_target, store_drone, store_path, store_mission, interval,
    ],
)

# ==========================
# CALLBACKS
# ==========================
@app.callback(
    Output("store-target", "data", allow_duplicate=True),
    [Input("btn-up", "n_clicks"), Input("btn-down", "n_clicks"),
     Input("btn-left", "n_clicks"), Input("btn-right", "n_clicks"),
     Input("btn-zup", "n_clicks"), Input("btn-zdown", "n_clicks"),
     Input("btn-send-target", "n_clicks")],
    [State("input-x", "value"), State("input-y", "value"), State("input-z", "value"),
     State("store-target", "data")],
    prevent_initial_call=True,
)
def joystick_and_input(n_up, n_down, n_left, n_right, n_zup, n_zdown, n_send, x, y, z, target):
    ctx = callback_context
    if not ctx.triggered:
        return target
    bid = ctx.triggered[0]["prop_id"].split(".")[0]
    t = target.copy()
    if bid == "btn-up": t["y"] += STEP_XY
    elif bid == "btn-down": t["y"] -= STEP_XY
    elif bid == "btn-left": t["x"] -= STEP_XY
    elif bid == "btn-right": t["x"] += STEP_XY
    elif bid == "btn-zup": t["z"] += STEP_Z
    elif bid == "btn-zdown": t["z"] = max(0.2, t["z"] - STEP_Z)
    elif bid == "btn-send-target":
        if x is not None: t["x"] = x
        if y is not None: t["y"] = y
        if z is not None: t["z"] = z
    return t

@app.callback(
    Output("store-target", "data", allow_duplicate=True),
    Input("btn-goto-square", "n_clicks"), State("dropdown-square", "value"), State("store-target", "data"), prevent_initial_call=True,
)
def goto_square(n_clicks, square_id, target):
    if not n_clicks or not square_id or square_id not in SQUARES:
        return target
    sq = SQUARES[square_id]
    return {"x": sq["x"], "y": sq["y"], "z": sq["z"]}

@app.callback(
    [Output("store-mission", "data"), Output("store-target", "data")],
    Input("btn-scan", "n_clicks"), State("store-mission", "data"), State("store-target", "data"), prevent_initial_call=True,
)
def start_scan_mission(n_clicks, mission, target):
    if not n_clicks: return mission, target
    first_sq = SQUARES["Q1"]
    return {"mode": "scan", "index": 0}, {"x": first_sq["x"], "y": first_sq["y"], "z": first_sq["z"]}

@app.callback(
    [Output("store-drone", "data"),
     Output("store-path", "data"),
     Output("store-mission", "data", allow_duplicate=True),
     Output("map-graph", "figure"),
     Output("info-pos", "children")],
    Input("interval-update", "n_intervals"),
    State("store-target", "data"), State("store-drone", "data"),
    State("store-path", "data"), State("store-mission", "data"),
    allow_duplicate=True, prevent_initial_call="initial_duplicate",
)
def periodic_update(n_intervals, target, drone, path, mission):
    new_drone = drone.copy()
    status = "OK"
    try:
        x_d, y_d, z_d = send_target_and_get_pos(target)
        new_drone = {"x": x_d, "y": y_d, "z": z_d}
    except Exception as e:
        status = f"Erro TCP/CLP: {e}"
    new_mission = mission.copy(); new_target = target.copy()
    if mission.get("mode") == "scan":
        keys = list(SQUARES.keys())
        idx = int(mission.get("index", 0))
        if 0 <= idx < len(keys):
            sq = SQUARES[keys[idx]]
            dx = new_drone["x"] - sq["x"]; dy = new_drone["y"] - sq["y"]; dz = new_drone["z"] - sq["z"]
            if sqrt(dx*dx + dy*dy + dz*dz) < MISSION_TOL:
                idx += 1
                if idx < len(keys):
                    new_target = SQUARES[keys[idx]]
                    new_mission["index"] = idx
                else:
                    new_mission = {"mode": "idle", "index": 0}
    xs, ys, zs = path.get("x", []), path.get("y", []), path.get("z", [])
    xs.append(new_drone["x"]); ys.append(new_drone["y"]); zs.append(new_drone["z"])
    if len(xs) > 500: xs, ys, zs = xs[-500:], ys[-500:], zs[-500:]
    new_path = {"x": xs, "y": ys, "z": zs}
    fig = go.Figure()
    fig.update_layout(
        xaxis_title="X (m)", yaxis_title="Y (m)",
        xaxis=dict(scaleanchor="y", scaleratio=1, range=[-3, 3]),
        yaxis=dict(range=[-3, 3]), plot_bgcolor="#f9f9f9", paper_bgcolor="#ffffff"
    )
    if xs:
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name="Trajetória", line=dict(color="#2980b9", width=2)))
        fig.add_trace(go.Scatter(x=[new_drone["x"]], y=[new_drone["y"]], mode="markers", name="Drone", marker=dict(size=12, color="#e67e22")))
        fig.add_trace(go.Scatter(x=[target["x"]], y=[target["y"]], mode="markers", name="Target", marker=dict(symbol="x", size=12, color="#c0392b")))
        fig.add_trace(go.Scatter(x=[v["x"] for v in SQUARES.values()], y=[v["y"] for v in SQUARES.values()],
                                 mode="markers+text", text=list(SQUARES.keys()), textposition="top center",
                                 marker=dict(size=10, color="#27ae60")))
    info = f"🚁 Drone ({new_drone['x']:.2f},{new_drone['y']:.2f},{new_drone['z']:.2f}) | 🎯 Target ({target['x']:.2f},{target['y']:.2f},{target['z']:.2f}) | Missão: {new_mission.get('mode')} idx={new_mission.get('index')} | {status}"
    return new_drone, new_path, new_mission, fig, info

# ==========================
# EXECUÇÃO
# ==========================
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
