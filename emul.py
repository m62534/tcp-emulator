#!/usr/local/bin/python3
import sys
import time
from socket import *
import logging

# server: 172.31.29.103
# client: 172.31.29.28
# emul: 172.31.29.146

def main():
    
    # Configure Logging
    logging.basicConfig(filename='client.log', level=logging.INFO)
    logging.info('Client Started')
    
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