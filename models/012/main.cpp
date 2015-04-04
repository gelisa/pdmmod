#include <algorithm>
#include <fstream>
#include <time.h>
#include "totalPopulation.h"
#include "output.h"

// Those modules are for loading parameters and data used by class Specie
#include <map>
#include "parametersLoader.h"

/* General-purpose global dictionary of parameters */
std::map<std::string,Parameter> configDict;

/* HP-model-specific headers and global variables */
#include "nativeListLoader.h"
#include "parametersLoader.h"
std::map<std::string,std::string> catPatterns;
std::map<std::string,int> wellDepths;

void printUsage(){
    std::cout << "Usage:" << std::endl;
    std::cout << "  pdmmod simulateTime <totalTime> <timeBetweenRecords> <outputFileName> [-c <parametersFileName>] [-i <initialPopulationFileName>]" << std::endl;
    std::cout << "  pdmmod simulateReactions <numberOfReactions> <recordingPeriod> <outputFileName> [-c <parametersFileName>] [-i <initialPopulationFileName>]" << std::endl;
    std::cout << "totalTime=0 causes the program to run the simulation until it runs out of possible reactions or indefinitely" << std::endl;
    std::cout << "timeBetweenRecords=0 causes the program to record the population after every reaction" << std::endl;
    std::cout << "numberOfReactions must be a multiple of recordingPeriod" << std::endl;
    std::cout << "parametersFileName is a path to the configuration .ini file. Defaults to parameters.ini" << std::endl;
    std::cout << "initialPopulationFileName is a path to the file holding initial configurations. Defaults to populations.txt" << std::endl;
}

bool cmdOptionExists(char** begin, char** end, const std::string& option){
    return std::find(begin, end, option) != end;
}

char* getCmdOption(char** begin, char** end, const std::string & option){
    char** itr = std::find(begin, end, option);
    if (itr != end && ++itr != end)
        return *itr;
    return NULL;
}

int main (int argc, char** argv){

    /* Parsing command line options */

    // treating nonpositinal arguments first
    int positionalArgc = argc;
    std::string configFileName("parameters.ini");
    if (getCmdOption(argv, argv+argc, "-c") != NULL){
        char* cConfigFileName = getCmdOption(argv, argv+argc, "-c");
        configFileName = std::string(cConfigFileName);
        positionalArgc -= 2;
    }
    std::string initialPopulationFileName("populations.txt");
    if (getCmdOption(argv, argv+argc, "-i") != NULL){
        char* cInitialPopulationsFileName = getCmdOption(argv, argv+argc, "-i");
        initialPopulationFileName = std::string(cInitialPopulationsFileName);
        positionalArgc -= 2;
    }

    // then treating positional arguments
    int simType = -1;
    float totalTime = 0.0;
    float stepLen = 0.0;
    int totalReactions = 0;
    int recordingPeriod = 0;
    std::string outputFilename;
    if (positionalArgc == 5 && std::string(argv[1]).compare("simulateTime") == 0){
        simType = 0;
        //total time of simulation
        totalTime = std::atof(argv[2]);
        //how often to record
        stepLen = std::atof(argv[3]);
        outputFilename = std::string(argv[4]);
    }
    else if (positionalArgc == 5 && std::string(argv[1]).compare("simulateReactions") == 0){
        simType = 1;
        //total number of reactions
        totalReactions = std::atoi(argv[2]);
        recordingPeriod = std::atoi(argv[3]);
        if(totalReactions % recordingPeriod != 0){
            std::cout << "Unrecognized arguments" << std::endl;
            printUsage();
            return 1;
        }
        outputFilename = std::string(argv[4]);
    }
    else {
        std::cout << "Unrecognized arguments" << std::endl;
        printUsage();
        return 1;
    }

    /* Loading parameters */
    readConfig(&configDict, configFileName);
    showConfig(&configDict);

    /* Reading initial conditions from file */
    std::cout << " before beginning" << std::endl;
    TotalPopulation tp(initialPopulationFileName);

    /* Loading HP-model-specific data */
    catPatterns = readCatPatterns("nativeList.txt");
    wellDepths = readWellDepths("nativeList.txt");

    /* Main loop of the simulation */
    std::cout << "beginning" << std::endl;
    std::string prevPops = storePopulations(&tp);
    float prevStep = 0.f;
    std::ofstream myfile;
    myfile.open(outputFilename);
    writeHeaderToFile(&tp, argc, argv, &myfile);
    writeToFile(prevPops, 0.0, &myfile);

    int reacNum = 0;
    clock_t t1,t2;
    int stp;

    t1=clock();
    if (simType == 0){
        while(true){
            if (totalTime == 0.f)
            {
                //TODO
            }
            else{
                stp = tp.stepSimulation();
                reacNum = reacNum+1;
                //std::cout << "after stepping:\n" << tp;
                prevPops = writeOrNotTo(stepLen, &tp, prevStep, prevPops, &myfile);
                prevStep = getPrevStep(stepLen, prevStep, tp.m_t);
                if (tp.m_t >= totalTime){
                    myfile.close();
                    break;
                }
                if (stp==1){
                    break;
                }
            }
        }
    }
    else if (simType == 1){
        while(true){
            stp = tp.stepSimulation();
            reacNum = reacNum + 1;
            if (reacNum % recordingPeriod == 0)
                writeToFile(storePopulations(&tp), tp.m_t, &myfile);

            if (stp == 1 || reacNum >= totalReactions){
                myfile.close();
                break;
            }
        }
    }
    t2=clock();
    std::cout << "status is " << stp << std::endl;
    if (simType == 0 && tp.m_t < totalTime && stp == 1){
        std::cout <<"simulations is over. prevStep is " << prevStep << std::endl;
        for (float time=(prevStep+stepLen);time<=totalTime;time=time+stepLen){
            writeToFile(prevPops,time,&myfile);
        }

        myfile.close();
    }

    float diff = ((float)t2-(float)t1);
    float timePerReac = diff/CLOCKS_PER_SEC/reacNum;
    std::cout << "Number of reactions is " << reacNum << std::endl;
    std::ofstream timeFile;
    timeFile.open ("runtime.txt");
    timeFile << timePerReac << std:: endl;
    timeFile.close();
    std::cout << "total time is " << tp.m_t << std::endl;

    return 0;
}