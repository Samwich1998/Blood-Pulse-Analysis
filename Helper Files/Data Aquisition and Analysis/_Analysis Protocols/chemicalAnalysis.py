
# Basic Modules
import os
import sys
import math
import numpy as np
# Peak Detection Modules
import scipy
import scipy.signal
# Data Filtering Modules
from scipy.signal import savgol_filter
# Matlab Plotting Modules
import matplotlib.pyplot as plt
# Gaussian Decomposition
from lmfit import Model
from sklearn.metrics import r2_score
# Feature Extraction Modules
from scipy.fft import fft
from scipy.stats import skew
from scipy.stats import entropy
from scipy.stats import kurtosis
from scipy.interpolate import UnivariateSpline

# Import Files
import _filteringProtocols as filteringMethods # Import Files with Filtering Methods

# Import Data Extraction Files (And Their Location)
sys.path.append('./Helper Files/Data Aquisition and Analysis/')  # Folder with All the Helper Files
import excelProcessing


# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #

class signalProcessing:
    
    def __init__(self, plotData = False):
        self.lowPassCutoff = 0.01
        
        self.minPeakDuration = 200
        
        self.minLeftBoundaryInd = 200
        
        self.plotData = plotData
        
        self.saveDataFolder = None
        
        self.resetGlobalVariables()  
        
        # Define the Class with all the Filtering Methods
        self.filteringMethods = filteringMethods.filteringMethods()
    
    def resetGlobalVariables(self, stimulusTimes = [None, None], saveDataFolder = "./", stimulusBuffer = 500):
        self.saveDataFolder = saveDataFolder
        os.makedirs(self.saveDataFolder, exist_ok=True)
        
        if stimulusTimes[0] != None:
            self.startStimulus = stimulusTimes[0]
            self.endStimulus = stimulusTimes[1]
            self.endStimulusBuffer = stimulusTimes[1] + stimulusBuffer
            self.startStimulusBuffer = stimulusTimes[0] - 200
        
        self.chemicalFeatures = {
            # Enzym
            'glucoseFeatures': [],
            'lactateFeatures': [],
            'uricAcidFeatures': [],
            # ISE
            'sodiumFeatures': [],
            'potassiumFeatures': [],
            'ammoniumFeatures': [],
        }
        
        self.chemicalFeatureLabels = {
            # Enzym
            'glucoseLabels': [],
            'lactateLabels': [],
            'uricAcidLabels': [], 
            # ISE
            'sodiumLabels': [],
            'potassiumLabels': [],
            'ammoniumLabels': [],
        }
        
        self.peakData = {"lactate":[], "glucose":[], "uricAcid":[], "sodium":[], "potassium":[], "ammonium":[]}        
    
    def analyzeData(self, xData, yData, chemicalName = ""):
        
        # ------------------------- Filter the Data ------------------------- #
        # Apply a Low Pass Filter
        self.samplingFreq = len(xData)/(xData[-1] - xData[0])
        yData = self.filteringMethods.bandPassFilter.butterFilter(yData, self.lowPassCutoff, self.samplingFreq, order = 4, filterType = 'low')
        #yData = self.filteringMethods.filterSVD.denoise(yData, math.ceil(np.sqrt(len(yData))))
        # ------------------------------------------------------------------- #
        
        # ---------------------- Find the Chemical Peak --------------------- #
        # Find Peaks in the Data
        chemicalPeakInd = self.findPeak(xData, yData)
        # Return None if No Peak Found
        if chemicalPeakInd == None:
            print("No Peak Found in " + chemicalName + " Data")
            self.plot(xData, yData, [], [], 0, 0, 0, chemicalName + " NO PEAK FOUND")
            return []
        # ------------------------------------------------------------------- #

        # ------------------- Find and Remove the Baseline ------------------ #
        # Get Baseline from Best Linear Fit
        leftCutInd, rightCutInd = self.findLinearBaseline(xData, yData, chemicalPeakInd)
        if None in [leftCutInd, rightCutInd] or rightCutInd - leftCutInd < self.minPeakDuration:
            print("No Baseline Found in " + chemicalName + " Data")
            # self.plot(xData, yData, [], [], chemicalPeakInd, 0, 0, chemicalName + " NO BASELINE FOUND")
            # return []
            
            leftCutInd = 250; rightCutInd = len(xData)-1
        
        # Fit Lines to Ends of Graph
        lineSlope, slopeIntercept = np.polyfit(xData[[leftCutInd, rightCutInd]], yData[[leftCutInd, rightCutInd]], 1)
        linearFit = lineSlope*xData + slopeIntercept

        # Apply a Smoothing Function
        yData = savgol_filter(yData, max(3, self.convertToOddInt((rightCutInd-leftCutInd)/5)), 2)  
        
        # Piece Together yData's Baseline
        baseline = np.concatenate((yData[0:leftCutInd], linearFit[leftCutInd: rightCutInd+1], yData[rightCutInd+1:len(yData)]))
        # Find yData After Baseline Subtraction
        baselineData = yData - baseline
        # ------------------------------------------------------------------- #

        # -------------------- Extract Features from Peak ------------------- #
        # Adjust the Peak's Ind After Baseline Subtraction
        chemicalPeakInd = np.argmax(baselineData)

        leftBaseInd = leftCutInd; rightBaseInd = rightCutInd
        # Extract the Features from the Data
        peakFeatures = self.extractFeatures(xData[leftBaseInd:rightBaseInd+1] - xData[leftBaseInd], baselineData[leftBaseInd:rightBaseInd+1], chemicalPeakInd-leftBaseInd, chemicalName)
        #peakFeatures = self.extractFeatures_Pointwise(xData[leftBaseInd:rightBaseInd+1] - xData[leftBaseInd], baselineData[leftBaseInd:rightBaseInd+1], chemicalPeakInd-leftBaseInd, chemicalName)
        
        if len(peakFeatures) == 0:
            print("No Features Found in " + chemicalName + " Data")
            return []
        # ------------------------------------------------------------------- #
        
        # -------------------------- Plot the Data -------------------------- #
        if self.plotData:
            self.plot(xData, yData, baselineData, linearFit, chemicalPeakInd, leftCutInd, rightCutInd, chemicalName)
        # ------------------------------------------------------------------- #
        
        # Store the Peak Data
        self.peakData[chemicalName].append((xData[leftBaseInd:rightBaseInd+1] - xData[leftBaseInd], baselineData[leftBaseInd:rightBaseInd+1]))
        # Return the Peak Features
        return peakFeatures
    
    def analyzeChemicals(self, timePoints, chemicalDataList, chemicalNames, label, analyzeTogether = True, iseData = False):
        assert(len(chemicalDataList) == len(chemicalNames))
        
        # Loop through each chemical
        for chemicalInd in range(len(chemicalDataList)):
            chemicalData = chemicalDataList[chemicalInd]
            chemicalName = chemicalNames[chemicalInd]
            
            chemicalFeatures = []; label = None
            if len(chemicalData) != 0:
                # Get the Chemical Features
                if iseData:
                    chemicalFeatures = self.analyzeData_ISE(timePoints, chemicalData, chemicalName)
                else:
                    chemicalFeatures = self.analyzeData(timePoints, chemicalData, chemicalName)
            elif analyzeTogether:
                self.resetGlobalVariables()

            # Save the Data
            self.chemicalFeatures[chemicalName + "Features"].append(chemicalFeatures)
            self.chemicalFeatureLabels[chemicalName + "Labels"].append(label)

    # ----------------------------------------------------------------------- #
    # ----------------------------------------------------------------------- #
    
    def convertToOddInt(self, x):
        return 2*math.floor((x+1)/2) - 1
    
    def findPeak(self, xData, yData, ignoredBoundaryPoints = 10, deriv = False):
        # Find All Peaks in the Data
        peakInfo = scipy.signal.find_peaks(yData, prominence=10E-10, width=20, distance = 20)
        # Extract the Peak Information
        peakProminences = peakInfo[1]['prominences']
        peakIndices = peakInfo[0]
        
        # Remove Peaks Nearby Boundaries
        allProminences = peakProminences[np.logical_and(peakIndices < len(xData) - ignoredBoundaryPoints, peakIndices >= ignoredBoundaryPoints)]
        peakIndices = peakIndices[np.logical_and(peakIndices < len(xData) - ignoredBoundaryPoints, peakIndices >= ignoredBoundaryPoints)]
        # Seperate Out the Stimulus Window
        allProminences = allProminences[self.startStimulusBuffer < xData[peakIndices]]
        peakIndices = peakIndices[self.startStimulusBuffer < xData[peakIndices]]
        allProminences = allProminences[self.endStimulusBuffer > xData[peakIndices]]
        peakIndices = peakIndices[self.endStimulusBuffer > xData[peakIndices]]

        # If Peaks are Found
        if len(peakIndices) > 0:
            # Take the Most Prominent Peak
            bestPeak = allProminences.argmax()
            peakInd = peakIndices[bestPeak]
            return peakInd
        elif not deriv:
            filteredVelocity = savgol_filter(np.gradient(yData), 251, 3)
            return self.findPeak(xData, filteredVelocity, deriv = True)
        # If No Peak is Found, Return None
        return None
    
    def findClosestExtrema(self, data, xPointer, binarySearchWindow = 1, maxPointsSearch = 500):
        if binarySearchWindow < 0:
            print("Setting binarySearchWindow to Positive")
            binarySearchWindow = abs(binarySearchWindow)
            
        # Check the Trends on Both Sides
        leftPoint = data[xPointer - abs(binarySearchWindow)]
        rightPoint = data[xPointer + abs(binarySearchWindow)]
        leftSlopesDown = leftPoint < data[xPointer]
        rightSlopesDown = rightPoint < data[xPointer]
                
        # If Both Sides Slope the Same Way, its an Extrema
        if leftSlopesDown == rightSlopesDown:
            return xPointer
        # If the Left Goes Down and the Right Goes Up -> its a positive slope
        elif leftSlopesDown and not rightSlopesDown:
            newPointer_Left = self.findNearbyMinimum(data, xPointer, -binarySearchWindow, maxPointsSearch)
            newPointer_Right = self.findNearbyMaximum(data, xPointer, binarySearchWindow, maxPointsSearch)
        # If the Left Goes Up and the Right Goes Down -> its a Negative slope
        else:
            newPointer_Left = self.findNearbyMinimum(data, xPointer, binarySearchWindow, maxPointsSearch)
            newPointer_Right = self.findNearbyMaximum(data, xPointer, -binarySearchWindow, maxPointsSearch)
        # Return the Furthest Pointer Away
        return min([newPointer_Left, newPointer_Right], key = lambda ind: abs(xPointer - ind))  
    
    def findClosestMax(self, data, xPointer, binarySearchWindow = 1, maxPointsSearch = 500):
        newPointer_Left = self.findNearbyMaximum(data, xPointer, -binarySearchWindow, maxPointsSearch)
        newPointer_Right = self.findNearbyMaximum(data, xPointer, binarySearchWindow, maxPointsSearch)
        if newPointer_Right == xPointer and newPointer_Left == xPointer:
            return self.findClosestMax(data, xPointer, binarySearchWindow*2, maxPointsSearch)
        if newPointer_Right == xPointer:
            return newPointer_Left
        elif newPointer_Left == xPointer:
            return newPointer_Right
        else:
            return min([newPointer_Left, newPointer_Right], key = lambda ind: abs(xPointer - ind))  
            
    def findNearbyMinimum(self, data, xPointer, binarySearchWindow = 5, maxPointsSearch = 10000):
        """
        Search Right: binarySearchWindow > 0
        Search Left: binarySearchWindow < 0
        """
        # Base Case
        if abs(binarySearchWindow) < 1 or maxPointsSearch == 0:
            searchSegment = data[max(0,xPointer-1):min(xPointer+2, len(data))]
            xPointer -= np.where(searchSegment==data[xPointer])[0][0]
            return xPointer + np.argmin(searchSegment) 
        
        maxHeightPointer = xPointer
        maxHeight = data[xPointer]; searchDirection = binarySearchWindow//abs(binarySearchWindow)
        # Binary Search Data to Find the Minimum (Skip Over Minor Fluctuations)
        for dataPointer in range(max(xPointer, 0), max(0, min(xPointer + searchDirection*maxPointsSearch, len(data))), binarySearchWindow):
            # If the Next Point is Greater Than the Previous, Take a Step Back
            if data[dataPointer] >= maxHeight and xPointer != dataPointer:
                return self.findNearbyMinimum(data, dataPointer - binarySearchWindow, round(binarySearchWindow/4), maxPointsSearch - searchDirection*(abs(dataPointer - binarySearchWindow)) - xPointer)
            # Else, Continue Searching
            else:
                maxHeightPointer = dataPointer
                maxHeight = data[dataPointer]

        # If Your Binary Search is Too Large, Reduce it
        return self.findNearbyMinimum(data, maxHeightPointer, round(binarySearchWindow/2), maxPointsSearch-1)
    
    def findNearbyMaximum(self, data, xPointer, binarySearchWindow = 5, maxPointsSearch = 10000):
        """
        Search Right: binarySearchWindow > 0
        Search Left: binarySearchWindow < 0
        """
        # Base Case
        xPointer = min(max(xPointer, 0), len(data)-1)
        if abs(binarySearchWindow) < 1 or maxPointsSearch == 0:
            searchSegment = data[max(0,xPointer-1):min(xPointer+2, len(data))]
            xPointer -= np.where(searchSegment==data[xPointer])[0][0]
            return xPointer + np.argmax(searchSegment)
        
        minHeightPointer = xPointer; minHeight = data[xPointer];
        searchDirection = binarySearchWindow//abs(binarySearchWindow)
        # Binary Search Data to Find the Minimum (Skip Over Minor Fluctuations)
        for dataPointer in range(xPointer, max(0, min(xPointer + searchDirection*maxPointsSearch, len(data))), binarySearchWindow):
            # If the Next Point is Greater Than the Previous, Take a Step Back
            if data[dataPointer] < minHeight and xPointer != dataPointer:
                return self.findNearbyMaximum(data, dataPointer - binarySearchWindow, round(binarySearchWindow/2), maxPointsSearch - searchDirection*(abs(dataPointer - binarySearchWindow)) - xPointer)
            # Else, Continue Searching
            else:
                minHeightPointer = dataPointer
                minHeight = data[dataPointer]

        # If Your Binary Search is Too Large, Reduce it
        return self.findNearbyMaximum(data, minHeightPointer, round(binarySearchWindow/2), maxPointsSearch-1)
    
    
    def findLinearBaseline(self, xData, yData, peakInd):
        # Define a threshold for distinguishing good/bad lines
        maxBadPointsTotal = int(len(xData)/10)
        # Store Possibly Good Tangent Indexes
        goodTangentInd = [[] for _ in range(maxBadPointsTotal)]
        
        # For Each Index Pair on the Left and Right of the Peak
        for rightInd in range(peakInd+2, len(yData), 1):
            for leftInd in range(peakInd-2, self.minLeftBoundaryInd, -1):
                
                # Initialize range of data to check
                checkPeakBuffer = 0#int((rightInd - leftInd)/4)
                xDataCut = xData[max(0, leftInd - checkPeakBuffer):rightInd + checkPeakBuffer]
                yDataCut = yData[max(0, leftInd - checkPeakBuffer):rightInd + checkPeakBuffer]
                
                # Draw a Linear Line Between the Points
                lineSlope = (yData[leftInd] - yData[rightInd])/(xData[leftInd] - xData[rightInd])
                slopeIntercept = yData[leftInd] - lineSlope*xData[leftInd]
                linearFit = lineSlope*xDataCut + slopeIntercept

                # Find the Number of Points Above the Tangent Line
                numWrongSideOfTangent = len(linearFit[linearFit - yDataCut > 0])
                
                # If a Tangent Line is Drawn Correctly, Return the Tangent Points' Indexes
                # if numWrongSideOfTangent == 0 and rightInd - leftInd > self.minPeakDuration:
                #     return (leftInd, rightInd)
                # Define a threshold for distinguishing good/bad lines
                maxBadPoints = int(len(linearFit)/15) # Minimum 1/6
                if numWrongSideOfTangent < maxBadPoints and rightInd - leftInd > self.minPeakDuration:
                    goodTangentInd[numWrongSideOfTangent].append((leftInd, rightInd))
                    
        # If Nothing Found, Try and Return a Semi-Optimal Tangent Position
        for goodInd in range(maxBadPointsTotal):
            if len(goodTangentInd[goodInd]) != 0:
                return max(goodTangentInd[goodInd], key=lambda tangentPair: tangentPair[1]-tangentPair[0])
        return None, None
    
    def findLineIntersectionPoint(self, leftLineParams, rightLineParams):
        xPoint = (rightLineParams[1] - leftLineParams[1])/(leftLineParams[0] - rightLineParams[0])
        yPoint = leftLineParams[0]*xPoint + leftLineParams[1]
        return xPoint, yPoint
    
    def pinpointExtrema(self, yData, xPointer, binarySearchMag, bufferSearch = 5):
        if yData[xPointer - bufferSearch]  < yData[xPointer + bufferSearch]:
            return xPointer
        elif yData[xPointer - bufferSearch] < yData[xPointer + bufferSearch]:
            return xPointer
    
    def calculateCurvature(self, xData, yData):
        # Calculate Derivatives
        dx_dt = np.gradient(xData); dx_dt2 = np.gradient(dx_dt); 
        dy_dt = np.gradient(yData); dy_dt2 = np.gradient(dy_dt);
        
        # Calculate Peak Shape parameters
        speed = np.sqrt(dx_dt * dx_dt + dy_dt * dy_dt)
        curvature = np.abs((dx_dt2 * dy_dt - dx_dt * dy_dt2)) / speed**3  # Units 1/Volts
        # Return the Curvature
        return curvature
        
    def extractFeatures_Pointwise(self, xData, baselineData, peakInd, chemicalName):
        # ----------------------- Derivative Analysis ----------------------- #   
        # Calculate the Signal Derivatives
        velocity = np.gradient(baselineData, xData, edge_order = 2)
        # Find the Velocity Extremas
        leftVelPeakInd = self.findNearbyMaximum(velocity, peakInd, binarySearchWindow = -1) - xData[peakInd]
        rightVelPeakInd = self.findNearbyMinimum(velocity, peakInd, binarySearchWindow = 1) - xData[peakInd]
        while rightVelPeakInd - leftVelPeakInd < 100:
            baselineData = savgol_filter(baselineData, max(3, self.convertToOddInt(len(baselineData)/5)), 2)  # 61/3,2
            leftVelPeakInd = self.findNearbyMaximum(velocity, peakInd, binarySearchWindow = -2) - xData[peakInd]
            rightVelPeakInd = self.findNearbyMinimum(velocity, peakInd, binarySearchWindow = 2) - xData[peakInd]
        xData -= xData[peakInd];
        
        # Normalize the Data
        baselineData = baselineData/baselineData[peakInd]
        xData = xData/baselineData[peakInd]
        
        # Fit the Data
        spl = UnivariateSpline(xData, baselineData, k=5)
        xs = np.linspace(leftVelPeakInd, rightVelPeakInd, 1000)
        baselineDataFit = spl(xs)
        # Calculate the Signal Derivatives
        velocity = np.gradient(baselineDataFit, xs, edge_order = 2)
        acceleration = np.gradient(velocity, xs, edge_order = 2)
        thirdDeriv = np.gradient(acceleration, xs, edge_order = 2)
        forthDeriv = np.gradient(thirdDeriv, xs, edge_order = 2)
        # ------------------------------------------------------------------- #
        
        
        # plt.show()
        # plt.plot(xData, baselineData, 'k--', linewidth= 2)
        # plt.plot(xs, baselineDataFit, 'k', linewidth= 2)
        # #plt.plot(xs[peakInd], baselineDataFit[peakInd], 'bo')
        # plt.plot(xs, velocity/max(abs(velocity)), 'tab:blue')
        # plt.plot(xs, acceleration/max(abs(acceleration)), 'tab:red')
        # #plt.plot(xs[[leftVelPeakInd, rightVelPeakInd]], (velocity/max(abs(velocity)))[[leftVelPeakInd, rightVelPeakInd]], 'o')
        # plt.ylim([-1.1, 1.1])
        # plt.show()

        # ----------------------- Store Peak Features ----------------------- #
        peakFeatures = []
        for peakInd in range(len(baselineDataFit)):
            peakFeatures.append([xs[peakInd], baselineDataFit[peakInd], velocity[peakInd], acceleration[peakInd], thirdDeriv[peakInd], forthDeriv[peakInd]])
        return peakFeatures
        # ------------------------------------------------------------------- #
    
    def extractFeatures(self, xData, baselineData, peakInd, chemicalName):
        
        # ------------------ Pre-Extract Relevant Features ------------------ #   
        # Extract PreNormalized Features
        peakConcentration = baselineData[peakInd]
        peakLeftBaselineConc = baselineData[0]
        peakRightBaselineConc = baselineData[-1]
        # Save the Features into an Array
        peakFeatures = [[peakConcentration, peakLeftBaselineConc, peakRightBaselineConc]]
        # ------------------------------------------------------------------- #

        # ---------------------- Gaussian Decomposition --------------------- #   
        # Calculate the Signal Derivatives
        velocity = np.gradient(baselineData, xData, edge_order = 2)
        acceleration = np.gradient(velocity, xData, edge_order = 2)
        thirdDeriv = np.gradient(acceleration, xData, edge_order = 2)
        forthDeriv = np.gradient(thirdDeriv, xData, edge_order = 2)
        
        isolatePeak = False
        if isolatePeak:
            # Find the Velocity Extremas
            leftStartVelSearch = self.findNearbyMinimum(velocity, 0, binarySearchWindow = 2)
            leftVelPeakInd = leftStartVelSearch + np.argmax(velocity[leftStartVelSearch:peakInd])
            rightEndVelSearch = self.findNearbyMinimum(velocity, len(velocity)-1, binarySearchWindow = -2)
            rightVelPeakInd = peakInd + np.argmin(velocity[peakInd:rightEndVelSearch])
            
            leftStartInd_Temp1 = self.findNearbyMaximum(acceleration, leftVelPeakInd, binarySearchWindow = -6)
            leftStartInd_Temp2 = self.findNearbyMaximum(thirdDeriv, leftStartInd_Temp1, binarySearchWindow = -6)
            leftStartInd_Temp3 = self.findNearbyMaximum(forthDeriv, leftStartInd_Temp2, binarySearchWindow = -6)
            leftStartInd_Temp4 = self.findNearbyMaximum(acceleration, leftStartInd_Temp3, binarySearchWindow = -6)
            leftStartInd = self.findNearbyMaximum(thirdDeriv, leftStartInd_Temp4, binarySearchWindow = -6)
    
            rightEndInd_Temp1 = self.findNearbyMaximum(acceleration, rightVelPeakInd, binarySearchWindow = 6)
            rightEndInd_Temp2 = self.findNearbyMinimum(thirdDeriv, rightEndInd_Temp1, binarySearchWindow = 6)
            rightEndInd = self.findNearbyMaximum(velocity, rightEndInd_Temp2, binarySearchWindow = 6)
            
            if rightEndInd - leftStartInd < 100:
                leftStartInd = 0; rightEndInd = len(baselineData)
                    
            xData = xData[leftStartInd:rightEndInd].copy()
            baselineData = baselineData[leftStartInd:rightEndInd].copy()
            peakInd = peakInd - leftStartInd
            
        xData -= xData[0]
        # Interpolate to increase points
        baselineDataInterpFunc = scipy.interpolate.interp1d(xData, baselineData, kind='cubic')
        xData = np.arange(xData[0], xData[-1], 1/10)
        baselineData = baselineDataInterpFunc(xData)
        peakInd = np.argmax(baselineData)
        # Gaussdian Decomposition
        baselineData = self.gausDecomp(xData/max(xData), baselineData/max(baselineData), peakInd, chemicalName)*max(baselineData)
        if len(baselineData) == 0:
            print("Bad Gaussian Decomp")
            return []
        peakInd = np.argmax(baselineData)
        # ------------------------------------------------------------------- #
        
        # ----------------------- Derivative Analysis ----------------------- #        
        # Calculate the Signal Derivatives
        velocity = np.gradient(baselineData, xData, edge_order = 2)
        acceleration = np.gradient(velocity, xData, edge_order = 2)
        thirdDeriv = np.gradient(acceleration, xData, edge_order = 2)

        # Find the Velocity Extremas
        leftVelPeakInd = self.findNearbyMaximum(velocity, peakInd, binarySearchWindow = -20, maxPointsSearch = len(velocity))
        rightVelPeakInd = self.findNearbyMinimum(velocity, peakInd, binarySearchWindow = 20, maxPointsSearch = len(velocity))
        
        # Find the Acceleration Extremas
        maxAccelLeftInd = self.findNearbyMaximum(acceleration, leftVelPeakInd, binarySearchWindow = -20, maxPointsSearch = len(acceleration))
        minAccelCenterInd = self.findNearbyMinimum(acceleration, leftVelPeakInd, binarySearchWindow = 30, maxPointsSearch = len(acceleration))
        maxAccelRightInd = self.findNearbyMaximum(acceleration, rightVelPeakInd, binarySearchWindow = 30, maxPointsSearch = len(acceleration))

        thirdDerivLeftMin = self.findNearbyMinimum(thirdDeriv, peakInd, binarySearchWindow = -20, maxPointsSearch = len(thirdDeriv))
        thirdDerivRightMax = self.findNearbyMaximum(thirdDeriv, peakInd, binarySearchWindow = 20, maxPointsSearch = len(thirdDeriv))
        # ------------------------------------------------------------------- #
        
        fig = plt.figure()
        # Plot Data
        plt.plot(xData, baselineData/max(baselineData), 'k', linewidth= 2, label = "Normalized Chemical Peak")
        plt.plot(xData, velocity/max(abs(velocity)), 'tab:blue', alpha = 0.8, label="Normalized First Derivative")
        plt.plot(xData, acceleration/max(abs(acceleration)), 'tab:red', alpha = 0.8, label="Normalized Second Derivative")
        # plt.plot(xData, thirdDeriv/max(abs(thirdDeriv)), 'tab:brown')
        # Label Peaks
        plt.plot(xData[peakInd], (baselineData/max(baselineData))[peakInd], 'ko', linewidth = 2)
        plt.plot(xData[[leftVelPeakInd, rightVelPeakInd]], (velocity/max(abs(velocity)))[[leftVelPeakInd, rightVelPeakInd]], 'o', c="tab:blue")
        plt.plot(xData[[maxAccelLeftInd, minAccelCenterInd, maxAccelRightInd]], (acceleration/max(abs(acceleration)))[[maxAccelLeftInd, minAccelCenterInd, maxAccelRightInd]], 'o', c="tab:red")
        # plt.plot(xData[[thirdDerivLeftMin, thirdDerivRightMax]], (thirdDeriv/max(abs(thirdDeriv[maxAccelLeftInd:maxAccelRightInd])))[[thirdDerivLeftMin, thirdDerivRightMax]], 'o')
        plt.title("Normalized " + chemicalName + " Signal")
        plt.xlabel("Time (Seconds)")
        plt.ylabel("Normalized peaks")
        plt.legend(prop={'size': 8})
        fig.savefig(self.saveDataFolder + "Normalized " + chemicalName.capitalize() + " Signal.pdf", dpi=300, bbox_inches='tight')
        plt.show()
        
        excelProcessing.dataProcessing().saveResults(np.array([xData, baselineData/max(baselineData), velocity/max(abs(velocity)), acceleration/max(abs(acceleration))]).T, ['xData', 'baselineData with peak at ' + str(peakInd), 'Deriv with cutoffs at' + str(leftVelPeakInd) + ', ' + str(rightVelPeakInd), '2nd Deriv with cutoffs at' + str(maxAccelLeftInd) + ', ' + str(minAccelCenterInd) + "," + str(maxAccelRightInd)], self.saveDataFolder, "Normalized " + chemicalName.capitalize() + " Signal.xlsx")

        
        # ----------------------- Indivisual Analysis ----------------------- #   
        # Store the Chemical Indices for Feature Extraction
        velInds = [leftVelPeakInd, rightVelPeakInd]
        accelInds = [maxAccelLeftInd, minAccelCenterInd, maxAccelRightInd]
        thirdDerivInds = [thirdDerivLeftMin, thirdDerivRightMax]
        
        # Perform Chemical-Specific Feature Extraction
        # if chemicalName == "Glucose":
        #     peakFeaturesNew = self.extractGlucoseFeatures(xData, baselineData, velocity, acceleration, peakInd, velInds, accelInds, thirdDerivInds)
        # elif chemicalName == "Lactate":
        #     peakFeaturesNew = self.extractLactateFeatures(xData, baselineData, velocity, acceleration, peakInd, velInds, accelInds, thirdDerivInds)
        # elif chemicalName == "Uric Acid":
        #     peakFeaturesNew = self.extractUricAcidFeatures(xData, baselineData, velocity, acceleration, peakInd, velInds, accelInds, thirdDerivInds)
        peakFeaturesNew = self.extractLactateFeatures(xData, baselineData, velocity, acceleration, peakInd, velInds, accelInds, thirdDerivInds)

        # Return the Final Peak Features
        if len(peakFeaturesNew) == 0:
            return []
        else:
            peakFeatures[0].extend(peakFeaturesNew)
            return peakFeatures        
        # ------------------------------------------------------------------- #
    
    def extractGlucoseFeatures(self, xData, baselineData, velocity, acceleration, peakInd, velInds, accelInds, thirdDerivInds):
        return []
        # ------------------------------------------------------------------- #
        
    def extractLactateFeatures(self, xData, baselineData, velocity, acceleration, peakInd, velInds, accelInds, thirdDerivInds):
        leftVelPeakInd, rightVelPeakInd = velInds
        maxAccelLeftInd, minAccelCenterInd, maxAccelRightInd = accelInds
        thirdDerivLeftMin, thirdDerivRightMax = thirdDerivInds

        # -------------------------- Time Features -------------------------- # 
        # Velocity Intervals
        velInterval = xData[rightVelPeakInd] - xData[leftVelPeakInd]
        velIntervalLeft = xData[peakInd] - xData[leftVelPeakInd]
        velIntervalRight = xData[rightVelPeakInd] - xData[peakInd]
        # Acceleration Intervals
        accelIntervalLeft = xData[maxAccelRightInd] - xData[minAccelCenterInd]
        accelIntervalRight = xData[minAccelCenterInd] - xData[maxAccelLeftInd]
        accelInterval = xData[maxAccelRightInd] - xData[maxAccelLeftInd]
        minAccelToPeak = xData[peakInd] - xData[minAccelCenterInd]

        # Third Derivative Intervals
        thirdDerivInterval = xData[thirdDerivRightMax] - xData[thirdDerivLeftMin]
        
        # Mixed Intervals
        peakRise_VelAccelInterval = xData[leftVelPeakInd] - xData[maxAccelLeftInd]
        peakFall_VelAccelInterval = xData[rightVelPeakInd] - xData[maxAccelRightInd]
        # ------------------------------------------------------------------- #
        
        # ------------------------ Amplitude Features ----------------------- #  
        # Amplitudes Based on the Velocity Extremas
        maxUpSlopeConc, maxDownSlopeConc = baselineData[[leftVelPeakInd, rightVelPeakInd]]
        maxUpSlopeVel, maxDownSlopeVel = velocity[[leftVelPeakInd, rightVelPeakInd]]
        # Amplitudes Based on the Acceleration Extremas
        maxAccelLeftIndConc, minAccelCenterIndConc, maxAccelRightIndConc = baselineData[[maxAccelLeftInd, minAccelCenterInd, maxAccelRightInd]]
        maxAccelLeftIndAccel, minAccelCenterIndAccel, maxAccelRightIndAccel = acceleration[[maxAccelLeftInd, minAccelCenterInd, maxAccelRightInd]]

        # Concentration Differences
        velDiffConc = maxUpSlopeConc - maxDownSlopeConc
        accelDiffMaxConc = maxAccelLeftIndConc - maxAccelRightIndConc
        accelDiffRightConc = maxAccelRightIndConc - minAccelCenterIndConc
        accelDiffLeftConc = maxAccelLeftIndConc - minAccelCenterIndConc
        # Velocity Differences
        velDiff = maxUpSlopeVel - maxDownSlopeVel
        # Acceleration Differences
        accelDiffMax = maxAccelLeftIndAccel - maxAccelRightIndAccel
        accelDiffRight = maxAccelRightIndAccel - minAccelCenterIndAccel
        accelDiffLeft = maxAccelLeftIndAccel - minAccelCenterIndAccel    
        
        # Peak Skew Amplitude
        leftDiffAmp = baselineData[peakInd] - baselineData[0]
        rightDiffAmp = baselineData[peakInd] - baselineData[-1]
        # ------------------------------------------------------------------- #

        # -------------------------- Slope Features ------------------------- #     
        # Get Full Slope Parameters
        maxSlopeRise = velocity[leftVelPeakInd]
        minSlopeFall = velocity[rightVelPeakInd]
        
        upSlopeTangentParams = [maxSlopeRise, baselineData[velInds[0]] - maxSlopeRise*xData[velInds[0]]]
        downSlopeTangentParams = [minSlopeFall, baselineData[velInds[1]] - minSlopeFall*xData[velInds[1]]]
        # ------------------------------------------------------------------- #
        
        # --------------------- Under the Curve Features -------------------- #        
        # General Areas
        velToVelArea = scipy.integrate.simpson(baselineData[leftVelPeakInd:rightVelPeakInd+1], xData[leftVelPeakInd:rightVelPeakInd+1])
        # ------------------------------------------------------------------- #
        
        # ----------------------- Peak Shape Features ----------------------- #   
        # Find Peak's Tent Features
        peakTentX, peakTentY = self.findLineIntersectionPoint(upSlopeTangentParams, downSlopeTangentParams)
        tentDeviationX = peakTentX - xData[peakInd]
        tentDeviationY = peakTentY - baselineData[peakInd]
        tentDeviationRatio = tentDeviationY/tentDeviationX

        # Calculate the New Baseline of the Peak
        startBlinkX, _ = self.findLineIntersectionPoint([0, 0], upSlopeTangentParams)
        endBlinkX, _ = self.findLineIntersectionPoint(downSlopeTangentParams, [0, 0])
        peakDuration_Final = endBlinkX - startBlinkX
        
        # Shape Parameters
        peakAverage = np.mean(baselineData[leftVelPeakInd:rightVelPeakInd+1])
        peakSTD = np.std(baselineData[leftVelPeakInd:rightVelPeakInd+1])
        peakEntropy = entropy(baselineData[leftVelPeakInd:rightVelPeakInd+1])
        peakSkew = skew(baselineData[leftVelPeakInd:rightVelPeakInd+1], bias=False)
        peakKurtosis = kurtosis(baselineData[leftVelPeakInd:rightVelPeakInd+1], fisher=True, bias = False)
        
        # Shape Parameters FFT
        baselineDataFFT = fft(baselineData)[leftVelPeakInd:rightVelPeakInd+1]
        peakHeightFFT = abs(baselineDataFFT[peakInd - leftVelPeakInd])
        leftVelHeightFFT = abs(baselineDataFFT[0])
        rightVelHeightFFT = abs(baselineDataFFT[rightVelPeakInd - leftVelPeakInd])
        
        peakSTD_FFT = np.std(baselineDataFFT, ddof=1)
        peakEntropyFFT = entropy(abs(baselineDataFFT))
        peakAverage = np.mean(baselineData[leftVelPeakInd:rightVelPeakInd+1])
        
        curvature = self.calculateCurvature(xData, baselineData)
        peakCurvature, leftVelCurvature, rightVelCurvature = curvature[[peakInd, leftVelPeakInd, rightVelPeakInd]]
        # ------------------------------------------------------------------- #

        # ----------------------- Store Peak Features ----------------------- #
        peakFeatures = []
        # Saving Features from Section: Time
        peakFeatures.extend([velInterval, velIntervalLeft, velIntervalRight])
        peakFeatures.extend([accelIntervalLeft, accelIntervalRight, accelInterval, minAccelToPeak])
        peakFeatures.extend([peakRise_VelAccelInterval, peakFall_VelAccelInterval, thirdDerivInterval])
        
        # Saving Features from Section: Amplitude Features
        peakFeatures.extend([maxUpSlopeConc, maxDownSlopeConc])
        peakFeatures.extend([maxUpSlopeVel, maxDownSlopeVel])
        peakFeatures.extend([maxAccelLeftIndConc, minAccelCenterIndConc, maxAccelRightIndConc])
        peakFeatures.extend([maxAccelLeftIndAccel, minAccelCenterIndAccel, maxAccelRightIndAccel])
        peakFeatures.extend([velDiffConc, accelDiffMaxConc, accelDiffRightConc, accelDiffLeftConc])
        peakFeatures.extend([velDiff, accelDiffMax, accelDiffRight, accelDiffLeft])
        peakFeatures.extend([leftDiffAmp, rightDiffAmp])
        
        # Saving Features from Section: Slope Features
        peakFeatures.extend([maxSlopeRise, minSlopeFall])
        
        # Saving Features from Section: Under the Curve Features
        peakFeatures.extend([velToVelArea])
        
        # Saving Features from Section: Peak Shape Features
        peakFeatures.extend([peakTentX, peakTentY, tentDeviationX, tentDeviationY, tentDeviationRatio, peakDuration_Final])
        peakFeatures.extend([peakAverage, peakSTD, peakEntropy, peakSkew, peakKurtosis])
        peakFeatures.extend([peakHeightFFT, leftVelHeightFFT,rightVelHeightFFT, peakSTD_FFT, peakEntropyFFT])
        peakFeatures.extend([peakCurvature, leftVelCurvature, rightVelCurvature])
        
        # Features for the Stress Scores (LACTATE)
        # peakFeatures.extend([accelDiffRightConc, rightDiffAmp])
                
        return peakFeatures
        # ------------------------------------------------------------------- #
        
        
    def extractUricAcidFeatures(self, xData, baselineData, velocity, acceleration, peakInd, velInds, accelInds, thirdDerivInds):
        return  []    
    
        # ------------------------------------------------------------------- #
        
        
    def analyzeData_ISE(self, xData, yData, chemicalName):
        
        # ------------------------- Filter the Data ------------------------ #
        # Apply a Low Pass Filter
        samplingFreq = len(xData)/(xData[-1] - xData[0])
        yData = self.filteringMethods.bandPassFilter.butterFilter(yData, self.lowPassCutoff, samplingFreq, order = 4, filterType = 'low')
        yData = self.filteringMethods.savgolFilter.savgolFilter(yData, 21, 2)
        # ------------------------------------------------------------------ #
        
        # ----------------------- Feature Extraction ----------------------- #
        # Find the Stimulus Start/Stop Ind
        startStimulusInd = self.startStimulus
        endStimulusInd = self.endStimulus
        
        # Extract Mean of the Data
        meanSignal = np.mean(yData)
        meanSignalRest = np.mean(yData[0:startStimulusInd])
        meanSignalStress = np.mean(yData[startStimulusInd:endStimulusInd])
        meanSignalRecovery = np.mean(yData[endStimulusInd:])
        meanStressIncrease = meanSignalStress - meanSignalRest
        
        # Extract Shape Features
        peakSTD = np.std(yData[startStimulusInd:], ddof=1)
        
        # Extract Slopes
        restSlope = np.polyfit(xData[int(startStimulusInd/4):int(startStimulusInd*3/4):], yData[int(startStimulusInd/4):int(startStimulusInd*3/4):], 1)[0]
        stressSlope = np.polyfit(xData[startStimulusInd + int((startStimulusInd-endStimulusInd)/4):endStimulusInd], yData[startStimulusInd + int((startStimulusInd-endStimulusInd)/4):endStimulusInd], 1)[0]
        relaxationSlope = np.polyfit(xData[self.endStimulusBuffer:], yData[self.endStimulusBuffer:], 1)[0]

        # Compile the Features
        peakFeatures = []
        peakFeatures.extend([meanSignal, meanSignalRest, meanSignalStress, meanSignalRecovery, meanStressIncrease])
        peakFeatures.extend([peakSTD, restSlope, stressSlope, relaxationSlope])
        # ------------------------------------------------------------------ #
        
        return peakFeatures
    
    def plot(self, xData, yData, baselineData, linearFit, peakInd, leftCutInd, rightCutInd, chemicalName = "Chemical"):
        fig = plt.figure()
        plt.plot(xData, yData, 'k', linewidth=2)
        plt.plot(xData[peakInd], yData[peakInd], 'bo')
        plt.plot(xData[[leftCutInd,rightCutInd]], yData[[leftCutInd,rightCutInd]], 'ro')
        if len(linearFit) > 0:
            plt.plot(xData, linearFit, 'r', alpha=0.5)
        if len(baselineData) > 0:
            plt.plot(xData, baselineData, 'tab:brown', linewidth=1.5)
         # Add Figure Title and Labels
        plt.title(chemicalName + " Data")
        plt.xlabel("Time (Sec)")
        plt.ylabel("Concentration (uM)")
        fig.savefig(self.saveDataFolder + chemicalName.capitalize() + " Data.pdf", dpi=300, bbox_inches='tight')
        # Display the Plot
        plt.show()
        
        excelProcessing.dataProcessing().saveResults(np.array([xData, yData, linearFit, baselineData]).T, ['xData', 'yData with peak at ' + str(peakInd), 'linearFit with cutoffs at' + str(leftCutInd) + ', ' + str(rightCutInd), 'baselineData'], self.saveDataFolder, chemicalName.capitalize() + " Data.xlsx")
        
        
    def gaussModel(self, xData, amplitude, fwtm, center):
        sigma = fwtm/(2*math.sqrt(2*math.log(10)))
        return amplitude * np.exp(-(xData-center)**2 / (2*sigma**2))
    
    def skewedGaussModel(self, xData, amplitude, fwtm, center, gamma):
        sigma = fwtm/(2*math.sqrt(2*math.log(10)))
        return amplitude * np.exp(-(xData-center)**2 / (2*sigma**2)) * (1 + scipy.special.erf(gamma*(xData - center)/(math.sqrt(2)*sigma)))
            
    def gausDecomp(self, xData, yData, peakInd, chemicalName, addExtraGauss = False, addExtraGauss2 = False, addExtraGauss3 = False):
        # https://lmfit.github.io/lmfit-py/builtin_models.html#example-1-fit-peak-data-to-gaussian-lorentzian-and-voigt-profiles

        peakAmp = yData[peakInd]; peakCenter = xData[peakInd];
        fwtm = xData[-1] - xData[0]
        numberOfGaussians = 1
        
        gmodel =  Model(self.skewedGaussModel, prefix = "g1_", xData = xData)
        pars = gmodel.make_params()
        pars['g1_gamma'].set(value = 0, min = -50, max = 50)
        pars['g1_center'].set(value = xData[peakInd], min = xData[0], max = xData[-1])
        pars['g1_fwtm'].set(value = fwtm*3/4, min = 0.1, max = fwtm)
        pars['g1_amplitude'].set(value = peakAmp, min= 0.1, max = peakAmp*1.1)
        
        if addExtraGauss:
            numberOfGaussians += 1
            g2PeakInd = len(xData)-peakInd
            peakCenter2 = xData[g2PeakInd]
            peakAmp2 = yData[g2PeakInd]
            
            gmodel2 =  Model(self.skewedGaussModel, prefix = "g2_", xData = xData)
            pars.update(gmodel2.make_params())
            pars['g2_gamma'].set(value = 0, min = -50, max = 50)
            pars['g2_center'].set(value = peakCenter2, min = xData[0], max = xData[-1])
            pars['g2_fwtm'].set(value = fwtm/3, min = 0.05, max = fwtm*1.5)
            pars['g2_amplitude'].set(value = peakAmp2/2, min= 0.025, max = peakAmp)
            gmodel += gmodel2
            
        if addExtraGauss2:
            numberOfGaussians += 1
            gmodel3 =  Model(self.gaussModel, prefix = "g3_", xData = xData)
            pars.update(gmodel3.make_params())
            pars['g3_amplitude'].set(value = peakAmp/3, min= 0.025, max = peakAmp)
            pars['g3_fwtm'].set(value = fwtm/5, min = 0.05, max = fwtm)
            pars['g3_center'].set(value = peakCenter, min = xData[0], max = xData[-1])
            gmodel += gmodel3
        
        if addExtraGauss3:
            numberOfGaussians += 1
            gmodel4 =  Model(self.gaussModel, prefix = "g4_", xData = xData)
            pars.update(gmodel4.make_params())
            pars['g4_amplitude'].set(value = peakAmp/4, min= 0.025, max = peakAmp)
            pars['g4_fwtm'].set(value = fwtm/6, min = 0.05, max = fwtm)
            pars['g4_center'].set(value = peakCenter, min = xData[0], max = xData[-1])
            gmodel += gmodel4
            
        finalFitInfo = gmodel.fit(yData, pars, xData=xData, method='bfgs')

        coefficient_of_dermination = np.round(r2_score(yData, finalFitInfo.best_fit), 6)
        comps = finalFitInfo.eval_components(xData=xData)
    
        def findBestGaus():
            Amplitudes = []
            for prefix in range(1, 1+numberOfGaussians):
                prefix = 'g' + str(prefix) + '_'
                data = finalFitInfo.eval_components(xData=xData)[prefix]
                
                Amplitudes.append(max(data))
            return 'g' + str(np.argmax(Amplitudes)+1) + '_'                
                    
        # Plot the Pulse with its Fit 
        def plotGaussianFit(xData, yData, peakInd, comps):
            gaussDecompInfo = [xData, yData];
            gaussDecompHeader = ["Normalized X-Data", "Normalized Y-Data"]
            
            fig = plt.figure()
            
            xData = np.array(xData); yData = np.array(yData)
            dely = finalFitInfo.eval_uncertainty(sigma=3)
            plt.plot(xData, yData, linewidth = 2, color = "black")
            plt.plot(xData[peakInd], yData[peakInd], 'o')

            plt.plot(xData, comps[findBestGaus()], '--', color = "tab:brown", alpha = 1, linewidth=4, label='Chosen Gaussian')
            plt.plot(xData, comps['g1_'], '--', color = "tab:red", alpha = 0.8, label='Skewed Gaussian Fit')
            
            gaussDecompHeader.append("Final Fit"); gaussDecompInfo.append(finalFitInfo.best_fit)
            gaussDecompHeader.append("Final Fit Uncertainty"); gaussDecompInfo.append(dely)
            gaussDecompHeader.append("Chosen Gaus Data"); gaussDecompInfo.append(comps[findBestGaus()])
            gaussDecompHeader.append("Gaus Data"); gaussDecompInfo.append(comps['g1_'])

            if addExtraGauss:
                plt.plot(xData, comps['g2_'], '--', color = "tab:blue", alpha = 0.5, label='Extra Skewed Gauss')
                gaussDecompHeader.append("Second Gaus Data"); gaussDecompInfo.append(comps['g2_'])
            if addExtraGauss2:
                plt.plot(xData, comps['g3_'], '--', color = "tab:purple", alpha = 0.5, label='Extra Gauss')
                gaussDecompHeader.append("Third Gaus Data"); gaussDecompInfo.append(comps['g3_'])
            if addExtraGauss3:
                plt.plot(xData, comps['g4_'], '--', color = "tab:orange", alpha = 0.5, label='Extra Gauss2')
                gaussDecompHeader.append("Fourth Gaus Data"); gaussDecompInfo.append(comps['g4_'])

            plt.fill_between(xData, finalFitInfo.best_fit-dely, finalFitInfo.best_fit+dely, color="#ABABAB", label='3-$\sigma$ uncertainty band')
            
            plt.legend(loc='best')
            plt.title("Gaussian Decomposition for " + chemicalName + " " + str(np.round(coefficient_of_dermination, 4)))
            plt.xlabel("Time (Seconds)")
            plt.ylabel("Chemical peak")
            fig.savefig(self.saveDataFolder + chemicalName.capitalize() + " Gaussian Decomposition using " + str(numberOfGaussians) + " Gaussians.pdf", dpi=300, bbox_inches='tight')
            plt.show()
            
            excelProcessing.dataProcessing().saveResults(np.array(gaussDecompInfo).T, gaussDecompHeader, self.saveDataFolder, chemicalName.capitalize() + " Gaussian Decomposition using " + str(numberOfGaussians) + " Gaussians.xlsx")
        
        dely = finalFitInfo.eval_uncertainty(sigma=3)
        avUncertainty = np.round(sum(finalFitInfo.best_fit-dely)/len(dely), 5)
        plotGaussianFit(xData, yData, peakInd, comps)
        if np.mean(dely) < 1 and \
                (coefficient_of_dermination > 0.984 or \
                (coefficient_of_dermination > 0.98 and addExtraGauss) or \
                (coefficient_of_dermination > 0.98 and addExtraGauss2) or \
                (coefficient_of_dermination > 0.98 and addExtraGauss3)):
            bestPrefix = findBestGaus()
            return finalFitInfo.eval_components(xData=xData)[bestPrefix]
        elif not addExtraGauss:
            return self.gausDecomp(xData, yData, peakInd, chemicalName, addExtraGauss = True)
        elif not addExtraGauss2:
            return self.gausDecomp(xData, yData, peakInd, chemicalName, addExtraGauss = True, addExtraGauss2 = True)
        elif not addExtraGauss3:
            return self.gausDecomp(xData, yData, peakInd, chemicalName, addExtraGauss = True, addExtraGauss2 = True, addExtraGauss3 = True)
        else:
            print(avUncertainty, coefficient_of_dermination)
            return finalFitInfo.eval_components(xData=xData)[findBestGaus()] #[]

        




   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   
   

    