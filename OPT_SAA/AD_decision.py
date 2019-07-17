import sys
import os
from config import scenario_generator
import numpy as np
from OPT_SAA.DES_SAA import DES_SAA
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from OPT.AD_decision import Opt


class Opt_SAA(Opt):
    def __init__(self, args):
        super().__init__(args)
        self.step = args['step']
        self.T = args['T']
        self.AD_DV_cand = []
        self.obj = {}

    def reset_saa(self, args):
        self.AD_DV_cand = []
        for key in ['s_pat_amb', 's_pat_walk', 's_svc_t']:
            if key in args:
                del (args[key])
        self.num_sample = 0
        self.best = 0.0
        self.best_sol = [float("inf"), float("inf")]
        return args

    def run_saa(self, args, cur_t, sim_result):
        self.reset_saa(args)

        while True:
            args = self.sample_scenario_adder(cur_t, args)  # sample 수를 step개 추가 생성
            self.new_cand = 0
            for s in range(self.num_sample - self.step, self.num_sample):
                temp_AD_DV = self.run_opt(args, cur_t, sim_result, saa_sample_sce=s)
                self.AD_DV_cand = self.check_overlap_and_update(temp_AD_DV, self.AD_DV_cand)
            cand_avg_obj = self.cand_evaluation(cur_t, args)
            """
            # 중간과정 print
            print("--[SAA] w: %d, t: %d, sample 생성 개수: %d --------------------------------------------" % (w, cur_t, s + 1))
            print("해 개수: %d, 최적값 E[Z]: " % len(self.AD_DV_cand), ["%.2f" % cand_avg_obj[i] for i in range(len(cand_avg_obj))])
            print("최적해index: %d, min(최적값): %.2f" % (np.argmin(cand_avg_obj), np.min(cand_avg_obj)))
            if np.min(cand_avg_obj) > 0:
                print("직전 최적, 이번 최적: (%.2f, %.2f), GAP: %.2f%%" % (self.best, np.min(cand_avg_obj), 100 * (self.best - np.min(cand_avg_obj)) / np.min(cand_avg_obj)))
            else:
                print("직전 최적, 이번 최적: (%.2f, %.2f), GAP: nan%%" % (self.best, np.min(cand_avg_obj)))
            """
            # 종료조건: step 수만큼 하고 종료
            if self.num_sample >= self.step:
            # 종료조건: <GAP 0.1% 미만> 혹은 <3연속 해 동일>
            #if self.num_sample >= 2 * self.step and \
             #       ((-0.001 < (self.best - np.min(cand_avg_obj)) / np.min(cand_avg_obj) < 0.001)
              #       or (self.best_sol[0] == self.best_sol[1] and self.best_sol[1] == np.argmin(cand_avg_obj))):
                for i in range(self.H):
                    self.AD_decision["x, %d, %d" % (i, cur_t)] = self.AD_DV_cand[np.argmin(cand_avg_obj)]["x, %d, %d" % (i, cur_t)]
                    self.AD_decision["y, %d, %d" % (i, cur_t)] = self.AD_DV_cand[np.argmin(cand_avg_obj)]["y, %d, %d" % (i, cur_t)]
                break
            else:
                self.best = np.min(cand_avg_obj)
                self.best_sol[0] = self.best_sol[1]
                self.best_sol[1] = np.argmin(cand_avg_obj)
        print("SAA t: %d, num_sample: %d" % (cur_t, self.num_sample))
        return self.AD_decision

    def sample_scenario_adder(self, t, args):
        args = scenario_generator(args, saa=1, seed=int(t * (self.T + self.tp) + 814 + self.T * self.num_sample / self.step))
        self.num_sample += self.step
        return args

    def check_overlap_and_update(self, temp_AD_DV, AD_DV_cand):
        overlap = 0
        for sol in range(len(AD_DV_cand)):
            if len({k: AD_DV_cand[sol][k] for k in AD_DV_cand[sol]
                    if k in temp_AD_DV and AD_DV_cand[sol][k] != temp_AD_DV[k]}) == 0:
                overlap = 1
                break
        if overlap == 0:
            self.new_cand += 1
            AD_DV_cand.append(temp_AD_DV)
        return AD_DV_cand

    def cand_evaluation(self, cur_t, args):
        cand_avg_obj_list = []
        for s1 in range(len(self.AD_DV_cand)):
            for s2 in range(self.num_sample):
                if s1 < len(self.AD_DV_cand) - self.new_cand and s2 < self.num_sample - self.step:
                    continue
                sim = DES_SAA(args, cur_t)
                self.obj[s1, s2] = sim.run_tp_time_simulation(self.AD_DV_cand[s1], s2, args)
            cand_avg_obj_list.append(sum(self.obj[s1, s2] / self.num_sample for s2 in range(self.num_sample)))
        return cand_avg_obj_list
