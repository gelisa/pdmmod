#include "parametersLoader.h"
#include "inih/cpp/INIReader.h"
#include <cstdlib>
#include <iostream>

void readConfig(std::map<std::string,Parameter>* dict, std::string filename){

    INIReader reader("parameters.ini");
    if (reader.ParseError() < 0) {
        std::cout << "Can't load parameters.ini\n";
        exit(1);
    }
    dict->emplace("monomerBirthH",          (float) reader.GetReal("kinetic model", "monomerBirthH", 0.0));
    dict->emplace("monomerBirthP",          (float) reader.GetReal("kinetic model", "monomerBirthP", 0.0));
    dict->emplace("growth",                 (float) reader.GetReal("kinetic model", "growth", 0.0));
    dict->emplace("unfoldedDegradation",    (float) reader.GetReal("kinetic model", "unfoldedDegradation", 0.0));
    dict->emplace("unfoldingCoefficient",   (float) reader.GetReal("kinetic model", "unfoldingCoefficient", 0.0));
    dict->emplace("foldedDegradation",      (float) reader.GetReal("kinetic model", "foldedDegradation", 0.0));
    dict->emplace("hydrophobicEnergy",      (float) reader.GetReal("kinetic model", "hydrophobicEnergy", -1.0));
    dict->emplace("maxLength",              (int) reader.GetInteger("kinetic model", "maxLength", -1));
    // explicit type convertions are required because GetReal() returns double and GetInteger() returns long int

    return;
}

void showConfig(std::map<std::string,Parameter>* dictionary){
    std::cout << "Parameters: ";
    for(auto it=dictionary->begin(); it!=dictionary->end(); it++)
        std::cout << it->first << "=" << (it->second).getString() << " ";
    std::cout << std::endl;
    return;
}