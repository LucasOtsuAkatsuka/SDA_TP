# Trabalho Prático SDA

# Lucas Jun Otsu Akatsuka e Clara Temponi Marigo

## VISÃO GERAL
Componentes:
- Comunicação OPC UA
- Comunicação TCP/IP entre CLP virtual e IHM
- Comunicação com o CoppeliaSim via ZMQ Remote API
- Interface web (IHM)

Cada arquivo deve ser executado em um terminal independente


## 1. PRÉ-REQUISITOS
Python instalado.

### Bibliotecas necessárias:
Execute os comandos abaixo no terminal:

pip install dash plotly flask opcua pyzmq coppeliasim_zmqremoteapi_client

## 2. SOFTWARE EXTERNO NECESSÁRIO

### Servidor OPC UA - Prosys Simulation Server
1. Instale o Prosys OPC UA Simulation Server.
2. Crie os seguintes elementos:

Objeto: Drone  
Variáveis: DroneX, DroneY, DroneZ, TargetX, TargetY, TargetZ  
NodeID Type: Numeric  
Value Type: Constant  
Data Type: BaseDataType  
Valor inicial: 0.1

3. Inicie o servidor antes de rodar o sistema.

### CoppeliaSim
1. Instale o CoppeliaSim EDU (ou PRO).
2. Abra a cena do drone configurada para receber coordenadas via ZMQ.


## 3. ESTRUTURA DE ARQUIVOS

Projeto_Drone_OPCUA/
├── CLP.py                → CLP virtual (TCP/IP + OPC UA)
├── bridge.py             → Ponte OPC UA ↔ CoppeliaSim
├── clienteTCPIP.py       → Cliente TCP/IP (operador)
├── MES.py                → Servidor e cliente MES
├── IHM.py                → Interface Homem Máquina


## 4. ORDEM DE EXECUÇÃO
Execute cada arquivo em um terminal separado, na seguinte ordem:

1️ - python CLP.py
2️ - python bridge.py
3️ - python clienteTCPIP.py
4️ - python MES.py servidor
5 - python MES.py cliente
6 - python IHM.py 


## 5. INTERFACE HOMEM-MÁQUINA (IHM)
O arquivo IHM.py cria uma interface web com controle em tempo real do drone.

Para iniciar:

python IHM.py

Aguarde a mensagem:

Dash is running on http://127.0.0.1:8050/

Abra no navegador o endereço:
http://127.0.0.1:8050
