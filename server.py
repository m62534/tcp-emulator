#!/usr/bin/python3
import sys
import time
from socket import *
import json
import base64
import logging
from random import randint

# server: 172.31.29.103
# client: 172.31.29.28
# emul: 172.31.29.146

def main():

    filename = ''

    # Configure Logging
    myConfig = configObject('config.json')
    loglevel = myConfig.loglevel
    setLoglevel(loglevel)
    
    logging.info('### Server Started ###')

    # Assign values to global vars
    global serverHost, serverPort, clientHost, clientPort, emulHost, emulPort
    serverHost = myConfig.serverHost
    serverPort = myConfig.serverPort
    clientHost = myConfig.clientHost
    clientPort = myConfig.clientPort
    emulHost = myConfig.emulHost
    emulPort = myConfig.emulPort
    # emulHost = clientHost
    # emulPort = clientPort

    global timeoutVal, maxRetry, windowSize
    timeoutVal = myConfig.timeoutVal
    maxRetry = myConfig.maxRetry
    windowSize = myConfig.windowSize

    #Socket for receiving
    global sockObjServer, sockObjClient
    sockObjServer = socket(AF_INET, SOCK_DGRAM)
    sockObjServer.bind((serverHost, serverPort))
    #Socket for sending
    sockObjClient = socket(AF_INET, SOCK_DGRAM)

    # Randomizes initial seqNum
    seqNum = randint(0, (2**32 - 1)) ##0 to 2^32 -1
    ackNumCache = -1
    #fin = False
    emulServerRecvPort = 7777
    # emulServerRecvPort = clientPort

    endOfFile = False

    ## Always listen
    while True:
        print("top of while True")
        data, address = sockObjServer.recvfrom(4096)
        fileData = b''
        senderWindow = 0  # instantiate windowSize
        if data:
            print("top of if data")
            jsonObj = json.loads(data.decode("utf-8"))
            fileData = bytes.fromhex(jsonObj[0]['data'])
            ackNum = jsonObj[0]['seqNum']
            senderWindow = jsonObj[0]['windowSize']
            data = b''.hex()


            ## if seqNum is from last one received, drop. else cache seqNum and AckNum
            #    drop any packet that doesnt match the ackNum
            print("I am expecting sequence: ", ackNumCache)
            print("I received sequence: ", jsonObj[0]['seqNum'])
            if ackNumCache != -1 and ackNumCache != jsonObj[0]['seqNum']:
                endOfFile = False
                print(jsonObj[0]['seqNum'])
                continue
                
            if jsonObj[0]['transferState'].lower() == 'eof':
                endOfFile = True
                print("I've reached the end")

            print("  =====")
            ## The 1st syn from Initial handshake
            if (len(fileData) == 0 and jsonObj[0]['packetType'] == 'syn') and not endOfFile:
                logging.info("Initial Handshake: received the first syn")
                print("Initial Handshake: received the first syn")
                ackNum = ackNum + 1
                ackNumCache = ackNum
                print("sent acknum: ", ackNum)
                outboundPacket = generatePacket(filename, 'synack', seqNum, data, windowSize, ackNum)
                sockObjServer.sendto(bytes(json.dumps(outboundPacket), "utf-8"),(emulHost, emulServerRecvPort))
            
            ##  The 3rd ack from Initial 3 way handshake
            elif (len(fileData) == 0 and jsonObj[0]['packetType'] == 'ack') and not endOfFile:
                print("sent acknum: ", ackNum)
                ackNumCache = ackNum
                logging.info("Initial Handshake: Received ack to synack")
                print("Initial Handshake: Received ack to synack")
                #outboundPacket = generatePacket(filename, 'skip', seqNum, data, windowSize, ackNum)
                #sockObjServer.sendto(bytes(json.dumps(outboundPacket), "utf-8"),(emulHost, emulServerRecvPort))
            ## If filedata
            elif len(fileData) > 0 and jsonObj[0]['packetType'] == 'ack':
                ackNum =  ackNum + len(fileData)
                ackNumCache = ackNum
                if endOfFile:
                    print("  endOfFile acknum: ", ackNum)
                else:
                    print("  data acknum: ", ackNum)
                
                outboundPacket = generatePacket(filename, 'ack', seqNum, data, windowSize, ackNum)
                print(" sending: ", outboundPacket)
                logging.debug("======")
                logging.debug("senderWindow: %s" % senderWindow)
                logging.debug("Filedata length: %s" % len(fileData))
                logging.debug("Received seqNum %s" % jsonObj[0]['seqNum'])
                logging.debug("The ack packet being sent back: %s" % outboundPacket)
                logging.debug("The Filedata received: %s" % fileData)
                logging.debug("======")
                sockObjServer.sendto(bytes(json.dumps(outboundPacket), "utf-8"),(emulHost, emulServerRecvPort))
                
                with open(jsonObj[0]['fileName'], 'ab') as fileBuffer:  # write binary
                    fileBuffer.write(fileData)

                print("sent ack to data")

            ## First fin sets fin to true
            elif (len(fileData) == 0 and jsonObj[0]['packetType'] == 'fin' and endOfFile):
                ackNumCache = ackNum
                print("sent acknum: ", ackNum)
                logging.info("First fin. Responding with finack")
                outboundPacket = generatePacket(filename, 'finack', seqNum, data, windowSize, ackNum)
                sockObjServer.sendto(bytes(json.dumps(outboundPacket), "utf-8"),(emulHost, emulServerRecvPort))
            
            ## Final Ack received. Can close connection and break out of loop
            elif (len(fileData) == 0 and jsonObj[0]['packetType'] == 'ack' and endOfFile):
                logging.info("Received the final ack")
                print("Received the final ack")
                sockObjServer.close()
                break
            
    logging.info('### Server Finished ##')



class configObject:
    def __init__(self, configFile):
        with open(configFile) as config_file:
            data = json.load((config_file))
            self.serverHost = data['server']['host']
            self.serverPort = data['server']['port']
            self.clientHost = data['client']['host']
            self.clientPort = data['client']['port']
            self.emulHost = data['server']['emul']['host']
            self.emulPort = data['server']['emul']['port']
            self.loglevel = data['server']['loglevel']
            self.timeoutVal = data['server']['timeoutVal']
            self.maxRetry = data['server']['maxRetry']
            self.windowSize = data['server']['windowSize']



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
    logging.basicConfig(filename='server.log', level=loglevels[loglevel])



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
