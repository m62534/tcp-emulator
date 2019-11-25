#!/usr/bin/python3
import sys
import time
from socket import *
import json
import logging
import random


# server: 172.31.29.103
# client: 172.31.29.28
# emul: 172.31.29.146

def main():

    # load Config
    myConfig = configObject('config.json')
    loglevel = myConfig.loglevel
    setLoglevel(loglevel)

    # Assign values to global vars
    global serverHost, serverPort, clientHost, clientPort, emulHost, emulPort
    serverHost = myConfig.serverHost
    serverPort = myConfig.serverPort
    clientHost = myConfig.clientHost
    clientPort = myConfig.clientPort
    emulHost = myConfig.emulHost
    emulClientRecvPort = myConfig.emulPort
    emulServerRecvPort = 7777
    #Socket for listening
    global sockObjEmul, sockObjServer
    sockObjEmul = socket(AF_INET, SOCK_DGRAM)
    sockObjEmul.bind((emulHost, emulClientRecvPort))
    #Socket for sending
    sockObjServer = socket(AF_INET, SOCK_DGRAM)
    sockObjServer.bind((emulHost, emulServerRecvPort))

    forwardSocket = socket(AF_INET, SOCK_DGRAM)

    BER = myConfig.BER

    while True:
        clientBER = random.randint(1, 101)
        print("Listening on port: ", emulClientRecvPort)
        data, addr = sockObjEmul.recvfrom(4096)
        if clientBER < BER:
            print("Skipping client")
            continue
        print("Forwarding data to server")
        #time.sleep(packetDelay)
        forwardSocket.sendto(data, (serverHost, serverPort))
        print("Forwarded data sent")
        while True:
            serverBER = random.randint(1, 101)
            data, addr = sockObjServer.recvfrom(4096)
            if serverBER < BER:
                print("Skipping server")
                break
            if data:
                jsonObj = json.loads(data.decode("utf-8"))
                responseType = jsonObj[0]['packetType']
                if responseType == 'skip':
                    break
                print("Forwarding data to client")
                #time.sleep(packetDelay)
                forwardSocket.sendto(data, (clientHost, clientPort))
                break

    return 0

    '''
    need following initializations
        listening for server.
        listening for client.
    '''

def noise(percentDrop):
    return 0
    '''
    receive percent to drop
    also increment packetCounter after drop
    '''

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
            self.BER = data['BER']

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

# class packetObject:
#     packetType = ""
#     seqNum = 0
#     data = 0
#     windowSize = 0
#     ackNum = 0

#     def __init__(self, packetType, seqNum, data, windowSize, ackNum):
#         self.packetType = packetType
#         self.seqNum = seqNum
#         self.data = data
#         self.windowSize = windowSize
#         self.ackNum

if __name__ == "__main__":
    main()