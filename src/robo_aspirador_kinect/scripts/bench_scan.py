#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Benchmark leve do /scan derivado do Kinect (depth vs. cloud).

Mede, ao longo de ~duration_sec, o LaserScan publicado em /scan:
  - Rate     : Hz efetivo (msgs recebidas / duracao real).
  - Latencia : idade do scan ao chegar no subscriber (now - header.stamp),
               media + p50/p95, em ms.
  - Qualidade: % de feixes com range FINITO dentro de [range_min, range_max].
  - Angular  : cobertura (angle_max - angle_min) e numero de feixes.

Uso (com a base ja no ar via bringup_sim.launch):
    rosrun robo_aspirador_kinect bench_scan.py _duration_sec:=30

Compare rodando a base com scan_source:=depth e depois scan_source:=cloud.
Nao escreve arquivos: imprime o resumo no stdout (facil de copiar).
"""

from __future__ import print_function

import math

import rospy
from sensor_msgs.msg import LaserScan


def percentile(sorted_values, pct):
    """Percentil linear simples sobre uma lista JA ordenada."""
    if not sorted_values:
        return float("nan")
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return sorted_values[low]
    frac = rank - low
    return sorted_values[low] * (1.0 - frac) + sorted_values[high] * frac


class ScanBenchmark(object):
    def __init__(self):
        rospy.init_node("bench_scan", anonymous=True)

        self._scan_topic = rospy.get_param("~scan_topic", "/scan")
        self._duration = float(rospy.get_param("~duration_sec", 30.0))

        self._latencies_ms = []
        self._valid_ratios = []
        self._count = 0
        self._first_stamp = None
        self._last_stamp = None
        self._angle_span = None
        self._num_beams = None

        rospy.Subscriber(self._scan_topic, LaserScan, self._cb, queue_size=50)
        rospy.loginfo(
            "bench_scan: coletando %s por %.1f s...", self._scan_topic, self._duration
        )

    def _cb(self, msg):
        now = rospy.Time.now()
        if self._first_stamp is None:
            self._first_stamp = now
        self._last_stamp = now
        self._count += 1

        latency_ms = (now - msg.header.stamp).to_sec() * 1000.0
        self._latencies_ms.append(latency_ms)

        rmin = msg.range_min
        rmax = msg.range_max
        total = len(msg.ranges)
        if total > 0:
            valid = 0
            for r in msg.ranges:
                if not math.isinf(r) and not math.isnan(r) and rmin <= r <= rmax:
                    valid += 1
            self._valid_ratios.append(100.0 * valid / total)

        self._angle_span = msg.angle_max - msg.angle_min
        self._num_beams = total

    def run(self):
        rate = rospy.Rate(2.0)
        start = rospy.Time.now()
        while not rospy.is_shutdown():
            if (rospy.Time.now() - start).to_sec() >= self._duration:
                break
            rate.sleep()
        self._report()

    def _report(self):
        print("")
        print("==================== bench_scan ====================")
        print("topico            : %s" % self._scan_topic)
        print("duracao alvo      : %.1f s" % self._duration)

        if self._count == 0:
            print("NENHUMA mensagem recebida. A base esta no ar? /scan publica?")
            print("====================================================")
            return

        elapsed = (self._last_stamp - self._first_stamp).to_sec()
        hz = (self._count - 1) / elapsed if elapsed > 0 else float("nan")

        lat = sorted(self._latencies_ms)
        lat_avg = sum(lat) / len(lat)

        if self._valid_ratios:
            valid_avg = sum(self._valid_ratios) / len(self._valid_ratios)
        else:
            valid_avg = float("nan")

        print("mensagens         : %d" % self._count)
        print("janela medida     : %.2f s" % elapsed)
        print("rate efetivo      : %.2f Hz" % hz)
        print("latencia media    : %.1f ms" % lat_avg)
        print("latencia p50      : %.1f ms" % percentile(lat, 50))
        print("latencia p95      : %.1f ms" % percentile(lat, 95))
        print("feixes validos    : %.1f %%" % valid_avg)
        if self._angle_span is not None:
            print(
                "cobertura angular : %.1f deg (%d feixes)"
                % (math.degrees(self._angle_span), self._num_beams or 0)
            )
        print("====================================================")


if __name__ == "__main__":
    try:
        ScanBenchmark().run()
    except rospy.ROSInterruptException:
        pass
