from config import init_params
from dataIO import write_model_result
from DES import DES
from time import time


def load_AD_opt_model(args):
    if args['policy'] == 'opt':
        from OPT.AD_decision import Opt
        AD_opt = Opt(args)
    else:
        raise Exception("policy name does not exist")
    return AD_opt


def run_AD_opt_model(AD_opt, args, t, sim_result):
    if args['policy'] == 'opt':
        return AD_opt.run_opt(args, t, sim_result)
    else:
        raise Exception("policy name does not exist")


if __name__ == "__main__":
    start_time = time()
    args = init_params(policy='alt2')  # 'opt', 'opt_NoFuture', 'opt_NoOtherHospitals', 'opt_NoBoth' 중 택1
    AD_opt = load_AD_opt_model(args)
    AD_sim = DES(args)

    sim_sce_details = [{} for w in range(args['scenarios'])]  # mu, lambda, congestion
    sim_tard = [[[[[] for t in range(args['T'])] for i in range(args['H'])] for l in range(args['L'])] for w in range(args['scenarios'])]
    sim_traveling_t = [[[[[] for t in range(args['T'])] for i in range(args['H'])] for l in range(args['L'])] for w in range(args['scenarios'])]
    sim_pat_info = [{} for w in range(args['scenarios'])]
    sim_svr_util = [{} for w in range(args['scenarios'])]
    sim_num_pat_over_thd = [{} for w in range(args['scenarios'])]
    sim_tard_over_thd = [{} for w in range(args['scenarios'])]
    AD_sce_result = [{} for w in range(args['scenarios'])]  # x, y
    for w in range(args['scenarios']):
        AD_opt.reset()
        AD_sim.reset()
        for t in range(args['T']):
            if t == 0:
                sim_lambda_mu_result = []
                print("초기상태 로딩시간: %.2f" % (time() - start_time))
            time1 = time()
            AD_result = run_AD_opt_model(AD_opt, args, t, sim_lambda_mu_result, pat_waiting=AD_sim.pat_waiting)
            time2 = time()
            print("t: %d, AD결정 소요시간: %.2f" % (t, time2 - time1))
            sim_lambda_mu_result = AD_sim.run_one_time_simulation(AD_result, w, args)
            print("t: %d, 시뮬레이션 소요시간: %.2f" % (t, time() - time2))
        # 시나리오 종료 후 결과 저장
        sim_sce_details[w], sim_tard[w], sim_traveling_t[w], sim_pat_info[w], sim_svr_util[w], sim_num_pat_over_thd[w], sim_tard_over_thd[w] \
            = AD_sim.sim_result, AD_sim.sim_tard, AD_sim.sim_traveling_t, AD_sim.pat_info, AD_sim.sim_svr_util, AD_sim.num_pat_over_thd, AD_sim.sim_tard_over_thd
        AD_sce_result[w] = AD_opt.AD_decision
    # 결과 출력
    write_model_result(args, sim_tard, AD_sce_result, sim_sce_details, sim_pat_info, sim_traveling_t, sim_svr_util, sim_num_pat_over_thd, sim_tard_over_thd)
    print("전체 소요시간: %.2f" % (time() - start_time))

