#include <map>
#include <string>
#include <iostream>
#include <math.h>
#include "parameter.h"
#include "specie.h"


/* hp-model 
 * monomers import 
 * degradation
 * folded degradation
 * growth
 * false degradation
 * 
 */

/*DATA
 * catPattern -- string. (cases)
 * interp.:
 *  - if consists of 'H' and 'P' then represents a catalytic site of a given catalyst.
 *  - if it's 'N' then it means the sequence is NOT a catalyst
 * 
 * catPatterns -- dict. {string: string}
 * interp. a dictionary from monomer sequence string to catalytic pattern string
 * 
 * wellDepth -- dict. {string: int}
 * interp. a dictionary form monomer sequence string to potential well depth (energy of folded state)
 */


#include <map>

extern std::map<std::string,Parameter> configDict;

/* HP-model-specific global variables */
extern std::map<std::string,std::string> catPatterns;
extern std::map<std::string,int> wellDepths;


Specie::Specie(std::string id){
    m_id = id;
    
    //if sequence doesn't have HH in its sequence it cannot be substrate for catalyzed growth
    if (m_id.find(std::string("HH"))==std::string::npos){
        m_substrate = std::string("N");
        m_product = false;
    }
    //otherwise we need to check how long the substrate site is
    else{
        std::string maxPat = std::string("HHHHHHHH");
        int patLength=8;
        for (int i=0;i<patLength-1;i++){
            int subLen=patLength-i;
            std::string pat= maxPat.substr(i,subLen);
            if (m_id.find(pat)!=std::string::npos){
                m_substrate = pat;
                if (subLen>2){
                    m_product = true;
                }
                else{
                    m_product = false;
                }
                break;
            }
        }
    }
    //if sequence isn't folded (it doesn't have 'f' letter)
    if (m_id.find(std::string("f"))==std::string::npos){
        m_folded = false;
        //its lenght is the length of the m_id
        m_length = m_id.length();
        //it's not a catalyst
        m_catalyst = std::string("N");
        auto it = wellDepths.find(m_id);
        if (it!=wellDepths.end()){
            m_native = (it -> second);
        }
        else{
            m_native = 0;
        }
        
    }
    //if sequence is folded (it has 'f' in front of the actual sequence)
    else{
        m_folded = true;
        //so the length of the sequence is shorter than m_id by 1.
        m_length = m_id.length()-1;
        //it can be a catalyst
        //if it's a catalyst we'll get a catPattern, if not we'll get "N" as m_catalyst
        m_catalyst = catPatterns[m_id.substr(1,m_length)];
        m_native = wellDepths.find(m_id.substr(1,m_length)) -> second;
    }
    
}
//Overloading <<
std::ostream& operator<<(std::ostream& os, const Specie& sp)
{
    os << sp.m_id  ;
    return os;
}
//methods


//Defining reactions here

std::list<Reaction> Specie::reactions(Specie specie){
    //parameters
    float aH = configDict["monomerBirthH"].getFloat();
    float aP = configDict["monomerBirthP"].getFloat();
    int maxLength = configDict["maxLength"].getInt();
    float alpha = configDict["growth"].getFloat();
    float d = configDict["unfoldedDegradation"].getFloat();
    float dF = configDict["foldedDegradation"].getFloat();
    float k_unf = 0.1;//configDict["unfolding"].getFloat();
    float eH = configDict["hydrophobicEnergy"].getFloat();
    
    //all the reactions two species can have
    std::list<Reaction> allReactions;

    // 'H' and 'P' monomers are being produced from activated monomers, concentration of which is const.
    if (m_id==std::string("")){
        if (specie.m_id==std::string("")){
            Reaction importH(m_id, 0, specie.m_id, 0, aH);
            importH.addProduct(std::string("H"),1);
            allReactions.push_back(importH);
            
            Reaction importP(m_id, 0, specie.m_id, 0, aP);
            importP.addProduct(std::string("P"),1);
            allReactions.push_back(importP);
        }
    }
    //monomolecular reactions
    else if (m_id == specie.m_id){
        //if it's not folded
        if (m_folded == false){
            //it degrades
            Reaction degradation(m_id,1,specie.m_id,0,d);
            allReactions.push_back(degradation);
            //and might fold
            if (m_native!=0){
                Reaction fold(m_id,1,specie.m_id,0,k_unf*exp(eH*m_native));
                fold.addProduct(std::string("f")+m_id,1);
                allReactions.push_back(fold);
            }
        }
        else{
            //folded degrade too
            Reaction degradationF(m_id,1,specie.m_id,0,dF);
            allReactions.push_back(degradationF);
            //and unfold
            Reaction unfold(m_id,1,specie.m_id,0,k_unf);
            unfold.addProduct(m_id.substr(1,m_length),1);
            allReactions.push_back(unfold);
        }
        
        //it grows if it's not of a max length and not folded
        if (m_length != maxLength && m_folded == false) {
            Reaction growH(m_id,1,specie.m_id,0,alpha);
            growH.addProduct(m_id+std::string("H"),1);
            allReactions.push_back(growH);
            
            Reaction growP(m_id,1,specie.m_id,0,alpha);
            growP.addProduct(m_id+std::string("P"),1);
            allReactions.push_back(growP);
        }
        //false degradation (we are blind if sequence grows too long)
        else if (m_length == maxLength && m_folded == false){
            Reaction falseGrowH(m_id,1,specie.m_id,0,alpha);
            allReactions.push_back(falseGrowH);
            
            Reaction falseGrowP(m_id,1,specie.m_id,0,alpha);
            allReactions.push_back(falseGrowP);
        }
       
    }
    //binary reactions TODO
    /*else if (specie.m_catalyst && m_folded == false){
        if (m_length < maxLength){
            Reaction catGrowth(m_id,1.specie.m_id,1,)
        }
    }*/
    
    return allReactions;
}

Specie::~Specie(){

}
