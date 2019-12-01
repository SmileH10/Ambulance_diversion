from datetime import datetime
import os
from dataIO import load_data
import numpy as np
from math import floor
from copy import deepcopy


class Patient(object):
    def __init__(self, pat_id, hospital, severity, path, occurred_time, args):
        self.id = pat_id
        self.i = hospital  # 원래 가려던 병원
        self.j = hospital  # 실제로 간 병원
        self.l = severity
        self.path = path  # 'amb' or 'walk'
        self.occ_t = occurred_time
        self.arr_t = self.occ_t
        self.time_unit = args['time_unit']
        self.thd = args['thd']
        self.pat_tard_t = 0.0
        self.pat_tard = 0.0
        self.svc_start_t = float("inf")
        self.comp_t = float("inf")

    def calc_tard_t(self, t, end_t):
        self.pat_tard_t = min(end_t - t * self.time_unit, max(0, end_t - self.occ_t - self.thd[self.l] * self.time_unit)) \
                        / self.time_unit
        self.pat_tard += self.pat_tard_t


def init_params(policy):
    args = {}
    args['policy'] = policy.lower()
    assert args['policy'] in ['opt', 'opt_no_hosp', 'no_future', 'open']
    args['scenarios'] = 30  # 시나리오 수
    args['L'] = 2
    args['H'] = 10
    args['T'] = 60  # 전체 시뮬레이션 길이
    args['time_planning'] = 18  # 최적화 할 때 얼마나 뒤 시점까지 계산할 것인가
    args['time_unit'] = 30  # (min). : 1 time unit = 60분으로 설정
    args['warmup_period'] = 12  # (unit_time)
    args['tard_criteria_for_report'] = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210, 220, 230, 240, 250, 260, 270, 280, 290, 300, 310, 320, 330, 340, 350, 360]  # 갯수 제한없이 입력가능. thd를 x 분 이상 초과한 환자의 tard 평균 / 환자비율 출력
    assert 1440 % args['time_unit'] == 0  # 'time_unit'이 1440분(1일)의 인수여야 함
    args['thd'] = [4, 4]  # Threshold [중증도 0(응급), 1(비응급)]
    args['avg_svc_t'] = [100.0, 30.0]  # 중증도 별 치료시간 (단위: minutes / patient)
    args['prob_dist'] = 'tri'  # 'exp', 'tri', 'norm' 중 하나
    assert args['prob_dist'] in ['exp', 'tri', 'norm']
    if args['prob_dist'] == 'tri':
        args['tri_range'] = [10, 10]  # [응급, 비응급]. left = mode - tri_range; right = mode + tri_range
    elif args['prob_dist'] == 'norm':
        args['norm_std'] = [10, 10]  # [응급, 비응급]. stdev

    # 환자 비율 지정
    args['amb/total'] = 0.22  # 전체 환자 중 구급차로 오는 환자 비율
    args['severity_ratio(amb)'] = [0.91, 0.09]  # 구급차로 오는 환자 중 응급환자 비율
    args['severity_ratio(walk)'] = [0.78, 0.22]  # 도보로 오는 환자 중 응급환자 비율
    # severity_ratio, amb_ratio는 자동 계산되는 값
    # 예1) args['severity_ratio'] = [0.3, 0.7]  # severity_ratio[중증도]: 전체 환자 중증도 비율 (합이 1이어야 함)
    # 예2) args['amb_ratio'] = [1, 1]  # amb_ratio[중증도]; l 중증도의 환자 중 구급차로 오는 환자의 비율 (1:3, 1:7)
    args['severity_ratio'] = [args['amb/total'] * args['severity_ratio(amb)'][0] + (1 - args['amb/total']) * args['severity_ratio(walk)'][0],
                              args['amb/total'] * args['severity_ratio(amb)'][1] + (1 - args['amb/total']) * args['severity_ratio(walk)'][1]]
    if sum(args['severity_ratio(amb)'][l] for l in range(args['L'])) != 1 \
            or sum(args['severity_ratio(walk)'][l] for l in range(args['L'])) != 1\
            or sum(args['severity_ratio'][l] for l in range(args['L'])) != 1:
        raise Exception("severity ratio 합이 1이어야 함")
    args['amb_ratio'] = [args['amb/total'] * args['severity_ratio(amb)'][0]
                         / (args['amb/total'] * args['severity_ratio(amb)'][0] + (1-args['amb/total']) * args['severity_ratio(walk)'][0]),
                         args['amb/total'] * args['severity_ratio(amb)'][1]
                         / (args['amb/total'] * args['severity_ratio(amb)'][1] + (1 - args['amb/total']) * args['severity_ratio(walk)'][1])]

    # 결과파일 출력 주소 지정
    args['log_dir'] = "./logs/{}-{}/".format(args['policy'], datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
    args['ADmodel_dir'] = args['log_dir'] + "ADmodel/"
    os.makedirs(args['log_dir'])
    if args['policy'] == 'opt' or args['policy'] == 'opt_no_hosp':
        os.makedirs(args['ADmodel_dir'])

    # 목적함수
    args['alpha'] = [2, 1]  # tardiness
    args['coef_mu'] = [0.0001, 0.0001]  # - mu
    args['beta'] = [0.02, 0.01]  # traveling_time

    args = load_csv_dataset(args)
    args = init_policy_specific_params(args)
    args = scenario_generator(args)

    return args


def init_policy_specific_params(args):
    # AD 결정 수리모델 목적함수의 계수
    if args['policy'] == 'opt_no_hosp':
        args['gamma'] = [2, 1]  # AD
        args['avg_travel_t'] = avg_travel_t(args['traveling_t'])
    if args['policy'] == 'opt_no_hosp' or args['policy'] == 'no_future':
        args['delta'] = [3, 4]  # expected tardiness of an AD-patient (unit time)
    return args


def avg_travel_t(travel_matrix):
    avg_val = 0.0
    for i in range(len(travel_matrix)):
        for j in range(len(travel_matrix)):
            avg_val += travel_matrix[i][j]
    avg_val /= len(travel_matrix) * (len(travel_matrix) - 1)
    return avg_val


def load_csv_dataset(args):
    # 병원 간 거리 불러오기
    args['traveling_t'] = load_data("./dataset/traveling_time.csv", load_type='int')[:args['H']]
    for i in range(len(args['traveling_t'])):
        args['traveling_t'][i] = args['traveling_t'][i][:args['H']]
    args['unit_distance'] = deepcopy(args['traveling_t'])
    for i in range(len(args['traveling_t'])):
        for j in range(len(args['traveling_t'][i])):
            args['unit_distance'][i][j] = floor(args['unit_distance'][i][j] / args['time_unit'])
    # D, C 불러오기
    args['demand'] = load_data("./dataset/demand.csv")  # D[i][t]
    args['server'] = load_data("./dataset/server.csv", load_type='int')  # C[i][t]
    args['d_amb'] = [[[0.0 for t in range(1440//args['time_unit'])] for i in range(args['H'])] for l in range(args['L'])]
    args['d_walk'] = [[[0.0 for t in range(1440//args['time_unit'])] for i in range(args['H'])] for l in range(args['L'])]
    for i in range(args['H']):
        for t in range(1440 // args['time_unit']):
            for l in range(args['L']):
                # args['d_amb'][l][i][t] = args['demand'][i][t] * args['severity_ratio'][l] * args['amb_ratio'][l]
                args['d_amb'][l][i][t] = args['demand'][i][t] * args['amb/total'] * args['severity_ratio(amb)'][l]
                # args['d_walk'][l][i][t] = args['demand'][i][t] * args['severity_ratio'][l] * (1 - args['amb_ratio'][l])
                args['d_walk'][l][i][t] = args['demand'][i][t] * (1-args['amb/total']) * args['severity_ratio(walk)'][l]
    return args


def scenario_generator(args, seed=1):
    num_scenarios = args['scenarios']
    L = args['L']
    H = args['H']
    T = args['T']
    tp = args['time_planning']
    time_unit = args['time_unit']
    C = args['server']
    D = args['demand']
    t2day = lambda x: x % (1440 // args['time_unit'])

    temp_pat_amb = [{} for w in range(num_scenarios)]  # 시나리오 별 l, i, t구간 별 구급차 이송 환자 저장
    temp_pat_walk = [{} for w in range(num_scenarios)]  # 시나리오 별 l, i, t구간 별 도보 이송 환자 저장
    temp_svc_t = [{} for w in range(num_scenarios)]  # 시나리오 별 l, i, t구간 별 의사의 치료시간 순서대로 저장
    for w in range(num_scenarios):
        pat_id = 0
        for l in range(L):
            for i in range(H):
                seed += 200
                temp_pat_amb[w][(l, i, 0)] = []
                temp_pat_walk[w][(l, i, 0)] = []
                current_t = 0.0  # real time
                check_recorded = 1
                for t in range(T + tp):
                    np.random.seed(seed + t)
                    temp_pat_amb[w][(l, i, t + 1)] = []
                    temp_pat_walk[w][(l, i, t + 1)] = []
                    while 1:
                        if current_t > time_unit * (t + 1):
                            break
                        elif check_recorded == 1:
                            if args['prob_dist'] == 'exp':
                                current_t += np.random.exponential(args['time_unit'] /
                                                                   (D[i][t2day(t)]
                                                                    * args['severity_ratio'][l]))
                            elif args['prob_dist'] == 'tri':
                                mode = args['time_unit'] / (D[i][t2day(t)] * args['severity_ratio'][l])
                                current_t += np.random.triangular(mode - args['tri_range'][l], mode, mode + args['tri_range'][l])
                            elif args['prob_dist'] == 'norm':
                                current_t += np.random.normal(args['time_unit'] / (D[i][t2day(t)] * args['severity_ratio'][l]),
                                                              args['norm_std'][l])
                        else:
                            check_recorded = 1

                        if current_t > time_unit * (t + 1):
                            check_recorded = 0
                            break

                        pat_id += 1
                        if np.random.random() <= args['amb_ratio'][l]:
                            temp_pat_amb[w][(l, i, t)].append(Patient(pat_id, i, l, 'amb', current_t, args))
                        else:
                            temp_pat_walk[w][(l, i, t)].append(Patient(pat_id, i, l, 'walk', current_t, args))

        # # service time 생성
        for l in range(L):
            for i in range(H):
                seed += 200
                for t in range(T + tp):
                    np.random.seed(seed + t)
                    temp_svc_t[w][(l, i, t)] = []
                    # DES에서 그때그때 생성해도 되는데, 다른 전략과 비교하기 좋게 하려고(CRN) 미리 생성.
                    for cnt in range(int(args['time_unit'] / args['avg_svc_t'][l] * C[i][t2day(t)] * 5)):
                        if args['prob_dist'] == 'exp':
                            temp_svc_t[w][(l, i, t)].append(np.random.exponential(args['avg_svc_t'][l]))
                        elif args['prob_dist'] == 'tri':
                            temp_svc_t[w][(l, i, t)].append(np.random.triangular(args['avg_svc_t'][l] - args['tri_range'][l],
                                                                                 args['avg_svc_t'][l],
                                                                                 args['avg_svc_t'][l] + args['tri_range'][l]))
                        elif args['prob_dist'] == 'norm':
                            temp_svc_t[w][(l, i, t)].append(np.random.normal(args['avg_svc_t'][l], args['norm_std'][l]))

    args['pat_amb'] = temp_pat_amb
    args['pat_walk'] = temp_pat_walk
    args['svc_t'] = temp_svc_t
    args['num_pat'] = [0 for w in range(num_scenarios)]  # 시나리오 별 전체 환자 수
    for w in range(num_scenarios):
        for l in range(L):
            for i in range(H):
                for t in range(T):
                    args['num_pat'][w] += len(args['pat_amb'][w][(l, i, t)])
                    args['num_pat'][w] += len(args['pat_walk'][w][(l, i, t)])
    return args
