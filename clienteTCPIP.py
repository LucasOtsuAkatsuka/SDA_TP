import socket
import datetime
import re

CLP_HOST = "localhost"
CLP_PORT = 65432
FILENAME = "historiador.txt"

# Padrão "float,float,float" sem espaços.
PADRAO_COORDENADAS = re.compile(r"^-?\d+(\.\d+)?,-?\d+(\.\d+)?,-?\d+(\.\d+)?$")

def historian(sent_target, received_pos):
    # Registra as informações no arquivo historico.txt
    
    timestamp = datetime.datetime.now().isoformat()
    linha = f"[{timestamp}] - Target Enviado: <{sent_target}> | Posicao Recebida: <{received_pos}>\n"
    
    try:
        # Abre o arquivo em modo "append" (a) para adicionar no final
        with open(FILENAME, "a", encoding="utf-8") as f:
            f.write(linha)
    except Exception as e:
        print(f"[Erro Historiador] Falha ao escrever no arquivo: {e}")

def main():
    print("--- Cliente TCP/IP ---")
    print("Digite as coordenadas de target no formato 'x,y,z' (ex: 1.5,2.0,1.0)")
    print("Digite 'sair' para fechar.")

    while True:
        target_str = input("\nNovo Target (x,y,z): ")
        
        if target_str.lower() == 'sair':
            break

        # --- Validação ---
        # Verifica se a string bate com o padrão "n,n,n" antes de enviar
        if not PADRAO_COORDENADAS.match(target_str):
            print(f"  [Erro] Formato inválido. Use 'x,y,z' sem espaços.")
            continue
        
        # --- Comunicação TCP ---
        try:
            # Cria um novo socket para cada transação, pois o CLP.py desconecta após cada comando
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((CLP_HOST, CLP_PORT))
                
                # Envia novo target
                s.sendall(target_str.encode('utf-8'))
                
                # Recebe posição atual
                data = s.recv(1024)
                pos_drone_str = data.decode('utf-8')
                
                print(f"  > Target enviado: {target_str}")
                print(f"  < Posicao atual recebida: {pos_drone_str}")
                
                # Log no historiador
                historian(target_str, pos_drone_str)

        except ConnectionRefusedError:
            print(f"  [Erro TCP] Não foi possível conectar.")
        except Exception as e:
            print(f"  [Erro TCP] Falha na comunicação com o CLP: {e}")
            historian(target_str, f"ERRO NA COMUNICACAO: {e}")

if __name__ == "__main__":
    main()