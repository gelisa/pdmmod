#/usr/bin/python
"""
This module takes in results of *pdmmod* simulations, 
and transforms them into desirable data. 
It also make various plots of data.
"""

#format of the trajectory file is the following:
# time, specName specPopulation, specName specPopulation .....

#specPop -- {name: [populations during time steps]}
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from collections import OrderedDict
from os import system as system
import numpy as np
import scipy
import math
import glob
import os
import subprocess

from sklearn.cluster import DBSCAN
#from sklearn import metrics
#from sklearn.datasets.samples_generator import make_blobs
#from sklearn.preprocessing import StandardScaler

import routes
#from dictUtils import * #pylint:disable=wildcard-import
#if dealing with HP-model import this
import hpClasses
from dictUtils import *


class Result(object):
    '''
    Class Result is a class, purpose of which is to keep information of the 
    simulation results in order to extract information out of them.
    '''
    # pylint: disable=too-many-instance-attributes
    # it's 15 here
    def __init__(self, modelNum, simNum, reorganize=False, numOfRuns=None, traj=None):
        '''
            modelNum: int
            termCond: is a Tuple representing termination condition. It's one of:
              * ('simulateTime', int:simulation time, int: how often to record)
              * ('simulateReactions', int:number of reactions, int: 
                    how often to record)
              * ('simulateTillSteady', int: how often to record (time))
            numOfRuns: is Int repr. number of runs of the simulation
            traj: Bool, repr.:
              * True: keep data from individual runs
              * False: do not keep them, only mean and st.dev.
        '''
        #pylint: disable=too-many-arguments
        #the following 3 attributes aren't part of self.parameters
        self.records = None#defined in _makeHeader and _readSimData
        self.howTerm = None#defined in _makeHeader and _readSimData
        self.whenTerm = None#defined in _makeHeader and _readSimDat
        self.modelNum = modelNum
        self.simNum = simNum
        self.path2Folder = routes.routePDM + 'models/' + str("%03d" %self.modelNum) + '/'
        self.outputDir = self.path2Folder + \
            str("%03d" %self.modelNum) + '_output' + str(self.simNum) + '/'
        print('reorganize or not to reorganize?')
        if not reorganize:
            print(' do not reorganize!')
        else:
            print('reorganize!')
            self.reorganizeOutput(numOfRuns, traj)
        self.parameters = self._readSimData()
        self.times = self._readTimes()
        print('Result.__init__ done')


    def makeHeader(self, numOfRuns, traj):
        '''
        this function reads simulation information from traj0 file
        and writes in in certain format into file parameters.txt
        located inside the simulation output directory
        '''
        filename = 'traj0'
        proc = subprocess.call(
            ('rm ' + self.outputDir + 'parameters.txt'), shell=True
            )#pylint:disable=unused-variable
        header = open(self.outputDir + 'parameters.txt', 'a')
        f = open(self.outputDir + filename, 'r')
        for line in f:
            if line[0] == '#':
                raw = (line[2:].rstrip('\n')).split(' ')
                group = ' == ' + raw[0].rstrip(':') + ' == \n'
                header.write(group)
                if raw[0] == 'Model:':
                    header.write(raw[1] + '\n')
                elif raw[0] == 'Parameters:':
                    for item in raw[1:]:
                        pair = item.split('=')
                        header.write(pair[0] + ' ' + pair[1] + '\n')
                elif raw[0] == 'Command:':
                    header.write('howTerm ' + raw[2] + '\n')
                    self.howTerm = str(raw[2])
                    header.write('whenTerm ' + raw[3] + '\n')
                    self.whenTerm = float(raw[3])
                    header.write('records ' + raw[4] + '\n')
                    self.records = float(raw[4])

            else:
                break

        header.write(' == Simulation Parameters == \n')
        header.write('numOfRuns ' + str(numOfRuns) + '\n')
        header.write('keepTrajectories ' + str(traj) + '\n')

        return None

    def _points2Evolutions(self, points, evolutions, count):
        '''
        this is a auxiliary function for the function _makeStatistics, 
        which reads all the trajectory files and makes and evolutions dictionary:
        a dictionary of populations of every specie at every moment 
        averaged over the trajectories 

        _points2Evolutions modifies evolutions dictionary 
        as while loop in _makeStatistics progresses through time steps
        DATA:
         *points -- is a dict.: {specie:(mean, std)}
            keeps populations of species at the given time across trajectory files
         *evolutions -- is a dict.: {specie: np.array([populations over time])
         *count -- is int.: it counts time instances
        '''
        #print('making evolutions')
        #print('points\n',points)
        for spec in points.keys():
            #print(spec)
            if self.numOfRuns == 1:
                points[spec] = (np.mean(points[spec]), 0)
            else:
                points[spec] = (np.mean(points[spec]), np.std(points[spec]))

            if spec not in evolutions:
                #add it and its population
                #also add 0s as prev times populations
                evolutions[spec] = np.zeros(
                    int(self.whenTerm/self.records + 1), dtype=(float, 2))
                #FIXME this one has to be fluid to handle simulateTillSteady
                evolutions[spec][count] = points[spec]
            else:
                #otherwise append new point to the existing list of points
                evolutions[spec][count] = points[spec]

        return None

    def _line2Data(self, raw, points, fileCount):
        '''
        this is a auxiliary function for the function _makeStatistics, 
        which reads all the trajectory files and makes and evolutions dictionary:
        a dictionary of populations of every specie at every moment 
        averaged over the trajectories 

        _line2Data takes a line of a data in a given file, spcified by fileCount 
        and modifies points dictionary.
        DATA:
         *points -- is a dict.: {specie:(mean, std)}
            keeps populations of species at the given time across trajectory files
        *raw -- a list made from the raw data in the trajectory file by splitting
        *fileCount -- int.: calculates current trajectory number
        '''
        for item in raw[1:len(raw)]:#TEST
            #get a couple specie -- its population
            point = item.split(' ')
            if point[0] not in points:
                #add it and its population
                #also add 0s as prev times populations
                #print('point in the second file', point)
                points[point[0]] = np.zeros(self.numOfRuns)
                points[point[0]][fileCount-1] = int(point[1])
            else:
                points[point[0]][fileCount-1] = int(point[1])
        return None

    def _makeStatistics(self):
        '''
        reads all the trajectory files and makes and evolutions dictionary:   
        a dictionary of populations of every specie at every moment 
        averaged over the trajectories 
        *evolutions -- dict.: {specie:np.arry[populations over time]}
        
        trajectory files are of form <time>,<spec.name1> <spec.pop1>,etc
        
        '''
        files = [self.outputDir + 'traj' + str(i) for i in range(self.numOfRuns)]
        print(files)
        handles = [open(t, 'r') for t in files]
        count = -1 #counts time instances
        evolutions = {}
        self.times = []
        breakCondition = False
        #print('evolutions\n',evolutions)
        while not breakCondition:
            points = {}
            #keeps populations of species at the given moment across files
            fileCount = 0
            for inFile in handles:
                line = inFile.readline()
                if line == '':
                    breakCondition = True
                    print(
                        'Termination condition is met on line ' + 
                        str(count) + ' in ' + str(inFile))
                elif line[0] == "#":
                    continue
                else:
                    raw = (line.rstrip(', \n')).split(',')#TEST
                    if fileCount == 0:
                        count += 1
                        self.times.append(float(raw[0]))
                    fileCount += 1
                    self._line2Data(raw, points, fileCount)
                    #print('file #',fileCount)
                    #print('line\n',raw)
                    #print('points\n',points)#CORRECT
            #print('points2\n',points)

            if not breakCondition:
                #print('points again\n',points)
                self._points2Evolutions(points, evolutions, count)
                #print('evolutions\n',evolutions)#FIXME
                #if count>1:
                    #breakCondition = True
                    #actRecords = 3
            else:
                actRecords = count + 1
                print('number of points is ' + str(actRecords))
                break
            

        [t.close() for t in handles]#pylint:disable=expression-not-assigned

        return evolutions, actRecords

    def _deleteTraj(self, outputDir):
        '''
        deletes all the trajectory files
        '''
        files = [outputDir + 'traj' + str(i) for i in range(self.numOfRuns)]
        for traj in files:
            system('rm ' + traj)

        return None

    def _writeEvolutions(self):
        '''
        reads trajectory files, calculates average and std over them and
        writes files means.txt and standDivs.txt
        '''
        evolutions, actRecords = self._makeStatistics()
        system('rm ' + self.outputDir + 'means.txt')
        system('rm ' + self.outputDir + 'standDivs.txt')
        fMeans = open(self.outputDir + 'means.txt', 'a')
        fStd = open(self.outputDir + 'standDivs.txt', 'a')
        for spec in evolutions:
            printMean = spec
            printStd = spec
            for item in evolutions[spec][0:actRecords]:
                printMean += ' ' + str(item[0])
                printStd += ' ' + str(item[1])
            fMeans.write(printMean + '\n')
            fStd.write(printStd + '\n')
        fMeans.close()
        fStd.close()
        return None

    def _writeTimes(self):
        '''
        writes all the times, at which populations were recorded and
        writes them into file times.txt
        '''
        string = str(self.times[0])
        for item in self.times[1:]:
            string += ' ' + str(item)
        fTimes = open(self.outputDir + 'times.txt', 'w')
        fTimes.write(string)
        fTimes.close()
        return None

    def _writeRuntimesStats(self):
        '''
        writes how long it took to run a simulation.
        may fail if trajectories are run in parallel
        '''
        runtimes = []
        files = [self.outputDir + 'timePerReac' + str(i) 
                 for i in range(self.numOfRuns)]
        for f in files:
            with open(f, 'r') as cf:
                runtimes.append(float(cf.read().rstrip('\n')))
            cf.close()
        mean = np.mean(runtimes)
        std = np.std(runtimes)
        with open(self.outputDir + 'runtimeStat.txt', 'w') as wf:
            wf.write(str(mean) + ' ' + str(std))
        wf.close()
        
        return None
    
    def _delRuntimes(self):
        '''deletes information about runtimes
        '''
        files = [self.outputDir + 'timePerReac' + str(i) 
                 for i in range(self.numOfRuns)]
        for f in files:
            system('rm ' + f)
        return None
        
    
    def reorganizeOutput(self, numOfRuns, traj):
        '''
        reads raw data from the simulation output and writes files:
         *means.txt
         *standDivs.txt
         *times.txt
         *parameters.txt
        deletes files which were marked for deletion
        '''
        self.numOfRuns = numOfRuns
        self.traj = traj
        self.makeHeader(numOfRuns, traj)
        self._writeEvolutions()
        print('means and stds are written')
        self._writeTimes()
        #try:
            #self._writeRuntimesStats()
        #except:
            #self.log.warning('runtimes weren\'t saved. 
            #something went wrong. Perhabs you were running jobs in parallel.')
        if not self.traj:
            self._deleteTraj(self.outputDir)
            self._delRuntimes()
        system('rm ' + self.outputDir + 'shell*')
        system('rm ' + self.outputDir + 'run*')
        return None
    
    def _readTimes(self):
        '''
        reads times.txt
        returns times: list of the recorded times
        '''
        print('read times.txt')
        try:
            with open(self.outputDir + 'times.txt', 'r') as content_file:
                content = content_file.read()
            times = [float(item) for item in content.split(' ')]
            print('done reading')
        except FileNotFoundError:
            times = None
            print('WARNING! times.txt is missing. Continue without it.')
        return times
    
    def readMeans(self):
        '''reads means.txt
        returns evolutions: list of np.arrays([populations over time])
        '''
        evolutions = {}
        f = open(self.path2Folder + str("%03d" %self.modelNum) + 
                 '_output' + str(self.simNum) + '/means.txt', 'r')
        #count = 0
        for line in f:
            raw = (line.rstrip('\n')).split(' ')
            evolutions[raw[0]] = \
            scipy.sparse.csr_matrix(np.array([float(item) for item in raw[1:]]))
            #evolutions[raw[0]] = np.array([float(item) for item in raw[1:]])
            #count += 1
            #if count%100:
                #print('line',count)

        return evolutions

    def readStds(self):
        '''reads standDivs.txt
        returns evolutions: list of np.arrays([standard deviations over time])
        '''
        evolutions = {}
        f = open(self.path2Folder + str("%03d" %self.modelNum) + 
                 '_output' + str(self.simNum) + '/standDivs.txt', 'r')
        for line in f:
            raw = (line.rstrip('\n')).split(' ')
            #evolutions[raw[0]] = \
            #scipy.sparse.csr_matrix(np.array([float(item) for item in raw[1:]]))
            evolutions[raw[0]] = np.array([float(item) for item in raw[1:]])
        
        return evolutions
    
    def _readSimData(self):
        '''reads parameters.txt
        stores it as a dictionary: {par.name: par.value}
        '''
        print('reading simulation parameters')
        try:
            header = open(self.outputDir + 'parameters.txt', 'r')
        except FileNotFoundError:
            print('WARNING! parametres.txt is missing, continue without')
            parameters = None
        else:
            line = header.readline()
            parameters = {}
            count = 0
            while not 'Parameters' in line:
                count +=1
                if count > 100:
                    raise ValueError("coulnd't read"+str(self.outputDir)+'parameters.txt')
                self.name = line.rstrip('\n')
                line = header.readline()
            line = header.readline()
            count = 0
            while not 'Command' in line:
                if count > 100:
                    raise ValueError("coulnd't read"+str(self.outputDir)+'parameters.txt')
                _list = line.rstrip('\n').split(' ')
                parameters[_list[0]] = float(_list[1])
                line = header.readline()
            line = header.readline()
            self.howTerm = line.rstrip('\n').replace('howTerm ', '')
            line = header.readline()
            self.whenTerm = int(line.rstrip('\n').replace('whenTerm ', ''))
            line = header.readline()
            self.records = float(line.rstrip('\n').replace('records ', ''))
            line = header.readline()
            line = header.readline()
            self.numOfRuns = int(line.rstrip('\n').replace('numOfRuns ', ''))
            self.traj = bool(line.rstrip('\n').replace('keepTrajectories ', ''))
        return parameters

    def makeStats(self, natData): 
        '''return countAll, countFold, countCat, countAuto, length
        means/stds -- {name: [populations during time steps]}'''
        try:
            print("total number of species in all runs is " + str(len(self.means.keys())))
        except:#pylint:disable=bare-except
            self.means = self.readMeans()
            self.stds = self.readStds()
            print("total number of species in all runs is " + str(len(self.means.keys())))
        #natData = hpClasses.readNativeList(int(self.parameters['maxLength']))
        lengths = set([])     #keeps lengths present in simulation
        countAll = [(0)]*(len(self.times)) 
        countFold = [(0)]*(len(self.times)) 
        countCat = [(0)]*(len(self.times)) 
        countAuto = [(0)]*(len(self.times)) 
        #popStats = {}#lengths distribution in the last moment of simulation
        #FIXME modify for sparse
        for key in self.means.keys():
            #means = self.means[key].A[0]
            means = self.means[key]
            if key.find('f') == -1:
                polLen = len(key)
                lengths.add(polLen)
            else:
                polLen = len(key)-1
                lengths.add(polLen)

            for i in range(len(self.times)):
                countAll[i] += means[i] 
                #adds population of current sequence at time i to 
                #total population of all the sequences seen before 
                fold, cat, autocat = hpClasses.getHPClassOfSeq(key, natData)
                if fold:#TEST
                    countFold[i] += means[i]
                    if cat:
                        countCat[i] += means[i]
                        if autocat:
                            countAuto[i] += means[i]
            #here we store lengths distribution in the last moment of simulation  
            #addToDictNum(popStats, polLen, self.means[key][-1])
            
        print('len', lengths)
        
        return countAll, countFold, countCat, countAuto, lengths

    def _kin2str(self):#TEST
        '''produces string out of kinetic parameters to write in plot title etc
        '''
        title = 'Model #' + str(self.modelNum) + '.' + str(self.simNum) + ':\n'
        for parameter in self.parameters:
            title += str(parameter)+':'
            title += str(self.parameters[parameter]) + ', '
        return title

    def _writeGraphFilename(self, specDir=None):
        '''Results - >  String (filename)

        '''
        def ifNameExists(name, specDir):
            '''check is this current file exists??
            '''
            sR = glob.glob(os.path.join(specDir, name))
            if sR == []:
                return False
            else:
                return True

        if specDir == None:
            specDir = self.outputDir + 'figures/'
        s = '000'
        while ifNameExists(s + '.png', specDir):
            i = int(s)
            i += 1
            if len(str(i)) == 1:#LAME
                s = '00' + str(i)
            elif len(str(i)) == 2:
                s = '0' + str(i)
            elif len(str(i)) > 2:
                s = str(i)
        #if not ifNameExists(s)
        name = s + '.png'
            #if ifNameExists(name):
            #    raise('plot has been overwritten')


        path = os.path.join(specDir, name)

        return path

    def _plotTotalPop(self, fig, countAll):
        '''plots subplot: all specie count against time
        '''
        fig.plot(self.times, countAll, linewidth=4)
        fig.set_yscale('log')
        fig.set_ylabel('molecules count')
        fig.set_xlabel('time')
        fig.set_title("Total count of molecules at each moment")
        return None#times, countAll

    def _plotTypes(self, fig, countFold, countCat, countAuto):
        '''plots subplot: count of several types of species agains time
        '''
        fig.plot(self.times, countFold, linewidth=4, label='folded')
        fig.plot(self.times, countCat, linewidth=4, label='catalysts')
        fig.plot(self.times, countAuto, linewidth=4, label='autocats')
        fig.legend()
        fig.set_ylabel('molecules count')
        fig.set_xlabel('time')
        fig.set_title("count of molecules of various types at each moment")
        return None#(times, countFold), (times, countCat), (times, countAuto)

    def _plotLenDistr(self, fig, mL, lengths, lengthsDistr):
        '''plots length distribution
        '''
        fig.plot(lengths, lengthsDistr, linewidth=4, label=\
            str(mL) + '/' + str(len(self.means.keys())))
        fig.grid(True)
        fig.set_yscale('log')
        fig.set_xscale('log')
        fig.set_ylabel('average population')
        fig.set_xlabel('length')
        fig.set_title("Length distribution in the last moment")
        return None
    
    def getLengthDistribution(self,natData,jointData,nonSteadyPercent):
        lengths = list(jointData.copy().keys())
        mL = max(lengths)
        print("maximum length of a polymer is " + str(mL))
        lenPops = [
            sum([jointData[length][name][0] 
                    for name in jointData[length].keys()]) 
            for length in jointData.keys()
            ]
        tp = sum(lenPops)
        lengthsDistr = [ps/tp for ps in lenPops]
        return lengthsDistr
    
    def plotHPstats(self, natData, jointData=None, 
                    saveFig=False, nonSteadyPercent=0.9):
        '''combines 3 subplots above
        '''
        #pylint:disable=too-many-locals
        maxLength = int(self.parameters['maxLength'])
        print('getting data for plots')
        countAll, countFold, countCat, countAuto, lengths = \
            self.makeStats(natData)
        if jointData == None:
            try:
                jointData = self.jointData
                self.jointData.keys()
            except:#pylint:disable=bare-except
                self.jointData = self.makeDictOfLengths(maxLength, nonSteadyPercent)
                jointData = self.jointData


        mL = max(lengths)
        print("maximum length of a polymer is " + str(mL))
        lengths = list(jointData.copy().keys())
        lenPops = [
            sum([jointData[length][name][0] 
                 for name in jointData[length].keys()]) 
            for length in jointData.keys()
            ]
        tp = sum(lenPops)
        lengthsDistr = [ps/tp for ps in lenPops]


        fig, (ax0, ax1, ax2) = plt.subplots(nrows=3, figsize=(18, 14))
        self._plotTotalPop(ax0, countAll)
        self._plotTypes(ax1, countFold, countCat, countAuto)
        print(lengthsDistr)
        print(list(lengths))
        self._plotLenDistr(ax2, mL, list(lengths), lengthsDistr)

        title = 'Statistics of a HP-wordl simulation run'
        fig.suptitle(title  +  ' for ' + self.name)
        if not saveFig:
            plt.show()
        else:
            plt.suptitle(self._kin2str(), fontsize=20)
            plt.savefig(self._writeGraphFilename())
        
        return (countAll, countFold, countCat, countAuto), (list(lengths), lengthsDistr)

    #def plotLenEvolution(self, show=True):#TODO
        #'''
        #'''
        #return None


    def plotSpecific(self, listOfSeq, timeLims):
        '''plots time series of a given sequences
        '''
        arrays = [self.means[name] for name in listOfSeq]
        for (name, data) in zip(listOfSeq, arrays):
            if not 'f' in name:
                plt.plot(self.times, data, label=name, color='0.85', linewidth=3)
            else:
                plt.plot(self.times, data, label=name, linewidth=3)
        plt.legend()
        plt.title('Time evolutions of selected sequences', fontsize=30)
        plt.ylabel('Population', fontsize=22)
        plt.xlabel('Time', fontsize=22)
        plt.xlim(timeLims)
        plt.show()
        return None

    def plotLenDistrLogLog(self,natData,jointData,nonSteadyPercent,show=True):
        lengthsDistr = \
            self.getLengthDistribution(natData,jointData,nonSteadyPercent)
        plt.plot(list(range(1,25+1)), lengthsDistr, linewidth=4)
        plt.yscale('log')
        plt.xscale('log')
        plt.title(self._kin2str(), fontsize=20)
        if show:
            plt.show()
        else:
            plt.savefig(self._writeGraphFilename())
        return None

    def getSteadyMeanStd(self, nonSteadyPercent):
        '''takes average over time in the final x percent of data:
        x = 1 - nonSteadyPercent
        '''
        border = int(nonSteadyPercent*len(self.times))
        steadyMean = {}
        steadyStd = {}
        try:
            type(self.means)
        except AttributeError:
            print('we have to read means.txt')
            self.means = self.readMeans()
        else:
            pass
        for seq in self.means.keys():
            #means = self.means[seq].A[0]
            means = self.means[seq]
            points = means[border:]
            steadyMean[seq] = np.mean(points)
            steadyStd[seq] = np.std(points)
        
        steadyMeanSorted = OrderedDict(
            sorted(steadyMean.items(), key=lambda t: t[1], reverse=True)
            )
        steadyStdSorted = OrderedDict(
            sorted(steadyStd.items(), key=lambda t: t[1], reverse=True)
            )
        
        return steadyMeanSorted, steadyStdSorted
    
    #def getSteadyStd(self, nonSteadyPercent):
        #border=int(nonSteadyPercent*len(self.times))
        #steady={}
        #for seq in self.means.keys():
            ##stds = self.stds[seq].A[0]
            #stds = self.means[seq]
            #points=stds[border:]
            #steady[seq] = np.mean(points)
        
        #steadySorted = OrderedDict(
            #sorted(steady.items(), key=lambda t: t[1], reverse=True)
            #)
        
        #return steadySorted
    
    def makeDictOfLengths(self, maxLength, nonSteadyPercent):
        '''returns dictionary of ordereder dictionaries 
        it's called jointData everywhere. it has the following structure
        {length: OrderedDict{seq: float}}
        '''
        steadyMean, steadyStd = self.getSteadyMeanStd(nonSteadyPercent)   #sortedDict
        
        steadyLen = {}
        for i in range(1, maxLength + 1):      #initialyze dicts
            steadyLen[i] = {}

        #get sorted dictionary for every key of steadyLen
        for seq in steadyMean:
            if seq.find('f') == -1:
                sLen = len(seq)
            else:
                sLen = len(seq)-1
            if not (steadyMean[seq], steadyStd[seq]) == (0.0, 0.0):
                try:
                    steadyLen[sLen][seq] = (steadyMean[seq], steadyStd[seq])
                except KeyError:
                    print(seq,'length',sLen)
                    raise KeyError

        for length in steadyLen.keys():
            tmp = OrderedDict(
                sorted(steadyLen[length].items(), key=lambda t: t[1], reverse=True)
                )
            steadyLen[length] = tmp

        return steadyLen

    def clustLengths(self,minLength,maxLength,
                     nonSteadyPercent,samp=None,epsilonModifyer={0:0}):#TEST
        ''' returns dict jointLabels'''
        if self.numOfRuns == 1:
            raise ValueError('I cannot cluster data from 1 simulation:'+
                ' standard deviation isn\'t defined')
        try:
            type(self.jointData)
        except:
            self.jointData=self.makeDictOfLengths(maxLength,nonSteadyPercent)
        jointLabels={}
        _labels={}
        labels={}
        epsilons = {}
        
        for length in range(minLength,maxLength+1):
            _labels[length] = []
            labels[length] = {}
            if not self.jointData[length]=={}:
                print('analyzing length '+str(length))
                lenOffset=length-minLength
                means = []
                stds = []
                indxes = {}
                i=-1
                for seq in self.jointData[length].keys():
                    i+=1
                    means.append(self.jointData[length][seq][0])
                    stds.append(self.jointData[length][seq][1])
                    indxes[i]=seq
                print('passed means')
                if samp == None:
                    samp = 10
                jointLabels[length], epsilons[length]=clustList(
                        means,stds,length,samp,epsilonModifyer)
                
                n_clusters = len(set(jointLabels[length])) - (1 if -1 in jointLabels[length] else 0)
                print('Estimated number of clusters: %d' % n_clusters)
            else:
                jointLabels[length] = np.array([])
                indexes = {}
                print('indexes are empty')
            #i=-1
            for (i,seq) in indxes.items():
                try:
                    _labels[length].append((seq, jointLabels[length][i]))
                except IndexError:
                    if not self.jointData[length]==OrderedDict():
                        raise IndexError
                    else:
                        continue
                    
            if not _labels[length]==[]:
                for couple in _labels[length]:
                    addToDictList(labels[length],couple[1],couple[0])
            
            
        return labels, epsilons

    def enumerateAll(self, num2name=False, name2num=False):
        '''makes correspondence seq-name - to integer
        '''
        i = 0
        if name2num and num2name:
            num2nameDict = {}
            name2numDict = {}
            for key in self.means.keys():
                num2nameDict[i] = key
                name2numDict[key] = i
                i += 1
            return name2numDict, num2nameDict
        elif name2num and (not num2name):
            name2numDict = {}
            for key in self.means.keys():
                name2numDict[key] = i
                i += 1
            return name2numDict
        elif num2name and (not name2num):
            num2nameDict = {}
            for key in self.means.keys():
                num2nameDict[i] = key
                i += 1
            return num2nameDict
        else:
            raise ValueError('what to do?')



    def getInitPopFromTraj(self, trajNum, atTime, initFileName):
        '''reads trajectory 
        and writes a file with initial population for future simulations
        '''
        trajFile = open(
            os.path.join(
                self.path2Folder, 
                (str("%03d" %self.modelNum) + '_output' + str(self.simNum)), 
                'traj' + str(trajNum)
                ), 
            'r'
            )
        time = 0
        while not time == atTime:
            line = (trajFile.readline()).rstrip('\n')
            if line[0] == '#':
                continue
            else:
                raw = line.split(',')
                data = raw[1:]
                time = float(raw[0])
                print(time)
        initFile = open(os.path.join(self.path2Folder, initFileName), 'a')
        for point in data:
            initFile.write(point + '\n')
        return None    
    
    #########Trajectory analyzers########
    
    def totalPopTime(self,filename):
        totalPopList = []
        times = []
        with open(self.outputDir+filename) as infile:
            for line in infile:
                if not line[0]=='#':
                    dlist=line.split(',')[0:-1]
                    times.append(float(dlist[0]))
                    totalPopList.append(
                        sum([int((item.split(' '))[1]) for item in dlist[1:]])
                        )

        return times, totalPopList
    
    def seqDict(self,filename,minTime):
        seqDict = {}
        times = []
        with open(self.outputDir+filename) as infile:
            for line in infile:
                if not line[0]=='#':
                    dlist=line.split(',')[0:-1]
                    time = float(dlist[0])
                    if time >= minTime:
                        times.append(time)
                        for couple in dlist[1:]:
                            pair = couple.split(' ')
                            if pair[0] in seqDict.keys():
                                seqDict[pair[0]].append(int(pair[1]))
                            else:
                                seqDict[pair[0]]=[int(pair[1])]

        print(len(times))
        #print(times)
        return seqDict, len(times)
    
    def getFreqs(self,seqDict,maxLength,denominator):
        '''seqDict -- output of seqDict(self,filename,minTime)
        maxLength -- usually 25
        denominator -- number of time steps also output of
        seqDict(self,filename,minTime)
        '''
        seqSumDict = {}
        for seq in seqDict.keys():
            seqSumDict[seq]=sum(seqDict[seq])/denominator

        freqs = dict([(i,{}) for i in  range(1,maxLength+1)])
        for (seq, pop) in seqSumDict.items():
            if 'f' in seq:
                l = len(seq)-1
            else:
                l = len(seq)
            if pop in freqs[l].keys():
                (freqs[l])[pop]+=1
            else:
                (freqs[l])[pop]=1
        for (l, fr) in freqs.items():
            freqs[l]=OrderedDict(sorted(fr.items(), key=lambda t: t[0], reverse=False))
        intFr = {}
        for (l, fr) in freqs.items():
            intFr[l]={}
            for (freq,count) in fr.items():
                counts = list(fr.values())
                freqs = list(fr.keys())
                i = freqs.index(freq)
                intFr[l][freq]=sum(counts[i:])
        
        return freqs,intFr
    
    def plotInLen(self,freqs,title):
        '''
        freqs are either integral frequences or raw ones
        fits are results of fitting those frequences to straight lines (log-log)
        '''
        def fitInLen(freqs):
            fits = {}
            for (length, values) in freqs.items():
                xx = []
                yy = []
                for (pop,freq) in values.items():
                    xx.append(math.log10(pop))
                    yy.append(math.log10(freq))
                    x = np.array(xx)
                    y = np.array(yy)
                    A = np.vstack([x, np.ones(len(x))]).T
                    fits[length] = np.linalg.lstsq(A, y)[0]
            return fits
        
        fits = fitInLen(freqs)
        nc = 3
        minLength=8
        maxLength=25
        fig, axes = plt.subplots(
            nrows=int((maxLength-minLength+1)/2/nc), ncols=nc, figsize=(12, 12)
            )
        index = 0
        for (length,freqs) in freqs.items():
            if length>=minLength and length<=maxLength and length%2==1:
                sortedFreqs = OrderedDict(sorted(freqs.items(),key=lambda t: t[0], reverse=False))
                axes[int((index)/nc),(index)%(nc)].plot(
                    list(sortedFreqs.keys()),list(sortedFreqs.values()),'o'
                    )
                try:
                    m, c = fits[length-1]
                except KeyError:
                    m, c = (0,0)
                else:
                    axes[int((index)/nc),(index)%(nc)].plot(
                        list(sortedFreqs.keys()),
                        [(10**(c)*xi**(m)) for xi in sortedFreqs.keys()],
                        linewidth = 3,
                        label = 'y = '+str("%.2f" %(10**c))+'x^'+str("%.2f" %m)
                        )
                axes[int((index)/nc),(index)%(nc)].set_yscale('log')
                axes[int((index)/nc),(index)%(nc)].set_xscale('log')
                #axes[int((index)/nc),(index)%(nc)].legend()
                axes[int((index)/nc),(index)%(nc)].set_title(str(length)+'-mers')
                index+=1
        
        plt.suptitle(title,fontsize=30)
        plt.savefig(self.outputDir+'inlen.png')

#######EXTRA FUNCTIOS######



def median(mylist):
    '''calculates median, if median is zero:
    tries to find close to median non-zero percentile
    '''
    sorts = sorted(mylist)
    length = len(sorts)
    if not length % 2:
        med = (sorts[int(length / 2)]  +  sorts[int(length / 2) - 1]) / 2.0
    med = sorts[int(length / 2)]
    if med == 0.0:
        i = 1
        while i < 1000:
            med = sorts[int(length *i/(i + 1))]
            i += 1
        if med == 0.0:
            med = 0.0000000000001#BUG
            print('artificial median of 0.0000000000001 is set up')
        else:
            print('variance at ' + str(i) + '/' + str(i + 1))

    return med

def clustList(means, stds, length, samp, epsilonModifyer):
    '''uses a scipy algorithm to cluster data in a list
    '''
    X = np.array([means, [1]*len(means)]).T
    print('got X')
    med = median(stds)
    '''
    if length > 8:
        epsilon=sqrt(med)*4
    elif length > 12:
        epsilon = sqrt(med)*8
    else:
        epsilon = sqrt(med)
    '''
    epsilon = med
    if length in epsilonModifyer.keys():
        epsilon = epsilon*epsilonModifyer[length]
    print('epsilon=' + str(epsilon))
    #jointEpsilon[length] = epsilon
    #Y = StandardScaler(copy=True, with_mean=True, with_std=True).fit_transform(X)
    db = DBSCAN(epsilon, min_samples=samp).fit(X)
    #core_samples = db.core_sample_indices_
    labels = db.labels_

    return labels, epsilon





