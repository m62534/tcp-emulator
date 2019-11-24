#!/usr/bin/python3
import sys
import time
import pickle
from socket import *
import json
import base64
import logging
from random import randint

# We should change this so it is being read from a json configuration file
# server: 172.31.29.103
# client: 172.31.29.28
# emul: 172.31.29.146

serverHost = ''
serverPort = 0
clientHost = ''
clientPort = 0
emulHost = ''
emulPort = 0



def main():

    #fx, listOfFiles = argVerify(sys.argv)
    #print("verified fx: %s" % fx)
    filename = 'plan.txt'

    # load Config
    myConfig = configObject('config.json')
    loglevel = myConfig.loglevel
    setLoglevel(loglevel)

    logging.info('### Client Started ###')
    # Assign values to global vars
    global serverHost, serverPort, clientHost, clientPort, emulHost, emulPort
    serverHost = myConfig.serverHost
    serverPort = myConfig.serverPort
    clientHost = myConfig.clientHost
    clientPort = myConfig.clientPort
    emulHost = myConfig.emulHost
    emulPort = myConfig.emulPort

    # later to be replaced by value in config.json
    timeoutVal = 1
    maxRetry = 5 

    #Socket for server (to send data) and client (to receive acks)
    sockObjServer = socket(AF_INET, SOCK_DGRAM) 
    sockObjClient = socket(AF_INET, SOCK_DGRAM)
    sockObjClient.bind((clientHost, clientPort))
    sockObjClient.settimeout(timeoutVal)

    # Handle send and conditions
    # ** just need to change serverhost and serverport to emul* for the proxy config
    sendHandler(filename, sockObjServer, sockObjClient, serverHost, serverPort, timeoutVal, maxRetry)
    
    #close the connection
    sockObjServer.close()
    sockObjClient.close()

    logging.info('### Client Finished ##')



class configObject:
    def __init__(self, configFile):
        with open(configFile) as config_file:
            data = json.load((config_file))
            self.serverHost = data['server']['host']
            self.serverPort = data['server']['port']
            self.clientHost = data['client']['host']
            self.clientPort = data['client']['port']
            self.emulHost = data['client']['emul']['host']
            self.emulPort = data['client']['emul']['port']
            self.loglevel = data['client']['loglevel']


class sessionObject:
    def __init__(self, serverSockObj, clientSockObj, serverHost, clientHost, dataArray, timeoutVal, maxRetry):
        self.serverSockOjb = serverSockObj
        self.clientSockObj = clientSockObj
        self.serverHost = serverHost
        self.clientHost = clientHost
        self.dataArray = dataArray
        self.timeoutVal = timeoutVal
        self.maxRetry = maxRetry
    


#Segments the file to be sent
def dataArrayer(filename):
    fileDataArr = []
    fileBuffer = open(filename, 'rb')
    nextLine = fileBuffer.read(1024)
    while nextLine:
        fileDataArr.append(nextLine)
        nextLine = fileBuffer.read(1024)
    return fileDataArr

# Set Logging
def setLoglevel(loglevel):
    loglevels = {
        "critical": logging.CRITICAL,
        "error": logging.ERROR,
        "warning": logging.WARNING,
        "info": logging.INFO,
        "debug": logging.DEBUG,
        "notset": logging.NOTSET
    }
    logging.basicConfig(filename='client.log', level=loglevels[loglevel])

# Main function for handling the sends.
# Uses 3 sub functions: initialHandshake, dataTransfer, closingHandshake
def sendHandler(filename, sockObjectServer, sockObjClient, serverHost, serverPort, timeoutVal, maxRetry):
    counter = -1 # always start with -1 for initial handshake to work
    # Packet metadata initiaize
    maxSeq = 2**32 - 1
    seqNum = randint(0, maxSeq) ##0 to 2^32 -1
    ackNum = 0
    windowSize = 3
    dataArray = dataArrayer(filename)

    # Testing for handshake
    seqNum, handShake = initialHandshake(filename, seqNum, windowSize, ackNum, sockObjectServer, sockObjClient, timeoutVal , maxRetry)
    if handShake:
        ##### Data Transfer #########
        seqNum, counter = dataTransfer(filename, seqNum , dataArray, windowSize, ackNum, counter, sockObjectServer, sockObjClient, timeoutVal, maxRetry)
    closingHandshake(filename, seqNum, windowSize, ackNum, sockObjectServer, sockObjClient, timeoutVal, maxRetry)



# Controls the initial 3-way handshkae mechanism
def initialHandshake(filename, seqNum, windowSize, ackNum, sockObjectServer, sockObjClient, timeoutVal, maxRetry):
    jsonObj = ''
    responseType = ''
    responseAckNum = ''
    packetReceived = False
    retryCounter = 0
    
    while packetReceived == False and retryCounter < maxRetry:
        outboundPacket = generatePacket(filename, "syn", seqNum, b''.decode("utf-8"), windowSize, ackNum)
        sockObjectServer.sendto(bytes(json.dumps(outboundPacket), "utf-8"),(serverHost, serverPort))
        logging.info("Handshake: Sent SYN...")
        try:
            data, address = sockObjClient.recvfrom(4096)
            if data:
                jsonObj = json.loads(data.decode("utf-8"))
                responseType = jsonObj[0]['packetType']
                responseAckNum = jsonObj[0]['ackNum']
                expectAckNum = seqNum + 1

                if (responseType.lower() == 'synack' and responseAckNum  == expectAckNum):
                    logging.info("Handshake: Sending ack to synack")
                    outboundPacket = generatePacket(filename, "ack", seqNum, b''.decode("utf-8"), windowSize, ackNum)
                    sockObjectServer.sendto(bytes(json.dumps(outboundPacket), "utf-8"),(serverHost, serverPort))
                    packetReceived = True
                    logging.info("Handshake: Received SYNACK... Sending the final Ack")
                    retryCounter = 0 # Reset
                else:
                    print("Handshake: Received: ", responseType.lower())
                    
        except timeout:
            print("Initial Handshake: Socket Timeout, Retrying...")
            logging.error("Initial Handshake: Socket Timeout, Retrying...")
           
        retryCounter = retryCounter + 1
    
    return seqNum, packetReceived



# Receives dataArray, transfers data
def dataTransfer(filename, seqNum , dataArray, windowSize, ackNum, counter, sockObjectServer, sockObjectClient, timeoutVal, maxRetry):
    jsonObj = ''
    responseType = ''
    counter = 0
    retryCounter = 0

    logging.info("======================")
    logging.info("starting data transfer")

    while counter < len(dataArray) and retryCounter < maxRetry:
        outboundPacket = generatePacket(filename, "ack", seqNum, dataArray[counter].decode("utf-8"), windowSize, ackNum)
        sockObjectServer.sendto(bytes(json.dumps(outboundPacket), "utf-8"),(serverHost, serverPort))
        try:
            data, address = sockObjectClient.recvfrom(4096)
            if data:
                # increment the expected
                expectAckNum = seqNum + len(dataArray[counter])

                # print current state
                logging.debug("===")
                logging.debug("counter: %s" % counter)
                logging.info("  Sent data size: %s" % len(dataArray[counter]))
                jsonObj = json.loads(data.decode("utf-8"))
                responseType = jsonObj[0]['packetType']
                responseAckNum = jsonObj[0]['ackNum']
                logging.debug("  Sent seqNum:  %s" % seqNum)
                logging.debug("  expectAckNum: %s" % expectAckNum)
                logging.debug("  responseAcknum: %s" % responseAckNum)
                logging.debug("  responseType: %s" % responseType)
                logging.debug("  expectAckNum: %s" % expectAckNum)
                logging.debug("  object received: %s" % jsonObj[0])
                if (responseType.lower() == 'ack' and responseAckNum  == expectAckNum):
                    counter = counter + 1
                    retryCounter = 0 # Reset
                else:
                    retryCounter = retryCounter + 1
            else:
                logging.error("No data")
                break
                    
        except timeout:
            print("Data Transfer: Socket Timeout, Retrying...")
            logging.error("Data Transfer: Socket Timeout, Retrying...")
            retryCounter = retryCounter + 1
        
    logging.info("Finished data transfer")
    logging.info("======================")

    return seqNum, counter



# Controls fin finack ack handshake
def closingHandshake(filename, seqNum, windowSize, ackNum, sockObjectServer, sockObjClient, timeoutVal, maxRetry):
    jsonObj = ''
    
    retryCounter = 0
    while retryCounter < maxRetry:
        outboundPacket = generatePacket(filename, "fin", seqNum, b''.decode("utf-8"), windowSize, ackNum)
        sockObjectServer.sendto(bytes(json.dumps(outboundPacket), "utf-8"),(serverHost, serverPort))
        try:
            data, address = sockObjClient.recvfrom(4096)
            if data:
                jsonObj = json.loads(data.decode("utf-8"))
                responseType = jsonObj[0]['packetType']
                responseAckNum = jsonObj[0]['ackNum']
                retryCounter = 0
        except timeout:
            print("Fin Handshake: Socket Timeout, Retrying...")
            logging.error("Fin handshake: Socket Timeout, Retrying...")
            retryCounter = retryCounter + 1

        expectAckNum = seqNum
        logging.info("Fin Handshake")
        if (responseType.lower() == 'finack' and responseAckNum  == expectAckNum):
            outboundPacket = generatePacket(filename, "ack", seqNum, b''.decode("utf-8"), windowSize, ackNum)
            sockObjectServer.sendto(bytes(json.dumps(outboundPacket), "utf-8"),(serverHost, serverPort))
            logging.debug("i sent the ack to the finack")
            break
        else:
            logging.error("fin issue")
            retryCounter = retryCounter + 1



# Packages as json. windowSize is in seconds
def generatePacket(filename, packetType, seqNum, data, windowSize, ackNum):
    return [{"fileName": filename, "packetType": packetType, "seqNum": seqNum, "data": data, "windowSize": windowSize, "ackNum": ackNum}]



# Determine if user is requesting get or send
def determine(fx):
    return (fx.lower() == 'get' or fx.lower() == 'send')



# Ingests user input and validates
def argVerify(argument):
    prompt = "Enter \'get\' or \'send\' followed by filename: "
    inputStr = ' '.join(argument[1:])
    inputArr = list(inputStr.split(" "))
    listOfFiles = inputArr[1:]

    # Asks until user enters get or send
    while not (determine(inputArr[0]) and len(argument) >= 2):
        # encode every argument following into utf-8
        inputArr = list(input(prompt).split(" "))
        listOfFiles = inputArr[1:]
    fx = inputArr[0]
    return fx, listOfFiles



if __name__ == "__main__":
    main()
 
