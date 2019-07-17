import sys
import os
import numpy as np
from copy import deepcopy

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from DES import DES


class DES_SAA(DES):
    def __init__(self, args, cur_t):
        super().__init__(args)
        self.cur_t = cur_t

    def update_pat_scheduled_for_arr(self, AD_decisions):
        x = [[float("inf") for t in range(self.tp)] for i in range(self.H)]
        y = [[float("inf") for t in range(self.tp)] for i in range(self.H)]
        for i in range(self.H):
            for t in range(self.tp):
                x[i][t] = AD_decisions["x, %d, %d" % (i, self.cur_t + t)]
                y[i][t] = AD_decisions["y, %d, %d" % (i, self.cur_t + t)]
        # t ~ t + 1 시점에 도착이 예정된 환자 생성 (AD 정책에 맞추어 각 병원 별로)
        # # 구급차로 온 환자
        for l in range(self.L):
            for i in range(self.H):
                for j in np.argsort(self.dist[i]):
                    for t in range(self.tp):
                        if (l == 0 and (x[j][t] == 1 or sum(x[i][t] for i in range(self.H)) == 0)) or \
                                (l == 1 and (y[j][t] == 1 or sum(y[i][t] for i in range(self.H)) == 0)):
                            for p in range(len(self.pat_amb[(l, i, self.cur_t + t)])):
                                self.pat_amb[(l, i, self.cur_t + t)][p].arr_t += self.dist[i][j] * self.time_unit
                            self.pat_scheduled[l][j] += self.pat_amb[(l, i, self.cur_t + t)]
                            break

        # # 도보로 온 환자
        for l in range(self.L):
            for i in range(self.H):
                for t in range(self.tp):
                    self.pat_scheduled[l][i] += self.pat_walk[(l, i, self.cur_t + t)]
        # # 환자 도착 시간 빠른 순 정렬
        for l in range(self.L):
            for i in range(self.H):
                self.pat_scheduled[l][i].sort(key=lambda x: x.arr_t)

    def run_tp_time_simulation(self, AD_decisions, s2, args):
        self.pat_amb = deepcopy(args['s_pat_amb'][s2])
        self.pat_walk = deepcopy(args['s_pat_walk'][s2])
        self.svc_t = deepcopy(args['s_svc_t'][s2])
        self.temp_sim_tard = [0 for t in range(self.tp)]

        self.update_open_close()
        self.update_pat_scheduled_for_arr(AD_decisions)
        for t in range(self.tp):
            for i in range(self.H):
                while True:
                    self.next_event(i)
                    if self.sim_t >= (self.cur_t + 1) * self.time_unit:  # 시뮬레이션 종료조건
                        break
                    if self.event_index < self.L:
                        self.new_pat_arr_event(i)
                    else:
                        self.svc_comp_event(i)
            self.calc_tardiness_t()
            self.temp_sim_tard[t] = sum(self.sim_tard[l][i][self.cur_t] for l in range(self.L) for i in range(self.H))
            self.cur_t = self.cur_t + 1
        return np.sum(self.temp_sim_tard)
