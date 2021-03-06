#!/usr/bin/python
import os
import random
import sys
import shutil

sys.path.append('../')
import routes

import libSimulate


def countWeight(points):
    """
    what the hell are points?
    """
    weight = 0
    for (seq, pop) in points.items():
        if not seq[0] == 'f':
            weight += len(seq) * pop
        else:
            if not seq[1] == '*':
                weight += (len(seq) - 1) * pop
            else:
                weight += (len(seq) - 2) * pop
    return weight


class Vesicle(object):
    '''class representing a vesicle containing some sequences
     * matureWeight - Int. -  weight in terms of number of monomers,
        at which vesicles divide.
        They split into 2 vesicles with approximately equal weights.
     * generation - Int. - we start from mother vesicles (generation 0),
        its daughter is generation 1, ect
     * sequences - Dict. - {sequnce name: sequnce population}#TODO SeqInClust??
     * timeMature -- time, when it's time for vesicle to divide
     * populationMature -- population at timeMature
     * modelNum - Int. - model, which governs chemistry in the vesicle
     * path - String. - containing folder.
     * idInGen -- id of the vesicle among vesicles of the current generation
     * motherIdInGen -- mother's id
    '''

    def __init__(self, generation, sequences, idInGen, motherIdInGen, matureWeight, modelNum, path, paramFile=None):
        self.idInGen = idInGen
        self.sequencesAtBirth = sequences
        self.motherIdInGen = motherIdInGen
        self.generation = generation
        self.matureWeight = matureWeight
        self.modelNum = modelNum
        self.path = path
        self.outPath = os.path.join(self.path, str("%04d" % self.generation))
        self.initFile = self._getInitPopFile()
        self.paramFile = paramFile

    def __str__(self):
        str1 = 'Vesicle ' + str(self.generation) + ' of mature weight ' + \
               str(self.matureWeight)
        return str1

    def _getInitPopFile(self):  # TEST
        populFile = os.path.join(
            self.path, str("%04d" % self.generation), 'initPop' + str("%05d" % self.idInGen))
        return populFile

    def _makeInitPopFile(self):
        initFile = open(self.initFile, 'w')
        initFile.close()
        initFile = open(self.initFile, 'a')
        for (seq, pop) in self.sequencesAtBirth.items():
            initFile.write(seq + ' ' + str(pop) + '\n')
        initFile.close()
        return None

    def _findMature(self):  # TEST
        def line2Data(raw):
            points = {}
            for item in raw[1:len(raw) - 1]:
                # get a couple specie -- its population
                point = item.split(' ')
                points[point[0]] = int(point[1])
            return points

        weights = open(os.path.join(self.outPath, 'weights' + str("%05d" % self.idInGen) + '.txt'), 'w')
        weights.close()
        weights = open(os.path.join(self.outPath, 'weights' + str("%05d" % self.idInGen) + '.txt'), 'a')

        simRes = open(os.path.join(self.outPath, 'traj0'), 'r')

        growth = open(os.path.join(self.outPath, 'growth' + str("%05d" % self.idInGen)), 'w')
        growth.close()
        growth = open(os.path.join(self.outPath, 'growth' + str("%05d" % self.idInGen)), 'a')

        timeMature = -1
        for line in simRes:
            if line[0] == "#":
                continue
            else:
                growth.write(line)
                raw = (line.rstrip('\n')).split(',')
                points = line2Data(raw)
                weight = countWeight(points)
                weights.write(raw[0] + ' ' + str(weight) + '\n')
                # print(weight)
                if weight >= self.matureWeight:
                    timeMature = float(raw[0])
                    break
        simRes.close()
        growth.close()
        weights.close()
        if timeMature == -1:
            raise ValueError("Simulation was too short to get to mature weight")
        return timeMature, points

    def growCell(self, termTime, timeStep):  # TESTED
        '''
        form Simulation with special path
        run until some known time
        find time, when the mass of the vesicle == matureWeight
        rewrite trajectory till this time as generation 0
        split randomly
        '''
        sDef = libSimulate.Simulation(
            self.modelNum,
            termCond=('simulateTime', termTime, timeStep),
            rewrite=False,
            specialPath=self.outPath,
            numOfRuns=1,
            traj=True,
            log_level='WARNING')
        sDef.runSeveralSeries(paramFile=self.paramFile, populFile=self.initFile)
        timeMature, sequencesAtSplit = self._findMature()  # TEST
        print('mature time is: ', timeMature)
        return sequencesAtSplit, timeMature

    def getSeqsAtSplit(self):
        self.trajFile = os.path.join(self.outPath, 'growth' + str("%05d" % self.idInGen))
        with open(self.trajFile, 'r') as fh:
            for line in fh:
                pass
            last = line.split(',')[1:-1]
        mPop = {}
        for couple in last:
            pair = couple.split(' ')
            mPop[pair[0]] = int(pair[1])
        return mPop

    def splitCell(self, sequencesAtSplit):  # TESTED
        daughter1 = Vesicle(
            self.generation + 1,
            {},
            0,
            self.idInGen,
            self.matureWeight,
            self.modelNum,
            self.path,
            self.paramFile)
        daughter2 = Vesicle(
            self.generation + 1,
            {},
            1,
            self.idInGen,
            self.matureWeight,
            self.modelNum,
            self.path,
            self.paramFile)
        megaList = []
        for (seq, pop) in sequencesAtSplit.items():
            megaList += [seq] * pop
        random.shuffle(megaList)
        list1 = megaList[:int(len(megaList) / 2)]
        list2 = megaList[int(len(megaList) / 2):]
        for item in list1:
            daughter1.sequencesAtBirth[item] = list1.count(item)
        for item in list2:
            daughter2.sequencesAtBirth[item] = list2.count(item)
        print('d1 weight: ' + str(countWeight(daughter1.sequencesAtBirth)))
        print('d2 weight: ' + str(countWeight(daughter2.sequencesAtBirth)))

        return daughter1, daughter2

    def produceInitFolder(self):  # TEST
        """checks if the outputPath created and creates it
        initializes and fills out init populations
        """
        try:
            os.makedirs(self.outPath)
        except FileExistsError:
            print('dir exists')
        init1 = open(self.initFile, 'w')
        init1.close()
        init1 = open(self.initFile, 'a')
        for (seq, pop) in self.sequencesAtBirth.items():
            init1.write(seq + ' ' + str(pop) + '\n')
        init1.close()

    def _procreateVesicle(self, termTime, timeStep, nextGen, allVesicles):
        '''
        helper function for growAndSplit
        grows vesicles and produces two daughter cells ready to procreate
        '''
        self.sequencesAtSplit, self.timeMature = \
            self.growCell(termTime, timeStep)
        daughter1, daughter2 = \
            self.splitCell(self.sequencesAtSplit)

        daughter1.produceInitFolder()
        daughter2.produceInitFolder()

        nextGen.append(daughter1)
        nextGen.append(daughter2)
        allVesicles.append(daughter1)
        allVesicles.append(daughter2)

    def growAndSplit(self, termTime, timeStep, numOfGenerations, keepAll):
        '''grows cells for several generation either keeping them keeping them
        all or selecting
        keepAll is one of:
         - True
         - False (selects 1st vesicle)
        '''
        #        vesicles0 = [self]
        currGeneration = 0
        self.sequencesAtSplit, self.timeMature = \
            self.growCell(termTime, timeStep)
        # two daughter cells produced
        daughter1, daughter2 = self.splitCell(self.sequencesAtSplit)
        os.mkdir(daughter1.outPath)
        daughter1._makeInitPopFile()
        daughter2._makeInitPopFile()
        # now we have two daughters
        allVesicles = []
        nextGen = [daughter1, daughter2]
        while currGeneration < numOfGenerations:
            print('generation ', currGeneration)
            vesicles = nextGen
            nextGen = []
            if keepAll == True:
                # for every vesicle do a procedure
                for vesicle in vesicles:
                    vesicle._procreateVesicle(termTime, timeStep, nextGen, allVesicles)

            elif keepAll == False:  # TEST
                choose = 0
                vesicle = vesicles[choose]
                vesicle._procreateVesicle(termTime, timeStep, nextGen, allVesicles)

            else:
                raise ValueError('keepAll is either True, "random" or "select"')

            # vesicles = nextGen
            currGeneration += 1

        return allVesicles

    def makeInitParamFile(self):
        shutil.copyfile(os.path.join(routes.routePDM,'models',str("%03d" % self.modelNum),'parameters.ini'),
                        os.path.join(self.paramFile))
        # self.paramFile = os.path.join(destinationFolder,'parameters.ini')


    def readParamFile2List(self):#TESTED
        """
        Read file with parameters
        Returns:
            parLines: list [str]
        """
        parLines = []
        with open(self.paramFile, 'r') as pf:
            for line in pf:
                parLines.append(line)
        return parLines

    def changeParamFile(self,listOfPars,listOfVals):#TESTED
        parLines = self.readParamFile2List()
        for iLine in range(len(parLines)):
            for iPar in range(len(listOfPars)):
                if listOfPars[iPar] in parLines[iLine]:
                    parLines[iLine] = listOfPars[iPar] + ' = ' + str(listOfVals[iPar])+'\n'
        print('before file open' + self.paramFile)
        dummy = open(self.paramFile, 'w')
        dummy.close()
        with open(self.paramFile, 'a') as pf:
            for line in parLines:
                pf.write(line)
            print('after file writing' +self.paramFile)

        return parLines

    def growSelectTime(self, termTime, timeStep, numOfGenerations,maxImportRate):#TEST
        currGeneration = 0
        self.sequencesAtSplit, self.timeMature = \
            self.growCell(termTime, timeStep)
        # two daughter cells produced
        daughter1, daughter2 = self.splitCell(self.sequencesAtSplit)
        os.mkdir(daughter1.outPath)
        daughter1._makeInitPopFile()
        daughter2._makeInitPopFile()
        # now we have two daughters
        allVesicles = []
        importRates = []
        totalImportRates = []
        nextGen = [daughter1, daughter2]
        while currGeneration < numOfGenerations:
            print('generation ', currGeneration)
            vesicles = nextGen
            nextGen = []
            # first, grow both
            for vesicle in vesicles:
                vesicle.sequencesAtSplit, vesicle.timeMature = \
                    vesicle.growCell(termTime, timeStep)
            # then choose one which procreates faster
            if vesicles[0].timeMature <= vesicles[1].timeMature:
                choose = 0
            else:
                choose = 1
            vesicle = vesicles[choose]
            otherVesicle = vesicles[choose-1]
            # her daugheters are being produced
            daughter1, daughter2 = \
                vesicle.splitCell(vesicle.sequencesAtSplit)
            daughter1.produceInitFolder()
            daughter2.produceInitFolder()

            nextGen.append(daughter1)
            nextGen.append(daughter2)
            allVesicles.append(vesicle)
            # here we evolve import rate 
            # 
            newImportRate = vesicle.matureWeight / vesicle.timeMature / 4
            otherImportRate = otherVesicle.matureWeight / otherVesicle.timeMature / 4
            totalImportRate = newImportRate + otherImportRate
            if totalImportRate <= maxImportRate:
                pass
            else:
                newImportRate = newImportRate / totalImportRate * maxImportRate
                totalImportRate = maxImportRate

            totalImportRates.append(totalImportRate)
            print('At generation ' + str(currGeneration + 1) + 'New import rate will be: ', str(newImportRate))
            importRates.append(newImportRate)
            parLines = self.changeParamFile(['importH','importP'],[newImportRate,newImportRate])
            print(parLines)
            currGeneration += 1

        return allVesicles, importRates, totalImportRates


def readPopulations(popFile):
    sequences = {}
    with open(popFile) as infile:
        for line in infile:
            pair = line.rstrip('\n').split(' ')
            sequences[pair[0]] = int(pair[1])
    return sequences


def getSeq(seq):
    '''
    Arguments:
     - seq -- str. sequence as depicted in trajectory file
    Returns:
     - hps -- str. actual HP sequence
    '''
    if 'f' in seq:
        if '*' in seq:
            hps = seq[2:]
        else:
            hps = seq[1:]
    else:
        hps = seq
    return hps


def getWeight(populationDict):
    weight = 0
    for (seq, pop) in populationDict.items():
        weight += len(getSeq(seq)) * pop
    return weight


if __name__ == "__main__":
    idInGen = 0
    path = routes.routePDM + 'vesicles/multirun2/l0000/'
    sequences = readPopulations(path+'0000/initPop00000')
    paramFile = path+'parameters.ini'
    motherIdInGen = 0
    generation = 0
    matureWeight = 6000
    modelNum = 18

    termTime = 40
    timeStep = 0.0001
    numOfGenerations = 1
    v = Vesicle(generation, sequences, idInGen, motherIdInGen, matureWeight, modelNum, path,paramFile)
    # sAs = v.growCell(termTime,timeStep)
    # vs = v.growAndSplit(termTime, timeStep, numOfGenerations, keepAll=False)

