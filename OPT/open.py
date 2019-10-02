class OpenPolicy(object):
    def __init__(self, args):
        self.AD_decision = {}
        self.H = args['H']

    def reset(self):
        self.AD_decision = {}
        for i in range(self.H):
            self.AD_decision["x, %d, %d" % (i, 0)] = 1
            self.AD_decision["y, %d, %d" % (i, 0)] = 1

    def run_openpolicy(self, t):
        for i in range(self.H):
            self.AD_decision["x, %d, %d" % (i, t)] = 1
            self.AD_decision["y, %d, %d" % (i, t)] = 1
        return self.AD_decision
