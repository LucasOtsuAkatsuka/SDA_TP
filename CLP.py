import socket
import threading
import time
from opcua import Client

lock_data = threading.Lock()
pos_drone = {"x": 0.0, "y": 0.0, "z": 0.0}
pos_target = {"x": 0.0, "y": 0.0, "z": 0.0} 

OPCUA_URL = "opc.tcp://localhost:53530/OPCUA/SimulationServer" 
TCP_HOST = "localhost"
TCP_PORT = 65432

def connect_opc(url=OPCUA_URL):
    client = Client(url)
    client.connect()
    print("[OPC] Connected")

    root = client.get_objects_node()

    drone_folder = None
    try:
        drone_folder = root.get_child(["3:Drone"])
    except Exception:
    
        for n in root.get_children():
            try:
                name = n.get_browse_name().Name
                if name.lower() == "drone": 
                    drone_folder = n
                    break
            except Exception:
                pass
    if drone_folder is None:
        raise RuntimeError("Não encontrei a pasta 'Drone' no servidor OPC UA.") 

    name_to_node = {}
    for v in drone_folder.get_children():
        try:
            nm = v.get_browse_name().Name
            name_to_node[nm.lower()] = v
        except Exception:
            pass

    tX = name_to_node.get("targetx")
    tY = name_to_node.get("targety")
    tZ = name_to_node.get("targetz")
    dX = name_to_node.get("dronex")
    dY = name_to_node.get("droney")
    dZ = name_to_node.get("dronez")

    if not all([tX, tY, tZ, dX, dY, dZ]):
        found = ", ".join(sorted(name_to_node.keys()))
        raise RuntimeError(
            "Variáveis esperadas não encontradas. "
            "Quero TargetX, TargetY, TargetZ, DroneX, DroneY, DroneZ. "
            f"Encontradas: {found}"
        )

    print("[OPC] Vars bound:",
            "TargetX/TargetY/TargetZ & DroneX/DroneY/DroneZ")
    return client, (tX, tY, tZ, dX, dY, dZ)


def thread_opcua_client():
    
    while True:
        try:
            client, (node_tx, node_ty, node_tz, node_dx, node_dy, node_dz) = connect_opc(OPCUA_URL)

            while True:
                with lock_data:
                    pos_drone["x"] = node_dx.get_value()
                    pos_drone["y"] = node_dy.get_value()
                    pos_drone["z"] = node_dz.get_value()
                
                with lock_data:
                    local_target = pos_target.copy()
                
                node_tx.set_value(local_target["x"])
                node_ty.set_value(local_target["y"])
                node_tz.set_value(local_target["z"])
                
                print(f"[OPC] Lendo: {pos_drone} | Escrevendo: {local_target}")
                time.sleep(0.5)

        except Exception as e:
            print(f"[OPC] Erro: {e}. Tentando reconectar em 5s...")
            client.disconnect()
            time.sleep(5)

def thread_servidor_tcp():
    
    print(f"[TCP] Iniciando servidor TCP em {TCP_HOST}:{TCP_PORT}...")
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((TCP_HOST, TCP_PORT))
        s.listen()
        
        while True:
            conn, addr = s.accept()
            with conn:
                print(f"[TCP] Cliente {addr} conectado.")
                
                data = conn.recv(1024)
                if not data:
                    continue
                    
                new_target_str = data.decode('utf-8')
                print(f"[TCP] Recebido do Cliente TCP/IP: {new_target_str}")
                
                try:
                    x, y, z = map(float, new_target_str.split(','))
                    
                    with lock_data:
                        pos_target["x"] = x
                        pos_target["y"] = y
                        pos_target["z"] = z
                    
                    with lock_data:
                        pos_drone_str = f'{pos_drone["x"]},{pos_drone["y"]},{pos_drone["z"]}'
                    
                    conn.sendall(pos_drone_str.encode('utf-8'))

                except ValueError:
                    print("[TCP] Formato de target inválido. Esperado 'x,y,z'.")
                    conn.sendall(b"Erro: Formato invalido.")
                except Exception as e:
                    print(f"[TCP] Erro na conexão: {e}")

if __name__ == "__main__":
    
    opc_thread = threading.Thread(target=thread_opcua_client, daemon=True)
    opc_thread.start()

    tcp_thread = threading.Thread(target=thread_servidor_tcp, daemon=True)
    tcp_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        exit