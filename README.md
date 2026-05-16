# Robô Aspirador — POC Kinect (ROS Noetic)

**TurtleBot2** com base **Kobuki** e sensor **Kinect v1 (Xbox 360)** simulado no **Gazebo**, controle por **teleop** (teclado) e visualização **RGB + profundidade + nuvem de pontos** no **RViz**, executável via **Docker** (Linux e Windows/WSL2).

## O que esta POC faz (e o que não faz)

| Incluído | Não incluído nesta entrega |
|----------|----------------------------|
| Simulação Gazebo + casa | SLAM / gmapping |
| Teleop TurtleBot2 | Cobertura automática (MBF) |
| RViz: RGB, depth, PointCloud2, LaserScan | Kinect físico USB |
| Docker Linux + WSL2 | |

## Kinect, libfreenect, OpenNI e PCL

### Na simulação (esta POC)

O URDF `kobuki_hexagons_kinect.urdf.xacro` (pacote `turtlebot_description`) inclui um sensor RGB-D modelado com base no Microsoft Kinect no Gazebo. O plugin publica diretamente mensagens ROS:

| Mensagem ROS | Tópico típico | Papel |
|--------------|---------------|--------|
| `sensor_msgs/Image` | `/camera/rgb/image_raw` | Cor |
| `sensor_msgs/Image` | `/camera/depth/image_raw` | Profundidade |
| `sensor_msgs/CameraInfo` | `/camera/*/camera_info` | Calibração |
| `sensor_msgs/PointCloud2` | `/camera/depth/points` | Nuvem 3D |
| `sensor_msgs/LaserScan` | `/scan` | Gerado por `depthimage_to_laserscan` |

**Não** chamamos `libfreenect` nem `openni2_camera` em runtime na simulação: o hardware Kinect não existe no container; o Gazebo substitui o driver.

### Com Kinect físico (fase futura)

| Biblioteca / stack | Uso |
|--------------------|-----|
| **libfreenect** + **freenect_stack** | Driver open-source para Kinect v1 (Xbox 360). Publica os mesmos tipos de mensagem nos mesmos tópicos. |
| **OpenNI2** + **openni2_camera** | Alternativa para sensores PrimeSense/Xtion; **não** cobre Kinect v1 oficialmente no Noetic. |
| **PCL** | Processa `PointCloud2` (filtros, segmentação, reconhecimento 3D). RViz já exibe a nuvem; PCL seria usado em nós C++/Python de percepção. |

Tópicos documentados em: `src/robo_aspirador_kinect/config/rgbd_topics.yaml`.

## Pré-requisitos

- Docker + Docker Compose v2
- **Linux:** X11 (`xhost +local:docker`)
- **Windows:** Docker Desktop + WSL2 + [VcXsrv](https://sourceforge.net/projects/vcxsrv/) ou Xming

## Build da imagem

```bash
cd robo_aspirador_ROS_kinect
docker compose build
```

A primeira build clona TurtleBot2/Kobuki (vários minutos).

## Executar

### Linux

```bash
xhost +local:docker
docker compose -f docker-compose.yaml -f docker-compose.linux.yaml run --rm ros-kinect-poc
```

Dentro do container — use **dois terminais**:

**Terminal 1** (simulação + RViz):

```bash
source /root/catkin_ws/devel/setup.bash
roslaunch robo_aspirador_kinect poc_demo.launch
```

**Terminal 2** (teleop — mantenha o foco aqui ao dirigir):

```bash
source /root/catkin_ws/devel/setup.bash
roslaunch robo_aspirador_kinect teleop.launch
```

### Windows + WSL2

1. Inicie VcXsrv (Disable access control).
2. No WSL: `export DISPLAY=$(grep nameserver /etc/resolv.conf | awk '{print $2}'):0`
3. `docker compose -f docker-compose.yaml -f docker-compose.wsl2.yaml up -d`
4. `docker exec -it robo_aspirador_kinect bash` — depois os dois `roslaunch` acima (em shells separados).

Pode ser que não seja necessário VcXsrv, execução pura via WSL2 com apenas execução do docker-compose e roslaunch do launcher com Gazebo e RViz se mostraram possíveis em algumas versões.
É importante testar sem VcXsrv e verificar se em sua máquina a execução ocorre normalmente, caso não ocorra, então será necessário recorrer a VcXsrv.

## Teleop — teclas (`kinect_teleop.py`)

| Tecla | Ação |
|-------|------|
| `i` | Frente |
| `,` | Trás |
| `j` / `l` | Girar esquerda / direita |
| `k` ou `s` | Parar |
| `r` / `f` | Aumentar / diminuir velocidade |
| `q` | Sair |

**Não confundir com `teleop_twist_keyboard`:** lá `q`/`z`/`w`/`x`/`e`/`c` só ajustam velocidade; `i`/`j`/`l` precisam ser mantidos e competem com RViz se tudo sobe no mesmo `roslaunch`.

## Launches modulares

| Launch | Função |
|--------|--------|
| `bringup_sim.launch` | Gazebo + casa + TurtleBot2/Kinect |
| `teleop.launch` | Teclado |
| `rviz_sensors.launch` | RViz sensores |
| `poc_demo.launch` | Tudo junto + verificador de tópicos |

## Mapas (fase futura)

Mapas `casa.yaml` / `casa_v2.yaml` para futura implementação de SLAM e aspiração automática.

## Verificação rápida de tópicos

```bash
rosrun robo_aspirador_kinect verify_rgbd_topics.py
# ou
rostopic list | grep camera
```

## Simulação Kobuki no Gazebo

O movimento e o frame `odom` dependem do plugin `libgazebo_ros_kobuki.so` (pacote `kobuki_gazebo_plugins`, extraído de `kobuki_desktop`). Sem ele, o RViz acusa *Unknown frame odom* e o teleop não aciona as rodas. O setup Docker compila só esse pacote (não o `kobuki_desktop` inteiro, para evitar dependência PyQt no build). Após atualizar o projeto, refaça `docker compose build`.

## Referências

- [Robots/TurtleBot (ROS Wiki)](https://wiki.ros.org/Robots/TurtleBot)
- [freenect_stack](https://wiki.ros.org/freenect_stack)
- [openni2_camera](https://wiki.ros.org/openni2_camera)
- [turtlebot2-noetic (guia comunitário)](https://github.com/ailabspace/turtlebot2-noetic)
