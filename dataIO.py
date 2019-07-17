import numpy as np


def load_data(filename, load_type='float', head=True, col_index=True, delimiter=","):
    f = open(filename)
    data = []
    type = {'int': int, 'float': float}
    for line in f.readlines():
        if head:
            head = False
            continue
        else:
            line = line.strip().split(delimiter)
            if col_index:
                data.append([type[load_type](x) for x in line[1:]])
            else:
                data.append([type[load_type](x) for x in line])
    f.close()
    return data


def write_model_result(args, sim_tard, AD_sce_result, sim_sce_details, sim_pat_info, sim_traveling_t, sim_svr_util, sim_num_pat_over_thd, sim_tard_over_thd):
    # # 결과 출력: 파일 1 <Tardiness.csv>
    # # 시나리오별 tardiness 결과
    objective_print = {}
    num_pat_comp = [[0 for l in range(args['L'])] for w in range(args['scenarios'])]
    sum_tard_wl = [[0 for l in range(args['L'])] for w in range(args['scenarios'])]
    res = [[0.0 for _ in range(23)] for w in range(args['scenarios'] + 1)]
    for w in range(args['scenarios']):
        for l in range(args['L']):
            num_pat_comp[w][l] = sum(sim_sce_details[w]['mu'][l][i][t] for i in range(args['H']) for t in range(args['T']))
            sum_tard_wl[w][l] = sim_tard_over_thd[w][l]

        # avg tard (전체/응급/비응급)  "avg_tard(전체), avg_tard(응급), avg_tard(비응급)"
        res[w][0] = sum(sum_tard_wl[w][l] * args['time_unit'] for l in range(args['L'])) / sum(num_pat_comp[w][l] for l in range(args['L']))
        res[w][1] = sum_tard_wl[w][0] * args['time_unit'] / num_pat_comp[w][0]
        res[w][2] = sum_tard_wl[w][1] * args['time_unit'] / num_pat_comp[w][1]
        # avg_travel_t (전체/응급/비응급)
        res[w][3] = sum(sim_traveling_t[w][l][i][t] for l in range(args['L']) for i in range(args['H']) for t in range(args['T'])) \
                    / sum(num_pat_comp[w][l] for l in range(args['L']))
        res[w][4] = sum(sim_traveling_t[w][0][i][t] for i in range(args['H']) for t in range(args['T'])) / num_pat_comp[w][0]
        res[w][5] = sum(sim_traveling_t[w][1][i][t] for i in range(args['H']) for t in range(args['T'])) / num_pat_comp[w][1]
        # weighted_sum (전체/응급/비응급)
        res[w][6] = args['alpha'] * res[w][0] + args['coef_traveling_t'] * res[w][3]
        res[w][7] = args['alpha'] * res[w][1] + args['coef_traveling_t'] * res[w][4]
        res[w][8] = args['alpha'] * res[w][2] + args['coef_traveling_t'] * res[w][5]
        # thd넘긴환자의 tard평균 (전체/응급/비응급)
        if sim_num_pat_over_thd[w][0] + sim_num_pat_over_thd[w][1] == 0:
            res[w][9] = 0
        else:
            res[w][9] = (sum_tard_wl[w][0] + sum_tard_wl[w][1]) * args['time_unit'] / (sim_num_pat_over_thd[w][0] + sim_num_pat_over_thd[w][1])
        if sim_num_pat_over_thd[w][0] == 0:
            res[w][10] = 0
        else:
            res[w][10] = sum_tard_wl[w][0] * args['time_unit'] / sim_num_pat_over_thd[w][0]
        if sim_num_pat_over_thd[w][1] == 0:
            res[w][11] = 0
        else:
            res[w][11] = sum_tard_wl[w][1] * args['time_unit'] / sim_num_pat_over_thd[w][1]
        # thd넘긴환자비율 (분자/분모: 전체/응급/비응급)
        res[w][12] = (sim_num_pat_over_thd[w][0] + sim_num_pat_over_thd[w][1]) / (num_pat_comp[w][0] + num_pat_comp[w][1])
        res[w][13] = sim_num_pat_over_thd[w][0] / num_pat_comp[w][0]
        res[w][14] = sim_num_pat_over_thd[w][1] / num_pat_comp[w][1]
        # thd넘긴환자비율 (분자: 응급/비응급, 분모; 전체)
        res[w][15] = sim_num_pat_over_thd[w][0] / (num_pat_comp[w][0] + num_pat_comp[w][1])
        res[w][16] = sim_num_pat_over_thd[w][1] / (num_pat_comp[w][0] + num_pat_comp[w][1])
        res[w][17] = num_pat_comp[w][0] + num_pat_comp[w][1]
        res[w][18] = num_pat_comp[w][0]
        res[w][19] = num_pat_comp[w][1]
        res[w][20] = sim_num_pat_over_thd[w][0] + sim_num_pat_over_thd[w][1]
        res[w][21] = sim_num_pat_over_thd[w][0]
        res[w][22] = sim_num_pat_over_thd[w][1]

        val = ""
        for i in range(len(res[w])):
            val += "%.2f, " % res[w][i]
        objective_print[w] = val

    avg_val = ""
    for i in range(len(res[args['scenarios']])):
        res[args['scenarios']][i] = sum(res[w][i] for w in range(args['scenarios'])) / args['scenarios']
        avg_val += "%.2f, " % res[args['scenarios']][i]
    objective_print['avg(unit: min)'] = avg_val

    try:
        write_data(args, data=objective_print, filename="objective",
                   head="w, avg_tard(전체), avg_tard(응급), avg_tard(비응급), avg_travel_t(전체), avg_travel_t(응급), avg_travel_t(비응급),"
                        "weighted_sum(전체), weighted_sum(응급), weighted_sum(비응급), thd넘긴환자의 tard평균(전체),"
                        "thd넘긴환자의 tard평균(응급), thd넘긴환자의 tard평균(비응급), thd넘긴비율(%)(전체/전체), thd넘긴비율(응급/응급), "
                        "thd넘긴비율(비응급/비응급), thd넘긴비율(응급/전체), thd넘긴비율(비응급/전체), 전체환자수, 응급환자수, 비응급환자수,"
                        "tard넘긴전체환자수, tard넘긴응급환자수, tard넘긴비응급환자수")
        # write_data(args, data=tardiness_print, filename="Tardiness", head="w, tardiness_sum")
    except:
        print("write_data_error: Tardiness.csv")

    # # 결과 출력: 파일 2 <AD_result.csv>, 파일 7 <num_AD_change.csv>
    # # 시나리오별 병원별 AD 결과
    AD_change = {}
    AD_duration = {}
    AD_print = []
    for w in range(args['scenarios']):
        AD_print.append(["scenario: %d" % w])
        AD_print.append(["Hospital"] + list(range(args['T'])))
        for i in range(args['H']):
            AD_change["%d, %d" % (w, i)] = [0, 0, 0, 0, 0, 0]
            AD_duration["%d, %d, L-AD" % (w, i)] = 0
            AD_duration["%d, %d, A-AD" % (w, i)] = 0
            line = ["Hospital %d" % i]
            for t in range(args['T']):
                if AD_sce_result[w]["x, %d, %d" % (i, t)] == 1 and AD_sce_result[w]["y, %d, %d" % (i, t)] == 1:
                    if line[-1] == "L-AD":
                        AD_change["%d, %d" % (w, i)][2] += 1
                    elif line[-1] == "A-AD":
                        AD_change["%d, %d" % (w, i)][0] += 1
                    line.append("Open")
                elif AD_sce_result[w]["x, %d, %d" % (i, t)] == 1 and AD_sce_result[w]["y, %d, %d" % (i, t)] == 0:
                    if line[-1] == "Open":
                        AD_change["%d, %d" % (w, i)][3] += 1
                    elif line[-1] == "A-AD":
                        AD_change["%d, %d" % (w, i)][4] += 1
                    line.append("L-AD")
                    AD_duration["%d, %d, L-AD" % (w, i)] += args['time_unit']
                elif AD_sce_result[w]["x, %d, %d" % (i, t)] == 0 and AD_sce_result[w]["y, %d, %d" % (i, t)] == 0:
                    if line[-1] == "Open":
                        AD_change["%d, %d" % (w, i)][1] += 1
                    elif line[-1] == "L-AD":
                        AD_change["%d, %d" % (w, i)][5] += 1
                    line.append("A-AD")
                    AD_duration["%d, %d, A-AD" % (w, i)] += args['time_unit']
                else:
                    line.append("**ERROR**")
            AD_print.append(line)
        AD_print.append("\n")
    try:
        write_data(args, data=AD_print, filename='AD_result', list_2D=True)
    except:
        print("write_data_error: AD_result.csv")
    try:
        for w in range(args['scenarios']):
            for i in range(args['H']):
                AD_change["%d, %d" % (w, i)] = "%d, %d, %d, %d, %d, %d, %d" % (sum(AD_change["%d, %d" % (w, i)][idx] for idx in range(6)),
                                                AD_change["%d, %d" % (w, i)][0], AD_change["%d, %d" % (w, i)][1],
                                                AD_change["%d, %d" % (w, i)][2], AD_change["%d, %d" % (w, i)][3],
                                                AD_change["%d, %d" % (w, i)][4], AD_change["%d, %d" % (w, i)][5])
        write_data(args, data=AD_change, filename="AD_num_change",
                   head="W, I, AD_변경(0+1+2+3), (0)A-AD>OPEN, (1)OPEN>A-AD, (2)L-AD>OPEN, (3)OPEN>L-AD, (4)A-AD>L-AD, (5)L-AD>A-AD")
    except:
        print("write_data_error: num_AD_change.csv")
    try:
        write_data(args, data=AD_duration, filename='AD_duration', head="W, I, AD종류, 지속시간(min)")
    except:
        print("write_data_error: AD_duration.csv")

    # # 결과 출력: 파일 3 <sim_details.csv>
    # # mu/lambda/congestion(L 없음)/n(병원내환자수)
    sim_details_dict = {}
    for w in range(args['scenarios']):
        for key in sim_sce_details[w].keys():
            for i in range(args['H']):
                for t in range(args['T']):
                    if key == 'congestion':
                        sim_details_dict['%s, %d, -, %d, %d' % (key, w, i, t)] = round(sim_sce_details[w][key][i][t], 2)
                    else:
                        for l in range(args['L']):
                            sim_details_dict['%s, %d, %d, %d, %d' % (key, w, l, i, t)] = sim_sce_details[w][key][l][i][t]
    # # tardiness
    for w in range(args['scenarios']):
        for l in range(args['L']):
            for i in range(args['H']):
                for t in range(args['T']):
                    sim_details_dict['tardiness, %d, %d, %d, %d' % (w, l, i, t)] = round(sim_tard[w][l][i][t], 2)
                    sim_details_dict['traveling_t, %d, %d, %d, %d' % (w, l, i, t)] = round(sim_traveling_t[w][l][i][t], 2)
    try:
        write_data(args, data=sim_details_dict, filename="sim_details", head="variable, W, L, I, T, value")
    except:
        print("write_data_error: sim_details.csv")

    # # 결과 출력: 파일 4 <config.csv>
    # # mu/lambda/congestion(L 없음)/tardiness
    try:
        args_print = {}
        for key in args.keys():
            if not key in ['pat_amb', 'pat_walk', 'svc_t', 's_pat_amb', 's_pat_walk', 's_svc_t', 'd_amb', 'd_walk']:
                args_print[key] = args[key]
            elif key in ['pat_amb', 'pat_walk']:
                args_print[key + '합 (시나리오별)'] = [sum(len(args[key][w][key2]) for key2 in args[key][w].keys()) for w in range(args['scenarios'])]
            elif key in ['d_amb', 'd_walk']:
                args_print['평균 ' + key + '합 (병원별)'] = [round(sum(args[key][l][i][t] for l in range(args['L']) for t in range(args['T'])), 1) for i in range(args['H'])]
        write_data(args, data=args_print, filename='config')
    except:
        print("write_data_error: config.csv")

    # # 결과 출력: 파일 5 <patient_info.csv>
    try:
        sum_pat_info = {}
        for w in range(args['scenarios']):
            for key in sim_pat_info[w].keys():
                sum_pat_info["%d, %s" % (w, key)] = sim_pat_info[w][key]
            write_data(args, data=sim_pat_info[w], filename="patient_info_w%d" % w,
                       head="ID, L, I, J, T, occ_t(1), arr_t(2), svc_start_t(3), comp_t(4), 이송(2-1), 대기(3-2), 치료(4-3), stay(4-1)")
        write_data(args, data=sum_pat_info, filename="patient_info_SUM",
                   head="W, ID, L, I, J, T, occ_t(1), arr_t(2), svc_start_t(3), comp_t(4), 이송(2-1), 대기(3-2), 치료(4-3), stay(4-1)")
    except:
        print("write_data_error: patient_info.csv")

    # # 결과 출력: 파일 6 <svr_util.csv>
    try:
        sum_svr_util = {}
        for w in range(args['scenarios']):
            for key in sim_svr_util[w].keys():
                if sim_svr_util[w][key] != "closed":
                    sum_svr_util["%d, %s" % (w, key)] = "%.3f" % sim_svr_util[w][key]
                else:
                    sum_svr_util["%d, %s" % (w, key)] = sim_svr_util[w][key]
        write_data(args, data=sum_svr_util, filename="svr_util", head="W, I, T, svr, utilization")
    except:
        print("write_data_error: svr_util.csv")


def write_data(args, data, filename, head=False, list_2D=False, AD_model=False):
    if AD_model:
        f = open("%s%s.csv" % (args['ADmodel_dir'], filename), "w")  # file_name.csv 파일 만들기
    else:
        f = open("%s%s.csv" % (args['log_dir'], filename), "w")  # file_name.csv 파일 만들기
    if head:
        f.write("%s\n" % head)
    if type(data) == list:
        f = write_list_data(f, data, list_2D)
    elif type(data) == dict:
        f = write_dict_data(f, data)
    else:
        print("Can't write data")
    f.close()


def write_list_data(f, data, list_2D=False):
    if list_2D:
        for i in range(len(data)):
            for j in range(len(data[i])):
                f.write("%s," % data[i][j])
            f.write("\n")
    else:
        f = np.array(f)
        dims = len(f.shape)
        index_list = []
        write_content(f, data, dims, index_list)
    return f


def write_content(f, data, dims, index_list):
    dims -= 1
    for dim in range(len(data)):
        index_list.append(dim)
        if dims == 0:
            for index in index_list:
                f.write("%d, " % index)
            f.write("%s," % str(data[dim]))
            f.write("\n")
        else:
            write_content(f, data[dim], dims, index_list)
        del (index_list[-1])


def write_dict_data(f, data):
    for i in data.keys():
        f.write("%s, %s\n" % (i, data[i]))
    return f
