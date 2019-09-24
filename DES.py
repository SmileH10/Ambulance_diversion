import numpy as np


class DES(object):
    def __init__(self, args):
        # args
        self.T = args['T']
        self.H = args['H']
        self.L = args['L']
        self.tp = args['time_planning']
        self.time_unit = args['time_unit']
        self.t2day = lambda x: x % (1440 // args['time_unit'])
        self.avg_svc_t = args['avg_svc_t']

        # data
        self.dist = args['unit_distance']
        self.traveling_t = args['traveling_t']
        self.C = args['server']
        self.reset()

    def reset(self):
        self.cur_t = 0

        # 시뮬레이션 변수
        self.sim_t = 0.0
        # # 작업이 마치는대로 closed 되어야 하는 서버 수
        self.to_be_closed = [max(self.C[i]) - self.C[i][0] for i in range(self.H)]
        # # 현 시점에 open 되어야 하는 서버 수
        self.to_be_opened = [0 for i in range(self.H)]
        # # 병원 도착예정환자 리스트
        self.pat_scheduled = [[[] for i in range(self.H)] for l in range(self.L)]
        # # 병원에 대기중인 환자 리스트
        self.pat_waiting = [[[] for i in range(self.H)] for l in range(self.L)]
        # 병원 서버별 치료 중인 환자 리스트
        self.pat_in_svc = [["None" for c in range(max(self.C[i]))] for i in range(self.H)]
        # # 서버별 상태("closed", "idle") 및 치료 중인 환자의 치료 종료 시간(minutes)
        self.svr_comp_t = [["idle" for _ in range(max_svr)] for max_svr in np.max(self.C, axis=1)]

        # 시뮬레이션 결과 기록
        self.pat_comp = [[] for i in range(self.H)]
        self.sim_result = {}
        self.sim_result['lambda'] = [[[0 for t in range(self.T + self.tp)] for i in range(self.H)] for l in range(self.L)]
        self.sim_result['mu'] = [[[0 for t in range(self.T + self.tp)] for i in range(self.H)] for l in range(self.L)]
        self.sim_result['n'] = [[[0 for t in range(self.T + self.tp)] for i in range(self.H)] for l in range(self.L)]
        self.sim_result['congestion'] = [[0 for t in range(self.T + self.tp)] for i in range(self.H)]
        self.sim_result['pat_amb_hist'] = [[[0 for t in range(self.T)] for i in range(self.H)] for l in range(self.L)]
        self.sim_result['pat_walk_hist'] = [[[0 for t in range(self.T)] for i in range(self.H)] for l in range(self.L)]
        self.sim_tard = [[[0.0 for t in range(self.T + self.tp)] for i in range(self.H)] for l in range(self.L)]
        self.sim_traveling_t = [[[0.0 for t in range(self.T)] for i in range(self.H)] for l in range(self.L)]
        self.sim_total_tard = 0.0
        self.pat_info = {}
        self.svr_open_t = {}
        self.svr_busy_t = {}
        self.sim_svr_util = {}
        self.num_pat_over_thd = [0, 0]
        self.sim_tard_over_thd = [0.0, 0.0]

    def run_one_time_simulation(self, AD_decision, w, args):
        self.pat_amb = args['pat_amb'][w]
        self.pat_walk = args['pat_walk'][w]
        self.svc_t = args['svc_t'][w]

        self.update_open_close()
        self.update_pat_scheduled_for_arr(AD_decision)
        for i in range(self.H):
            while True:
                self.next_event(i)
                if self.sim_t >= (self.cur_t + 1) * self.time_unit:  # 시뮬레이션 종료조건
                    break
                if self.event_index < self.L:
                    self.new_pat_arr_event(args, i)
                else:
                    self.svc_comp_event(args, i)
        self.calc_tardiness_t(args)
        self.t_increment()
        return self.sim_result

    def update_open_close(self):
        # server 수 변경된 경우 반영하기. 작업 중인 server는 작업을 다 마친 후 closed 시킴. (to_be_closed에 기록)
        for i in range(self.H):
            if self.cur_t > 0:
                self.to_be_closed[i] += max(0, self.C[i][self.t2day(self.cur_t) - 1] - self.C[i][self.t2day(self.cur_t)])
                self.to_be_opened[i] += max(0, self.C[i][self.t2day(self.cur_t)] - self.C[i][self.t2day(self.cur_t) - 1])
            self.to_be_opened[i] -= min(self.to_be_opened[i], self.to_be_closed[i])
            self.to_be_closed[i] -= min(self.to_be_opened[i], self.to_be_closed[i])
            if self.to_be_opened[i] > 0:
                for c in range(max(self.C[i])):
                    if self.svr_comp_t[i][c] == "closed":  # float("inf"): 대기 중, (T + Time_planning) *Time_unit: closed.
                        self.svr_comp_t[i][c] = "idle"
                        self.to_be_opened[i] -= 1
                        if self.to_be_opened[i] == 0:
                            break
            if self.to_be_closed[i] > 0:
                for c in range(max(self.C[i])):
                    if self.svr_comp_t[i][c] == "idle":  # float("inf"): 대기 중, (T + Time_planning) *Time_unit: closed.
                        self.svr_comp_t[i][c] = "closed"
                        self.to_be_closed[i] -= 1
                        if self.to_be_closed[i] == 0:
                            break
            for c in range(max(self.C[i])):
                if self.svr_comp_t[i][c] != "closed":
                    self.svr_open_t[(i, c)] = self.time_unit
                else:
                    self.svr_open_t[(i, c)] = 0
                self.svr_busy_t[(i, c)] = 0

    def update_pat_scheduled_for_arr(self, AD_decision):
        x = [float("inf") for i in range(self.H)]
        y = [float("inf") for i in range(self.H)]
        for i in range(self.H):
            x[i] = AD_decision["x, %d, %d" % (i, self.cur_t)]
            y[i] = AD_decision["y, %d, %d" % (i, self.cur_t)]
        if self.cur_t >= 1:
            for l in range(self.L):
                for i in range(self.H):
                    self.sim_result['n'][l][i][self.cur_t] += self.sim_result['n'][l][i][self.cur_t - 1]

        # t ~ t + 1 시점에 도착이 예정된 환자 생성 (AD 정책에 맞추어 각 병원 별로)
        # # 구급차로 온 환자
        for l in range(self.L):
            for i in range(self.H):
                self.sim_result['pat_amb_hist'][l][i][self.cur_t] += len(self.pat_amb[(l, i, self.cur_t)])
                for j in np.argsort(self.traveling_t[i]):
                    if (l == 0 and (x[j] == 1 or sum(x[i] for i in range(self.H)) == 0)) or\
                            (l == 1 and (y[j] == 1 or sum(y[i] for i in range(self.H)) == 0)):
                        for p in range(len(self.pat_amb[(l, i, self.cur_t)])):
                            self.pat_amb[(l, i, self.cur_t)][p].arr_t += self.traveling_t[i][j]
                            self.pat_amb[(l, i, self.cur_t)][p].j = j
                        self.pat_scheduled[l][j] += self.pat_amb[(l, i, self.cur_t)]
                        # 출력용 결과 기록
                        self.sim_traveling_t[l][i][self.cur_t] += self.traveling_t[i][j] * len(self.pat_amb[(l, i, self.cur_t)])
                        self.sim_result['n'][l][j][self.cur_t + self.dist[i][j]] += len(self.pat_amb[(l, i, self.cur_t)])
                        self.sim_result['lambda'][l][j][self.cur_t + self.dist[i][j]] += len(self.pat_amb[(l, i, self.cur_t)])
                        break

        # # 도보로 온 환자
        for l in range(self.L):
            for i in range(self.H):
                self.pat_scheduled[l][i] += self.pat_walk[(l, i, self.cur_t)]
                self.sim_result['n'][l][i][self.cur_t] += len(self.pat_walk[(l, i, self.cur_t)])
                self.sim_result['lambda'][l][i][self.cur_t] += len(self.pat_walk[(l, i, self.cur_t)])
                self.sim_result['pat_walk_hist'][l][i][self.cur_t] += len(self.pat_walk[(l, i, self.cur_t)])

        # # 환자 도착 시간 빠른 순 정렬
        for l in range(self.L):
            for i in range(self.H):
                self.pat_scheduled[l][i].sort(key=lambda x: x.arr_t)

    def next_event(self, i):
        # 다음 event 시간: 1) 새로운 환자 도착, 2) server 중 하나가 작업 마침
        pat_arr_event = lambda x: [x[l][i][0].arr_t if len(x[l][i]) > 0 else float("inf") for l in range(self.L)]
        event_time_candidate = pat_arr_event(self.pat_scheduled) + [self.svr_comp_t[i][c] for c in range(max(self.C[i]))]
        str2inf = lambda x: [float("inf") if type(x[i])==str else x[i] for i in range(len(x))]
        self.event_index = np.argmin(str2inf(event_time_candidate))
        self.sim_t = np.min(str2inf(event_time_candidate))

    def new_pat_arr_event(self, args, i):
        event_l = self.event_index
        if any(self.svr_comp_t[i][c] == "idle" for c in range(max(self.C[i]))):  # idle server가 있는 경우
            # idle_svr index 저장
            idle_svr = self.svr_comp_t[i].index("idle")
            # 치료 종료시간 입력
            if not self.svc_t[(event_l, i, self.cur_t)]:
                if args['prob_dist'] == 'exp':
                    self.svc_t[(event_l, i, self.cur_t)].append(np.random.exponential(self.avg_svc_t[event_l]))
                elif args['prob_dist'] == 'tri':
                    self.svc_t[(event_l, i, self.cur_t)].append(np.random.triangular(self.avg_svc_t[event_l] - args['tri_range'][event_l],
                                                                                     self.avg_svc_t[event_l],
                                                                                     self.avg_svc_t[event_l] + args['tri_range'][event_l]))
                elif args['prob_dist'] == 'norm':
                    self.svc_t[(event_l, i, self.cur_t)].append(np.random.normal(self.avg_svc_t[event_l], args['norm_std'][event_l]))

            self.svr_comp_t[i][idle_svr] = self.sim_t + self.svc_t[(event_l, i, self.cur_t)][0]
            del self.svc_t[(event_l, i, self.cur_t)][0]
            # 환자를 pat_in_svc 로 이동
            self.pat_in_svc[i][idle_svr] = (self.pat_scheduled[event_l][i][0])
            self.pat_in_svc[i][idle_svr].svc_start_t = self.sim_t
        else:  # idle server가 없는 경우, 대기열에 추가
            self.pat_waiting[event_l][i].append(self.pat_scheduled[event_l][i][0])
        del self.pat_scheduled[event_l][i][0]  # 도착예정환자 리스트에서 환자 삭제

    def svc_comp_event(self, args, i):
        # 서비스 종료 svr의 index를 idle_svr에 저장
        idle_svr = self.event_index - self.L
        # 환자의 종료시간, 병원내 환자수(n)/빠져나간환자수(mu) 기록
        self.pat_in_svc[i][idle_svr].comp_t = self.sim_t
        self.svr_busy_t[(i, idle_svr)] += (self.sim_t - max(self.cur_t * self.time_unit, self.pat_in_svc[i][idle_svr].svc_start_t))
        self.sim_result['n'][self.pat_in_svc[i][idle_svr].l][i][self.cur_t] -= 1
        self.sim_result['mu'][self.pat_in_svc[i][idle_svr].l][i][self.cur_t] += 1
        # svr close/idle로 상태반영
        if self.to_be_closed[i] > 0:
            self.svr_comp_t[i][idle_svr] = "closed"
            self.to_be_closed[i] -= 1
            self.svr_open_t[(i, idle_svr)] = self.sim_t - (self.cur_t * self.time_unit)
        else:
            self.svr_comp_t[i][idle_svr] = "idle"
        # 환자를 pat_comp로 이동
        self.pat_comp[i].append(self.pat_in_svc[i][idle_svr])
        self.pat_in_svc[i][idle_svr] = "None"

        # # 대기 중인 환자 있나 확인
        if self.svr_comp_t[i][idle_svr] != "closed":
            for l in range(self.L):  # 응급환자부터 대기열 확인
                if self.pat_waiting[l][i] != []:  # 대기 중인 환자가 있다면
                    # 치료 종료시간 입력
                    if not self.svc_t[(l, i, self.cur_t)]:
                        if args['prob_dist'] == 'exp':
                            self.svc_t[(l, i, self.cur_t)].append(np.random.exponential(self.avg_svc_t[l]))
                        elif args['prob_dist'] == 'tri':
                            self.svc_t[(l, i, self.cur_t)].append(np.random.triangular(self.avg_svc_t[l] - args['tri_range'][l],
                                                                                       self.avg_svc_t[l],
                                                                                       self.avg_svc_t[l] + args['tri_range'][l]))
                        elif args['prob_dist'] == 'norm':
                            self.svc_t[(l, i, self.cur_t)].append(np.random.normal(self.avg_svc_t[l], args['norm_std'][l]))

                    self.svr_comp_t[i][idle_svr] = self.sim_t + self.svc_t[(l, i, self.cur_t)][0]
                    del self.svc_t[(l, i, self.cur_t)][0]
                    # 환자를 pat_in_svc로 이동
                    self.pat_in_svc[i][idle_svr] = self.pat_waiting[l][i][0]
                    self.pat_in_svc[i][idle_svr].svc_start_t = self.sim_t
                    del self.pat_waiting[l][i][0]
                    # 대기 환자 1명만 치료
                    break

    def t_increment(self):
        self.cur_t += 1

    def calc_tardiness_t(self, args):
        # sim_tard 기록
        self.sim_t = (self.cur_t + 1) * self.time_unit
        for i in range(self.H):
            for pat in self.pat_comp[i]:
                pat.calc_tard_t(self.cur_t, pat.comp_t)
                if self.cur_t >= args['warmup_period']:
                    if pat.pat_tard > 0:
                        self.sim_tard_over_thd[pat.l] += pat.pat_tard
                        self.num_pat_over_thd[pat.l] += 1
                    self.sim_tard[pat.l][i][self.cur_t] += pat.pat_tard_t
                    self.pat_info[(pat.id, pat.l, pat.i, pat.j, self.cur_t)] \
                        = (pat.occ_t, pat.arr_t, pat.svc_start_t, pat.comp_t,
                           pat.arr_t - pat.occ_t, pat.svc_start_t - pat.arr_t, pat.comp_t - pat.svc_start_t, pat.comp_t - pat.occ_t)
                self.pat_comp[i] = []
            for pat in self.pat_in_svc[i]:
                if pat != "None":
                    pat.calc_tard_t(self.cur_t, self.sim_t)
                    if self.cur_t >= args['warmup_period']:
                        self.sim_tard[pat.l][i][self.cur_t] += pat.pat_tard_t
            for l in range(self.L):
                for pat in self.pat_waiting[l][i]:
                    pat.calc_tard_t(self.cur_t, self.sim_t)
                    if self.cur_t >= args['warmup_period']:
                        self.sim_tard[pat.l][i][self.cur_t] += pat.pat_tard_t
            # utilization 기록
            for c in range(max(self.C[i])):
                if self.svr_comp_t[i][c] != "closed" and self.svr_comp_t[i][c] != "idle":
                    self.svr_busy_t[(i, c)] += self.sim_t - max(self.cur_t * self.time_unit, self.pat_in_svc[i][c].svc_start_t)
                if self.svr_open_t[(i, c)] > 0:
                    self.sim_svr_util["%d, %d, %d" % (i, self.cur_t, c)] = self.svr_busy_t[(i, c)] / self.svr_open_t[(i, c)]
                else:
                    self.sim_svr_util["%d, %d, %d" % (i, self.cur_t, c)] = "closed"

        # 혼잡도 기록
        for i in range(self.H):
            self.sim_result['congestion'][i][self.cur_t] = sum(
                (len(self.pat_waiting[l][i]) + sum(1 for pat in self.pat_in_svc[i] if pat != "None")) * self.avg_svc_t[l]
                for l in range(self.L)) / (self.C[i][self.t2day(self.cur_t)] * self.time_unit)
