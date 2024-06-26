
import re
import pandas as pd
import numpy as np
from datetime import date as rx
import datetime as xl





class CII:
    """
    Fuel data will be stored in a dict in the following format
    { "HFO" : 15,
      "MGO" : 30}
    """

    def __init__(self,vesselType,vesselName,DWT,distance,fuelData):


        self.fuelCoefs = {
            "Gas" : 3.206,
            "LFO" : 3.151,
            "HFO" : 3.114,
            "Propane" : 3.000,
            "Butane" : 3.030,
            "LNG" : 2.750,
            "Methanol" : 1.375,
            "Ethanol" : 1.913,
            "VLSFO" : 3.151
        }

        self.ddVectors = pd.read_excel(r"C:\Dashboard\tco_ui\tco_ui\tco\ui\ddVectors 1.xlsx")
        self.ciiRefVals = pd.read_excel(r"C:\Dashboard\tco_ui\tco_ui\tco\ui\ciiRefVals 1.xlsx")
        self.reductionVals = pd.read_excel(r"C:\Dashboard\tco_ui\tco_ui\tco\ui\ciiReductionVals 1.xlsx")

        self.vesselType = vesselType
        self.DWT = DWT
        self.distance = distance

        self.fuelData = fuelData

        self.vesselName = vesselName


        self.runModel()


    def runModel(self):
        #will run the CII model in order, pulling data from prestored datasets based off of vessel type and then run
        #cii ref , cii attained, and cii rating

        #modify vessel name based off of DWT
        vesselType = self.modifyVesselType(self.vesselType,self.DWT)

        #CII REF
        refVals = self.ciiRefVals[self.ciiRefVals["Ship Type"] == vesselType]
        a = refVals["a"]
        c = refVals["c"]
        ciiRef = round(self.calcCiiRef(a,c),2)

        #CII ATTAINED
        self.ciiAtt  = self.calcCiiAtt(self.fuelData)

        #CII REQUIRED
        if self.vesselType == "Bulk Carrier":
            reductVals = self.reductionVals[self.reductionVals["Ship Type"] == self.vesselType].values.flatten().tolist()[1:]
        else:
            reductVals = self.reductionVals[self.reductionVals["Ship Type"] == vesselType].values.flatten().tolist()[1:]

        ciiReq = self.calcCiiReq(ciiRef,reductVals)


        #CII RATING
        if self.vesselType == "Bulk Carrier":
            ddVectors = self.ddVectors[self.ddVectors["Ship Type"] == self.vesselType].values.flatten().tolist()[1:]
        else:
            ddVectors = self.ddVectors[self.ddVectors["Ship Type"] == vesselType].values.flatten().tolist()[1:]


        ciiRating = self.calcCiiRating(self.ciiAtt,ciiReq,ddVectors)


        #CII RANGES
        ciiRanges = self.calcCiiRanges()




        print("CII Reference : ", type(ciiRef) , ciiRef)
        print("CII Attained : ", type(self.ciiAtt) , self.ciiAtt)
        print("CII Required : ", type(ciiReq), ciiReq)
        print("CII Rating : ", type(ciiRating), ciiRating)


        ciiAtt = self.ciiAtt.loc[0, :].values.tolist()
        results , results_path = self.exportResults(ciiReq,ciiAtt,ciiRating)
        self.results_path = results_path



    def exportResults(self,ciiReq,ciiAtt,ciiRating):
        results = pd.DataFrame(columns = ["Metric","2019*","2020*","2021*","2022*","2023","2024","2025","2026","2027","2028*","2029*","2030*"])


        #need to do this before we append the string to the front of the list
        ciiRatio = ["CII Ratio"] + [round(float(ciiAtt[i])/float(ciiReq[i]),2) for i in range(0,len(ciiAtt))]

        ciiReq = ["CII Required"] + ciiReq
        ciiAtt = ["CII Attained"] + ciiAtt
        ciiRating = ["CII Rating"] + ciiRating


        results.loc[len(results)] = ciiReq
        results.loc[len(results)] = ciiAtt
        results.loc[len(results)] = ciiRatio
        results.loc[len(results)] = ciiRating

        results_path = r"C:\Dashboard\tco_ui\tco_ui\tco\ui\CII Results\CII RESULTS-" + str(self.vesselName) + ".xlsx"

        # Remove all characters from the vessel name that can't be saved to a file name
        invalid_chars = r'[:/\\*?"<>|\n]'
        self.vesselName = re.sub(invalid_chars, "", self.vesselName)


        results.to_excel(r"C:\Dashboard\tco_ui\tco_ui\tco\ui\CII Results\CII RESULTS-" + str(self.vesselName) + ".xlsx")

        self.results = results



        return results , results_path



    def modifyVesselType(self,vesselType,DWT):
        #modifies the name of the vessel type in the case that it is conditional on DWT

        modifyTypes = ["Bulk Carrier","Gas Carrier","General Cargo Ship","LNG Carrier"]

        if vesselType in modifyTypes:

            if vesselType == "Bulk Carrier":
                if DWT >= 279000:
                    print("Large Bulk Carrier detected, setting DWT to 279000")
                    self.DWT = 279000
                    return vesselType + " Big"
                else:
                    return vesselType + " Small"

            if vesselType == "Gas Carrier":
                if DWT >= 65000:
                    return vesselType + " Big"
                else:
                    return vesselType + " Small"

            if vesselType == "General Cargo Ship":
                if DWT >= 20000:
                    return vesselType + " Big"
                else:
                    return vesselType + " Small"

            if vesselType == "LNG Carrier":
                if DWT >= 100000:
                    return vesselType + " Big"
                elif 65000 <= DWT < 100000:
                    return vesselType + " Mid"
                else:
                    print("Small LNG Carrier Detected, setting DWT to 65000")
                    self.DWT = 65000
                    return vesselType + " Small"
        else:
            return vesselType


    def calcCiiRef(self,a,c):

        ciiRef = float(a * (self.DWT) ** (-c))

        return ciiRef

    def calcCiiAtt(self,fuelData):
        #calculate total emmissions

        #fuel data is sent in as a list of dicts, {type:consumption}
        #should return a list of CIIATT vals for 2019-2030 REGARDLESS OF DATES GIVEN
        #assume the dates given are from 2023-2027
        #use a 2.6% per year modifier to estimate fuel values outside of 2023-2027 range

        modifier = 0.026

        ciiAtt = pd.DataFrame(columns=[2019,2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030])

        #loop through 2023-2027 data
        for index,f in enumerate(fuelData):
            #calculate total emissions based off of fuel data (type/mass burned)
            emissions = self.calculateEmmisions(f)
            emissions = round(((emissions*10**6) / (self.distance*self.DWT)),2)

            ciiAtt.loc[0,index+2023] = emissions

        # < 2023
        for i in range(2022,2018,-1):
            ciiAtt.loc[0,i] = round(ciiAtt.loc[0,i+1]*(1-modifier),2)

        # > 2023
        for i in range(2028,2031):
            ciiAtt.loc[0,i] = round(ciiAtt.loc[0,i-1]*(1+modifier),2)

        return ciiAtt

    def calculateEmmisions(self,fuelData):

        totalEmm = 0

        for fuelType in fuelData:
            #fuel coeff * mass of fuel consumed
            thisEmm = self.fuelCoefs[fuelType] * fuelData[fuelType]
            totalEmm += thisEmm

        return totalEmm

    def calcCiiReq(self,ciiRef,reductVals):

        ciiReqVals = []

        for z in reductVals:
            ciiReqVals.append(round(float(ciiRef * (100-z*100)/100),2))


        return ciiReqVals

    def calcCiiRating(self,ciiAtt,ciiReq,ddVectors):

        ciiRatings = []

        years = [2019,2020,2021,2022,2023,2024,2025,2026,2027,2028,2029,2030]

        for index,y in enumerate(years):

            checkVal = ciiAtt.loc[0,y]/float(ciiReq[index])

            if checkVal < ddVectors[0]: ciiRatings.append("A")
            if ddVectors[1] > checkVal > ddVectors[0]: ciiRatings.append("B")
            if ddVectors[2] > checkVal > ddVectors[1]: ciiRatings.append("C")
            if ddVectors[3] > checkVal > ddVectors[2]: ciiRatings.append("D")
            if checkVal > ddVectors[3] : ciiRatings.append("E")

        return ciiRatings

    def calcCiiRanges(self):
        #calculate the CII ranges to be used in the CII plot
        #saves ranges as .xlsx to be read in by CII plot method
        pass



"""fuelData = [{"HFO" : 2477.04},{"HFO" : 2677.04}]

DWT = 26438
distance = 28123.2

XGIT = CII("Gas Carrier","XGIT-FUEL",DWT,distance,[{"HFO" : 2105.48},{"HFO" : 2126.54},{"HFO" : 2147.80},{"HFO" : 2169.28},{"HFO" : 2190.98}])
XGITRESULTS = XGIT.exportResults()"""

"""
silicone = CII("Gas Carrier","Silicone",DWT,distance,[{"HFO" : 2151.80},{"HFO" : 2194.84},{"HFO" : 2238.74},{"HFO" : 2283.51},{"HFO" : 2329.18}])
silicone = silicone.exportResults()

SPC = CII("Gas Carrier","SPC",DWT,distance,[{"HFO" : 2160.23},{"HFO" : 2214.23},{"HFO" : 2271.80},{"HFO" : 2339.96},{"HFO" : 2477.04}])
SPC = SPC.exportResults()

icebreak = CII("Gas Carrier","Icebreaking",DWT,distance,[{"HFO" : 2214.97},{"HFO" : 2303.57},{"HFO" : 2407.23},{"HFO" : 2527.59},{"HFO" : 2666.61}])
icebreak = icebreak.exportResults()"""


"""ciiData = pd.read_excel("kentCIIDATA.xlsx")
ciiRanges = pd.read_excel("kentRangesNorm.xlsx")


am.ciiPlot(ciiData,"Year",["Icebreaking","XGIT-FUEL","Silicone","SPC"],"kentRangesNorm")"""
#read in kent data
"""
kentRanges = pd.read_excel("kentRanges.xlsx",index_col="Boundary")
cols = kentRanges.columns #remove boundary col
print(kentRanges)

for c in cols:
    #flip
    kentRanges[c] = 15- kentRanges[c]
    #normalize
    kentRanges[c]=(kentRanges[c]-kentRanges[c].min())/(kentRanges[c].max()-kentRanges[c].min())
    #multiply by 10
    kentRanges[c] = kentRanges[c] * 10

kentRanges.drop(kentRanges.tail(1).index,inplace=True) # drop last n rows

#subtract each val from max val  (14.6)
print(kentRanges)

kentRanges.to_excel("kentRangesNorm.xlsx")

am.ciiBG("kentRangesNorm")"""

