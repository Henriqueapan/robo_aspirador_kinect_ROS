# Robô Aspirador — Kinect (ROS Noetic)

**TurtleBot2** com base **Kobuki** e sensor **Kinect v1 (Xbox 360)** simulado no **Gazebo**, com **navegação autônoma em dois modos** (mapeamento manual por SLAM + aspiração por cobertura de área), controle por **teleop** (teclado) e visualização **RGB + profundidade + nuvem de pontos** no **RViz**, executável via **Docker** (Linux e Windows/WSL2).

## O que este projeto faz (e o que não faz)


| Incluído                                                | Não incluído nesta entrega               |
| ------------------------------------------------------- | ---------------------------------------- |
| Simulação Gazebo + casa                                 | Kinect físico USB                        |
| Teleop TurtleBot2                                       | Uso 3D da nuvem no planejamento (fase 2) |
| SLAM / gmapping (mapa a partir do Kinect)               |                                          |
| Cobertura automática (MBF + full_coverage_path_planner) |                                          |
| Menu de modos (manual / salvar mapa / automático)       |                                          |
| RViz: RGB, depth, PointCloud2, LaserScan                |                                          |
| Docker Linux + WSL2                                     |                                          |


> A navegação autônoma reaproveita a stack do projeto `robo_aspirador_ROS-original`
> (gmapping + move_base_flex + full_coverage_path_planner + tracking_pid + amcl),
> alimentada pelo `/scan` **derivado do Kinect** via `depthimage_to_laserscan`.



## Kinect, libfreenect, OpenNI e PCL



### Na simulação (esta POC)

O URDF `kobuki_hexagons_kinect.urdf.xacro` (pacote `turtlebot_description`) inclui um sensor RGB-D modelado com base no Microsoft Kinect no Gazebo. O plugin publica diretamente mensagens ROS:


| Mensagem ROS              | Tópico típico             | Papel                                |
| ------------------------- | ------------------------- | ------------------------------------ |
| `sensor_msgs/Image`       | `/camera/rgb/image_raw`   | Cor                                  |
| `sensor_msgs/Image`       | `/camera/depth/image_raw` | Profundidade                         |
| `sensor_msgs/CameraInfo`  | `/camera/*/camera_info`   | Calibração                           |
| `sensor_msgs/PointCloud2` | `/camera/depth/points`    | Nuvem 3D                             |
| `sensor_msgs/LaserScan`   | `/scan`                   | Gerado por `depthimage_to_laserscan` |


**Não** chamamos `libfreenect` nem `openni2_camera` em runtime na simulação: o hardware Kinect não existe no container; o Gazebo substitui o driver.

### Com Kinect físico (fase futura)


| Biblioteca / stack                   | Uso                                                                                                                                      |
| ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **libfreenect** + **freenect_stack** | Driver open-source para Kinect v1 (Xbox 360). Publica os mesmos tipos de mensagem nos mesmos tópicos.                                    |
| **OpenNI2** + **openni2_camera**     | Alternativa para sensores PrimeSense/Xtion; **não** cobre Kinect v1 oficialmente no Noetic.                                              |
| **PCL**                              | Processa `PointCloud2` (filtros, segmentação, reconhecimento 3D). RViz já exibe a nuvem; PCL seria usado em nós C++/Python de percepção. |


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

Dentro do container:

- Para a **entrega completa** (mapeamento + aspiração autônoma), vá para a seção
[Navegação autônoma (dois modos)](#navegação-autônoma-dois-modos).
- Para o **demo apenas de sensores** (RGB-D + nuvem no RViz), use **dois terminais**:

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


| Tecla      | Ação                           |
| ---------- | ------------------------------ |
| `i`        | Frente                         |
| `,`        | Trás                           |
| `j` / `l`  | Girar esquerda / direita       |
| `k` ou `s` | Parar                          |
| `r` / `f`  | Aumentar / diminuir velocidade |
| `q`        | Sair                           |


**Não confundir com** `teleop_twist_keyboard`**:** lá `q`/`z`/`w`/`x`/`e`/`c` só ajustam velocidade; `i`/`j`/`l` precisam ser mantidos e competem com RViz se tudo sobe no mesmo `roslaunch`.

## Navegação autônoma (dois modos)

Fluxo análogo ao `robo_aspirador_ROS-original`, mas com Kobuki + Kinect e `/scan`
derivado da profundidade do Kinect. A abordagem é **um** `roslaunch` **por terminal**:
o launch principal sobe **apenas a base** (Gazebo + robô + Kinect + `/scan` +
**RViz**) e cada etapa (mapear, dirigir, aspirar) roda no seu próprio terminal.
É simples, previsível e portável (Linux/Windows/WSL2).

> Abrir novos terminais **automaticamente** pelo launch (`launch-prefix="xterm -e"`)
> exigiria um emulador de terminal + X server no container e é frágil no WSL2/Windows.
> Por isso cada terminal é aberto manualmente com `docker exec -it ... bash`.

Cada novo terminal começa igual:

```bash
docker exec -it robo_aspirador_kinect bash
source /root/catkin_ws/devel/setup.bash
```



### Passo a passo

**Terminal 1 — base (deixe rodando o tempo todo):**

```bash
roslaunch robo_aspirador_kinect bringup_sim.launch rviz:=true
```

Sobe Gazebo + casa + TurtleBot2/Kinect + `/scan` + RViz (config
`config/navigation.rviz`), onde você acompanha o mapa crescendo e, depois, o
caminho de cobertura.

**Terminal 2 — mapeamento (gmapping):**

```bash
roslaunch robo_aspirador_kinect manual_mapping.launch
```

**Terminal 3 — dirigir (teleop):**

```bash
roslaunch robo_aspirador_kinect teleop.launch
```

Dirija cobrindo todo o ambiente (teclas na seção acima). Quando o mapa no RViz
estiver bom, **salve o mapa** (em qualquer terminal com o ROS carregado):

```bash
rosrun map_server map_saver -f /root/catkin_ws/src/robo_aspirador_kinect/maps/mapa_atual
rosrun robo_aspirador_kinect fechar_mapa.py /root/catkin_ws/src/robo_aspirador_kinect/maps/mapa_atual.yaml
```

O segundo comando gera `mapa_atual_fechado.{yaml,pgm}`, com a área
**desconhecida (cinza) pintada como parede**. É esse mapa que a aspiração
automática usa por padrão: o planejador de cobertura (SpiralSTC) trata célula
desconhecida como espaço livre, então com o mapa "aberto" o caminho vazaria
pelas fronteiras não mapeadas — atravessando paredes e saindo do mapa. (No menu
`mode_selector`, a opção `s` já gera os dois arquivos.)

**Encerrar o mapeamento e aspirar:**

1. `Ctrl+C` no Terminal 2 (encerra o gmapping) e no Terminal 3 (teleop).
2. No Terminal 2, suba a aspiração autônoma por cobertura:

```bash
roslaunch robo_aspirador_kinect automatic_aspiracao.launch
```

Por padrão a pose do robô no mapa segue a **odometria do Kobuki** (arg
`localization:=odom` no `automatic_aspiracao.launch`): o launch publica uma TF
`map → odom` **estática** e a cobertura roda sem AMCL, evitando o "deslize" que
o AMCL causa com o FOV estreito do Kinect (~60°). Isso pressupõe que o robô
inicia a cobertura na mesma pose de spawn em que o mapa foi ancorado (o
gmapping ancora `map` na origem do `odom`); ajuste `map_odom_x/y/yaw` se
começar de outra pose conhecida. Para usar o comportamento clássico com AMCL:

```bash
roslaunch robo_aspirador_kinect automatic_aspiracao.launch localization:=amcl
```

O `full_coverage_path_planner` + MBF + `tracking_pid` percorrem a área. Para
encerrar tudo: `Ctrl+C` no Terminal 2 e depois no Terminal 1.

> Cada etapa em um terminal próprio porque teleop e (opcionalmente) o menu leem o
> teclado — no mesmo terminal competiriam pelo stdin. E, com launches separados,
> o `Ctrl+C` de cada um encerra exatamente aquela etapa, sem deixar processo órfão.



### Qualidade do mapa (Kinect vs. laser) e como mapear bem

O mapa é construído pelo **mesmo gmapping** do projeto original. A diferença de
qualidade **não é do código migrado** — é do sensor:


|                           | Original (P3DX) | Kinect (aqui) |
| ------------------------- | --------------- | ------------- |
| Campo de visão do `/scan` | **240°**        | **~60°**      |
| Feixes                    | 727             | ~640          |
| Alcance                   | 4 m             | ~8 m          |
| Taxa                      | 50 Hz           | 10 Hz         |


Com só ~60° de FOV (1/4 do laser original), o *scan-matching* do gmapping tem bem
menos geometria para "casar", sobretudo em **rotação** — daí o mapa parecer
"escorregar/girar" em torno do robô quando o casamento aceita uma correção ruim.

O `manual_mapping.launch` já vem ajustado para isso (ver comentários no arquivo):
`minimumScore` com default **50** (rejeita casamento ruim e cai na odometria,
evitando o "salto" de pose), `maxUrange`/`maxRange` no alcance real do Kinect
(8 m), mais `particles` e atualização mais frequente. O modelo de ruído da
odometria fica no **default do gmapping** (como no original) — reduzi-lo
estreita demais a busca do matcher.

**Dicas de operação (fazem muita diferença com FOV estreito):**

- Dirija **devagar**, principalmente nas **curvas** (gire pouco de cada vez).
- Sempre aponte o Kinect para **paredes/quinas** próximas (<8 m); girar no meio de
um cômodo grande, "olhando para o nada", degrada o casamento.
- Faça **passagens sobrepostas** e **feche voltas** passando de novo por lugares já
vistos — ajuda o gmapping a corrigir.

**Calibração fina** (o `manual_mapping.launch` expõe como `arg`):

```bash
# se o mapa ainda "escorregar", exija casamento melhor (aumente):
roslaunch robo_aspirador_kinect manual_mapping.launch minimum_score:=80
# se o mapa ficar SÓ por odometria (derivando ao fechar voltas), relaxe:
roslaunch robo_aspirador_kinect manual_mapping.launch minimum_score:=0
```



### Alternativa: menu interativo (`mode_selector`)

Se preferir orquestrar tudo por um **menu** em vez de vários `roslaunch`, use:

```bash
roslaunch robo_aspirador_kinect robo_aspirador_mode_selector.launch
```

Ele sobe a base e um menu: `1` = manual (gmapping) · `s` = salvar mapa · `2` =
automático (cobertura) · `q` = sair do menu. O teleop continua em outro terminal
(`roslaunch robo_aspirador_kinect teleop.launch`). O fluxo por terminais acima é
o recomendado; o menu é mantido como conveniência.

### Fonte do `/scan` (modular)

A geração do `/scan` é isolada em `scan_source.launch` com o argumento `scan_source`:


| Valor            | Nó                        | Uso                                                                                                                                                                |
| ---------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `depth` (padrão) | `depthimage_to_laserscan` | Achata a imagem de profundidade do Kinect. Leve e validado.                                                                                                        |
| `cloud`          | `pointcloud_to_laserscan` | Projeta a nuvem 3D (`/camera/depth/points`) com filtro de altura, como nodelet no mesmo manager. Requer `ros-noetic-pointcloud-to-laserscan` (já no `Dockerfile`). |


Trocar a fonte é um argumento — o resto da stack só conhece o tópico `/scan`:

```bash
roslaunch robo_aspirador_kinect bringup_sim.launch scan_source:=cloud
```

O modo `cloud` usa `target_frame=base_footprint`, então o filtro de altura é
referente ao **chão** (não ao plano do sensor): `min_height` corta o chão e
`max_height` corta o teto, mas obstáculos baixos (pé de mesa, cadeira) continuam
visíveis. Os parâmetros de tuning ficam expostos como `arg` em
`scan_source.launch` (calibração ao vivo, sem editar o launch):


| `arg`                                 | Default              | Papel                                               |
| ------------------------------------- | -------------------- | --------------------------------------------------- |
| `cloud_target_frame`                  | `base_footprint`     | Frame do filtro/saída (Z=0 no chão)                 |
| `cloud_min_height`                    | `0.05`               | Altura mínima (descarta chão)                       |
| `cloud_max_height`                    | `1.20`               | Altura máxima (descarta teto)                       |
| `range_max`                           | `8.0`                | Alcance máximo (alinhado ao `maxRange` do gmapping) |
| `cloud_angle_min` / `cloud_angle_max` | `-0.5236` / `0.5236` | FOV horizontal (~60°)                               |


> Diferença de frame proposital: `depth` publica em `camera_depth_frame`;
> `cloud` publica em `base_footprint`. Ambos são válidos para os consumidores
> (gmapping/amcl/costmaps) via TF. Se precisar igualar, passe
> `cloud_target_frame:=camera_depth_frame` (aí ajuste `min/max_height` ao plano
> do sensor).



#### Comparar depth vs. cloud (benchmark)

`bench_scan.py` mede o `/scan` (Hz efetivo, latência sensor→scan e % de feixes
válidos), sem escrever arquivos — imprime o resumo no stdout. Rode a base em um
modo, meça, encerre e repita no outro:

```bash
# Terminal 1 (base com scan depth):
roslaunch robo_aspirador_kinect bringup_sim.launch scan_source:=depth
# Terminal 2 (mede 30 s):
rosrun robo_aspirador_kinect bench_scan.py _duration_sec:=30

# Ctrl+C no Terminal 1 e repita com scan_source:=cloud
roslaunch robo_aspirador_kinect bringup_sim.launch scan_source:=cloud
rosrun robo_aspirador_kinect bench_scan.py _duration_sec:=30
```

> Após atualizar o `Dockerfile` (inclusão do `pointcloud_to_laserscan`), refaça
> `docker compose build` para o modo `cloud` funcionar.



## Launches modulares


| Launch                                | Função                                                                                             |
| ------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `bringup_sim.launch`                  | **Base (launch principal)**: Gazebo + casa + TurtleBot2/Kinect + `/scan` (+ RViz com `rviz:=true`) |
| `manual_mapping.launch`               | SLAM gmapping (etapa de mapeamento)                                                                |
| `teleop.launch`                       | Teclado (dirigir no mapeamento)                                                                    |
| `automatic_aspiracao.launch`          | Cobertura (MBF + full_coverage) + amcl (etapa autônoma)                                            |
| `scan_source.launch`                  | Geração do `/scan` (depth | cloud)                                                                 |
| `coverage_mbf_tracking.launch`        | Stack de cobertura (usada pelo modo automático)                                                    |
| `rviz_sensors.launch`                 | RViz sensores                                                                                      |
| `poc_demo.launch`                     | Sensores: bringup + RViz + verificador de tópicos                                                  |
| `robo_aspirador_mode_selector.launch` | Alternativa: base + menu interativo de modos                                                       |




## Mapas

Mapas de exemplo `casa.yaml` / `casa_v2.yaml`. Na etapa de mapeamento você gera e
salva `maps/mapa_atual.{yaml,pgm}` com `rosrun map_server map_saver -f .../maps/mapa_atual` seguido de `rosrun robo_aspirador_kinect fechar_mapa.py .../maps/mapa_atual.yaml` (ou pela opção `s` do menu, na alternativa
`mode_selector`, que faz os dois passos). A etapa automática carrega por padrão
o `maps/mapa_atual_fechado.yaml` (desconhecido pintado como parede, para a
cobertura não vazar pelas fronteiras não mapeadas).

### Raios da cobertura (importante)

O `full_coverage_path_planner` exige `robot_radius` **>=** `tool_radius` (os
defaults dos launches já respeitam isso: `0.2`/`0.18`). Os raios viram tamanhos
em pixels `uint32_t` no `parseGrid`; com `tool_radius > robot_radius` a
subtração interna sofre *underflow*, o índice do mapa clampa em 0 e o
planejador passa a ler sempre a célula `[0]` — enxerga o mapa **inteiro como
livre** e traça o zigue-zague de cobertura por cima de paredes e para fora do
mapa.

## Verificação rápida de tópicos

```bash
rosrun robo_aspirador_kinect verify_rgbd_topics.py
# ou
rostopic list | grep camera
```



## Simulação Kobuki no Gazebo

O movimento e o frame `odom` dependem do plugin `libgazebo_ros_kobuki.so` (pacote `kobuki_gazebo_plugins`, extraído de `kobuki_desktop`). Sem ele, o RViz acusa *Unknown frame odom* e o teleop não aciona as rodas. O setup Docker compila só esse pacote (não o `kobuki_desktop` inteiro, para evitar dependência PyQt no build). Após atualizar o projeto, refaça `docker compose build`.

### Aviso `TF_REPEATED_DATA` (inofensivo)

A TF `odom → base_footprint` é publicada pelo próprio plugin do Kobuki no Gazebo
(como no projeto original, em que a TF vinha do plugin `diff_drive`). O plugin do
Kobuki publica essa TF a uma taxa alta e às vezes com o mesmo timestamp, o que faz
consumidores de TF (RViz, `gmapping`) emitirem avisos `TF_REPEATED_DATA`. **É um
aviso inofensivo** — não afeta odometria, mapa nem navegação.

`config/rosconsole.conf` (aplicado via `<env ROSCONSOLE_CONFIG_FILE>` nos launches)
eleva o logger `ros.tf2` para `ERROR`, reduzindo esses avisos. Como a maior parte
do fluxo roda em terminais separados (o de mapeamento/`gmapping` à parte da base),
o terminal principal permanece utilizável.

## Referências

- [Robots/TurtleBot (ROS Wiki)](https://wiki.ros.org/Robots/TurtleBot)
- [freenect_stack](https://wiki.ros.org/freenect_stack)
- [openni2_camera](https://wiki.ros.org/openni2_camera)
- [turtlebot2-noetic (guia comunitário)](https://github.com/ailabspace/turtlebot2-noetic)

