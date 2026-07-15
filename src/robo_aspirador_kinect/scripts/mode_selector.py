#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seletor de modos do robô aspirador (Kobuki + Kinect).

Adaptado de robo_aspirador_ROS-original/src/robo_aspirador/scripts/mode_selector.py.

IMPORTANTE (arquitetura): a BASE (Gazebo + Kobuki + Kinect + /scan + RViz) é
subida pelo LAUNCH PRINCIPAL (robo_aspirador_mode_selector.launch), NÃO por este
script. Assim o roslaunch externo é o dono do gazebo e o encerra corretamente no
Ctrl+C — evitando processos órfãos que, ao relançar, criariam um segundo publisher
de odom->base_footprint e gerariam o flood de TF_REPEATED_DATA.

Este script só gerencia os MODOS (leves, rápidos de encerrar):
  1 - Manual  : sobe o gmapping. O usuário dirige em OUTRO terminal com
                'roslaunch robo_aspirador_kinect teleop.launch'.
  s - Salvar  : roda 'map_server map_saver' e grava maps/mapa_atual.{yaml,pgm},
                mais a versão maps/mapa_atual_fechado.{yaml,pgm} (desconhecido
                pintado como parede — ver fechar_mapa.py) usada pela cobertura.
  2 - Auto    : para o gmapping e sobe cobertura (MBF + full_coverage) + amcl.
  q - Sair do menu (a base/sim continua; use Ctrl+C no launch principal p/ encerrar).
"""
import os
import signal
import subprocess
import sys
import time

import rospy
import rospkg
import roslaunch
import tf
import tf2_ros

import fechar_mapa


def _preferir_mapa_fechado(map_path):
    """Se existir a versão *_fechado do mapa, usa ela na cobertura.

    O SpiralSTC trata área desconhecida como livre; o mapa fechado (cinza
    pintado de preto) confina o caminho ao que foi realmente mapeado.
    """
    if map_path.endswith(".yaml") and not map_path.endswith("_fechado.yaml"):
        fechado = map_path[:-len(".yaml")] + "_fechado.yaml"
        if os.path.isfile(fechado):
            return fechado
    return map_path


def _open_tty():
    try:
        return open("/dev/tty", "r")
    except Exception:
        return sys.stdin


def _prompt(tty, text):
    sys.stdout.write(text)
    sys.stdout.flush()
    line = tty.readline()
    if not line:
        return ""
    return line.strip()


class ModeSelector:
    def __init__(self, manual_launch, auto_launch, frames, use_current_pose):
        self.manual_launch = manual_launch
        self.auto_launch = auto_launch
        self.frames = frames
        self.use_current_pose = use_current_pose
        self.mode_parent = None
        self.current_mode = None

    def _start_launch(self, launch_path, args):
        uuid = roslaunch.rlutil.get_or_generate_uuid(None, False)
        roslaunch.configure_logging(uuid)
        parent = roslaunch.parent.ROSLaunchParent(uuid, [(launch_path, args)])
        parent.start()
        return parent

    def stop_mode(self):
        if self.mode_parent is not None:
            self.mode_parent.shutdown()
            self.mode_parent = None
            self.current_mode = None
            time.sleep(0.5)

    def start_manual(self):
        if self.current_mode == "manual":
            sys.stdout.write("Modo manual já está ativo.\n")
            sys.stdout.flush()
            return
        self.stop_mode()
        self.mode_parent = self._start_launch(self.manual_launch, [])
        self.current_mode = "manual"
        sys.stdout.write(
            "Modo MANUAL de mapeamento iniciado (gmapping).\n"
            "Dirija o robô em OUTRO terminal:\n"
            "  docker exec -it robo_aspirador_kinect bash\n"
            "  roslaunch robo_aspirador_kinect teleop.launch\n"
        )
        sys.stdout.flush()

    def save_map(self, map_path_no_ext):
        if self.current_mode != "manual":
            sys.stdout.write(
                "Salve o mapa durante o modo MANUAL (gmapping precisa estar ativo).\n"
            )
            sys.stdout.flush()
            return
        map_dir = os.path.dirname(map_path_no_ext)
        if map_dir and not os.path.isdir(map_dir):
            os.makedirs(map_dir, exist_ok=True)
        sys.stdout.write("Salvando mapa em {}.yaml ...\n".format(map_path_no_ext))
        sys.stdout.flush()
        try:
            subprocess.check_call(
                ["rosrun", "map_server", "map_saver", "-f", map_path_no_ext]
            )
            sys.stdout.write("Mapa salvo com sucesso.\n")
        except subprocess.CalledProcessError as exc:
            sys.stdout.write("Falha ao salvar o mapa: {}\n".format(exc))
            sys.stdout.flush()
            return
        # Versão "fechada" (desconhecido -> parede) para a cobertura: o
        # SpiralSTC trata célula desconhecida como livre, então sem isso o
        # caminho vazaria pelas fronteiras não mapeadas para fora da casa.
        try:
            fechado = fechar_mapa.fechar_mapa(map_path_no_ext)
            sys.stdout.write("Mapa fechado (p/ cobertura): {}\n".format(fechado))
        except Exception as exc:
            sys.stdout.write("Falha ao gerar o mapa fechado: {}\n".format(exc))
        sys.stdout.flush()

    def _get_current_pose(self):
        # Listener criado sob demanda (lazy): manter um TransformListener vivo o
        # tempo todo faz o tf2 imprimir avisos TF_REPEATED_DATA (ruído do plugin
        # Kobuki) direto no terminal do menu. Aqui ele vive só por alguns segundos.
        tf_buffer = tf2_ros.Buffer()
        listener = tf2_ros.TransformListener(tf_buffer)
        try:
            transform = tf_buffer.lookup_transform(
                self.frames["map"],
                self.frames["base"],
                rospy.Time(0),
                rospy.Duration(2.0),
            )
            translation = transform.transform.translation
            rotation = transform.transform.rotation
            yaw = tf.transformations.euler_from_quaternion(
                [rotation.x, rotation.y, rotation.z, rotation.w]
            )[2]
            return {"x": translation.x, "y": translation.y, "a": yaw}
        except Exception:
            return None
        finally:
            del listener

    def start_auto(self, map_path, initial_pose, radius_params):
        if self.current_mode == "auto":
            sys.stdout.write("Modo automático já está ativo.\n")
            sys.stdout.flush()
            return
        if not os.path.isfile(map_path):
            sys.stdout.write(
                "Mapa não encontrado: {}\n"
                "Mapeie no modo manual (1) e salve com a opção 's' antes de usar o auto.\n".format(
                    map_path
                )
            )
            sys.stdout.flush()
            return
        if self.use_current_pose:
            current_pose = self._get_current_pose()
            if current_pose is not None:
                initial_pose = current_pose
        self.stop_mode()
        # RViz persistente já sobe com a base; não abrir uma segunda janela aqui.
        args = [
            "map:={}".format(map_path),
            "rviz:=false",
            "initial_pose_x:={}".format(initial_pose["x"]),
            "initial_pose_y:={}".format(initial_pose["y"]),
            "initial_pose_a:={}".format(initial_pose["a"]),
            "robot_radius:={}".format(radius_params["robot"]),
            "tool_radius:={}".format(radius_params["tool"]),
        ]
        self.mode_parent = self._start_launch(self.auto_launch, args)
        self.current_mode = "auto"
        sys.stdout.write("Modo AUTOMÁTICO de aspiração iniciado.\n")
        sys.stdout.flush()

    def shutdown(self):
        # Só encerra o modo atual (gmapping/cobertura). A base é do launch externo.
        self.stop_mode()


def main():
    rospy.init_node("robo_aspirador_mode_selector", anonymous=False, disable_signals=True)
    rospack = rospkg.RosPack()
    pkg_path = rospack.get_path("robo_aspirador_kinect")

    manual_launch = os.path.join(pkg_path, "launch", "manual_mapping.launch")
    auto_launch = os.path.join(pkg_path, "launch", "automatic_aspiracao.launch")

    default_map = rospy.get_param("~default_map", "")
    if not default_map:
        default_map = os.path.join(pkg_path, "maps", "mapa_atual.yaml")
    # Caminho (sem extensão) onde o map_saver grava o mapa do gmapping.
    save_map_path = rospy.get_param(
        "~save_map_path", os.path.join(pkg_path, "maps", "mapa_atual")
    )

    initial_pose = {
        "x": float(rospy.get_param("~initial_pose_x", 0.0)),
        "y": float(rospy.get_param("~initial_pose_y", 0.0)),
        "a": float(rospy.get_param("~initial_pose_a", 0.0)),
    }
    # robot_radius deve ser >= tool_radius: no parseGrid do
    # full_coverage_path_planner os raios viram pixels uint32; tool > robot
    # causa underflow (robotNodeSize - nodeSize) e o planejador enxerga o mapa
    # inteiro como livre (caminhos através de paredes e fora do mapa).
    radius_params = {
        "robot": float(rospy.get_param("~robot_radius", 0.2)),
        "tool": float(rospy.get_param("~tool_radius", 0.18)),
    }

    use_current_pose = bool(rospy.get_param("~use_current_pose", True))
    frames = {
        "map": rospy.get_param("~map_frame", "map"),
        "base": rospy.get_param("~base_frame", "base_footprint"),
    }

    selector = ModeSelector(manual_launch, auto_launch, frames, use_current_pose)

    # Encerra o modo atual de forma limpa também em SIGTERM (roslaunch shutdown),
    # além do SIGINT/KeyboardInterrupt tratado no loop.
    def _on_term(signum, frame):
        selector.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _on_term)

    tty = _open_tty()
    try:
        menu = (
            "\nA base (Gazebo + Kobuki + Kinect + RViz) sobe pelo launch principal.\n"
            "Escolha o modo:\n"
            "  1 - Manual (mapeamento com gmapping; teleop em outro terminal)\n"
            "  s - Salvar mapa atual (durante o modo manual)\n"
            "  2 - Automático (aspiração por cobertura)\n"
            "  q - Sair do menu (Ctrl+C no launch principal encerra a simulação)\n"
        )
        sys.stdout.write(menu)
        sys.stdout.flush()
        while not rospy.is_shutdown():
            choice = _prompt(tty, "modo [1/s/2/q]> ").lower()

            if choice in ("1", "manual", "m"):
                selector.start_manual()
            elif choice in ("s", "salvar", "save"):
                selector.save_map(save_map_path)
            elif choice in ("2", "auto", "a"):
                map_path = _prompt(
                    tty,
                    "Mapa .yaml para aspiração (ENTER para o padrão {}): ".format(default_map),
                )
                if not map_path:
                    map_path = default_map
                mapa_fechado = _preferir_mapa_fechado(map_path)
                if mapa_fechado != map_path:
                    sys.stdout.write(
                        "Usando a versão fechada do mapa: {}\n".format(mapa_fechado)
                    )
                    sys.stdout.flush()
                selector.start_auto(mapa_fechado, initial_pose, radius_params)
            elif choice in ("q", "quit", "sair", "exit"):
                break
            elif choice == "":
                time.sleep(0.2)
            else:
                sys.stdout.write("Opção inválida.\n")
                sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    finally:
        selector.shutdown()


if __name__ == "__main__":
    main()
