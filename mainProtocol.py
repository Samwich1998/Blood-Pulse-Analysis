"""
    Written by Samuel Solomon
    
    --------------------------------------------------------------------------
    Program Description:
    
    Perform signal processing to filter blood pulse peaks. Seperate the peaks,
    and extract key features from each pulse. 
    
    --------------------------------------------------------------------------
    
    Modules to Import Before Running the Program (Some May be Missing):
        %conda install matplotlib
        %conda install openpyxl
        %conda install numpy
        %pip install pyexcel
        %pip install pyexcel-xls
        %pip install pyexcel-xlsx;
        %pip install BaselineRemoval
        %pip install peakutils
        %pip install lmfit
        %pip install findpeaks
        %pip install scikit-image
        
    --------------------------------------------------------------------------
"""

# -------------------------------------------------------------------------- #
# ---------------------------- Imported Modules ---------------------------- #

# Basic Modules
import os
import sys
import shutil
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

from natsort import natsorted
# Import Data Extraction Files (And Their Location)
sys.path.append('./Helper Files/Data Aquisition and Analysis/')  # Folder with All the Helper Files
import excelProcessing

# Import Analysis Files (And Their Locations)
sys.path.append('./Data Aquisition and Analysis/_Analysis Protocols')  # Folder with All the Helper Files
sys.path.append('./Helper Files/Data Aquisition and Analysis/_Analysis Protocols')  # Folder with All the Helper Files
import gsrAnalysis
import pulseAnalysis
import chemicalAnalysis
import temperatureAnalysis

# Import Machine Learning Files (And They Location)
sys.path.append("./Helper Files/Machine Learning/")
import machineLearningMain   # Class Header for All Machine Learning
import featureAnalysis       # Functions for Feature Analysis


from numpy import arange

import matplotlib as mpl
from matplotlib import pyplot as plt
from matplotlib import cm
from matplotlib.colors import LinearSegmentedColormap

N = 17
data = np.arange(N +1)


# =================
## custom colormap:

# red-green colormap:
cdict = {'blue':   [(0.0,  0.0, 0.0),
                   (0.5,  1.0, 0),
                   (1.0,  1.0, 1.0)],

         'red': [(0.0,  0.0, 0.0),
                   (0.25, 0.0, 0.0),
                   (0.75, 1.0, 0.5),
                   (1.0,  0.5, 0)],

         'green':  [(0.0,  0.0, 0.0),
                   (0.5,  0.0, 0.0),
                   (1.0,  1.0, 0)]}

red_green_cm = LinearSegmentedColormap('RedGreen', cdict, N)

colors = cm.get_cmap(red_green_cm, N)

# fig = plt.figure()



# -------------------------------------------------------------------------- #
# --------------------------- Program Starts Here -------------------------- #

if __name__ == "__main__":
    # ---------------------------------------------------------------------- #
    #    User Parameters to Edit (More Complex Edits are Inside the Files)   #
    # ---------------------------------------------------------------------- #    

    # Analysis Parameters
    timePermits = False                     # Construct Plots that Take a Long TIme
    plotFeatures = False                     # Plot the Analyzed Features
    saveAnalysis = True                     # Save the Analyzed Data: The Peak Features for Each Well-Shaped Pulse
    stimulusTimes = [1000, 1000 + 60*3]     # The [Beginning, End] of the Stimulus in Seconds; Type List.
    stimulusTimes_Delayed = [1500, 1500 + 60*3]     # The [Beginning, End] of the Stimulus in Seconds; Type List.

    # Specify Which Signals to Use
    extractGSR = True
    extractPulse = True
    extractChemical = True
    extractTemperature = True
    # Reanalyze Peaks from Scratch (Don't Use Saved Features)
    reanalyzeData_GSR = False
    reanalyzeData_Pulse = False
    reanalyzeData_Chemical = False    
    reanalyzeData_Temperature = False

    # Specify the Unit of Data for Each 
    unitOfData_GSR = "micro"                # Specify the Unit the Data is Represented as: ['', 'milli', 'micro', 'nano', 'pico', 'fempto']
    unitOfData_Pulse = "pico"             # Specify the Unit the Data is Represented as: ['', 'milli', 'micro', 'nano', 'pico', 'fempto']
    unitOfData_Temperature = ""             # Specify the Unit the Data is Represented as: ['', 'milli', 'micro', 'nano', 'pico', 'fempto']
    unitOfData_Chemical_ISE = "milli"       # Specify the Unit the Data is Represented as: ['', 'milli', 'micro', 'nano', 'pico', 'fempto']
    unitOfData_Chemical_Enzym = "micro"     # Specify the Unit the Data is Represented as: ['', 'milli', 'micro', 'nano', 'pico', 'fempto']

    # Specify the Location of the Subject Files
    dataFolderWithSubjects = './Input Data/All Data/Current Analysis/Cleaned data for ML Full/'  # Path to ALL the Subject Data. The Path Must End with '/'
    compiledFeatureNamesFolder = "./Helper Files/Machine Learning/Compiled Feature Names/All Features/"

    # Specify the Stressors/Sensors Used in this Experiment
    listOfStressors = ['cpt', 'exercise', 'vr']         # This Keyword MUST be Present in the Filename
    listOfSensors = ['pulse', 'ise', 'enzym', 'gsr', 'temp']   # This Keyword MUST be Present in the Filename
    
    removeScores = [[], [14, 17], []]
    
    # ---------------------------------------------------------------------- #
    # ------------------------- Preparation Steps -------------------------- #
    
    # Create Instance of Excel Processing Methods
    excelProcessingGSR = excelProcessing.processGSRData()
    excelProcessingPulse = excelProcessing.processPulseData()
    excelProcessingChemical = excelProcessing.processChemicalData()
    excelProcessingTemperature = excelProcessing.processTemperatureData()

    # Create Instances of all Analysis Protocols
    gsrAnalysisProtocol = gsrAnalysis.signalProcessing(stimulusTimes)
    pulseAnalysisProtocol = pulseAnalysis.signalProcessing()
    chemicalAnalysisProtocol = chemicalAnalysis.signalProcessing(plotData = True)
    temperatureAnalysisProtocol = temperatureAnalysis.signalProcessing(stimulusTimes)

    subjectFolderPaths = []
    # Extract the Files for from Each Subject
    for folder in os.listdir(dataFolderWithSubjects):
        if 'subject' not in folder.lower() and not folder.startswith(("$", '~', '_')):
            continue
        
        subjectFolder = dataFolderWithSubjects + folder + "/"
        # Check Whether the Path is a Folder (Exclude Cache Folders)
        if os.path.isdir(subjectFolder):
                # Save the Folder's path for Later Analysis
                subjectFolderPaths.append(subjectFolder)
    # Sort the Folders for Ease in Debugging
    subjectFolderPaths = natsorted(subjectFolderPaths)

    # Define Map of Units to Scale Factors
    scaleFactorMap = {'': 1, 'milli': 10**-3, 'micro': 10**-6, 'nano': 10**-9, 'pico': 10**-12, 'fempto': 10**-15}
    # Find the Scale Factor for the Data
    scaleFactor_GSR = 1 #scaleFactorMap[unitOfData_GSR]
    scaleFactor_Pulse = scaleFactorMap[unitOfData_Pulse] # Pulse 10**-12 
    scaleFactor_Temperature = 1 #scaleFactorMap[unitOfData_Temperature]
    scaleFactor_Chemical_ISE = 1 #scaleFactorMap[unitOfData_Chemical_ISE]
    scaleFactor_Chemical_Enzym = 1 #scaleFactorMap[unitOfData_Chemical_Enzym]
    
    # ---------------------------------------------------------------------- #
    # ------------------------ Specify the Features ------------------------ #
        
    # Compile Features
    scoreFeatureLabels = []  # Compile Stress Scores
    
    if extractPulse:
        # Specify the Paths to the Pulse Feature Names
        pulseFeaturesFile_StressLevel = compiledFeatureNamesFolder + "pulseFeatureNames_StressLevel.txt"
        pulseFeaturesFile_SignalIncrease = compiledFeatureNamesFolder + "pulseFeatureNames_SignalIncrease.txt"
        # Extract the Pulse Feature Names we are Using
        pulseFeatureNames_StressLevel = excelProcessingPulse.extractFeatureNames(pulseFeaturesFile_StressLevel, prependedString = "pulseFeatures.extend([", appendToName = "_StressLevel")[1:]
        pulseFeatureNames_SignalIncrease = excelProcessingPulse.extractFeatureNames(pulseFeaturesFile_SignalIncrease, prependedString = "pulseFeatures.extend([", appendToName = "_SignalIncrease")[1:]
        # Combine all the Features
        pulseFeatureNames = []
        pulseFeatureNames.extend(pulseFeatureNames_StressLevel)
        pulseFeatureNames.extend(pulseFeatureNames_SignalIncrease)
        # Get Pulse Names Without Anything Appended
        pulseFeatureNamesFull = excelProcessingPulse.extractFeatureNames(pulseFeaturesFile_SignalIncrease, prependedString = "pulseFeatures.extend([", appendToName = "")
        pulseFeatureNamesFull.extend(excelProcessingPulse.extractFeatureNames(pulseFeaturesFile_StressLevel, prependedString = "pulseFeatures.extend([", appendToName = "")[1:])
        # Create Data Structure to Hold the Features
        pulseFeatures = []
        pulseFeatureLabels = []  
    
    if extractChemical:
        # Specify the Paths to the Chemical Feature Names
        glucoseFeaturesFile = compiledFeatureNamesFolder + "glucoseFeatureNames.txt"
        lactateFeaturesFile = compiledFeatureNamesFolder + "lactateFeatureNames.txt"
        uricAcidFeaturesFile = compiledFeatureNamesFolder + "uricAcidFeatureNames.txt"
        # Extract the Chemical Feature Names we are Using
        glucoseFeatureNames = excelProcessingChemical.extractFeatureNames(glucoseFeaturesFile, prependedString = "peakFeatures.extend([", appendToName = '_Glucose')
        lactateFeatureNames = excelProcessingChemical.extractFeatureNames(lactateFeaturesFile, prependedString = "peakFeatures.extend([", appendToName = '_Lactate', )
        uricAcidFeatureNames = excelProcessingChemical.extractFeatureNames(uricAcidFeaturesFile, prependedString = "peakFeatures.extend([", appendToName = '_UricAid', )
        # Combine all the Features
        chemicalFeatureNames_Enzym = []
        chemicalFeatureNames_Enzym.extend(glucoseFeatureNames)
        chemicalFeatureNames_Enzym.extend(lactateFeatureNames)
        chemicalFeatureNames_Enzym.extend(uricAcidFeatureNames)
        # Create Data Structure to Hold the Features
        chemicalFeatures_Enzym = []
        chemicalFeatureLabels_Enzym = []
        
        # Specify the Paths to the Chemical Feature Names
        sodiumFeaturesFile = compiledFeatureNamesFolder + "sodiumFeatureNames.txt"
        potassiumFeaturesFile = compiledFeatureNamesFolder + "potassiumFeatureNames.txt"
        ammoniumFeaturesFile = compiledFeatureNamesFolder + "ammoniumFeatureNames.txt"
        # Extract the Chemical Feature Names we are Using
        sodiumFeatureNames = excelProcessingChemical.extractFeatureNames(sodiumFeaturesFile, prependedString = "peakFeatures.extend([", appendToName = '_Sodium')
        potassiumFeatureNames = excelProcessingChemical.extractFeatureNames(potassiumFeaturesFile, prependedString = "peakFeatures.extend([", appendToName = '_Potassium', )
        ammoniumFeatureNames = excelProcessingChemical.extractFeatureNames(ammoniumFeaturesFile, prependedString = "peakFeatures.extend([", appendToName = '_Ammonium', )
        # Combine all the Features
        chemicalFeatureNames_ISE = []
        chemicalFeatureNames_ISE.extend(sodiumFeatureNames)
        chemicalFeatureNames_ISE.extend(potassiumFeatureNames)
        chemicalFeatureNames_ISE.extend(ammoniumFeatureNames)
        # Create Data Structure to Hold the Features
        chemicalFeatures_ISE = []
        chemicalFeatureLabels_ISE = []
        
    if extractGSR:
        # Specify the Paths to the GSR Feature Names
        gsrFeaturesFile = compiledFeatureNamesFolder + "gsrFeatureNames.txt"
        # Extract the GSR Feature Names we are Using
        gsrFeatureNames = excelProcessingGSR.extractFeatureNames(gsrFeaturesFile, prependedString = "gsrFeatures.extend([", appendToName = '_GSR')
        # Create Data Structure to Hold the Features
        gsrFeatures = []
        gsrFeatureLabels = []
        
    if extractTemperature:
        # Specify the Paths to the Temperature Feature Names
        temperatureFeaturesFile = compiledFeatureNamesFolder + "temperatureFeatureNames.txt"
        # Extract the GSR Feature Names we are Using
        temperatureFeatureNames = excelProcessingTemperature.extractFeatureNames(temperatureFeaturesFile, prependedString = "temperatureFeatures.extend([", appendToName = '_Temperature')
        # Create Data Structure to Hold the Features
        temperatureFeatures = []
        temperatureFeatureLabels = []
        
    # ---------------------------------------------------------------------- #
    # -------------------- Data Collection and Analysis -------------------- #
    
    # Loop Through Each Subject
    for subjectFolder in subjectFolderPaths:
        
        # CPT Score
        cptScore = subjectFolder.split("CPT")
        if len(cptScore) == 1:
            cptScore = None
        else:
            cptScore = int(cptScore[1][0:2])
        # Excersize Score
        exerciseScore = subjectFolder.split("Exercise")
        if len(exerciseScore) == 1:
            exerciseScore = subjectFolder.split("Exer")
        if len(exerciseScore) == 1:
            exerciseScore = None
        else:
            exerciseScore = int(exerciseScore[1][0:2])
        # CPT Score
        vrScore = subjectFolder.split("VR")
        if len(vrScore) == 1:
            vrScore = None
        else:
            vrScore = int(vrScore[1][0:2])
            
        # Remove bad scores
        if cptScore in removeScores[0]:
            cptScore = None
        if exerciseScore in removeScores[1]:
            exerciseScore = None
        if vrScore in removeScores[2]:
            vrScore = None
            
        # Label the Score of the File
        scoreLabels_OneTrial = [cptScore, exerciseScore, vrScore]
        scoreFeatureLabels.extend([None]*len(scoreLabels_OneTrial))
                        
        # ------- Organize the Files within Each Stressor and Sensor ------- #
        
        # Organize/Label the Files in the Folder: Pulse, Chemical, GSR, Temp
        fileMap = [[None for _ in  range(len(listOfSensors))] for _ in range(len(listOfStressors))]
        # Loop Through Each File and Label the Stressor Analyzed
        for file in os.listdir(subjectFolder):
            if file.startswith(("#","~","$")):
                continue

            # Find the Type of Stressor in the File
            for stressorInd, stressor in enumerate(listOfStressors):
                if stressor.lower() in file.lower():
                    
                    # Extract the Stress Information from the Filename
                    if scoreFeatureLabels[stressorInd - len(listOfStressors)] == None:
                        scoreFeatureLabels[stressorInd - len(listOfStressors)] = scoreLabels_OneTrial[stressorInd]
                
                    # Find the Type of Sensor the File Used
                    for sensorInd, sensor in enumerate(listOfSensors):
                        if sensor.lower() in file[len(stressor):].lower():
                            
                            # Organize the Files by Their Stressor and Sensor Type 
                            if sensor == "pulse":
                                fileMap[stressorInd][sensorInd] = subjectFolder + file + "/";
                            else:
                                fileMap[stressorInd][sensorInd] = subjectFolder + file;
                            break
                    break
        fileMap = np.array(fileMap)
        
        # Quick check if files are found (Alert user if not)
        for stressorFiles in fileMap:
            if None in stressorFiles:
                print("\n\nNot all files found here:\n", stressorFiles, "\n\n")
                
        # ------------------------- Pulse Analysis ------------------------- #
        
        if extractPulse:
            # Extract the Pulse Folder Paths in the Map
            pulseFolders = fileMap[:, listOfSensors.index("pulse")]
            
            # Loop Through the Pulse Data for Each Stressor
            for featureLabel, pulseFolder in enumerate(pulseFolders):
                if pulseFolder == None:
                    # Compile the Featues into One Array
                    pulseFeatureLabels.append(None)
                    pulseFeatures.append([None]*len(pulseFeatureNames))
                    continue
                
                savePulseDataFolder = pulseFolder + "Pulse Analysis/"    # Data Folder to Save the Data; MUST END IN '/'
                if not reanalyzeData_Pulse and os.path.isfile(pulseFolder + "/Pulse Analysis/Compiled Data in Excel/Feature List.xlsx"):
                    pulseFeatureList_Full = excelProcessingPulse.getSavedFeatures(pulseFolder + "/Pulse Analysis/Compiled Data in Excel/Feature List.xlsx")
                    featureTimes = pulseFeatureList_Full[:,0]
                    pulseFeatureListExact = pulseFeatureList_Full[:,1:]
                    
                    numSecondsAverage = 30; pulseFeatureList = []
                    # Calculate the Running Average
                    for timePointInd in range(len(featureTimes)):
                        currentTimePoint = featureTimes[timePointInd]
                        
                        # Get the Interval of Feature and Take the Average
                        featureInterval = pulseFeatureListExact[0:timePointInd+1][featureTimes[0:timePointInd+1] > currentTimePoint - numSecondsAverage]
                        pulseFeatureList.append(stats.trim_mean(featureInterval, 0.3))
                    pulseFeatureList = np.array(pulseFeatureList)

                else:
                    pulseExcelFiles = []
                    # Collect all the Pulse Files for the Stressor
                    for file in os.listdir(pulseFolder):
                        file = file.decode("utf-8") if type(file) == type(b'') else file
                        if file.endswith(("xlsx", "xls")) and not file.startswith(("$", '~')):
                            pulseExcelFiles.append(pulseFolder + file)
                    pulseExcelFiles = natsorted(pulseExcelFiles)
                
                    # Loop Through Each Pulse File
                    pulseAnalysisProtocol.resetGlobalVariables()
                    for pulseExcelFile in pulseExcelFiles:
                        
                        # Read Data from Excel
                        time, signalData = excelProcessingPulse.getData(pulseExcelFile, testSheetNum = 0)
                        signalData = signalData*scaleFactor_Pulse
                                        
                        # Calibrate Systolic and Diastolic Pressure
                        fileBasename = os.path.basename(pulseExcelFile)
                        pressureInfo = fileBasename.split("SYS")
                        if len(pressureInfo) > 1 and pulseAnalysisProtocol.systolicPressure0 == None:
                            pressureInfo = pressureInfo[-1].split(".")[0]
                            systolicPressure0, diastolicPressure0 = pressureInfo.split("_DIA")
                            pulseAnalysisProtocol.setPressureCalibration(float(systolicPressure0), float(diastolicPressure0))
                        
                        # Check Whether the StartTime is Specified in the File
                        if fileBasename.lower() in ["cpt", "exer", "vr", "start"] and not stimulusTimes[0]:
                            stimulusTimes[0] = pulseAnalysisProtocol.timeOffset
                                                    
                        # Seperate Pulses, Perform Indivisual Analysis, and Extract Features
                        pulseAnalysisProtocol.analyzePulse(time, signalData, minBPM = 30, maxBPM = 180)
                    
                    # Remove Previous Analysis if Present
                    if os.path.isdir(savePulseDataFolder):
                        shutil.rmtree(savePulseDataFolder)
                    pulseAnalysisProtocol.featureListExact = np.array(pulseAnalysisProtocol.featureListExact)
                    # Save the Features and Filtered Data
                    saveCompiledDataPulse = savePulseDataFolder + "Compiled Data in Excel/"
                    excelProcessingPulse.saveResults(pulseAnalysisProtocol.featureListExact, pulseFeatureNamesFull, saveCompiledDataPulse, "Feature List.xlsx", sheetName = "Pulse Features")
                    excelProcessingPulse.saveFilteredData(pulseAnalysisProtocol.time, pulseAnalysisProtocol.signalData, pulseAnalysisProtocol.filteredData, saveCompiledDataPulse, "Filtered Data.xlsx", "Filtered Data")
                    
                    # Compile the Features from the Data
                    featureTimes = pulseAnalysisProtocol.featureListExact[:,0]
                    pulseFeatureList = np.array(pulseAnalysisProtocol.featureListAverage)
                    pulseFeatureListExact = pulseAnalysisProtocol.featureListExact[:,1:]
                    # Assert That There are Equal Features and Feature Times
                    assert len(featureTimes) == len(pulseFeatureList)
    
                # Quick Check that All Points Have the Correct Number of Features
                for feature in pulseFeatureList:
                    assert len(feature) == len(pulseFeatureNames)
                
                # Plot the Features in Time
                if timePermits:
                    plotPulseFeatures = featureAnalysis.featureAnalysis(featureTimes, pulseFeatureListExact, pulseFeatureNamesFull[1:], stimulusTimes, savePulseDataFolder)
                    plotPulseFeatures.singleFeatureAnalysis()   
                    
                # Downsize the Features into One Data Point
                # ********************************
                # FInd the Indices of the Stimuli
                startStimulusInd = np.argmin(abs(featureTimes - stimulusTimes[0]))
                endStimulusInd = np.argmin(abs(featureTimes - stimulusTimes[1]))
                
                # Caluclate the Baseline/Stress Levels
                restValues = stats.trim_mean(pulseFeatureList[ int(startStimulusInd/6):int(2*startStimulusInd/4),:], 0.4)
                stressValues = stats.trim_mean(pulseFeatureList[ int((endStimulusInd+startStimulusInd)/2) :endStimulusInd,: ], 0.4)
                stressElevation = stressValues - restValues
                # Calculate the Stress Rise/Fall
                stressSlopes = np.polyfit(featureTimes[startStimulusInd:endStimulusInd], pulseFeatureList[ startStimulusInd:endStimulusInd,: ], 1)[0]
    
                # Organize the Signals
                pulseFeatures_StressLevel = stressValues[0:len(pulseFeatureNames_StressLevel)]
                pulseFeatures_SignalIncrease = stressElevation[len(pulseFeatureNames_StressLevel):]
                # Compile the Signals
                subjectPulseFeatures = []
                subjectPulseFeatures.extend(pulseFeatures_StressLevel)
                subjectPulseFeatures.extend(pulseFeatures_SignalIncrease)
                # Assert the Number of Signals are Correct
                assert len(subjectPulseFeatures) == len(pulseFeatureNames)
                assert len(pulseFeatures_StressLevel) == len(pulseFeatureNames_StressLevel)
                assert len(pulseFeatures_SignalIncrease) == len(pulseFeatureNames_SignalIncrease)
                # ********************************
                
                # Compile the Featues into One Array
                pulseFeatureLabels.append(featureLabel)
                pulseFeatures.append(subjectPulseFeatures)
    
        # ------------------------ Chemical Analysis ----------------------- #
        
        if extractChemical:
            # Extract the Chemical Folder Paths in the Map
            chemicalFiles_ISE = fileMap[:, listOfSensors.index("ise")]
            chemicalFiles_Enzym = fileMap[:, listOfSensors.index("enzym")]
            
            # --------------- Enzym
            # Loop Through the Pulse Data for Each Stressor
            for featureLabel, chemicalFile in enumerate(chemicalFiles_Enzym):
                if chemicalFile == None:
                    chemicalFeatureLabels_Enzym.append(None)
                    chemicalFeatures_Enzym.append([None]*len(chemicalFeatureNames_Enzym))
                    continue
                # Extract the Specific Chemical Filename
                chemicalFilename = os.path.basename(chemicalFile[:-1]).split(".")[0]
                saveCompiledDataChemical = subjectFolder + "Chemical Analysis/Compiled Data in Excel/" + chemicalFilename + "/"
    
                if not reanalyzeData_Chemical and os.path.isfile(saveCompiledDataChemical + "Feature List.xlsx"):
                    subjectChemicalFeatures = excelProcessingChemical.getSavedFeatures(saveCompiledDataChemical + "Feature List.xlsx")[0]
                    
                    # Organize the Features of Enzymatic
                    glucoseFeatures = subjectChemicalFeatures[0:len(glucoseFeatureNames)]
                    lactateFeatures = subjectChemicalFeatures[len(glucoseFeatureNames):len(glucoseFeatureNames) + len(lactateFeatureNames)]
                    uricAcidFeatures = subjectChemicalFeatures[len(lactateFeatureNames) + len(glucoseFeatureNames):]
                    
                    # Quick Check that All Points Have the Correct Number of Features
                    assert len(subjectChemicalFeatures) == len(chemicalFeatureNames_Enzym)
                    assert len(glucoseFeatures) == len(glucoseFeatureNames)
                    assert len(lactateFeatures) == len(lactateFeatureNames)
                    assert len(uricAcidFeatures) == len(uricAcidFeatureNames)
                else:
                    # Read in the Chemical Data from Excel
                    timePoints, chemicalData = excelProcessingChemical.getData(chemicalFile, testSheetNum = 0)
                    glucose, lactate, uricAcid = chemicalData*scaleFactor_Chemical_Enzym # Extract the Specific Chemicals
                    #lactate = lactate*1000 # Correction on Lactate Data
                    
                    # if len(uricAcid) != 0:
                    #     plt.plot(timePoints, uricAcid, c=colors(cptScore))
                    #     plt.title("Uric Acid")
                    #     plt.xlabel("Time (Seconds)")
                    #     plt.ylabel("Concentration (M)")
                    
                    # break
                    
                    # Cull Subjects with Missing Data
                    if len(glucose) == 0 or len(lactate) == 0 or len(uricAcid) == 0:
                        print("Missing Chemical Data in Folder:", subjectFolder)
                        sys.exit()
            
                    # Compile the Features from the Data
                    chemicalAnalysisProtocol.resetGlobalVariables(stimulusTimes)
                    chemicalAnalysisProtocol.analyzeChemicals(timePoints, [glucose, lactate, uricAcid], ['glucose', 'lactate', 'uricAcid'], featureLabel)
                    # Get the ChemicalFeatures
                    glucoseFeatures = chemicalAnalysisProtocol.chemicalFeatures['glucoseFeatures'][0][0]
                    lactateFeatures = chemicalAnalysisProtocol.chemicalFeatures['lactateFeatures'][0][0]
                    uricAcidFeatures = chemicalAnalysisProtocol.chemicalFeatures['uricAcidFeatures'][0][0]
                    chemicalAnalysisProtocol.resetGlobalVariables(stimulusTimes)
                    # Verify that Features were Found in for All Chemicals
                    if len(glucoseFeatures) == 0 or len(lactateFeatures) == 0 or len(uricAcidFeatures) == 0:
                        print("No Features Found in Some Chemical Data in Folder:", subjectFolder)
                        sys.exit()   
                        
                    # Quick Check that All Points Have the Correct Number of Features
                    assert len(glucoseFeatures) == len(glucoseFeatureNames)
                    assert len(lactateFeatures) == len(lactateFeatureNames)
                    assert len(uricAcidFeatures) == len(uricAcidFeatureNames)
                    
                    # Organize the Chemical Features
                    subjectChemicalFeatures = []
                    subjectChemicalFeatures.extend(glucoseFeatures)
                    subjectChemicalFeatures.extend(lactateFeatures)
                    subjectChemicalFeatures.extend(uricAcidFeatures)
                    
                    # Save the Features and Filtered Data
                    excelProcessingChemical.saveResults([subjectChemicalFeatures], chemicalFeatureNames_Enzym, saveCompiledDataChemical, "Feature List.xlsx", sheetName = "Chemical Features")
                
                # Compile the Featues into One Array
                chemicalFeatureLabels_Enzym.append(featureLabel)
                chemicalFeatures_Enzym.append(subjectChemicalFeatures)
            
            # --------------- ISE
            # Loop Through the Pulse Data for Each Stressor
            for featureLabel, chemicalFile in enumerate(chemicalFiles_ISE):
                if chemicalFile == None:
                    chemicalFeatureLabels_ISE.append(None)
                    chemicalFeatures_ISE.append([None]*len(chemicalFeatureNames_ISE))
                    continue
                # Extract the Specific Chemical Filename
                chemicalFilename = os.path.basename(chemicalFile[:-1]).split(".")[0]
                saveCompiledDataChemical = subjectFolder + "Chemical Analysis/Compiled Data in Excel/" + chemicalFilename + "/"
    
                if not reanalyzeData_Chemical and os.path.isfile(saveCompiledDataChemical + "Feature List.xlsx"):
                    subjectChemicalFeatures = excelProcessingChemical.getSavedFeatures(saveCompiledDataChemical + "Feature List.xlsx")[0]
                    
                    # Organize the Features of ISE
                    sodiumFeatures = subjectChemicalFeatures[0:len(sodiumFeatureNames)]
                    potassiumFeatures = subjectChemicalFeatures[len(sodiumFeatureNames):len(sodiumFeatureNames) + len(potassiumFeatureNames)]
                    ammoniumFeatures = subjectChemicalFeatures[len(sodiumFeatureNames) + len(potassiumFeatureNames):]
                    
                    # Quick Check that All Points Have the Correct Number of Features
                    assert len(subjectChemicalFeatures) == len(chemicalFeatureNames_ISE)
                    assert len(sodiumFeatures) == len(sodiumFeatureNames)
                    assert len(potassiumFeatures) == len(potassiumFeatureNames)
                    assert len(ammoniumFeatures) == len(ammoniumFeatureNames)
                else:
                    # Read in the Chemical Data from Excel
                    timePoints, chemicalData = excelProcessingChemical.getData(chemicalFile, testSheetNum = 0)
                    sodium, potassium, ammonium = chemicalData*scaleFactor_Chemical_ISE # Extract the Specific Chemicals
                    
                    # plt.plot(timePoints, sodium, c=colors(cptScore))
                    # plt.title("Sodium")
                    # plt.xlabel("Time (Seconds)")
                    # plt.ylabel("Concentration (M)")
                    
                    # break
                    
                    # Cull Subjects with Missing Data
                    if len(sodium) == 0 or len(potassium) == 0 or len(ammonium) == 0:
                        print("Missing Chemical Data in Folder:", subjectFolder)
                        sys.exit()
            
                    # Compile the Features from the Data
                    chemicalAnalysisProtocol.resetGlobalVariables(stimulusTimes_Delayed)
                    chemicalAnalysisProtocol.analyzeChemicals(timePoints, [sodium, potassium, ammonium], ['sodium', 'potassium', 'ammonium'], featureLabel, iseData = True)
                    # Get the ChemicalFeatures
                    sodiumFeatures = chemicalAnalysisProtocol.chemicalFeatures['sodiumFeatures'][0]
                    potassiumFeatures = chemicalAnalysisProtocol.chemicalFeatures['potassiumFeatures'][0]
                    ammoniumFeatures = chemicalAnalysisProtocol.chemicalFeatures['ammoniumFeatures'][0]
                    # Verify that Features were Found in for All Chemicals
                    if len(sodiumFeatures) == 0 or len(potassiumFeatures) == 0 or len(ammoniumFeatures) == 0:
                        print("No Features Found in Some Chemical Data in Folder:", subjectFolder)
                        sys.exit()   
                    chemicalAnalysisProtocol.resetGlobalVariables(stimulusTimes_Delayed)
                        
                    # Quick Check that All Points Have the Correct Number of Features
                    assert len(sodiumFeatures) == len(sodiumFeatureNames)
                    assert len(potassiumFeatures) == len(potassiumFeatureNames)
                    assert len(ammoniumFeatures) == len(ammoniumFeatureNames)
                    
                    # Organize the Chemical Features
                    subjectChemicalFeatures = []
                    subjectChemicalFeatures.extend(sodiumFeatures)
                    subjectChemicalFeatures.extend(potassiumFeatures)
                    subjectChemicalFeatures.extend(ammoniumFeatures)
                    
                    # Save the Features and Filtered Data
                    excelProcessingChemical.saveResults([subjectChemicalFeatures], chemicalFeatureNames_ISE, saveCompiledDataChemical, "Feature List.xlsx", sheetName = "Chemical Features")
                
                # Compile the Featues into One Array
                chemicalFeatureLabels_ISE.append(featureLabel)
                chemicalFeatures_ISE.append(subjectChemicalFeatures)
                        
        # -------------------------- GSR Analysis -------------------------- #
        
        if extractGSR:
            colorList = ['k', 'tab:blue', 'tab:red']
            # Extract the Pulse Folder Paths in the Map
            gsrFiles = fileMap[:, listOfSensors.index("gsr")]
            # Loop Through the Pulse Data for Each Stressor
            for featureLabel, gsrFile in enumerate(gsrFiles):
                if gsrFile == None:
                    gsrFeatureLabels.append(None)
                    gsrFeatures.append([None]*len(gsrFeatureNames))
                    continue
                # Extract the Specific GSR Filename
                gsrFilename = os.path.basename(gsrFile[:-1]).split(".")[0]
                saveCompiledDataGSR = subjectFolder + "GSR Analysis/Compiled Data in Excel/" + gsrFilename + "/"
    
                if not reanalyzeData_GSR and os.path.isfile(saveCompiledDataGSR + "Feature List.xlsx"):
                    subjectGSRFeatures = excelProcessingChemical.getSavedFeatures(saveCompiledDataGSR + "Feature List.xlsx")[0]
                    # Quick Check that All Points Have the Correct Number of Features
                    assert len(subjectGSRFeatures) == len(gsrFeatureNames)
                else:
                    # Read in the GSR Data from Excel
                    excelDataGSR = excelProcessing.processGSRData()
                    timeGSR, currentGSR = excelDataGSR.getData(gsrFile, testSheetNum = 0, method = "processed")
                    currentGSR = currentGSR*scaleFactor_GSR # Get Data into micro-Ampes

                    # Process the Data
                    subjectGSRFeatures = gsrAnalysisProtocol.analyzeGSR(timeGSR, currentGSR)
                    
                    # Quick Check that All Points Have the Correct Number of Features
                    assert len(subjectGSRFeatures) == len(gsrFeatureNames)
                    
                    # Save the Features and Filtered Data
                    excelProcessingGSR.saveResults([subjectGSRFeatures], gsrFeatureNames, saveCompiledDataGSR, "Feature List.xlsx", sheetName = "GSR Features")

                # Compile the Featues into One Array
                gsrFeatureLabels.append(featureLabel)
                gsrFeatures.append(subjectGSRFeatures)
        
        # ---------------------- Temperature Analysis ---------------------- #
        
        if extractTemperature:
            # Extract the Pulse Folder Paths in the Map
            temperatureFiles = fileMap[:, listOfSensors.index("temp")]
            # Loop Through the Pulse Data for Each Stressor
            for featureLabel, temperatureFile in enumerate(temperatureFiles):
                if temperatureFile == None:
                    temperatureFeatureLabels.append(None)
                    temperatureFeatures.append([None]*len(temperatureFeatureNames))
                    continue
                # Extract the Specific temperature Filename
                temperatureFilename = os.path.basename(temperatureFile[:-1]).split(".")[0]
                saveCompiledDataTemperature = subjectFolder + "temperature Analysis/Compiled Data in Excel/" + temperatureFilename + "/"
    
                if not reanalyzeData_Temperature and os.path.isfile(saveCompiledDataTemperature + "Feature List.xlsx"):
                    subjectTemperatureFeatures = excelProcessingChemical.getSavedFeatures(saveCompiledDataTemperature + "Feature List.xlsx")[0]
                    # Quick Check that All Points Have the Correct Number of Features
                    assert len(subjectTemperatureFeatures) == len(temperatureFeatureNames)
                else:
                    # Read in the temperature Data from Excel
                    excelDataTemperature = excelProcessing.processTemperatureData()
                    timeTemp, temperatureData = excelDataTemperature.getData(temperatureFile, testSheetNum = 0)
                    temperatureData = temperatureData*scaleFactor_Temperature # Get Data into micro-Ampes

                    # Process the Data
                    subjectTemperatureFeatures = temperatureAnalysisProtocol.analyzeTemperature(timeTemp, temperatureData)
                    
                    # Quick Check that All Points Have the Correct Number of Features
                    assert len(subjectTemperatureFeatures) == len(temperatureFeatureNames)
                    
                    # Save the Features and Filtered Data
                    excelProcessingTemperature.saveResults([subjectTemperatureFeatures], temperatureFeatureNames, saveCompiledDataTemperature, "Feature List.xlsx", sheetName = "Temperature Features")

                # Compile the Featues into One Array
                temperatureFeatureLabels.append(featureLabel)
                temperatureFeatures.append(subjectTemperatureFeatures)

    # ---------------------- Compile Features Together --------------------- #
    # Compile Labels
    allLabels = []
    if extractGSR: allLabels.append(gsrFeatureLabels) 
    if extractPulse: allLabels.append(pulseFeatureLabels)
    if extractChemical: allLabels.append(chemicalFeatureLabels_ISE)
    if extractChemical: allLabels.append(chemicalFeatureLabels_Enzym)
    if extractTemperature: allLabels.append(temperatureFeatureLabels)
    # Assert That We Have the Same Number of Points in Both
    for labelList in allLabels:
        assert len(labelList) == len(scoreFeatureLabels)
    # Do Not Continue if No Labels Found
    if len(allLabels) == 0:
        sys.exit("Please Specify Features to Extract")
    allLabels = np.array(allLabels)
       
    # Compile Data for Machine Learning
    signalData = []; stressLabels = []; scoreLabels = []
    # Merge the Features
    for arrayInd in range(len(allLabels[0])):
        currentLabels = allLabels[:,arrayInd]
        stressLabel = scoreFeatureLabels[arrayInd]
        
        # If the Subject had All the Data for the Sensor.
        if None not in currentLabels and stressLabel != None:
            # Assert That the Features are the Same
            assert len(set(currentLabels)) == 1
            
            features = []
            # Compile the Features. ORDER MATTERS
            if extractPulse: features.extend(pulseFeatures[arrayInd]) 
            if extractChemical: features.extend(chemicalFeatures_Enzym[arrayInd]) 
            if extractChemical: features.extend(chemicalFeatures_ISE[arrayInd])
            if extractGSR: features.extend(gsrFeatures[arrayInd]) 
            if extractTemperature: features.extend(temperatureFeatures[arrayInd])
            # Save the Compiled Features
            signalData.append(features)
            stressLabels.append(currentLabels[0])
            scoreLabels.append(stressLabel)
    signalData = np.array(signalData)
    stressLabels = np.array(stressLabels)
    scoreLabels = np.array(scoreLabels)
    
    # Compile Feature Names
    featureNames = []        
    featureNames.extend(pulseFeatureNames)
    featureNames.extend(chemicalFeatureNames_Enzym)
    featureNames.extend(chemicalFeatureNames_ISE)
    featureNames.extend(gsrFeatureNames)
    featureNames.extend(temperatureFeatureNames)
        
        
    print("Finished Collecting All the Data")
        
    # ----------------------- Extra Feature Analysis ----------------------- #
    print("\nPlotting Feature Comparison")
    
    if plotFeatures:
        if extractChemical:
            chemicalFeatures_ISE = np.array(chemicalFeatures_ISE); chemicalFeatureLabels_ISE = np.array(chemicalFeatureLabels_ISE)
            chemicalFeatures_Enzym = np.array(chemicalFeatures_Enzym); chemicalFeatureLabels_Enzym = np.array(chemicalFeatureLabels_Enzym)
            # Remove None Values
            chemicalFeatures_ISE_NonNone = chemicalFeatures_ISE[chemicalFeatureLabels_ISE != np.array(None)]
            chemicalFeatureLabels_ISE_NonNone = chemicalFeatureLabels_ISE[chemicalFeatureLabels_ISE != np.array(None)]
            chemicalFeatures_Enzym_NonNone = chemicalFeatures_Enzym[chemicalFeatureLabels_Enzym != np.array(None)]
            chemicalFeatureLabels_Enzym_NonNone = chemicalFeatureLabels_Enzym[chemicalFeatureLabels_Enzym != np.array(None)]
            
            # Organize the Features Enzym
            glucoseFeatures = chemicalFeatures_Enzym_NonNone[:, 0:len(glucoseFeatureNames)]
            lactateFeatures = chemicalFeatures_Enzym_NonNone[:, len(glucoseFeatureNames):len(glucoseFeatureNames) + len(lactateFeatureNames)]
            uricAcidFeatures = chemicalFeatures_Enzym_NonNone[:, len(glucoseFeatureNames) + len(lactateFeatureNames):]
            # Organize the Features ISE
            sodiumFeatures = chemicalFeatures_ISE_NonNone[:, 0:len(sodiumFeatureNames)]
            potassiumFeatures = chemicalFeatures_ISE_NonNone[:, len(sodiumFeatureNames):len(sodiumFeatureNames) + len(potassiumFeatureNames)]
            ammoniumFeatures = chemicalFeatures_ISE_NonNone[:, len(sodiumFeatureNames) + len(potassiumFeatureNames):]
                        
            # Plot the Features within a Single Chemical
            analyzeFeatures_ISE = featureAnalysis.featureAnalysis([], [], chemicalFeatureNames_ISE, stimulusTimes_Delayed, dataFolderWithSubjects + "Machine Learning/Compiled Chemical Feature Analysis/")
            analyzeFeatures_ISE.singleFeatureComparison([sodiumFeatures, potassiumFeatures, ammoniumFeatures], [chemicalFeatureLabels_ISE_NonNone, chemicalFeatureLabels_ISE_NonNone, chemicalFeatureLabels_ISE_NonNone], ["Sodium", "Potassium", "Ammonium"], chemicalFeatureNames_ISE)
            analyzeFeatures_Enzym = featureAnalysis.featureAnalysis([], [], chemicalFeatureNames_Enzym, stimulusTimes, dataFolderWithSubjects + "Machine Learning/Compiled Chemical Feature Analysis/")
            analyzeFeatures_Enzym.singleFeatureComparison([glucoseFeatures, lactateFeatures, uricAcidFeatures], [chemicalFeatureLabels_Enzym_NonNone, chemicalFeatureLabels_Enzym_NonNone, chemicalFeatureLabels_Enzym_NonNone], ["Glucose", "Lactate", "UricAcid"], chemicalFeatureNames_Enzym)
            if timePermits:
                # Compare the Features Between Themselves
                analyzeFeatures_Enzym.featureComparison(glucoseFeatures, glucoseFeatures, chemicalFeatureLabels_Enzym_NonNone, glucoseFeatureNames, glucoseFeatureNames, 'Glucose', 'Glucose')
                analyzeFeatures_Enzym.featureComparison(lactateFeatures, lactateFeatures, chemicalFeatureLabels_Enzym_NonNone, lactateFeatureNames, lactateFeatureNames, 'Lactate', 'Lactate')
                analyzeFeatures_Enzym.featureComparison(uricAcidFeatures, uricAcidFeatures, chemicalFeatureLabels_Enzym_NonNone, uricAcidFeatureNames, uricAcidFeatureNames, 'Uric Acid', 'Uric Acid')
                analyzeFeatures_ISE.featureComparison(sodiumFeatures, sodiumFeatures, chemicalFeatureLabels_ISE_NonNone, sodiumFeatureNames, sodiumFeatureNames, 'Sodium', 'Sodium')
                analyzeFeatures_ISE.featureComparison(potassiumFeatures, potassiumFeatures, chemicalFeatureLabels_ISE_NonNone, potassiumFeatureNames, potassiumFeatureNames, 'Potassium', 'Potassium')
                analyzeFeatures_ISE.featureComparison(ammoniumFeatures, ammoniumFeatures, chemicalFeatureLabels_ISE_NonNone, ammoniumFeatureNames, ammoniumFeatureNames, 'Ammonium', 'Ammonium')
                # Cross-Compare the Features Between Each Other
                # analyzeFeatures.featureComparison(lactateFeatures, uricAcidFeatures, chemicalFeatureLabels_NonNone, lactateFeatureNames, uricAcidFeatureNames, 'Lactate', 'Uric Acid')
                # analyzeFeatures.featureComparison(glucoseFeatures, uricAcidFeatures, chemicalFeatureLabels_NonNone, glucoseFeatureNames, uricAcidFeatureNames, 'Glucose', 'Uric Acid')
                # analyzeFeatures.featureComparison(lactateFeatures, glucoseFeatures, chemicalFeatureLabels_NonNone, lactateFeatureNames, glucoseFeatureNames, 'Lactate', 'Glucose')
            
        if extractPulse:
            pulseFeatures = np.array(pulseFeatures)
            pulseFeatureLabels = np.array(pulseFeatureLabels)
            # Remove None Values
            pulseFeatures_NonNone = pulseFeatures[pulseFeatureLabels != np.array(None)]
            pulseFeatureLabels_NonNone = pulseFeatureLabels[pulseFeatureLabels != np.array(None)]
            # Plot the Features within a Pulse
            analyzeFeatures = featureAnalysis.featureAnalysis([], [], pulseFeatureNames, stimulusTimes, dataFolderWithSubjects + "Machine Learning/Compiled Pulse Feature Analysis/")
            analyzeFeatures.singleFeatureComparison([pulseFeatures_NonNone], [pulseFeatureLabels_NonNone], ["Pulse"], pulseFeatureNames)
            if timePermits:
                # Cross-Compare the Features Between Each Other
                analyzeFeatures.featureComparison(pulseFeatures_NonNone, pulseFeatures_NonNone, pulseFeatureLabels_NonNone, pulseFeatureNames, pulseFeatureNames, 'Pulse', 'Pulse')
        
        if extractGSR:
            gsrFeatures = np.array(gsrFeatures)
            gsrFeatureLabels = np.array(gsrFeatureLabels)
            # Remove None Values
            gsrFeatures_NonNone = gsrFeatures[gsrFeatureLabels != np.array(None)]
            gsrFeatureLabels_NonNone = gsrFeatureLabels[gsrFeatureLabels != np.array(None)]
            # Plot the Features within a gsr
            analyzeFeatures = featureAnalysis.featureAnalysis([], [], gsrFeatureNames, stimulusTimes, dataFolderWithSubjects + "Machine Learning/Compiled GSR Feature Analysis/")
            analyzeFeatures.singleFeatureComparison([gsrFeatures_NonNone], [gsrFeatureLabels_NonNone], ["GSR"], gsrFeatureNames)
            if timePermits:
                # Cross-Compare the Features Between Each Other
                analyzeFeatures.featureComparison(gsrFeatures_NonNone, gsrFeatures_NonNone, gsrFeatureLabels_NonNone, gsrFeatureNames, gsrFeatureNames, 'GSR', 'GSR')
                
        if extractTemperature:
            temperatureFeatures = np.array(temperatureFeatures)
            temperatureFeatureLabels = np.array(temperatureFeatureLabels)
            # Remove None Values
            temperatureFeatures_NonNone = temperatureFeatures[temperatureFeatureLabels != np.array(None)]
            temperatureFeatureLabels_NonNone = temperatureFeatureLabels[temperatureFeatureLabels != np.array(None)]
            # Plot the Features within a temperature
            analyzeFeatures = featureAnalysis.featureAnalysis([], [], temperatureFeatureNames, stimulusTimes, dataFolderWithSubjects + "Machine Learning/Compiled Temperature Feature Analysis/")
            analyzeFeatures.singleFeatureComparison([temperatureFeatures_NonNone], [temperatureFeatureLabels_NonNone], ["Temperature"], temperatureFeatureNames)
            if timePermits:
                # Cross-Compare the Features Between Each Other
                analyzeFeatures.featureComparison(temperatureFeatures_NonNone, temperatureFeatures_NonNone, gsrFeatureLabels_NonNone, temperatureFeatureNames, temperatureFeatureNames, 'Temperature', 'Temperature')
                
        #Compare Stress Scores with the Features
        analyzeFeatures = featureAnalysis.featureAnalysis([], [], featureNames, [None, None], dataFolderWithSubjects + "Machine Learning/Compiled Stress Score Feature Analysis/")
        analyzeFeatures.featureComparisonAgainstONE(signalData, scoreLabels, stressLabels, featureNames, "Stress Scores", 'Stress Scores')
    
    # ---------------------------------------------------------------------- #
    # ---------------------- Machine Learning Analysis --------------------- #
    print("\nBeginning Machine Learning Section")
    
    
    # from sklearn.preprocessing import StandardScaler
    # scaler = StandardScaler()
    # scaler.fit(signalData)
    # signalData_Scaled = scaler.transform(signalData)
    
    testStressScores = True
    if testStressScores:
        signalLabels = scoreLabels
        # Machine Learning File/Model Paths + Titles
        modelType = "SVR"  # Machine Learning Options: NN, RF, LR, KNN, SVM, RG, EN, SVR
        supportVectorKernel = "linear" # linear, poly, rbf, sigmoid, precomputed
        modelPath = "./Helper Files/Machine Learning Modules/Models/machineLearningModel_ALL.pkl"
        saveModelFolder = dataFolderWithSubjects + "Machine Learning/" + modelType + "/"
    else:
        signalLabels = stressLabels
        # Machine Learning File/Model Paths + Titles
        modelType = "KNN"  # Machine Learning Options: NN, RF, LR, KNN, SVM, RG, EN, SVR
        supportVectorKernel = "linear" # linear, poly, rbf, sigmoid, precomputed
        modelPath = "./Helper Files/Machine Learning Modules/Models/machineLearningModel_ALL.pkl"
        saveModelFolder = dataFolderWithSubjects + "Machine Learning/" + modelType + "/"
                
    # Get the Machine Learning Module
    performMachineLearning = machineLearningMain.predictionModelHead(modelType, modelPath, numFeatures = len(featureNames), machineLearningClasses = listOfStressors, saveDataFolder = saveModelFolder, supportVectorKernel = supportVectorKernel)
    # # Train the Data on the Gestures
    # print(performMachineLearning.trainModel(signalData, signalLabels, featureNames, returnScore = True, stratifyBy = stressLabels))
    # print(performMachineLearning.predictionModel.scoreModel(signalData, signalLabels))
    
    
    numFeaturesCombine = 1
    performMachineLearning = machineLearningMain.predictionModelHead(modelType, modelPath, numFeatures = len(featureNames), machineLearningClasses = listOfStressors, saveDataFolder = saveModelFolder, supportVectorKernel = supportVectorKernel)
    modelScores, featureNames_Combinations = performMachineLearning.analyzeFeatureCombinations(signalData, signalLabels, featureNames, numFeaturesCombine, saveData = True, printUpdateAfterTrial = 15000, scaleY = testStressScores)
   
    featureNamesPermute_Good = featureNames_Combinations[np.array(modelScores) >= 0]
    signalData_Good = signalData[:,np.array(modelScores) >= 0]
    
    for numFeaturesCombine in [2,3,4]:
        performMachineLearning = machineLearningMain.predictionModelHead(modelType, modelPath, numFeatures = len(featureNames), machineLearningClasses = listOfStressors, saveDataFolder = saveModelFolder, supportVectorKernel = supportVectorKernel)
        modelScores, featureNames_Combinations = performMachineLearning.analyzeFeatureCombinations(signalData_Good, signalLabels, featureNamesPermute_Good, numFeaturesCombine, saveData = True, printUpdateAfterTrial = 100000, scaleY = testStressScores)
    
    
    
    
    
    
    sys.exit("STOPPING")
    
    for supportVectorKernel in ['linear', 'poly', 'rbf', 'sigmoid']:
    
        numFeaturesCombine = 1
        performMachineLearning = machineLearningMain.predictionModelHead(modelType, modelPath, numFeatures = len(featureNames), machineLearningClasses = listOfStressors, saveDataFolder = saveModelFolder, supportVectorKernel = supportVectorKernel)
        modelScores, featureNames_Combinations = performMachineLearning.analyzeFeatureCombinations(signalData, signalLabels, featureNames, numFeaturesCombine, saveData = True, printUpdateAfterTrial = 15000, scaleY = testStressScores)
       
        numFeaturesCombine = 2
        performMachineLearning = machineLearningMain.predictionModelHead(modelType, modelPath, numFeatures = len(featureNames), machineLearningClasses = listOfStressors, saveDataFolder = saveModelFolder, supportVectorKernel = supportVectorKernel)
        modelScores, featureNames_Combinations = performMachineLearning.analyzeFeatureCombinations(signalData, signalLabels, featureNames, numFeaturesCombine, saveData = True, printUpdateAfterTrial = 15000, scaleY = testStressScores)
    
    sys.exit()
    
    numFeaturesCombine = 3
    performMachineLearning = machineLearningMain.predictionModelHead(modelType, modelPath, numFeatures = len(featureNames), machineLearningClasses = listOfStressors, saveDataFolder = saveModelFolder, supportVectorKernel = supportVectorKernel)
    modelScores, featureNames_Combinations = performMachineLearning.analyzeFeatureCombinations(signalData, signalLabels, featureNames, numFeaturesCombine, saveData = True, printUpdateAfterTrial = 15000, scaleY = testStressScores)
    
    sys.exit("STOPPING")
    
    # modelScores_Single0 = []
    # modelScores_Single1 = []
    # modelScores_Single2 = []
    # modelScores_SingleTotal = []
    # for featureInd in range(len(featureNames)):
    #     featureRow = featureNames[featureInd]
    
    #     signalDataCull = np.reshape(signalData[:,featureInd], (-1,1))
    
    #     performMachineLearning = machineLearningMain.predictionModelHead(modelType, modelPath, numFeatures = 1, machineLearningClasses = listOfStressors, saveDataFolder = saveModelFolder, supportVectorKernel = supportVectorKernel)
        
    #     modelScore = performMachineLearning.scoreClassificationModel(signalDataCull, signalLabels, stratifyBy = stressLabels)
        
    #     # modelScores_Single0.append(modelScore[0])
    #     # modelScores_Single1.append(modelScore[1])
    #     # modelScores_Single2.append(modelScore[2])
    #     # modelScores_SingleTotal.append(modelScore[3])
        
    #     modelScores_SingleTotal.append(modelScore[0])
        
    # # excelProcessing.processMLData().saveFeatureComparison([modelScores_Single0], [], featureNames, saveModelFolder, "Single Feature Accuracy.xlsx", sheetName = "Feature Comparison Cold")
    # # excelProcessing.processMLData().saveFeatureComparison([modelScores_Single1], [], featureNames, saveModelFolder, "Single Feature Accuracy.xlsx", sheetName = "Feature Comparison Excersize")
    # # excelProcessing.processMLData().saveFeatureComparison([modelScores_Single2], [], featureNames, saveModelFolder, "Single Feature Accuracy.xlsx", sheetName = "Feature Comparison VR")
    # excelProcessing.processMLData().saveFeatureComparison([modelScores_SingleTotal], [], featureNames, saveModelFolder, "Single Feature Accuracy.xlsx", sheetName = "Feature Comparison Total")
    
    # modelScores = np.zeros((len(featureNames), len(featureNames)))
    # for featureIndRow in range(len(featureNames)):
    #     print(featureIndRow)
    #     featureRow = featureNames[featureIndRow]
    #     for featureIndCol in range(len(featureNames)):
    #         if featureIndCol < featureIndRow:
    #              modelScores[featureIndRow][featureIndCol] = modelScores[featureIndCol][featureIndRow]
    #              continue
             
    #         featureCol = featureNames[featureIndCol]
    #         signalDataCull = np.dstack((signalData[:,featureIndRow], signalData[:,featureIndCol]))[0]
            
    #         performMachineLearning = machineLearningMain.predictionModelHead(modelType, modelPath, numFeatures = 2, machineLearningClasses = listOfStressors, saveDataFolder = saveModelFolder, supportVectorKernel = supportVectorKernel)
    #         modelScore = performMachineLearning.trainModel(signalDataCull, signalLabels, returnScore = True, stratifyBy = stressLabels)
    #         modelScores[featureIndRow][featureIndCol] = modelScore
    # for featureIndRow in range(len(featureNames)):
    #     featureRow = featureNames[featureIndRow]
    #     for featureIndCol in range(len(featureNames)):
    #         if featureIndCol < featureIndRow:
    #              modelScores[featureIndRow][featureIndCol] = modelScores[featureIndCol][featureIndRow]
    #              continue
    # excelProcessing.processMLData().saveFeatureComparison(modelScores, featureNames, featureNames, saveModelFolder, "Pairwise Feature Accuracy.xlsx", sheetName = "Feature Comparison")

    sys.exit()
    

        
    
    featureNames = np.array(featureNames)
    
    
    featureNamesPermute_Good = featureNames_Combinations[np.array(modelScores) >= 0]
    signalData_Good = signalData[:,np.array(modelScores) >= 0]
    
    numFeaturesCombine = 3
    performMachineLearning = machineLearningMain.predictionModelHead(modelType, modelPath, numFeatures = len(featureNamesPermute_Good), machineLearningClasses = listOfStressors, saveDataFolder = saveModelFolder, supportVectorKernel = supportVectorKernel)
    modelScores, featureNames_Combinations = performMachineLearning.analyzeFeatureCombinations(signalData_Good, signalLabels, featureNamesPermute_Good, numFeaturesCombine, saveData = True, printUpdateAfterTrial = 15000, scaleY = testStressScores)
    



    bestFeatureNames = featureNames_Combinations[np.array(modelScores) >= 0.7]
    featureFound, featureFoundCounter = performMachineLearning.countScoredFeatures(bestFeatureNames)

    plt.bar(featureFound[featureFoundCounter > 2000], featureFoundCounter[featureFoundCounter > 2000])
    plt.xticks(rotation='vertical')
    
    
    
    featureNamesPermute_Good = featureFound[featureFoundCounter > 2]
    signalData_Good = performMachineLearning.getSpecificFeatures(featureNames, featureNamesPermute_Good, signalData)


    numFeaturesCombine = 4
    performMachineLearning = machineLearningMain.predictionModelHead(modelType, modelPath, numFeatures = len(featureNamesPermute_Good), machineLearningClasses = listOfStressors, saveDataFolder = saveModelFolder, supportVectorKernel = supportVectorKernel)
    modelScores, featureNames_Combinations = performMachineLearning.analyzeFeatureCombinations(signalData_Good, signalLabels, featureNamesPermute_Good, numFeaturesCombine, saveData = True, printUpdateAfterTrial = 15000, scaleY = testStressScores)
        
    
    
    
    
    
    
        
    
    sys.exit()
    
    
    if False:
        bestFeatures = ['systolicUpstrokeAccelMinVel_StressLevel', 'systolicUpSlopeArea_SignalIncrease', 'velDiffConc_Glucose', 'accelDiffMaxConc_Glucose', 'rightDiffAmp_Lactate']
        
        bestFeatures = ['reflectionIndex_SignalIncrease', 'dicroticPeakVel_SignalIncrease', 'dicroticPeakAccel_SignalIncrease', 'centralAugmentationIndex_EST_SignalIncrease']
        bestFeatures.extend(['bestprominence_GSR'])
        
        bestFeatures = ['systolicUpSlopeTime_SignalIncrease', 'accelDiffLeft_Glucose', 'maxAccelLeftIndAccel_Lactate', 'leftDiffAmp_Glucose', 'accelDiffLeftConc_Glucose']

        newSignalData = performMachineLearning.getSpecificFeatures(featureNames, bestFeatures, signalData)
    
    sys.exit()
    
    from sklearn.preprocessing import StandardScaler
    sc_X = StandardScaler()
    sc_y = StandardScaler()
    signalData_Standard = sc_X.fit_transform(newSignalData)
    signalLabels_Standard = sc_y.fit_transform(signalLabels.reshape(-1, 1))
    
    performMachineLearning.predictionModel.trainModel(signalData_Standard, signalLabels_Standard, signalData_Standard, signalLabels_Standard)
    performMachineLearning.predictionModel.scoreModel(signalData_Standard, signalLabels_Standard)

    signalData_Standard_Full = sc_X.fit_transform(signalData)
    performMachineLearning.predictionModel.trainModel(signalData_Standard, signalLabels, signalData_Standard, signalLabels)
    performMachineLearning.predictionModel.scoreModel(signalData_Standard, signalLabels)
    
    stressEquation = ""
    featureCoefficients = performMachineLearning.predictionModel.model.coef_[0]
   # featureCoefficients = performMachineLearning.predictionModel.model.dual_coef_
    for featureNum in range(len(featureCoefficients)):
        featureCoef = featureCoefficients[featureNum]
        featureName = bestFeatures[featureNum]
        print(featureCoef)
        
        stressEquation += str(np.round(featureCoef, 2)) + "*" + featureName + " + "
    stressEquation[0:-3]
    
    
    predictedLabels = performMachineLearning.predictionModel.predictData(signalData_Standard)
    
    signalLabels_Unscaled = sc_y.inverse_transform(signalLabels_Standard)
    predictedLabels_Unscaled = sc_y.inverse_transform(predictedLabels.reshape(-1, 1))
    
    plt.plot(predictedLabels_Unscaled, signalLabels_Unscaled, 'o', c='tab:brown')
    plt.title("Stress Prediction Accuracy")
    plt.xlabel("Predicted Stress Score")
    plt.ylabel("Actual Stress Score")

        
    # # ---------------------------------------------------------------------- #
    # #                          Train the Model                               #
    # # ---------------------------------------------------------------------- #
    
    # if trainModel:
    #     excelDataML = excelProcessing.processMLData()
    #     # Read in Training Data/Labels
    #     signalData = []; signalLabels = []; FeatureNames = []
    #     for MLFile in os.listdir(trainingDataExcelFolder):
    #         MLFile = trainingDataExcelFolder + MLFile
    #         signalData, signalLabels, FeatureNames = excelDataML.getData(MLFile, signalData = signalData, signalLabels = signalLabels, testSheetNum = 0)
    #     signalData = np.array(signalData); signalLabels = np.array(signalLabels)
    #     # Read in Validation Data/Labels
    #     Validation_Data = []; Validation_Labels = [];
    #     for MLFile in os.listdir(validationDataExcelFolder):
    #         MLFile = validationDataExcelFolder + MLFile
    #         Validation_Data, Validation_Labels, FeatureNames = excelDataML.getData(MLFile, signalData = Validation_Data, signalLabels = Validation_Labels, testSheetNum = 0)
    #     Validation_Data = np.array(Validation_Data); Validation_Labels = np.array(Validation_Labels)
    #     print("\nCollected Signal Data")
        
    #     Validation_Data = Validation_Data[:][:,0:6]
    #     signalData = signalData[:][:,0:6]
    #     FeatureNames = FeatureNames[0:6]
                    
    #     # Train the Data on the Gestures
    #     performMachineLearning.trainModel(signalData, signalLabels, pulseFeatureNames)
    #     # Save Signals and Labels
    #     if False and performMachineLearning.map2D:
    #         saveInputs = excelProcessing.saveExcel()
    #         saveExcelNameMap = "mapedData.xlsx" #"Signal Features with Predicted and True Labels New.xlsx"
    #         saveInputs.saveLabeledPoints(performMachineLearning.map2D, signalLabels,  performMachineLearning.predictionModel.predictData(signalData), saveDataFolder, saveExcelNameMap, sheetName = "Signal Data and Labels")
    #     # Save the Neural Network (The Weights of Each Edge)
    #     if saveModel:
    #         modelPathFolder = os.path.dirname(modelPath)
    #         os.makedirs(modelPathFolder, exist_ok=True)
    #         performMachineLearning.predictionModel.saveModel(modelPath)
    
    

     
     
     

     
     
     
     
     
     
     
     
     
     
     
     
     
     
     
     

     
     
     
     
     
     
     
     
     
     
     
     
     
  
   
   
   

