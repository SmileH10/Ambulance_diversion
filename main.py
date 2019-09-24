from config import init_params
from dataIO import write_model_result
from DES import DES
from time import time
import numpy as np
from tqdm import tqdm
from time import sleep

def load_AD_opt_model(args):
    if args['policy'] == 'opt':
        from opt.opt_full import Opt
        AD_opt = Opt(args)
    elif args['policy'] == 'opt_no_hosp':
        from opt.opt_no_hosp import OptNoHosp
        AD_opt = OptNoHosp(args)
    elif args['policy'] == 'no_future':
        from opt.no_future import NoFuture
        AD_opt = NoFuture(args)
    elif args['policy'] == 'open':
        from opt.open import OpenPolicy
        AD_opt = OpenPolicy(args)
    else:
        raise Exception("policy name does not exist")
    return AD_opt


def run_AD_opt_model(AD_opt, args, t, sim_result, pat_waiting=False):
    if args['policy'] == 'opt':
        return AD_opt.run_opt(args, t, sim_result)
    elif args['policy'] == 'opt_no_hosp':
        return AD_opt.run_opt(args, t, sim_result)
    elif args['policy'] == 'no_future':
        return AD_opt.run_nofuture(args, t, pat_waiting)
    elif args['policy'] == 'open':
        return AD_opt.run_openpolicy(t)
    else:
        raise Exception("policy name does not exist")


if __name__ == "__main__":
    start_time = time()
    args = init_params(policy='open')  # 'opt', 'opt_no_hosp', 'no_future', 'open' 중 택1
    AD_opt = load_AD_opt_model(args)
    AD_sim = DES(args)

    print("policy : %s" % args['policy'])

    sim_sce_details = [{} for w in range(args['scenarios'])]  # mu, lambda, congestion
    sim_tard = [[[[[] for t in range(args['T'])] for i in range(args['H'])] for l in range(args['L'])] for w in range(args['scenarios'])]
    sim_traveling_t = [[[[[] for t in range(args['T'])] for i in range(args['H'])] for l in range(args['L'])] for w in range(args['scenarios'])]
    sim_pat_info = [{} for w in range(args['scenarios'])]
    sim_svr_util = [{} for w in range(args['scenarios'])]
    sim_num_pat_over_thd = [{} for w in range(args['scenarios'])]
    sim_tard_over_thd = [{} for w in range(args['scenarios'])]
    AD_sce_result = [{} for w in range(args['scenarios'])]  # x, y
    for w in range(args['scenarios']):
        start_iter_time = time()
        AD_opt.reset()
        AD_sim.reset()
        for t in tqdm(range(args['T'])):
            if t == 0:
                sim_lambda_mu_result = []
            AD_result = run_AD_opt_model(AD_opt, args, t, sim_lambda_mu_result, pat_waiting=AD_sim.pat_waiting)
            sim_lambda_mu_result = AD_sim.run_one_time_simulation(AD_result, w, args)
        # 시나리오 종료 후 결과 저장
        sleep(0.1)
        print("시나리오 %d / %d 종료 (소요시간: %.1f)" % (w, args['scenarios'] - 1, time() - start_iter_time))
        sleep(0.1)
        sim_sce_details[w], sim_tard[w], sim_traveling_t[w], sim_pat_info[w], sim_svr_util[w], sim_num_pat_over_thd[w], sim_tard_over_thd[w] \
            = AD_sim.sim_result, AD_sim.sim_tard, AD_sim.sim_traveling_t, AD_sim.pat_info, AD_sim.sim_svr_util, AD_sim.num_pat_over_thd, AD_sim.sim_tard_over_thd
        AD_sce_result[w] = AD_opt.AD_decision
    # 결과 출력
    write_model_result(args, sim_tard, AD_sce_result, sim_sce_details, sim_pat_info, sim_traveling_t, sim_svr_util, sim_num_pat_over_thd, sim_tard_over_thd)
    print("전체 소요시간: %.2f" % (time() - start_time))

