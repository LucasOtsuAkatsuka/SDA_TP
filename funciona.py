import socket
import datetime
from math import sqrt
from dash import Dash, dcc, html, Input, Output, State, callback_context
import plotly.graph_objs as go

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

def send_target_and_get_pos(target):
    msg = f"{target['x']:.3f},{target['y']:.3f},{target['z']:.3f}"
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        s.connect((CLP_HOST, CLP_PORT))
        s.sendall(msg.encode("utf-8"))
        data = s.recv(1024)
    pos_str = data.decode("utf-8").strip()
    try:
        x_d, y_d, z_d = map(float, pos_str.split(","))
    except Exception:
        raise RuntimeError(f"Resposta inválida do CLP: {pos_str!r}")
    ts = datetime.datetime.now().isoformat()
    linha = f"[{ts}] - Target Enviado: <{msg}> | Posicao Recebida: <{pos_str}>\n"
    with open(HIST_FILE, "a", encoding="utf-8") as f:
        f.write(linha)
    return x_d, y_d, z_d

app = Dash(__name__)
app.title = "Supervisório Drone SDA"

store_target = dcc.Store(id="store-target", data={"x": 0.0, "y": 0.0, "z": 1.2})
store_drone = dcc.Store(id="store-drone", data={"x": 0.0, "y": 0.0, "z": 0.0})
store_path = dcc.Store(id="store-path", data={"x": [], "y": [], "z": []})
store_mission = dcc.Store(id="store-mission", data={"mode": "idle", "index": 0})
interval = dcc.Interval(id="interval-update", interval=500, n_intervals=0)

graph = dcc.Graph(
    id="map-graph",
    style={"height": "600px", "border-radius": "10px", "box-shadow": "0px 0px 10px rgba(0,0,0,0.2)"},
    config={"displayModeBar": True, "scrollZoom": True}
)

dropdown_quadrado = dcc.Dropdown(
    id="dropdown-square",
    options=[{"label": f"{k} ({v['x']},{v['y']})", "value": k} for k, v in SQUARES.items()],
    placeholder="Escolha um quadrado",
    style={"width": "100%", "border-radius": "8px"}
)

app.layout = html.Div(
    style={"font-family": "Segoe UI", "margin": "20px", "background-color": "#f9f9f9"},
    children=[
        html.H1("🛰️ Supervisório Drone SDA", style={"text-align": "center", "color": "#2c3e50"}),
        html.Div(
            style={"display": "flex", "gap": "20px", "justify-content": "center"},
            children=[
                html.Div(
                    style={"flex": "2", "background": "white", "padding": "20px", "border-radius": "12px", "box-shadow": "0 0 10px rgba(0,0,0,0.1)"},
                    children=[
                        html.H3("📍 Mapa XY (clique para enviar Target)", style={"text-align": "center", "color": "#34495e"}),
                        graph,
                        html.Div(id="info-pos", style={"margin-top": "10px", "font-size": "15px", "text-align": "center", "color": "#2c3e50"}),
                    ],
                ),
                html.Div(
                    style={"flex": "1", "background": "white", "padding": "20px", "border-radius": "12px", "box-shadow": "0 0 10px rgba(0,0,0,0.1)"},
                    children=[
                        html.H3("🎮 Joystick", style={"text-align": "center", "color": "#34495e"}),
                        html.Div(
                            style={"display": "flex", "flex-direction": "column", "align-items": "center"},
                            children=[
                                html.Button("↑", id="btn-up", n_clicks=0, style={"width": "60px", "height": "40px", "background-color": "#3498db", "color": "white", "border": "none", "border-radius": "5px"}),
                                html.Div(
                                    style={"display": "flex", "margin-top": "5px", "margin-bottom": "5px"},
                                    children=[
                                        html.Button("←", id="btn-left", n_clicks=0, style={"width": "60px", "height": "40px", "background-color": "#3498db", "color": "white", "border": "none", "border-radius": "5px"}),
                                        html.Button("→", id="btn-right", n_clicks=0, style={"width": "60px", "height": "40px", "background-color": "#3498db", "color": "white", "border": "none", "border-radius": "5px", "margin-left": "5px"}),
                                    ],
                                ),
                                html.Button("↓", id="btn-down", n_clicks=0, style={"width": "60px", "height": "40px", "background-color": "#3498db", "color": "white", "border": "none", "border-radius": "5px"}),
                                html.Div(style={"height": "10px"}),
                                html.Div("Altura (Z)", style={"font-weight": "bold", "color": "#2c3e50"}),
                                html.Div(
                                    style={"display": "flex", "margin-top": "5px"},
                                    children=[
                                        html.Button("Z+", id="btn-zup", n_clicks=0, style={"width": "60px", "height": "40px", "background-color": "#2ecc71", "color": "white", "border": "none", "border-radius": "5px"}),
                                        html.Button("Z-", id="btn-zdown", n_clicks=0, style={"width": "60px", "height": "40px", "background-color": "#e74c3c", "color": "white", "border": "none", "border-radius": "5px", "margin-left": "5px"}),
                                    ],
                                ),
                            ],
                        ),
                        html.Hr(),
                        html.H3("🗺️ Missões", style={"text-align": "center", "color": "#34495e"}),
                        html.Div(
                            [
                                html.Button("Percorrer todos os quadrados", id="btn-scan", n_clicks=0, style={"width": "100%", "margin-bottom": "10px", "background-color": "#9b59b6", "color": "white", "border": "none", "border-radius": "6px", "height": "35px"}),
                                dropdown_quadrado,
                                html.Button("Ir para quadrado", id="btn-goto-square", n_clicks=0, style={"width": "100%", "margin-top": "8px", "background-color": "#8e44ad", "color": "white", "border": "none", "border-radius": "6px", "height": "35px"}),
                            ]
                        ),
                        html.Hr(),
                        html.H3("🎯 Target manual", style={"text-align": "center", "color": "#34495e"}),
                        html.Div(
                            [
                                html.Div("X:"), dcc.Input(id="input-x", type="number", value=0.0, step=0.1, style={"width": "100%", "margin-bottom": "5px", "border-radius": "6px", "padding": "5px"}),
                                html.Div("Y:"), dcc.Input(id="input-y", type="number", value=0.0, step=0.1, style={"width": "100%", "margin-bottom": "5px", "border-radius": "6px", "padding": "5px"}),
                                html.Div("Z:"), dcc.Input(id="input-z", type="number", value=1.2, step=0.1, style={"width": "100%", "margin-bottom": "10px", "border-radius": "6px", "padding": "5px"}),
                                html.Button("Enviar Target", id="btn-send-target", n_clicks=0, style={"width": "100%", "background-color": "#27ae60", "color": "white", "border": "none", "border-radius": "6px", "height": "35px"}),
                            ]
                        ),
                    ],
                ),
            ],
        ),
        store_target, store_drone, store_path, store_mission, interval,
    ],
)

@app.callback(
    Output("store-target", "data", allow_duplicate=True),
    [Input("btn-up", "n_clicks"), Input("btn-down", "n_clicks"), Input("btn-left", "n_clicks"),
     Input("btn-right", "n_clicks"), Input("btn-zup", "n_clicks"), Input("btn-zdown", "n_clicks")],
    State("store-target", "data"), prevent_initial_call=True,
)
def joystick(n_up, n_down, n_left, n_right, n_zup, n_zdown, target):
    ctx = callback_context
    if not ctx.triggered:
        return target
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    t = target.copy()
    if button_id == "btn-up": t["y"] += STEP_XY
    elif button_id == "btn-down": t["y"] -= STEP_XY
    elif button_id == "btn-left": t["x"] -= STEP_XY
    elif button_id == "btn-right": t["x"] += STEP_XY
    elif button_id == "btn-zup": t["z"] += STEP_Z
    elif button_id == "btn-zdown": t["z"] = max(0.2, t["z"] - STEP_Z)
    return t

@app.callback(
    Output("store-target", "data", allow_duplicate=True),
    Input("map-graph", "clickData"), State("store-target", "data"), prevent_initial_call=True,
)
def click_map(clickData, target):
    if clickData is None: return target
    try:
        x = float(clickData["points"][0]["x"])
        y = float(clickData["points"][0]["y"])
    except Exception:
        return target
    t = target.copy(); t["x"] = x; t["y"] = y
    return t

@app.callback(
    Output("store-target", "data", allow_duplicate=True),
    Input("btn-send-target", "n_clicks"), State("input-x", "value"), State("input-y", "value"), State("input-z", "value"),
    State("store-target", "data"), prevent_initial_call=True,
)
def send_manual_target(n_clicks, x, y, z, target):
    if n_clicks is None or n_clicks == 0: return target
    t = target.copy()
    if x is not None: t["x"] = float(x)
    if y is not None: t["y"] = float(y)
    if z is not None: t["z"] = float(z)
    return t

@app.callback(
    Output("store-target", "data", allow_duplicate=True),
    Input("btn-goto-square", "n_clicks"), State("dropdown-square", "value"), State("store-target", "data"), prevent_initial_call=True,
)
def goto_square(n_clicks, square_id, target):
    if n_clicks is None or n_clicks == 0 or square_id is None: return target
    if square_id not in SQUARES: return target
    sq = SQUARES[square_id]
    return {"x": sq["x"], "y": sq["y"], "z": sq["z"]}

@app.callback(
    [Output("store-mission", "data"), Output("store-target", "data")],
    Input("btn-scan", "n_clicks"), State("store-mission", "data"), State("store-target", "data"), prevent_initial_call=True,
)
def start_scan_mission(n_clicks, mission, target):
    if n_clicks is None or n_clicks == 0: return mission, target
    ordered_keys = list(SQUARES.keys())
    if not ordered_keys: return mission, target
    first_sq = SQUARES[ordered_keys[0]]
    new_mission = {"mode": "scan", "index": 0}
    new_target = {"x": first_sq["x"], "y": first_sq["y"], "z": first_sq["z"]}
    return new_mission, new_target

@app.callback(
    [
        Output("store-drone", "data"),
        Output("store-path", "data"),
        Output("store-mission", "data", allow_duplicate=True),
        Output("map-graph", "figure"),
        Output("info-pos", "children"),
    ],
    Input("interval-update", "n_intervals"),
    State("store-target", "data"),
    State("store-drone", "data"),
    State("store-path", "data"),
    State("store-mission", "data"),
    allow_duplicate=True,
    prevent_initial_call="initial_duplicate",
)
def periodic_update(n_intervals, target, drone, path, mission):
    new_drone = drone.copy(); status = "OK"
    try:
        x_d, y_d, z_d = send_target_and_get_pos(target)
        new_drone = {"x": x_d, "y": y_d, "z": z_d}
    except Exception as e:
        status = f"Erro TCP/CLP: {e}"
    new_mission = mission.copy(); new_target = target.copy()
    if mission.get("mode") == "scan":
        keys = list(SQUARES.keys()); idx = int(mission.get("index", 0))
        if 0 <= idx < len(keys):
            sq_id = keys[idx]; sq = SQUARES[sq_id]
            dx = new_drone["x"] - sq["x"]; dy = new_drone["y"] - sq["y"]; dz = new_drone["z"] - sq["z"]
            dist = sqrt(dx*dx + dy*dy + dz*dz)
            if dist < MISSION_TOL:
                idx += 1
                if idx < len(keys):
                    next_sq = SQUARES[keys[idx]]
                    new_target = {"x": next_sq["x"], "y": next_sq["y"], "z": next_sq["z"]}
                    new_mission["index"] = idx
                else:
                    new_mission = {"mode": "idle", "index": 0}
        else:
            new_mission = {"mode": "idle", "index": 0}
    xs = path.get("x", []); ys = path.get("y", []); zs = path.get("z", [])
    xs.append(new_drone["x"]); ys.append(new_drone["y"]); zs.append(new_drone["z"])
    if len(xs) > 500:
        xs = xs[-500:]; ys = ys[-500:]; zs = zs[-500:]
    new_path = {"x": xs, "y": ys, "z": zs}
    fig = go.Figure()
    fig.update_layout(
        xaxis_title="X (m)", yaxis_title="Y (m)", 
        xaxis=dict(scaleanchor="y", scaleratio=1, range=[-3, 3]), 
        yaxis=dict(range=[-3, 3]),
        clickmode="event+select",
        margin=dict(l=40, r=10, t=40, b=40),
        plot_bgcolor="#ecf0f1",
        paper_bgcolor="#ffffff"
    )
    if len(xs) > 1:
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name="Trajetória", line=dict(color="#2980b9", width=2)))
    fig.add_trace(go.Scatter(x=[new_drone["x"]], y=[new_drone["y"]], mode="markers", name="Drone", marker=dict(size=12, color="#e67e22")))
    fig.add_trace(go.Scatter(x=[new_target["x"]], y=[new_target["y"]], mode="markers", name="Target", marker=dict(symbol="x", size=12, color="#c0392b")))
    fig.add_trace(go.Scatter(x=[v["x"] for v in SQUARES.values()], y=[v["y"] for v in SQUARES.values()],
                             mode="markers+text", name="Quadrados", text=list(SQUARES.keys()), textposition="top center", marker=dict(size=10, color="#27ae60")))
    info_text = (f"Drone: X={new_drone['x']:.2f}, Y={new_drone['y']:.2f}, Z={new_drone['z']:.2f} | "
                 f"Target: X={new_target['x']:.2f}, Y={new_target['y']:.2f}, Z={new_target['z']:.2f} | "
                 f"Missão: {new_mission.get('mode')} (idx={new_mission.get('index')}) | {status}")
    return new_drone, new_path, new_mission, fig, info_text

if __name__ == "__main__":
    app.run(debug=True)
