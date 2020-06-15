class DASRS(object):

    def __init__(
        self,
        minValue=0,
        maxValue=100,
        normValue=7,
        memoryWindow=2,
        restPeriod=30,
        probPeriod=1440):

        self.minValue = minValue
        self.maxValue = maxValue
        self.normValue = normValue
        self.memoryWindow = memoryWindow
        self.fullValueRange = self.maxValue - self.minValue
        if self.fullValueRange == 0.0:
            self.fullValueRange = self.normValue
        self.valueStep = self.fullValueRange / self.normValue
        self.restPeriod = restPeriod
        self.probPeriod = probPeriod
        self.restWeakenFactor = 0
        self.baseThreshold = 100.0
        self.normInputWindow = []
        self.windows = {}

        self.ORDERTIMEFAIL = 0
        self.TRAINING = 1
        self.REST = 2
        self.REGULAR = 3

        self.period = None
        self.lastInputTime = None
        self.lastDataPoint = 0

    def getAnomalyScore(self, inputValue, inputTime):

        if self.lastInputTime and inputTime < self.lastInputTime:
            self.period = self.ORDERTIMEFAIL
            return 0.0
        self.lastInputTime = inputTime

        if self.lastDataPoint <= self.probPeriod:
            self.lastDataPoint += 1
            self.period = self.TRAINING
        else:
            self.period = self.REGULAR


        normInpVal = int((inputValue - self.minValue) / self.valueStep)
        self.normInputWindow.append(normInpVal)

        if len(self.normInputWindow) < self.memoryWindow:
            return 0.0

        window = tuple(self.normInputWindow)
        windowHash = window.__hash__()
        occurrences = self.windows.setdefault(windowHash, 0) + 1
        self.windows[windowHash] += 1

        currentAnomalyScore = self.computeScoreFromOccurrences(occurrences)
        returnedAnomalyScore = self.computeFinalScore(currentAnomalyScore)

        self.normInputWindow.pop(0)

        return returnedAnomalyScore

    def get_period_description(self):
        if self.period == self.ORDERTIMEFAIL:
            return 'Input Time Out Of Order'
        elif self.period == self.TRAINING:
            return 'Training'
        elif self.period == self.REST:
            return 'Rest'
        else:
            return 'Regular'

    def is_anomaly(self, anomaly_score):
        if anomaly_score >= self.baseThreshold:
            if self.period > self.TRAINING:
                return True
        return False

    def computeScoreFromOccurrences(self, occurrences):
        score = round(100.0 / occurrences, 2)
        return score

    def computeFinalScore(self, currentScore):
        finalScore = currentScore
        if self.restWeakenFactor > 0:
            finalScore = round(currentScore / self.restWeakenFactor, 2)
            self.restWeakenFactor -= 1
            if self.period == self.REGULAR:
                self.period = self.REST
        elif currentScore >= self.baseThreshold:
            self.restWeakenFactor = self.restPeriod
        return finalScore
