class alt2(object):
    def __init__(self, args):
        self.AD_decision = {}
        self.L = args['L']
        self.H = args['H']
        self.C = args['server']
        # AD 조건: 대기 중인 모든 환자들을 치료하는 데 소요되는 예상시간 > RULE_AD 시간
        # OPEN 조건: AD 후 RULE_OPEN 시간 경과 후

    def reset(self):
        self.AD_decision = {}
        for i in range(self.H):
            self.AD_decision["x, %d, %d" % (i, 0)] = 1
            self.AD_decision["y, %d, %d" % (i, 0)] = 1

    def run_alt2(self, args, t, pat_waiting):
        t2day = lambda x: x % (1440 // args['time_unit'])
        for i in range(self.H):
            if t > 0:
                # 응급환자 먼저
                # # AD 지속시간 체크: H-AD 중인데 지속기간이 rule2_open_urg를 못채웠으면 계속 AD 시킴
                if (sum(self.AD_decision["x, %d, %d" % (i, t2)] for t2 in range(max(t - args['rule2_open_urg'], 0), t)) != 0 or t < args['rule2_open_urg']) \
                        and self.AD_decision["x, %d, %d" % (i, t - 1)] == 0:
                    self.AD_decision["x, %d, %d" % (i, t)] = 0
                # # AD 조건 체크: '응급'환자 다 빠져나가는 예상 소요시간이 rule2_AD_urg를 초과하면 AD
                elif len(pat_waiting[0][i]) * args['avg_svc_t'][0] > self.C[i][t2day(t)] * args['time_unit'] * args['rule2_AD_urg']:
                    self.AD_decision["x, %d, %d" % (i, t)] = 0
                # # 위 두 조건에 해당안되면 OPEN
                else:
                    self.AD_decision["x, %d, %d" % (i, t)] = 1

                # 비응급환자
                # # H-AD 면 L-AD
                if self.AD_decision["x, %d, %d" % (i, t)] == 0:
                    self.AD_decision["y, %d, %d" % (i, t)] = 0
                # # AD 지속시간
                elif (sum(self.AD_decision["y, %d, %d" % (i, t2)] for t2 in range(max(t - args['rule2_open_nonurg'], 0), t)) != 0 or t < args['rule2_open_nonurg']) \
                        and self.AD_decision["y, %d, %d" % (i, t - 1)] == 0:
                    self.AD_decision["y, %d, %d" % (i, t)] = 0
                # # AD 조건
                elif sum(len(pat_waiting[l][i]) * args['avg_svc_t'][l] for l in range(self.L)) \
                        > self.C[i][t2day(t)] * args['time_unit'] * args['rule2_AD_nonurg']:
                    self.AD_decision["y, %d, %d" % (i, t)] = 0
                # # 위 세 조건에 해당안되면 OPEN
                else:
                    self.AD_decision["y, %d, %d" % (i, t)] = 1

        return self.AD_decision
