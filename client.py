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

def main():

    #fx, listOfFiles = argVerify(sys.argv)
    #print("verified fx: %s" % fx)
    filename = 'plan.txt'

    # load Config
    myConfig = configObject('../config.json')
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

    global timeoutVal, maxRetry, windowSize
    timeoutVal = myConfig.timeoutVal
    maxRetry = myConfig.maxRetry
    windowSize = myConfig.windowSize

    #Socket for server (to send data) and client (to receive acks)
    global sockObjServer, sockObjClient
    sockObjServer = socket(AF_INET, SOCK_DGRAM) 
    sockObjClient = socket(AF_INET, SOCK_DGRAM)
    sockObjClient.bind((clientHost, clientPort))
    sockObjClient.settimeout(timeoutVal)

    # Handle send and conditions
    sendHandler(filename)

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
            self.timeoutVal = data['client']['timeoutVal']
            self.maxRetry = data['client']['maxRetry']
            self.windowSize = data['client']['windowSize']


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
def sendHandler(filename):
    # Packet metadata initiaize
    maxSeq = 2**32 - 1

    # Randomizes initial sequence number
    seqNum = randint(0, maxSeq)
    ackNum = 0
    dataArray = dataArrayer(filename)

    # Controls the initial 3-way handshkae mechanism
    def initialHandshake():
        nonlocal filename, seqNum, ackNum
        jsonObj = ''
        responseType = ''
        responseAckNum = ''
        packetReceived = False
        retryCounter = 0
        
        while packetReceived == False and retryCounter < maxRetry:
            outboundPacket = generatePacket(filename, "syn", seqNum, b''.hex(), windowSize, ackNum, "3way-handshake")
            sockObjServer.sendto(bytes(json.dumps(outboundPacket), "utf-8"),(serverHost, serverPort))
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
                        outboundPacket = generatePacket(filename, "ack", seqNum, b''.hex(), windowSize, ackNum, "3way-handshake")
                        sockObjServer.sendto(bytes(json.dumps(outboundPacket), "utf-8"),(serverHost, serverPort))
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
    def dataTransfer():
        nonlocal filename, seqNum , dataArray, ackNum
        jsonObj = ''
        responseType = ''
        counter = 0
        backupSeqNum = seqNum # for testing
        retryCounter = 0

        logging.info("======================")
        logging.info("starting data transfer")

        # Initial window loader
        slidingWindow = []
        while len(slidingWindow) < windowSize:
            windowObject = generatePacket(filename, "ack", seqNum, dataArray[counter].hex(), windowSize, ackNum, "transferring")
            
            slidingWindow.append(windowObject)
            seqNum = seqNum + len(dataArray[counter]) # assigns value of next sequence #
            counter = counter + 1

        counter = 0 # for testing
        seqNum = backupSeqNum # for testing
        endOfFile = False

        while not len(slidingWindow) == 0 and retryCounter < maxRetry:
            if not retryCounter == 0:
                for x in slidingWindow:
                    sockObjServer.sendto(bytes(json.dumps(x), "utf-8"),(serverHost, serverPort))
            elif endOfFile: 
                sockObjServer.sendto(bytes(json.dumps(slidingWindow[-1]), "utf-8"),(serverHost, serverPort))
                break
            else:
                sockObjServer.sendto(bytes(json.dumps(slidingWindow[-1]), "utf-8"),(serverHost, serverPort))


            try:
                data, address = sockObjClient.recvfrom(4096)
                if data:

                    expectAckNum = slidingWindow[0][0]['seqNum'] + len(bytes.fromhex(slidingWindow[0][0]['data']))

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

                    # (for sliding window) if expected, then need to increment
                    if (responseType.lower() == 'ack' and responseAckNum  == expectAckNum):
                        # pop the first object in list, so new one can go in
                        slidingWindow.pop(0)
                        counter = counter + 1

                        if counter == len(dataArray) - 1:
                            windowObject = generatePacket(filename, "ack", seqNum, dataArray[counter].hex(), windowSize, ackNum, "eof")
                            slidingWindow.append(windowObject)
                            endOfFile = True
                            print(len(slidingWindow))
                            print("End of File")
                        else:
                            windowObject = generatePacket(filename, "ack", seqNum, dataArray[counter].hex(), windowSize, ackNum, "transferring")
                            slidingWindow.append(windowObject)

                        retryCounter = 0 # Reset counter
                    else:
                        retryCounter = retryCounter + 1
                else:
                    logging.error("No data")
                    retryCounter = retryCounter + 1
                    break
                        
            except timeout:
                print("Data Transfer: Socket Timeout, Retrying...")
                logging.error("Data Transfer: Socket Timeout, Retrying...")
                retryCounter = retryCounter + 1
        logging.info("Finished data transfer")
        logging.info("======================")

        return seqNum
    
    # Controls fin finack ack handshake
    # def closingHandshake():
    #     nonlocal filename, seqNum, ackNum
    #     jsonObj = ''
    #     packetReceived = False
    #     retryCounter = 0

    #     print("In closingHandshake")

    #     while packetReceived == False and retryCounter < maxRetry:
    #         outboundPacket = generatePacket(filename, "fin", seqNum, b''.hex(), windowSize, ackNum, "fin-handshake")
    #         sockObjServer.sendto(bytes(json.dumps(outboundPacket), "utf-8"),(serverHost, serverPort))
    #         try:
    #             data, address = sockObjClient.recvfrom(4096)
    #             if data:
    #                 print("hasData")
    #                 jsonObj = json.loads(data.decode("utf-8"))
    #                 responseType = jsonObj[0]['packetType']
    #                 responseAckNum = jsonObj[0]['ackNum']
    #                 retryCounter = 0
    #         except timeout:
    #             print("Fin Handshake: Socket Timeout, Retrying...")
    #             logging.error("Fin handshake: Socket Timeout, Retrying...")
    #             retryCounter = retryCounter + 1

    #         expectAckNum = seqNum
    #         logging.info("Fin Handshake")
    #         print("waiting for finack")
    #         if (responseType.lower() == 'finack' and responseAckNum  == expectAckNum):
    #             print("received Finack")
    #             outboundPacket = generatePacket(filename, "ack", seqNum, b''.hex(), windowSize, ackNum, "fin-handshake")
    #             sockObjServer.sendto(bytes(json.dumps(outboundPacket), "utf-8"),(serverHost, serverPort))
    #             logging.debug("i sent the ack to the finack")
    #             packetReceived = True
    #             break
    #         else:
    #             logging.error("fin issue")
    #             retryCounter = retryCounter + 1
    
    # # Testing for handshake
    # seqNum, handShake = initialHandshake()
    # if handShake:
    #     ##### Data Transfer #########
    #     seqNum = dataTransfer()
    # closingHandshake()
    def closingHandshake():
        nonlocal filename, seqNum, ackNum
        jsonObj = ''
        packetReceived = False

        retryCounter = 0
        while packetReceived == False and retryCounter < maxRetry:
            outboundPacket = generatePacket(filename, "fin", seqNum, b''.decode("utf-8"), windowSize, ackNum, "fin-handshake")
            sockObjEmul.sendto(bytes(json.dumps(outboundPacket), "utf-8"),(emulHost, emulPort))
            print("Closing Handshake: Sent FIN...")
            try:
                data, address = sockObjClient.recvfrom(4096)
                if data:
                    jsonObj = json.loads(data.decode("utf-8"))
                    responseType = jsonObj[0]['packetType']
                    responseAckNum = jsonObj[0]['ackNum']
                    expectAckNum = seqNum
                    if (responseType.lower() == 'finack' and responseAckNum == expectAckNum):
                        outboundPacket = generatePacket(filename, "ack", seqNum, b''.decode("utf-8"), windowSize, ackNum, "fin-handshake")
                        sockObjEmul.sendto(bytes(json.dumps(outboundPacket), "utf-8"), (emulHost, emulPort))
                        print("Closing Handshake: Received FINACK... Sending the final Ack")
                        packetReceived = True
                        retryCounter = 0
                        break
                    else:
                        print("Closing Handshake: Received: ", responseType.lower())

            except timeout:
                print("Fin Handshake: Socket Timeout, Retrying...")
                logging.error("Fin handshake: Socket Timeout, Retrying...")

            retryCounter = retryCounter + 1
        return seqNum, packetReceived

    # Testing for handshake
    seqNum, handShake = initialHandshake()
    if handShake:
        ##### Data Transfer #########
        seqNum = dataTransfer()
    seqNum, handShake = closingHandshake()



# Packages as json. windowSize is in seconds
def generatePacket(filename, packetType, seqNum, data, windowSize, ackNum, transferState):
    return [{"fileName": filename, "packetType": packetType, "seqNum": seqNum, "data": data, "windowSize": windowSize, "ackNum": ackNum, "transferState": transferState}]



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
 
