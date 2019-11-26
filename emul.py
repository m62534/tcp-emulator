#!/usr/bin/python3
import sys
import time
from socket import *
import json
import logging
import random
import threading
from fractions import Fraction


# server: 172.31.29.103
# client: 172.31.29.28
# emul: 172.31.29.146

def main():

    # load Config
    myConfig = configObject('config.json')
    loglevel = myConfig.loglevel
    setLoglevel(loglevel)

    # Assign values to global vars
    global serverHost, serverPort, clientHost, clientPort, emulHost, emulPort, emulClientRecvPort
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

    global forwardSocket, BERS, BERC
    forwardSocket = socket(AF_INET, SOCK_DGRAM)
    BERS = myConfig.BERS
    BERC = myConfig.BERC

    # sockObjEmul.setblocking(0)
    # sockObjServer.setblocking(0)

    threads = []
    clientThread = threading.Thread(target=clientBER)
    serverThread = threading.Thread(target=serverBER)
    threads = [clientThread, serverThread]
    for i in threads:
        i.start()
    

    return 0


def clientBER():
    clientDropCount = 0
    clientCount = 0
    while True:
        logging.debug('Starting')
        clientBER = random.randint(1, 101)
        print("Listening on port: ", emulClientRecvPort)
        data, addr = sockObjEmul.recvfrom(4096)
        clientCount = clientCount + 1
        if clientBER <= BERC:
            clientDropCount = clientDropCount + 1
            print("Skipping client")
            continue
        if data:
            print("Forwarding data to server")
            forwardSocket.sendto(data, (serverHost, serverPort))
        clientRatio = Fraction(clientDropCount, clientCount)
        print("Client Drop Status so far: ", clientRatio, "=", format(round((float(clientRatio) * 100),2)), "Percent")
        logging.debug('exiting')

def serverBER():
    serverDropCount = 0
    serverCount = 0
    while True:
        logging.debug('Starting')
        serverBER = random.randint(1, 101)
        data, addr = sockObjServer.recvfrom(4096)
        serverCount = serverCount + 1
        if serverBER <= BERS:
            serverDropCount = serverDropCount + 1
            print("Skipping server")
            continue
        if data:
            print("Forwarding data to client")
            forwardSocket.sendto(data, (clientHost, clientPort))
        serverRatio = Fraction(serverDropCount, serverCount)
        print("Client Drop Status so far: ", serverRatio, "=", format(round((float(serverRatio) * 100),2)), "Percent")
        logging.debug('exiting')

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
            self.BERS = data['BERS']
            self.BERC = data['BERC']

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
    # logging.basicConfig(filename='client.log', level=loglevels[loglevel])
    logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)s] (%(threadName)-10s) %(message)s',
                    )

if __name__ == "__main__":
    main()
