import sys
import time
import datetime
from opcua import Server, Client

# --- Configurações ---
OPCUA_URL = "opc.tcp://localhost:53530/OPCUA/SimulationServer" 
CHAINED_SERVER_URL = "opc.tcp://localhost:4850/MESServer" 
FILENAME = "mes.txt"
NS_MES = "MES_Namespace"


# --- Lógica de conexão ---
def connect_opc(url=OPCUA_URL):
    client = Client(url)
    client.connect()
    print("[OPC] Connected")

    root = client.get_objects_node()

    # Tente achar a pasta "Drone" no ns=3 (padrão do SimulationServer),
    # e tenha fallback para procurar por nome entre os filhos.
    drone_folder = None
    try:
        drone_folder = root.get_child(["3:Drone"])
    except Exception:
        # fallback: varrer filhos e procurar "Drone" 
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

    # Mapeie variáveis por nome (case-insensitive)
    name_to_node = {}
    for v in drone_folder.get_children():
        try:
            nm = v.get_browse_name().Name
            name_to_node[nm.lower()] = v
        except Exception:
            pass

    dX = name_to_node.get("dronex") 
    dY = name_to_node.get("droney") 
    dZ = name_to_node.get("dronez") 

    if not all([dX, dY, dZ]):
        found = ", ".join(sorted(name_to_node.keys()))
        raise RuntimeError(
            "Variáveis do Drone não encontradas. "
            "Quero DroneX, DroneY, DroneZ. "
            f"Encontradas: {found}"
        )

    print("[OPC] Vars bound:", "DroneX/DroneY/DroneZ")
    return client, (dX, dY, dZ)

def start_chained_server():

    # MODO SERVIDOR:
    # Atua como CLIENTE do Prosys (porta 53530) e como SERVIDOR na porta 4850.
    
    print("[Chained-Server] Iniciando...")
    
    # Configurar o chained server
    server = Server()
    server.set_endpoint(CHAINED_SERVER_URL)
    
    ns_idx = server.register_namespace(NS_MES)
    objects = server.get_objects_node()
    
    # Cria um objeto para organizar as variáveis
    mes_obj = objects.add_object(ns_idx, "MES_Data")
    
    # Cria as 3 variáveis no chained server
    mes_var_x = mes_obj.add_variable(ns_idx, "Drone_X_MES", 0.0)
    mes_var_y = mes_obj.add_variable(ns_idx, "Drone_Y_MES", 0.0)
    mes_var_z = mes_obj.add_variable(ns_idx, "Drone_Z_MES", 0.0)
    
    server.start()
    print(f"[Chained-Server] Servidor MES rodando em {CHAINED_SERVER_URL}")

    # Configura o cliente para ler do Prosys
    while True:
        try:
            # Conecta ao Prosys e obtém os nós do Drone
            client_prosys, (prosys_x, prosys_y, prosys_z) = connect_opc(OPCUA_URL)

            while True:
                try:
                    # Lê o valor do Prosys
                    val_x = prosys_x.get_value()
                    val_y = prosys_y.get_value()
                    val_z = prosys_z.get_value()
                    
                    # Escreve o valor no chained server
                    mes_var_x.set_value(val_x)
                    mes_var_y.set_value(val_y)
                    mes_var_z.set_value(val_z)
                    
                    print(f"[Chained-Server] Dados atualizados.")
                    
                except Exception as e_loop:
                    print(f"[Chained-Server] Erro no loop de dados: {e_loop}")
                    client_prosys.disconnect()
                    break # Tenta reconectar o cliente
                    
                time.sleep(2) 

        except Exception as e_conn:
            print(f"[Chained-Server] Erro de conexão com Prosys: {e_conn}. Tentando em 5s...")
            time.sleep(5)
            
    server.stop()


def iniciar_cliente_mes():
    
    # MODO CLIENTE:
    # Conecta-se ao chained server (porta 4850)
    # Lê os dados e salva em mes.txt
    
    print("[Cliente-MES] Iniciando...")
    print(f"[Cliente-MES] Conectando ao Chained Server em {CHAINED_SERVER_URL}")
    
    client_mes = Client(CHAINED_SERVER_URL)

    while True:
        try:
            client_mes.connect()
            print("[Cliente-MES] Conectado ao Chained Server.")
            
            # --- Busca de nós ---
            # Encontra o índice do namespace que o chained server criou e encontra o objeto "MES_Data"
            ns_idx_mes = client_mes.get_namespace_index(NS_MES)
            objects_node = client_mes.get_objects_node()
            mes_data_obj = objects_node.get_child(f"{ns_idx_mes}:MES_Data")
            
            # Encontra as variáveis dentro do objeto
            node_x = mes_data_obj.get_child(f"{ns_idx_mes}:Drone_X_MES")
            node_y = mes_data_obj.get_child(f"{ns_idx_mes}:Drone_Y_MES")
            node_z = mes_data_obj.get_child(f"{ns_idx_mes}:Drone_Z_MES")

            print("[Cliente-MES] Nós do chained server vinculados. Iniciando log...")

            while True:
                val_x = node_x.get_value()
                val_y = node_y.get_value()
                val_z = node_z.get_value()
                
                timestamp = datetime.datetime.now().isoformat()
                linha = f"[{timestamp}] - X={val_x:.4f}, Y={val_y:.4f}, Z={val_z:.4f}\n"
                                
                # Salva em mes.txt
                with open(FILENAME, "a", encoding="utf-8") as f:
                    f.write(linha)

                print("[Cliente-MES] Log realizado.")

                time.sleep(5) 

        except Exception as e:
            print(f"\n[Cliente-MES] Erro: {e}. Tentando reconectar em 5s...")
            client_mes.disconnect()
            time.sleep(5)

# --- Seletor de Execução ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Erro: Especifique o modo de execução.")
        print("Uso: python mes.py servidor")
        print(" ou: python mes.py cliente")
        sys.exit(1)

    modo = sys.argv[1].lower()
    
    if modo == "servidor":
        start_chained_server()
    elif modo == "cliente":
        iniciar_cliente_mes()
    else:
        print(f"Modo '{modo}' desconhecido.")
        print("Use 'servidor' ou 'cliente'.")