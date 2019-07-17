class alt1(object):
    def __init__(self, args):
        self.AD_decision = {}
        self.L = args['L']
        self.H = args['H']
        self.C = args['server']
        # AD 조건: 대기 중인 모든 환자들을 치료하는 데 소요되는 예상시간 > RULE_AD 시간
        # OPEN 조건: 대기 중인 모든 환자들을 치료하는 데 소요되는 예상시간 < RULE_OPEN 시간

    def reset(self):
        self.AD_decision = {}
        for i in range(self.H):
            self.AD_decision["x, %d, %d" % (i, 0)] = 1
            self.AD_decision["y, %d, %d" % (i, 0)] = 1

    def run_alt1(self, args, t, pat_waiting):
        t2day = lambda x: x % (1440 // args['time_unit'])
        for i in range(self.H):
            # 응급환자에 대해서 먼저 결정
            # # AD조건: '응급'환자 다 빠져나가는 예상 소요시간이 rule1_AD_urg 초과하면 H-AD
            if len(pat_waiting[0][i]) * args['avg_svc_t'][0] > self.C[i][t2day(t)] * args['time_unit'] * args['rule1_AD_urg']:
                self.AD_decision["x, %d, %d" % (i, t)] = 0
            # # OPEN 조건: '응급'환자 다 빠져나가는 예상 소요시간이 rule1_open_urg 미만이면 H-OPEN
            elif len(pat_waiting[0][i]) * args['avg_svc_t'][0] < self.C[i][t2day(t)] * args['time_unit'] * args['rule1_open_urg']:
                self.AD_decision["x, %d, %d" % (i, t)] = 1
            # # 둘 다 해당안되며 직전 시점 상태 유지
            else:
                self.AD_decision["x, %d, %d" % (i, t)] = self.AD_decision["x, %d, %d" % (i, t - 1)]

            # 비응급환자 결정
            # # H-AD면 L-AD 시킴.
            if self.AD_decision["x, %d, %d" % (i, t)] == 0:
                self.AD_decision["y, %d, %d" % (i, t)] = 0
            # # AD조건: '모든' 환자 다 빠져나가는 예상 소요시간이 rule1_AD_nonurg 초과하면 L-AD
            elif sum(len(pat_waiting[l][i]) * args['avg_svc_t'][l] for l in range(self.L)) \
                    > self.C[i][t2day(t)] * args['time_unit'] * args['rule1_AD_nonurg']:
                self.AD_decision["y, %d, %d" % (i, t)] = 0
            # # OPEN 조건: '모든' 환자 다 빠져나가는 예상 소요시간이 rule1_open_nonurg 미만이면 OPEN
            elif sum(len(pat_waiting[l][i]) * args['avg_svc_t'][l] for l in range(self.L)) \
                    < self.C[i][t2day(t)] * args['time_unit'] * args['rule1_open_nonurg']:
                self.AD_decision["y, %d, %d" % (i, t)] = 1
            # # 둘 다 해당안되며 직전 시점 상태 유지
            else:
                self.AD_decision["y, %d, %d" % (i, t)] = self.AD_decision["y, %d, %d" % (i, t - 1)]
        return self.AD_decision