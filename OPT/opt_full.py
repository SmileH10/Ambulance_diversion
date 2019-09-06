from gurobipy import *
import numpy as np
from dataIO import write_data


class Opt(object):
    def __init__(self, args):
        self.H = args['H']
        self.L = args['L']
        self.tp = args['time_planning']
        self.thd = args['thd']
        self.time_unit = args['time_unit']
        self.dist = args['unit_distance']
        self.traveling_t = args['traveling_t']
        self.d_amb = args['d_amb']
        self.d_walk = args['d_walk']
        self.avg_svc_t = args['avg_svc_t']
        self.C = args['server']

        self.t2day = lambda x: x % (1440 // args['time_unit'])

        self.alpha = args['alpha']
        self.coef_mu = args['coef_mu']
        self.beta = args['beta']

        self.AD_decision = {}

    def reset(self):
        # 결과 기록
        self.AD_decision = {}

    def run_opt(self, args, cur_t, sim_result, outputflag=False):
        # index
        Hs = tuplelist(range(self.H))  # [0,1,2]
        Ts = tuplelist(range(cur_t + self.tp))
        Ls = tuplelist(range(self.L))

        # Creat a new model
        m = Model("opt_AD")

        # m.setParam('TimeLimit', 30 * 60)  # 시간 제한
        if not outputflag:
            m.setParam('OutputFlag', False)  # Quieting Gurobi output

        # Creat variables
        x = m.addVars(Hs, Ts, vtype=GRB.BINARY, name='x')
        y = m.addVars(Hs, Ts, vtype=GRB.BINARY, name='y')
        z = m.addVars(Hs, Ts, vtype=GRB.BINARY, name='z')  # 응급환자가 대기열에 있으면 0, 없으면 1
        n = m.addVars(Ls, Hs, Ts, name='n')

        Ts2 = tuplelist(range(-np.max(self.dist), cur_t + self.tp))
        f = m.addVars(Ls, Hs, Hs, Ts2, vtype=GRB.BINARY, name='f')
        lamda = m.addVars(Ls, Hs, Ts, name='lambda')
        mu = m.addVars(Ls, Hs, Ts, name='mu')
        ConstBigM = 100.0
        obj1 = m.addVars(Ls, Hs, Ts, name='obj1')
        # Integrate new variables
        m.update()

        # Set objective
        # 실제 병원으로 들어오는 환자 수 lambda 결정
        m.setObjective((self.alpha * quicksum(obj1[l, i, t] for l in Ls for i in Hs for t in Ts if t >= self.thd[l] and t >= cur_t)
                        - self.coef_mu * quicksum(mu[l, i, t] for l in Ls for i in Hs for t in Ts if t >= cur_t)
                        + self.beta * quicksum(self.traveling_t[i][j] * f[l, i, j, t] * self.d_amb[l][i][self.t2day(t)]
                                               for l in Ls for i in Hs for j in Hs for t in Ts if t >= cur_t)
                        ), GRB.MINIMIZE)

        # Add constraint
        m.addConstrs((obj1[l, i, t] >=
                      quicksum(quicksum(f[l, j, i, t2] * self.d_amb[l][j][self.t2day(t2)] for j in Hs) + self.d_walk[l][i][self.t2day(t2)]
                               for t2 in Ts if cur_t <= t2 < t - self.thd[l])
                      + quicksum(quicksum(f[l, j, i, t2] * sim_result['pat_amb_hist'][l][j][t2] for j in Hs) + sim_result['pat_walk_hist'][l][i][t2]
                                 for t2 in Ts if t2 < t - self.thd[l] and t2 < cur_t)
                      - quicksum(mu[l, i, t2] for t2 in Ts if t2 <= t)
                      for l in Ls for i in Hs for t in Ts if t >= self.thd[l] and t >= cur_t), name='obj1')

        # 과거 상황(t < current_t) 입력: lambda, mu, AD
        m.addConstrs((lamda[l, i, t] == sim_result['lambda'][l][i][t] for l in Ls for i in Hs for t in Ts if t < cur_t))
        m.addConstrs((mu[l, i, t] == sim_result['mu'][l][i][t] for l in Ls for i in Hs for t in Ts if t < cur_t))
        m.addConstrs((n[l, i, t] == sim_result['n'][l][i][t] for l in Ls for i in Hs for t in Ts if t < cur_t))
        m.addConstrs((x[i, t] == self.AD_decision["x, %d, %d" % (i, t)] for i in Hs for t in Ts if t < cur_t))
        m.addConstrs((y[i, t] == self.AD_decision["y, %d, %d" % (i, t)] for i in Hs for t in Ts if t < cur_t))

        # # 여기서부터 미래 상황(t >= current_t) 예측을 통한 의사결정 제약식
        # 자기 병원 열었으면 자기 병원 수요는 모두 자기 병원으로
        m.addConstrs((f[1, i, i, t] == y[i, t] for i in Hs for t in Ts), name='Constr1')
        m.addConstrs((f[0, i, i, t] == x[i, t] for i in Hs for t in Ts), name='Constr2')
        # 이송할 다른 병원이 열려있어야 이송 가능
        m.addConstrs((f[1, j, i, t] <= y[i, t] for j in Hs for i in Hs if j != i for t in Ts), name='Constr3')
        m.addConstrs((f[0, j, i, t] <= x[i, t] for j in Hs for i in Hs if j != i for t in Ts), name='Constr4')
        # 어떤 병원의 수요는 오직 1개 병원으로만 가야함
        m.addConstrs((quicksum(f[l, i, j, t] for j in Hs) == 1 for l in Ls for i in Hs for t in Ts), name='Constr5')
        # 가까운 병원 순으로 할당
        m.addConstrs((f[1, i, j, t] - f[1, i, j2, t] >= y[j, t] + y[j2, t] - 2 for i in Hs for j in Hs for j2 in Hs for t in Ts
                      if j != i if j2 != i if self.traveling_t[i][j] < self.traveling_t[i][j2]), name='Constr6')
        m.addConstrs((f[0, i, j, t] - f[0, i, j2, t] >= x[j, t] + x[j2, t] - 2 for i in Hs for j in Hs for j2 in Hs for t in Ts
                      if j != i if j2 != i if self.traveling_t[i][j] < self.traveling_t[i][j2]), name='Constr7')
        #
        m.addConstrs((f[l, i, j, t] == 0 for l in Ls for i in Hs for j in Hs for t in Ts2 if t < 0), name='Constr8')
        # 응급환자 안받으면서 비응급환자만 받는 것 제한
        m.addConstrs((x[i, t] >= y[i, t] for i in Hs for t in Ts), name='Constr9')

        if cur_t >= 1:
            m.addConstrs((n[l, i, t] == n[l, i, t - 1] + lamda[l, i, t] - mu[l, i, t]
                          for t in Ts for l in Ls for i in Hs if t >= cur_t), name='Constr10')
        else:
            m.addConstrs((n[l, i, 0] == 0 for l in Ls for i in Hs), name='Constr11')

        # mu 결정
        m.addConstrs((z[i, t] <= 1 - n[0, i, t] / ConstBigM
                      for i in Hs for t in Ts if t >= cur_t), name='Constr12')
        m.addConstrs((mu[1, i, t] <= z[i, t] * ConstBigM for i in Hs for t in Ts if t >= cur_t), name='Constr13')
        m.addConstrs((quicksum(mu[l, i, t] * self.avg_svc_t[l] for l in Ls) <= self.C[i][self.t2day(t)] * self.time_unit
                      for i in Hs for t in Ts if t >= cur_t), name='Constr14')

        # 실제 병원으로 들어오는 환자 수 lambda 결정
        m.addConstrs((
            quicksum(f[l, j, i, t - self.dist[j][i]] * self.d_amb[l][j][self.t2day(t) - self.dist[j][i]] for j in Hs
                     if t - self.dist[i][j] >= cur_t)
            + quicksum(f[l, j, i, t - self.dist[j][i]] * sim_result['pat_amb_hist'][l][j][t - self.dist[j][i]] for j in Hs
                       if t - self.dist[i][j] < cur_t)
            + self.d_walk[l][i][self.t2day(t)] == lamda[l, i, t]
            for l in Ls for i in Hs for t in Ts if t >= cur_t and t >= np.max(self.dist)), name='Constr17')
        m.addConstrs(
            (self.d_walk[l][i][self.t2day(t)] == lamda[l, i, t] for l in Ls for i in Hs for t in Ts if cur_t <= t < np.max(self.dist)),
            name='Constr18')

        # # 동시에 모두 AD 상태 금지: 비응급환자는 받는데 응급환자는 AD하기 때문 (AAA, AAL, ALL, ALL 금지 > AAO, ALO, LLO)
        # # = 적어도 하나는 OPEN = 적어도 하나의 y는 1 (y가 1이면, x도 1이 되어 open이 됨)
        m.addConstrs((quicksum(y[i, t] for i in Hs) >= 1 for t in Ts), name='Constr19')

        # Compute optimal solution
        m.optimize()

        # Print solution
        if m.status == GRB.Status.OPTIMAL:
            AD_result_test = {}
            for v in m.getVars():
                var_split1 = v.var_Name.split('[')
                var_name = var_split1[0]
                var_index = var_split1[1].split(']')[0]
                # AD_result_test[v.var_Name] = v.x
                AD_result_test['%s, %s' % (var_name, var_index)] = v.x
            write_data(args, data=AD_result_test, filename='ADvar_t%d' % cur_t, head="variable, col1, col2, col3, col4, col5", AD_model=True)
            for i in Hs:
                self.AD_decision["x, %d, %d" % (i, cur_t)] = round(x[i, cur_t].x)
                self.AD_decision["y, %d, %d" % (i, cur_t)] = round(y[i, cur_t].x)
            return self.AD_decision
        else:
            print("m.status: ", m.status)
            print("NOT OPTIMAL")
