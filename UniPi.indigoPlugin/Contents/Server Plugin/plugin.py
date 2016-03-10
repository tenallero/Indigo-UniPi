#! /usr/bin/env python
# -*- coding: utf-8 -*-
#######################

import websocket
import socket
import json
import os
import sys
import indigo
from decimal import Decimal
import datetime
import urllib
import urllib2
import thread
import threading
from ghpu import GitHubPluginUpdater

class Plugin(indigo.PluginBase):

    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self.updater = GitHubPluginUpdater('tenallero', 'Indigo-UniPi', self)
        self.apiVersion    = "2.0"
        # Pooling
        self.pollingInterval = 0
        # create empty device list
        self.boardList = {}
        self.relayList = {}
        self.digitalInputList = {}
        self.digitalCounterList = {}
        self.analogInputList = {}
        self.analogOutputList = {}
        self.tempSensorList = {}

        self.websocketEnabled = True


    def __del__(self):
        indigo.PluginBase.__del__(self)

    ###################################################################
    # Plugin
    ###################################################################

    def deviceStartComm(self, device):
        self.debugLog(u"Started " + device.deviceTypeId + ": " + device.name)
        device.stateListOrDisplayStateIdChanged()
        self.addDeviceToList (device)

    def deviceCreated(self, device):
        self.debugLog(u"Created device of type \"%s\"" % device.deviceTypeId)
 
    def addDeviceToList(self,device):
        if device.deviceTypeId == u"UniPiBoard":
            #self.updateDeviceState (device,'state' ,'off')
            device.updateStateOnServer(key='onOffState', value=False)
            device.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
            propsAddress = ''
            propsPort = ''

            if device.id not in self.boardList:
                propsAddress = device.pluginProps["address"]
                propsPort    = device.pluginProps["port"]
                propsAddress = propsAddress.strip()
                propsAddress = propsAddress.replace (' ','')
                propsPort    = propsPort.replace (' ','')
                if int(propsPort) <=0:
                    propsPort = "80"

                if propsPort == "80":
                    wsurl = "ws://" + propsAddress + "/ws"
                else:
                    wsurl = "ws://" + propsAddress + ":" + propsPort + "/ws"

                self.boardList[device.id] = {'ref':device, 'address':propsAddress, 'port':propsPort, 'wsurl':wsurl, 'lastTimeSensor':datetime.datetime.now(),'websocketok': False}
            self.startupWebSockets (device)

        elif device.deviceTypeId == u"UniPiRelay":
            if device.id not in self.relayList:
                self.relayList[device.id] = {'ref':device, 'unipiSel':int(device.pluginProps["unipiSel"]), 'circuit':int(device.pluginProps["circuit"])}
                #device.pluginProps["address"] = 'relay' + str(device.pluginProps["circuit"])
        elif device.deviceTypeId == u"UniPiDigitalInput":
            if device.id not in self.digitalInputList:
                self.digitalInputList[device.id] = {'ref':device, 'unipiSel':int(device.pluginProps["unipiSel"]), 'circuit':int(device.pluginProps["circuit"])}
                #device.pluginProps["address"] = 'digitalinput' + str(device.pluginProps["circuit"])
        elif device.deviceTypeId == u"UniPiDigitalCounter":
            device.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)
            if device.id not in self.digitalCounterList:
                self.digitalCounterList[device.id] = {'ref':device, 'unipiSel':int(device.pluginProps["unipiSel"]), 'circuit':int(device.pluginProps["circuit"])}
                #device.pluginProps["address"] = 'digitalinput' + str(device.pluginProps["circuit"])

        elif device.deviceTypeId == u"UniPiAnalogInput":
            if device.id not in self.analogInputList:
                self.analogInputList[device.id] = {'ref':device, 'unipiSel':int(device.pluginProps["unipiSel"]), 'circuit':int(device.pluginProps["circuit"])}
                #device.pluginProps["address"] = 'analoginput' + str(device.pluginProps["circuit"])
        elif device.deviceTypeId == u"UniPiAnalogOutput":
            if device.id not in self.analogOutputList:
                self.analogOutputList[device.id] = {'ref':device, 'unipiSel':int(device.pluginProps["unipiSel"]), 'circuit':int(device.pluginProps["circuit"])}
                #device.pluginProps["address"] = 'analogoutput' + str(device.pluginProps["circuit"])
        elif device.deviceTypeId == u"UniPiTempSensor":
            device.updateStateImageOnServer(indigo.kStateImageSel.TemperatureSensorOn)
            if device.id not in self.tempSensorList:
                self.tempSensorList[device.id] = {'ref':device, 'unipiSel':int(device.pluginProps["unipiSel"]), 'circuit':device.pluginProps["circuit"], 'logLastValue':0.0}
                #device.pluginProps["address"] = '1wiresensor' + str(device.pluginProps["circuit"])


    def deviceStopComm(self,device):
        indigo.server.log (u"Stopping device \"%s\" of type \"%s\"" % (device.name, device.deviceTypeId))
        self.delDeviceFromList(device)   

    def deviceDeleted(self, device):
        indigo.server.log (u"Deleted device \"%s\" of type \"%s\"" % (device.name, device.deviceTypeId))
        self.delDeviceFromList(device)  
 
    def delDeviceFromList(self,device):
        if device.deviceTypeId == u"UniPiBoard":
            if device.id in self.boardList:
                self.debugLog("Stoping UniPi board device: " + device.name)
                del self.boardList[device.id]
        if device.deviceTypeId == u"UniPiRelay":
            if device.id in self.relayList:                
                del self.relayList[device.id]
        if device.deviceTypeId == u"UniPiDigitalInput":
            if device.id in self.digitalInputList:               
                del self.digitalInputList[device.id]
        if device.deviceTypeId == u"UniPiDigitalCounter":
            if device.id in self.digitalCounterList:               
                del self.digitalCounterList[device.id]
        if device.deviceTypeId == u"UniPiAnalogInput":
            if device.id in self.analogInputList:               
                del self.analogInputList[device.id]
        if device.deviceTypeId == u"UniPiAnalogOutput":
            if device.id in self.analogOutputList:               
                del self.analogOutputList[device.id]
        if device.deviceTypeId == u"UniPiTempSensor":
            if device.id in self.tempSensorList:              
                del self.tempSensorList[device.id]

    def startup(self):
        self.loadPluginPrefs()
        self.debugLog(u"startup called")
        self.updater.checkForUpdate()

    def shutdown(self):
        self.debugLog(u"shutdown called")

    def getDeviceConfigUiValues(self, pluginProps, typeId, devId):
        valuesDict = pluginProps
        errorMsgDict = indigo.Dict()
        if self._devTypeIdIsMirrorDevice(typeId):
            if "unipiSel" not in valuesDict:
                valuesDict["unipiSel"] = 0
            if "circuit" not in valuesDict:
                valuesDict["circuit"] = 0
        return (valuesDict, errorMsgDict)

    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        self.debugLog(u"validating device Prefs called")
        if typeId == u"UniPiBoard":
            self.debugLog(u"validating IP Address")
            ipAdr = valuesDict[u'address']
            if ipAdr.count('.') != 3:
                errorMsgDict = indigo.Dict()
                errorMsgDict[u'address'] = u"This needs to be a valid IP address."
                return (False, valuesDict, errorMsgDict)
            if self.validateAddress (ipAdr) == False:
                errorMsgDict = indigo.Dict()
                errorMsgDict[u'address'] = u"This needs to be a valid IP address."
                return (False, valuesDict, errorMsgDict)
            self.debugLog(u"validating TCP Port")
            tcpPort = valuesDict[u'port']
            try:
                iPort = int(tcpPort)
                if iPort <= 0:
                    errorMsgDict = indigo.Dict()
                    errorMsgDict[u'port'] = u"This needs to be a valid TCP port."
                    return (False, valuesDict, errorMsgDict)
            except Exception, e:
                errorMsgDict = indigo.Dict()
                errorMsgDict[u'port'] = u"This needs to be a valid TCP port."
                return (False, valuesDict, errorMsgDict)
        if typeId == u"UniPiRelay":
            if int(valuesDict[u'unipiSel']) <= 0:
                errorMsgDict[u'unipiSel'] = u"Need to choose a Unipi device"
                return (False, valuesDict, errorMsgDict)
            if int(valuesDict[u'circuit']) <= 0:
                errorMsgDict[u'circuit'] = u"Need to choose a relay"
                return (False, valuesDict, errorMsgDict)
            pass
        if typeId == u"UniPiDigitalInput":
            if int(valuesDict[u'unipiSel']) <= 0:
                errorMsgDict[u'unipiSel'] = u"Need to choose a Unipi device"
                return (False, valuesDict, errorMsgDict)
            if int(valuesDict[u'circuit']) <= 0:
                errorMsgDict[u'circuit'] = u"Need to choose a digital input"
                return (False, valuesDict, errorMsgDict)
            pass
        if typeId == u"UniPiDigitalCounter":
            if int(valuesDict[u'unipiSel']) <= 0:
                errorMsgDict[u'unipiSel'] = u"Need to choose a Unipi device"
                return (False, valuesDict, errorMsgDict)
            if int(valuesDict[u'circuit']) <= 0:
                errorMsgDict[u'circuit'] = u"Need to choose a digital input"
                return (False, valuesDict, errorMsgDict)
            pass
        if typeId == u"UniPiAnalogInput":
            if int(valuesDict[u'unipiSel']) <= 0:
                errorMsgDict[u'unipiSel'] = u"Need to choose a Unipi device"
                return (False, valuesDict, errorMsgDict)
            if int(valuesDict[u'circuit']) <= 0:
                errorMsgDict[u'circuit'] = u"Need to choose an analog input"
                return (False, valuesDict, errorMsgDict)
            pass
        if typeId == u"UniPiAnalogOutput":
            if int(valuesDict[u'unipiSel']) <= 0:
                errorMsgDict[u'unipiSel'] = u"Need to choose a Unipi device"
                return (False, valuesDict, errorMsgDict)
            if int(valuesDict[u'circuit']) <= 0:
                errorMsgDict[u'circuit'] = u"Need to choose an analog output"
                return (False, valuesDict, errorMsgDict)
            pass
        if typeId == u"UniPiTempSensor":
            if int(valuesDict[u'unipiSel']) <= 0:
                errorMsgDict[u'unipiSel'] = u"Need to choose a Unipi device"
                return (False, valuesDict, errorMsgDict)
            if valuesDict[u'circuit'].strip()  == "":
                errorMsgDict[u'circuit'] = u"Need to choose a 1-Wire address"
                return (False, valuesDict, errorMsgDict)
            pass

        return (True, valuesDict)

    def validatePrefsConfigUi(self, valuesDict):
        self.debugLog(u"validating Prefs called")
        return (True, valuesDict)

    def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):
        if userCancelled is False:
            indigo.server.log ("Device preferences were updated.")

    def closedPrefsConfigUi ( self, valuesDict, UserCancelled):
        #   If the user saves the preferences, reload the preferences
        if UserCancelled is False:
            indigo.server.log ("Preferences were updated, reloading Preferences...")
            self.loadPluginPrefs()

    def loadPluginPrefs(self):
        # set debug option
        if 'debugEnabled' in self.pluginPrefs:
            self.debug = self.pluginPrefs['debugEnabled']
        else:
            self.debug = False


    def validateAddress (self,value):
        try:
            socket.inet_aton(value)
        except socket.error:
            return False
        return True

    ######################



    def menuListUniPi(self, filter, valuesDict, typeId, elemId):
        menuList = []
        for dev in indigo.devices.iter("self"):
            if dev.deviceTypeId == "UniPiBoard":
                menuList.append((dev.id, dev.name))
        return menuList

    def menuListDigitalInput(self, filter, valuesDict, typeId, devId):
        menuList = []
        for pin in range(1, 14):
            labelVal = 'Digital input #' + str(pin)
            menuList.append((pin, labelVal))
        return menuList

    def menuListRelay(self, filter, valuesDict, typeId, devId):
        menuList = []
        for pin in range(1, 9):
            labelVal = 'Relay #' + str(pin)
            menuList.append((pin, labelVal))
        return menuList

    def menuListAnalogInput(self, filter, valuesDict, typeId, devId):
        menuList = []
        for pin in range(1, 3):
            labelVal = 'Analog input #' + str(pin)
            menuList.append((pin, labelVal))
        return menuList

    def menuListAnalogOutput(self, filter, valuesDict, typeId, devId):
        menuList = []
        for pin in range(1, 2):
            labelVal = 'Analog output #' + str(pin)
            menuList.append((pin, labelVal))
        return menuList

    def menuClearSelDev(self, valuesDict, typeId, elemId):
        valuesDict["circuit"] = 0
        return valuesDict


    def counterAcumResetUI(self, valuesDict, typeId, deviceId):
        if deviceId > 0:
            device = indigo.devices[deviceId]
            self.counterAcumReset(device)
        return valuesDict   
        
    def counterAcumReset(self, device):
        #indigo.device.resetaccumEnergyTotal(device)
        indigo.server.log (u"reseting values for device \"%s\" " % (device.name))  
        device.updateStateOnServer(key='counterAcum', value=0)
        device.updateStateOnServer(key='accumEnergyTotal', value=0) 
        device.updateStateOnServer(key='sensorValue', value=0, uiValue=u"(reset)")  
        device.updateStateOnServer(key='onOffState',value=False) 
        

    
    ###################################################################
    # Concurrent Thread.
    ###################################################################

    def runConcurrentThread(self):

        poolCheckWS = 10
        poolCheckStatus = 60

        countCheckWS = 0
        countCheckStatus = 1000

        while not self.stopThread:
            self.sleep(0.5)
            countCheckWS += 1
            countCheckStatus += 1

            if countCheckWS > poolCheckWS:
                countCheckWS = 0
                for unipi in self.boardList:
                    if not self.boardList[unipi]['websocketok']:
                        deviceBoard = self.boardList[unipi]["ref"]
                        self.startupWebSockets (deviceBoard)
            if countCheckStatus > poolCheckStatus:
                countCheckStatus = 0
                self.boardRequestStatusAll()

        pass

    def stopConcurrentThread(self):
        self.stopThread = True
        self.debugLog(u"stopConcurrentThread called")

    def updateDeviceState(self,device,state,newValue):
        if (newValue != device.states[state]):
            device.updateStateOnServer(key=state, value=newValue)

    ###################################################################
    # Web Sockets
    ###################################################################

    def on_wsmessage(self, ws, message):
        
        try:
            requestStatus = False
            obj = json.loads(message)
            itemType = obj['dev'] 
            if itemType == "relay":
                requestStatus = True
            elif itemType == "input":
                requestStatus = True
            elif itemType == "ai":
                pass
            elif itemType == "ao":
                pass
            elif itemType == "temp":
                requestStatus = True
        except Exception,e:
            self.errorLog(u"Websocket parsing error: " + str(e))
    
        if requestStatus:
            unipi = self.getUnipiBoardIndexFromUrl(ws.url)
            if not unipi == None:
                deviceBoard = self.boardList[unipi]["ref"]
                self.boardList[unipi]['websocketok'] = True
                self.updateDeviceState (deviceBoard,'state' ,'on')
                
                #self.boardRequestStatus(deviceBoard,False)
                mapObject = self.getMapFromMessage(obj)
                mapObject["deviceBoard"] = deviceBoard.id
                self.setIndigoStateFromJson (mapObject)
             
    def on_wserror(self, ws, error):
        self.errorLog(u"Websocket error: " + str(error))
        unipi = self.getUnipiBoardIndexFromUrl(ws.url)
        if not unipi == None:
            self.boardList[unipi]['websocketok'] = False
            #self.boardList[unipi]["ref"].updateStateImageOnServer(indigo.kStateImageSel.Error)

    def on_wsclose(self, ws):
        unipi = self.getUnipiBoardIndexFromUrl(ws.url)
        if not unipi == None:
            deviceBoard = self.boardList[unipi]["ref"]
            self.boardList[unipi]['websocketok'] = False
            self.errorLog (u"Websocket closed for " + deviceBoard.name)

    def getUnipiBoardDeviceFromUrl (self,url):
        deviceBoard = None
        for unipi in self.boardList:
            url2 = self.boardList[unipi]['wsurl']
            if url == url2:
                deviceBoard = self.boardList[unipi]["ref"]
        if deviceBoard == None:
            self.errorLog (u"Device not found for websocket url " + url)
        return deviceBoard

    def getUnipiBoardIndexFromUrl (self,url):
        index = None
        for unipi in self.boardList:
            url2 = self.boardList[unipi]['wsurl']
            if url == url2:
                index = unipi
        if index == None:
            self.errorLog (u"Device not found for websocket url " + url)
        return index

    def startupWebSocketsAll (self):
        for unipi in self.boardList:
            self.startupWebSockets(self.boardList[unipi])

    def startupWebSockets (self, device):
        try:
            url = self.boardList[device.id]["wsurl"]
            self.debugLog (u"Starting websocket client for " + device.name + " on url " + url)

            websocket.enableTrace(True)
            ws = websocket.WebSocketApp(url, on_message = self.on_wsmessage, on_error = self.on_wserror, on_close = self.on_wsclose)
            wst = threading.Thread(target=ws.run_forever)
            wst.setDaemon(True)
            wst.start()

            for unipi in self.boardList:
                if self.boardList[unipi]['ref'].id == device.id:
                    self.boardList[unipi]['websocketok'] = True

        except Exception,e:
            self.errorLog (u"startupWebSockets error: " + str(e))


    ###################################################################
    # Mirror relay
    ###################################################################

    def _devTypeIdIsMirrorDevice(self, typeId):
        return typeId in (u"UniPiBoard")

    def _devTypeIdIsMirrorOutput(self, typeId):
        return typeId in (u"UniPiRelay",u"UniPiAnalogOutput")

    def _devTypeIdIsMirrorInput(self, typeId):
        return typeId in (u"UniPiDigitalInput", u"UniPiAnalogInput", u"UniPiTemperatureeSensor")

    ###################################################################
    # Request Status
    ###################################################################
    
    def boardRequestStatusAll(self):
        for unipi in self.boardList:
            deviceBoard  = self.boardList[unipi]["ref"]
            self.boardRequestStatus(deviceBoard,False)

    def boardRequestStatus(self,device,verbose):
        payloadJson = ""
        deviceBoard = None

        if verbose and device == None:
            self.errorLog(u"no device specified")
            return

        if device.deviceTypeId == 'UniPiBoard':
            deviceBoard = device
            unipiSel = device.id
        else:
            unipiSel = int(device.pluginProps["unipiSel"])
            for unipi in self.boardList:
                if self.boardList[unipi]['ref'].id == unipiSel:
                    deviceBoard  = self.boardList[unipi]["ref"]


        if verbose and deviceBoard == None:
            self.errorLog(u"UniPi Board not found")
            return
        if verbose and not deviceBoard.deviceTypeId == 'UniPiBoard':
            self.errorLog(u"Expected Unipi board device type")
            return

        addressWrite = deviceBoard.pluginProps["address"]
        portWrite    = deviceBoard.pluginProps['port']

        if int(portWrite) <=0:
            portWrite = "80"

        restUrl = "http://" + addressWrite + ":" + portWrite + "/rest/all"

        try:
            if verbose:
                indigo.server.log(u'Sent "' + device.name + '" request status')
            f = urllib2.urlopen(restUrl)
        except Exception,e:
            self.errorLog (u"Error: " + str(e))
            if deviceBoard.states['onOffState'] == True:
                deviceBoard.updateStateOnServer(key='onOffState', value=False)
                deviceBoard.updateStateImageOnServer(indigo.kStateImageSel.PowerOff)
                deviceBoard.setErrorStateOnServer('Lost')
                for deviceItem in indigo.devices.itervalues(filter="self"):
                    if deviceItem.pluginProps.has_key("unipiSel"):
                        if deviceItem.pluginProps["unipiSel"] == deviceBoard.id:        
                            deviceItem.setErrorStateOnServer('Lost')              
                        
                        
            return False

        try:
            if deviceBoard.states['onOffState'] == False:
                deviceBoard.setErrorStateOnServer(None)
                deviceBoard.updateStateOnServer(key='onOffState', value=True)
                deviceBoard.updateStateImageOnServer(indigo.kStateImageSel.PowerOn)                
                for deviceItem in indigo.devices.itervalues(filter="self"):
                    if deviceItem.pluginProps.has_key("unipiSel"):
                        if deviceItem.pluginProps["unipiSel"] == deviceBoard.id:        
                            deviceItem.setErrorStateOnServer(None)        
                        
            payloadJson = f.read()
            if payloadJson == None:
                self.errorLog(device.name + ": nothing received.")
                return False
            else:
                if verbose:
                    self.debugLog(device.name + ": Status received.")


        except Exception, e:
            self.debugLog("Bad JSON file. ")
            self.debugLog(restUrl)
            self.debugLog(payloadJson)
            return False

        jsonObject = json.loads(payloadJson)


        for itemJson in range(len(jsonObject)):   
            mapObject = self.getMapFromMessage(jsonObject[itemJson])
            mapObject["deviceBoard"] = deviceBoard.id
            self.setIndigoStateFromJson (mapObject)

    def getMapFromMessage(self,message):
        #self.debugLog(u"getMapFromMessage message: " + str(message))
        mapObject = {
            "deviceBoard": None,
            "dev": '',
            "indigotype":'',
            "circuit": '0',
            "address": '',
            "value": 0,
            "counter_mode": False,
            "debounce": 0,
            "time": 0
                }
                
        mapObject["dev"] = message["dev"]
        mapObject["circuit"] = message["circuit"]
        mapObject["value"] = message["value"]

        if message.has_key("address"):
            mapObject["address"] = message["address"]
        if message.has_key("counter_mode"):
            mapObject["counter_mode"] = message["counter_mode"]
        if message.has_key("debounce"):
            mapObject["debounce"] = message["debounce"]
        if message.has_key("time"):
            mapObject["time"] = message["time"]
            
            
        if mapObject["dev"] == 'relay':
            mapObject["indigotype"] = 'UniPiRelay'
        elif mapObject["dev"] == 'input': 
            if mapObject["counter_mode"]:
                mapObject["indigotype"] = 'UniPiDigitalCounter'
            else:
                mapObject["indigotype"] = 'UniPiDigitalInput'
        elif mapObject["dev"] == 'ai':
            mapObject["indigotype"] = 'UniPiAnalogInput'
        elif mapObject["dev"] == 'ao':
            mapObject["indigotype"] = 'UniPiAnalogOutput'
        elif mapObject["dev"] == 'temp':
            mapObject["indigotype"] = 'UniPiTempSensor'
        return mapObject

    def setIndigoStateFromJson (self, mapObject):
        if mapObject["indigotype"] == 'UniPiRelay':
            self.setIndigoStateRelay(mapObject)
        elif mapObject["indigotype"] == 'UniPiDigitalInput':
            self.setIndigoStateDigitalInput(mapObject)
        elif mapObject["indigotype"] == 'UniPiDigitalCounter':
            self.setIndigoStateDigitalCounter(mapObject)
        elif mapObject["indigotype"] == 'UniPiAnalogInput':
            self.setIndigoStateAnalogInput(mapObject)
        elif mapObject["indigotype"] == 'UniPiAnalogOutput':
            self.setIndigoStateAnalogOutput(mapObject)
        elif mapObject["indigotype"] == 'UniPiTempSensor':
            self.setIndigoStateTempSensor(mapObject)
        
    def setIndigoStateRelay(self,mapObject):
        deviceBoard = indigo.devices[mapObject["deviceBoard"]]        
        itemCircuit = int(mapObject["circuit"])        
        itemValue = int(mapObject["value"])
        for x in self.relayList:
            itemList = self.relayList[x]
            if itemList["unipiSel"] == deviceBoard.id and itemList["circuit"] == itemCircuit:
                device = itemList["ref"]
                #self.debugLog(device.name + ": setIndigoStateRelay.")
                
                if itemValue == 1:
                    newValue = True
                    logValue = 'on'
                else:
                    newValue = False
                    logValue = 'off'
                
                if not newValue == device.states['onOffState']:
                    device.updateStateOnServer(key='onOffState', value=newValue)
                    indigo.server.log (u'received "' + device.name + '" status update is ' + logValue)
        
    def setIndigoStateDigitalInput(self,mapObject):
        deviceBoard = indigo.devices[mapObject["deviceBoard"]]        
        itemCircuit = int(mapObject["circuit"])        
        itemValue = int(mapObject["value"])
        for x in self.digitalInputList:
            itemList = self.digitalInputList[x]
            if itemList["unipiSel"] == deviceBoard.id and itemList["circuit"] == itemCircuit:
                device = itemList["ref"]
                #self.debugLog(device.name + ": setIndigoStateDigitalInput.")    
                
                if itemValue == 1:
                    newValue = True
                    logValue = 'on'
                else:
                    newValue = False
                    logValue = 'off'
                
                if not newValue == device.states['onOffState']:
                    device.updateStateOnServer(key='onOffState', value=newValue)
                    indigo.server.log (u'received "' + device.name + '" status update is ' + logValue)
                          
    def setIndigoStateDigitalCounter(self,mapObject):
        deviceBoard = indigo.devices[mapObject["deviceBoard"]]        
        itemCircuit = int(mapObject["circuit"])        
        itemValue = int(mapObject["value"])
        for x in self.digitalCounterList:
            itemList = self.digitalCounterList[x]
            if itemList["unipiSel"] == deviceBoard.id and itemList["circuit"] == itemCircuit:
                device = itemList["ref"]
                #self.debugLog(device.name + ": setIndigoStateDigitalCounter.")  
                  
                if itemValue == 1:
                    newValue = True                    
                else:
                    newValue = False  
                
                if device.states['onOffState'] == newValue:
                    break
                
                updateCounter = False
                if device.pluginProps["counterRaise"] and itemValue == 1:
                    updateCounter = True
                if not device.pluginProps["counterRaise"] and itemValue == 0:
                    updateCounter = True    
                if not updateCounter:
                    if not newValue == device.states['onOffState']:
                        device.updateStateOnServer(key='onOffState', value=newValue)
                        device.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOn)
                    break
                
                counterAcum = float (device.states["counterAcum"])
                counterAcum += 1
                self.updateDeviceState(device, "counterAcum", counterAcum)
                
                counterInitialValue  = int (device.pluginProps["counterInitialValue"])
                if not counterInitialValue > 0:
                    counterInitialValue = 0
                counterTotal = counterInitialValue + counterAcum
                
                counterFactor = float (device.pluginProps["counterFactor"])
                if not counterFactor > 0:
                    counterFactor = 1
                
                accumEnergyTotal = round ((counterTotal / counterFactor),3)
                #device.updateStateOnServer(key="accumEnergyTotal", value=accumEnergyTotal, decimalPlaces=3)
                #device.updateStateOnServer(key="accumEnergyTotal", value=accumEnergyTotal)
                #devProps = device.pluginProps
                #devProps.update({"accumEnergyTotal":accumEnergyTotal})
                #device.replacePluginPropsOnServer(devProps)
                
                # accumEnergyTotal
                # accumEnergyTotal.ui
                # curEnergyLevel
                # curEnergyLevel.ui
                # energyAccumBaseTime
                # energyAccumBaseTime.ui
                # accumEnergyTimeDelta
                # accumEnergyTimeDelta.ui
            
                
                
                logValue = str(accumEnergyTotal)
                units = device.pluginProps["units"]
                if units:
                    logValue += u' '
                    logValue += unicode(units)
 
                if not accumEnergyTotal == device.states['accumEnergyTotal']:
                    device.updateStateOnServer(key='onOffState', value=newValue)
                    device.updateStateOnServer("accumEnergyTotal", accumEnergyTotal, uiValue=logValue)
                    device.updateStateOnServer('sensorValue', accumEnergyTotal, uiValue=logValue)
                    #device.updateStateOnServer('accumEnergyTotal', accumEnergyTotal, decimalPlaces=3)
                    device.updateStateImageOnServer(indigo.kStateImageSel.EnergyMeterOff) 
                    indigo.server.log (u'received "' + device.name + u'" counter value is ' + logValue) 
                else:
                    indigo.server.log (device.name + '. sensorValue did not changed  newValue=' + str(newValue) + '. sensorValue=' + str(device.states['sensorValue']) )        
                
                    
    def setIndigoStateAnalogInput(self,mapObject):
        pass
    def setIndigoStateAnalogOutput(self,mapObject):
        #puerta.updateStateOnServer("brightnessLevel", brightnessLevel)
        pass
    def setIndigoStateTempSensor(self,mapObject):
        deviceBoard = indigo.devices[mapObject["deviceBoard"]]        
        itemCircuit = mapObject["circuit"]        
        itemAddress = mapObject["address"]      
        itemValue = float(mapObject["value"])
        if itemAddress > "":
            itemCircuit = itemAddress
        for x in self.tempSensorList:
            itemList = self.tempSensorList[x]
            if itemList["unipiSel"] == deviceBoard.id and itemList["circuit"] == itemCircuit:
                device = itemList["ref"]
                #self.debugLog(device.name + ": setIndigoStateTempSensor.")  
                
                try:
                    newValue = round(itemValue,1)
                    logValue = str(newValue) + u" °C"

                    if not newValue == device.states['sensorValue']:
                        device.updateStateOnServer('sensorValue', newValue, uiValue=logValue)
                        if abs(itemList["logLastValue"] - newValue) > 0.2:
                            self.tempSensorList[x]["logLastValue"] = newValue
                            indigo.server.log (u'received "' + device.name + '" sensor value is ' + logValue)
                except Exception,e:
                    self.errorLog (u"Error: " + str(e))
                    pass
 

    def sendActionToCircuit(self, device, action):
        addressWrite = ''
        unipiSel = 0
        circuit = 0
        unipi = 0
        portWrite = ''
        deviceBoard = None
        value = 0
        fvalue = 0.00
        restUrl = ''
        payload = {}
        logaction = ""

        if device == None:
            self.errorLog(u"no device specified")
            return
        if not self._devTypeIdIsMirrorOutput(device.deviceTypeId):
            self.errorLog(u"Expected mirror relay device type")
            return

        unipiSel = int(device.pluginProps["unipiSel"])
        circuit  = int(device.pluginProps["circuit"])

        if unipiSel <=0:
            self.errorLog(u"Expected PiFace board")
            return
        if circuit <=0:
            self.errorLog(u"Expected relay number")
            return


        for unipi in self.boardList:
            if self.boardList[unipi]['ref'].id == unipiSel:
                deviceBoard  = self.boardList[unipi]["ref"]
                addressWrite = self.boardList[unipi]['address']
                portWrite    = self.boardList[unipi]['port']

        if deviceBoard == None:
            self.errorLog (u"UniPi Board not found!")
            return
        if deviceBoard.states['onOffState'] == False:
            self.errorLog (deviceBoard.name + u" is lost!")
            return

        if not(addressWrite > ''):
            self.errorLog(u"IP address not defined")
            return

        if int(portWrite) <=0:
            portWrite = "80"

        restUrl = u"http://" + addressWrite + u":" + portWrite + u"/rest"

        if device.deviceTypeId == "UniPiRelay":
            restUrl = restUrl + u"/relay/" + str(circuit)
            if action.deviceAction == indigo.kDeviceAction.TurnOn:
                value = 1
            elif action.deviceAction == indigo.kDeviceAction.TurnOff:
                value = 0
            elif action.deviceAction == indigo.kDeviceAction.Toggle:
                if device.states["onOffState"]:
                    value = 0
                else:
                    value = 1
            else:
                return

            payload={u'value' : str(value) }

            if value == 1:
                logaction = 'on'
                newValue = True
            else:
                logaction = 'off'
                newValue = False
            device.updateStateOnServer(key='onOffState', value=newValue)
            indigo.server.log (u'Sent "' + device.name + '" ' + logaction)
        elif device.deviceTypeId == "UniPiAnalogOutput":
            restUrl = restUrl + u"/ao/" + str(circuit)
            if action.deviceAction == indigo.kDeviceAction.SetBrightness:
                # value(0-10) of Analog Output by circuit number
                fvalue = 10 * action.actionValue / 100
                logaction = str(action.actionValue) + '%'
            else:
                return
            payload={u'value' : str(fvalue) }
            indigo.server.log (u'Sent "' + device.name + '" ' + logaction)

        try:
            payloadEncoded = urllib.urlencode(payload)
            req = urllib2.Request(restUrl, payloadEncoded)
            response = urllib2.urlopen(req)
        except Exception,e:
            self.errorLog (u"Error: " + str(e))
            pass

        return

    def dummyVal (self,dev):
        return

    ###################################################################
    # Custom Action callbacks
    ###################################################################

    def actionControlDimmerRelay(self, action, dev):
        if action.deviceAction == indigo.kDeviceAction.TurnOn:
            self.sendActionToCircuit(dev, action)
        elif action.deviceAction == indigo.kDeviceAction.TurnOff:
            self.sendActionToCircuit(dev, action)
        elif action.deviceAction == indigo.kDeviceAction.Toggle:
            self.sendActionToCircuit(dev, action)
        elif action.deviceAction == indigo.kDeviceAction.SetBrightness:
            self.sendActionToCircuit(dev, action)
        elif action.deviceAction == indigo.kDeviceAction.RequestStatus:
            self.boardRequestStatus(dev,True)
            pass

    def actionControlSensor(self, action, dev):
        if action.sensorAction == indigo.kSensorAction.RequestStatus:
            self.boardRequestStatus(dev,True)
            pass
    
    def actionControlGeneral(self, action, dev):
        if action.deviceAction == indigo.kDeviceGeneralAction.Beep:
            pass
        elif action.deviceAction == indigo.kDeviceGeneralAction.EnergyUpdate:
            self.boardRequestStatus(dev,True)
        elif action.deviceAction == indigo.kDeviceGeneralAction.EnergyReset:
            self.counterAcumReset(dev)
        elif action.deviceAction == indigo.kDeviceGeneralAction.RequestStatus:
            self.boardRequestStatus(dev,True)   

    ########################################
    # Menu Methods
    ########################################
    def toggleDebugging(self):
        if self.debug:
            indigo.server.log("Turning off debug logging")
            self.pluginPrefs["debugEnabled"] = False                
        else:
            indigo.server.log("Turning on debug logging")
            self.pluginPrefs["debugEnabled"] = True
        self.debug = not self.debug
        return

    def checkForUpdates(self):
        update = self.updater.checkForUpdate() 
        if (update != None):
            pass
        return    

    def updatePlugin(self):
        self.updater.update()