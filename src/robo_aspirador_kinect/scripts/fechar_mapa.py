#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera a versão "fechada" de um mapa salvo pelo map_saver:
<nome>.pgm/.yaml -> <nome>_fechado.pgm/.yaml, pintando de PRETO (ocupado) todo
pixel que não é comprovadamente LIVRE (branco).

Por quê: o full_coverage_path_planner (SpiralSTC) só considera obstáculo a
célula OCUPADA (occupancy > 65). Célula DESCONHECIDA (-1, cinza no PGM) conta
como espaço livre. Como o mapa do gmapping é parcial, há fronteiras onde o
espaço livre encosta direto no cinza — e o caminho de cobertura "vaza" por ali,
atravessando paredes e saindo do mapa. Fechando o mapa (cinza -> preto), a
cobertura fica confinada ao que foi realmente mapeado como livre.

Uso:
    rosrun robo_aspirador_kinect fechar_mapa.py /caminho/para/mapa_atual.yaml
    (aceita também o caminho sem extensão ou do .pgm)
"""
import os
import sys

# map_saver (modo trinário): livre=254, ocupado=0, desconhecido=205.
# Mantém livre só o que é branco (>=250); o resto vira preto (ocupado).
_LUT = bytes(254 if v >= 250 else 0 for v in range(256))


def _parse_pgm_header(data):
    """Retorna (offset do início dos pixels, largura, altura). Formato P5."""
    tokens = []
    i = 0
    while len(tokens) < 4:
        if data[i:i + 1] == b"#":  # comentário até o fim da linha
            i = data.index(b"\n", i) + 1
            continue
        if data[i:i + 1].isspace():
            i += 1
            continue
        j = i
        while not data[j:j + 1].isspace():
            j += 1
        tokens.append(data[i:j])
        i = j
    if tokens[0] != b"P5":
        raise ValueError("PGM não é binário (P5): {}".format(tokens[0]))
    return i + 1, int(tokens[1]), int(tokens[2])


def fechar_mapa(map_path_no_ext):
    pgm_in = map_path_no_ext + ".pgm"
    yaml_in = map_path_no_ext + ".yaml"
    out_no_ext = map_path_no_ext + "_fechado"
    pgm_out = out_no_ext + ".pgm"
    yaml_out = out_no_ext + ".yaml"

    with open(pgm_in, "rb") as f:
        data = f.read()
    pix_off, _, _ = _parse_pgm_header(data)
    with open(pgm_out, "wb") as f:
        f.write(data[:pix_off])
        f.write(data[pix_off:].translate(_LUT))

    # Copia o yaml trocando apenas a linha da imagem (caminho relativo: o
    # map_server resolve em relação ao diretório do próprio yaml).
    with open(yaml_in, "r") as f:
        lines = f.readlines()
    with open(yaml_out, "w") as f:
        for line in lines:
            if line.startswith("image:"):
                f.write("image: {}\n".format(os.path.basename(pgm_out)))
            else:
                f.write(line)
    return yaml_out


def _normalize(path):
    for ext in (".yaml", ".pgm"):
        if path.endswith(ext):
            return path[: -len(ext)]
    return path


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write(__doc__ + "\n")
        sys.exit(1)
    out = fechar_mapa(_normalize(sys.argv[1]))
    print("Mapa fechado gravado em: {}".format(out))
