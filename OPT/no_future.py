class NoFuture(object):
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

    def run_nofuture(self, args, t, pat_waiting):
        t2day = lambda x: x % (1440 // args['time_unit'])
        for i in range(self.H):
            # 마지막 응급/비응급 환자 치료가 끝나는 시간 추정
            # end_time = 1) 현재시간(=t * args['time_unit'])
            # + 2) 마지막환자치료종료까지 예상소요시간(대기환자수 len(pat_waiting) * 평균치료시간 'avg_svc_t' / 서버수 C)
            end_time = [0, 0]
            end_time[0] = t * args['time_unit'] \
                          + len(pat_waiting[0][i]) * args['avg_svc_t'][0] / self.C[i][t2day(t)]
            end_time[1] = t * args['time_unit'] \
                          + sum(len(pat_waiting[l][i]) * args['avg_svc_t'][l] for l in range(self.L)) / self.C[i][t2day(t)]
            max_tard = 0
            decision_made = 0
            for p in range(len(pat_waiting[0][i])):
                tard = max(0, end_time[0] - pat_waiting[0][i][p].occ_t - args['thd'][0] * args['time_unit'])
                if tard > max_tard:
                    max_tard = tard
                    # 응급환자 중 최대 tardiness 가지는 사람의 tardiness 가 delta(penalty) 이상이면 All-AD
                    if max_tard / args['time_unit'] > args['delta']:
                        self.AD_decision["x, %d, %d" % (i, t)] = 0
                        self.AD_decision["y, %d, %d" % (i, t)] = 0
                        decision_made = 1
                        break
            if not decision_made:
                # 응급환자 중 최대 tardiness 가지는 사람의 tardiness 가 delta(penalty) 이하면 일단 응급환자는 open
                self.AD_decision["x, %d, %d" % (i, t)] = 1
                for p in range(len(pat_waiting[1][i])):
                    tard = max(0, end_time[1] - pat_waiting[1][i][p].occ_t - args['thd'][1] * args['time_unit'])
                    if tard > max_tard:
                        max_tard = tard
                        # 비응급환자 중 최대 tardiness 가지는 사람의 tardiness 가 delta(penalty) 이상이면 L-AD
                        if max_tard / args['time_unit'] > args['delta']:
                            self.AD_decision["y, %d, %d" % (i, t)] = 0
                            decision_made = 1
                            break
            # 둘 다 아니면 OPEN
            if not decision_made:
                self.AD_decision["y, %d, %d" % (i, t)] = 1

        return self.AD_decision