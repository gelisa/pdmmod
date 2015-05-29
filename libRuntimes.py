#!/usr/bin/python
import subprocess
from os import system as system
#from statistics import mean
#from statistics import stdev
from math import sqrt as sqrt
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import scipy.optimize as optimization
from numpy import array
from numpy import polyfit
from numpy import poly1d
from numpy import linspace
import numpy as np
from matplotlib.legend_handler import HandlerLine2D
import libSimulate

'''DATA
* numSpec -- int.
  interp. number of species types
* population -- int. 
  interp. the number of molecules of each monomer
* command -- string. 
  interp. simulation run command with parameters, like ./pdmmdo 10 1 x
* runs -- int.
  interp. the number of times simulation is being run
* currPops -- List [int.]
  interp. list of the populations with which simulations are being run
* species -- list [int.]  
  interp. list of number of species with which simulations are being run
* arrayOfChanges -- one of:
  - currPops
  - species
'''


def changeInitPop(numSpec,population): 
    '''
    goes to populations.txt and changes population of each species to a given one as well as number of species
    '''
    popFile = open("populations.txt", mode='w', encoding='utf-8')
    for i in range(numSpec):
        popFile.write(str("%04d" %(i+1))+"_1 "+str(population)+"\n")
    popFile.close()
    
    return None

def changeParameters(collRate,numSpec):
    '''
    goes to parameters.ini and changes number of species and collision rate
    '''
    popFile = open("parameters.ini", mode='w', encoding='utf-8')
    popFile.write("[kinetic model]\n")
    popFile.write("specNumber = "+str(numSpec)+"\n")
    popFile.write("collRate = "+str(collRate)+"\n")
    popFile.close()
    
    
    return None

def getSimTime(simulation):
    '''
    runs the simulation and then retrieves its running time
    '''
    def runtimesStats(simulation):
        runtimes = []
        files = [simulation.outputDir+'timePerReac'+str(i) 
                 for i in range(simulation.numOfRuns)]
        for f in files:
            with open(f,'r') as cf:
                runtimes.append(float(cf.read().rstrip('\n')))
            cf.close()
        mean = np.mean(runtimes)
        std = np.std(runtimes)
        return mean, std
    
    simulation.runSeveralSeries()
    simulation.reorganizeOutput()
    with open(simulation.outputDir+'runtimeStat.txt','r') as sf:
        [time, timeStd] = [float(item) for item in sf.readline().split(' ')]
    
    return time, timeStd

#def getTimeStat(command,numSpec,population,runs):
    #'''runs the simulation several times with fixed parameters and then returns average time of running
    #'''
    #changeInitPop(numSpec,population)
    #times=[]
    #for i in range(runs):
        #time, retValue = getSimTime(command)
        #while retValue == 2:
            #print('rerun')
            #time, retValue = getSimTime(command)
            
        #times.append(time)
    
    #ave = mean(times)
    #stdDev = stdev(times)
    #print(ave, stdDev)
    #return ave, stdDev

def runSeveralChangePop(command,runs,numSpec,currPops):#TEST
    '''runs several simulations with different population of the fixed number of species
    '''
    system('rm runTemp.txt && touch runTemp.txt' )
    for population in currPops:
        pair=getTimeStat(command,numSpec,population,runs)#average time and standard deviation of it.
        with open("runTemp.txt", "a") as myfile:
            myfile.write(str(population*numSpec)+' '+str(pair[0])+' '+str(pair[1])+'\n')
        #numSpec=numSpec+steps[i]

    
    return None

def runSeveralChangeNumSpec(modelNum,termCond,numOfRuns,population,species):#TEST
    '''runs several simulations with different number of species but fixed population of every specie
    '''
    
    traj = True
    log_level = 'INFO'
    rewrite = True
    s = libSimulate.Simulation(
            modelNum,termCond,rewrite,None,numOfRuns,traj,log_level)
    system('touch '+s.path2Folder+'runTemp.txt' )
    for numSpec in species:
        changeParameters(collRate,numSpec)
        s = libSimulate.Simulation(
            modelNum,termCond,rewrite,None,numOfRuns,traj,log_level)
        changeInitPop(numSpec,population)
        time, timeStd = getSimTime(s)
        
        with open("runTemp.txt", "a") as myfile:
            myfile.write(str(numSpec)+' '+str(time)+' '+str(timeStd)+'\n')
        #numSpec=numSpec+steps[i]

    
    return None

def runSeveralChangeNumSpec2(command,runs,population,species,collRate):#TODO
    '''runs several simulations with different number of species but fixed population of every specie
    also changes parameters.ini
    '''
    system('rm runTemp.txt && touch runTemp.txt' )
    for numSpec in species:
        changeParameters(numSpec,collRate)
        pair=getTimeStat(command,numSpec,population,runs)#average time and standard deviation of it.
        with open("runTemp.txt", "a") as myfile:
            myfile.write(str(numSpec)+' '+str(pair[0])+' '+str(pair[1])+'\n')
        #numSpec=numSpec+steps[i]

    
    return None

def analyzeRuntime(command,runs,numOfPoints,filename):
    '''
    '''
    runtimes=[]
    myfile = open(filename,'rt')
        
    for i in range(numOfPoints):
        raw=((myfile.readline()).rstrip('\n')).split(' ')
        if not raw ==['']:
            runtimes.append((int(raw[0]),float(raw[1]),float(raw[2])))
    
    
    
    ratios=[]
    for i in range(1,len(runtimes)):
        m=(runtimes[i][1]-runtimes[i-1][1])/(runtimes[i][0]-runtimes[i-1][0])
        e=sqrt((runtimes[i][2])**2+(runtimes[i-1][2])**2)/(runtimes[i][0]-runtimes[i-1][0])
        ratios.append((runtimes[i][0],m,e))
    
    #print(ratios)
    
    return runtimes, ratios
    
def plotRuntimes(runtimes,ratios,title):
    '''runtimes fitting'''
    x=[r[0] for r in runtimes]
    y=[r[1]*10**6 for r in runtimes]
    y_err=[r[2]*10**6 for r in runtimes]
    
    z = polyfit(x, y, 1)
    f = poly1d(z)
    
    z2 = polyfit(x, y, 2)
    f2 = poly1d(z2)
    
    x_new = linspace(x[0], x[-1], 50)
    y_new = f(x_new)
    y_new2= f2(x_new)
    
    '''ratios fitting'''
    xr=[r[0] for r in ratios[2:]]
    yr=[r[1] for r in ratios[2:]]
    zr=polyfit(xr, yr, 1)
    fr = poly1d(zr)
    xr_new = linspace(xr[0], xr[-1], 50)
    yr_new = fr(xr_new)
    
    fig, (ax0, ax1) = plt.subplots(nrows=2,sharex=False)
    
    
    ax0.errorbar(x,y,yerr=y_err,fmt='o')
    ax0.plot(x_new,y_new,label='y = '+'%.2e' %z[0]+' x +'+'%.2e' %z[1])
    ax0.plot(x_new,y_new2,label='y = '+'%.2e' %z2[0]+' x^2 +'+'%.2e' %z2[1]+' x '+'%.2e' %z2[2])
    ax1.plot(xr_new,yr_new,label='y = '+'%.2e' %zr[0]+' x +'+'%.2e' %zr[1])
    for i in range(len(runtimes)):
        element=runtimes[i]
    
        rat=ratios[i-1]
        ax1.errorbar(rat[0],rat[1],yerr=rat[2],fmt='-o')
        
    #ax0.set_yscale('log')
    #ax0.set_xscale('log')
    #ax1.set_xscale('log')
    ax0.legend(loc=4)
    ax1.legend(loc=4)
    ax0.set_title('Simulation run time vs number species types in the simulation')
    ax1.set_title('Current slope of the graph above')
    ax0.set_ylabel('runtime, microseconds')
    #plt.savefig('timeStats.pdf')
    fig.suptitle(title)
    plt.show()
    return None

def analyzeFile(filename):
    runtimes=[]
    myfile = open(filename,'rt')
    for line in myfile:
        raw=(line.rstrip('\n')).split(' ')
        if not raw ==['']:
            runtimes.append((int(raw[0]),float(raw[1]),float(raw[2])))
    ratios=[]
    for i in range(1,len(runtimes)):
        m=(runtimes[i][1]-runtimes[i-1][1])/(runtimes[i][0]-runtimes[i-1][0])
        e=sqrt((runtimes[i][2])**2+(runtimes[i-1][2])**2)/(runtimes[i][0]-runtimes[i-1][0])
        ratios.append((runtimes[i][0],m,e))
    
    x=[r[0] for r in runtimes] #number of specs
    y=[r[1]*10**3 for r in runtimes] #time per reaction
    y_err=[r[2]*10**3 for r in runtimes] #std of time per reaction
    
    #z = polyfit(x, y, 1)
    #print(z)
    #f = poly1d(z)
    #_x = (np.array(x))[:,np.newaxis]
    #k = np.linalg.lstsq(_x, y)[0]
    #z = (k, 0.0)
    ### if we want to fit intercept too
    _x = np.vstack([np.array(x),np.ones(len(x))]).T
    k, b = np.linalg.lstsq(_x, y)[0]
    z = (k, b)
    def f(x):
        return k*x+b
    
    z2 = polyfit(x, y, 2)
    f2 = poly1d(z2)
    
    x_new = linspace(x[0], x[-1], 50)
    y_new = [f(x) for x in x_new]
    y_new2= f2(x_new)
    
    '''ratios fitting'''
    xr=[r[0] for r in ratios[2:]]
    yr=[r[1] for r in ratios[2:]]
    zr=polyfit(xr, yr, 1)
    fr = poly1d(zr)
    xr_new = linspace(xr[0], xr[-1], 50)
    yr_new = fr(xr_new)
    #print(ratios)    
    return (x,y,y_err),(x_new, y_new, y_new2), (xr_new, yr_new), ratios,(z,z2,zr)

def plotSeveral(filenames):#TODO
    '''filenames = [string]
    '''
    fig, (ax0, ax1) = plt.subplots(nrows=2,sharex=False)
    labCols = dict(
        zip(filenames,cm.rainbow(np.linspace(0, 1, len(filenames))))
        )
    for filename in filenames:
        data, lines, slope, ratios, fits = analyzeFile(filename)
        col = labCols[filename]
        if not filename.find('pssa')== -1:
            ax0.errorbar(data[0],data[1],yerr=data[2],fmt='v',
                         color = col,
                         markersize=12)
            ax0.plot([],[],marker='v',
                        markersize=12,
                        color = col,label='PDM')
            ax0.plot(lines[0],lines[1],
                     linewidth=3,
                     color = col)
            print('PDM: y = '+'%.2e' %fits[0][0]+' x'+'%.2e' %fits[0][1])
        elif not filename.find('stochkit')== -1:
            ax0.errorbar(data[0],data[1],yerr=data[2],fmt='o',
                         color = col,markersize=12)
            ax0.plot([],[],marker='o',
                        markersize=12,
                        color = col,label='SSA')
            ax0.plot(lines[0],lines[2],
                     linewidth=3,
                     color = col)
            print('SSA: y = '+
                    '%.2e' %fits[1][0]+' x^2 +'+
                    '%.2e' %fits[1][1]+' x '+
                    '%.2e' %fits[1][2],)
        else:
            ax0.errorbar(data[0],data[1],yerr=data[2],fmt='D', 
                        color = col,markersize=12)
            ax0.plot([],[],marker='D',
                        markersize=12,
                        color = col,label='PDMmod')
            ax0.plot(lines[0],lines[1],
                     linewidth=3,
                     color = col)
        #ax1.plot(slope[0],slope[1],label='y = '+'%.2e' %fits[2][0]+' x +'+'%.2e' %fits[2][1])
            print('PDMmod: y ='+'%.2e' %fits[0][0]+
                        ' x'+'%.2e' %fits[0][1])
        for i in range(len(data[1])):
            element=data[1][i]
        
            rat=ratios[i-1]
            ax1.errorbar(rat[0],rat[1],yerr=rat[2],fmt='-o',color = col)
        
    
    ax0.legend(loc=4,fontsize=20)
    ax1.legend(loc=4,fontsize=20)
    ax0.set_title('Simulation run time vs number species types in the simulation',
                  fontsize = 20)
    ax1.set_title('Current slope of the graph above',
                  fontsize = 20)
    ax0.set_ylabel('t, ms',
                   fontsize =16)
    ax0.set_xlabel('N',fontsize=16)
    #plt.savefig('timeStats.pdf')
    #fig.suptitle(title)
    plt.show()
    return None

