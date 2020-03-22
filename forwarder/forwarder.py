#!/usr/bin/python3

import json
import socket
import select

def main():
    print("hello")

    # Read static variables from json
    myConfig = configObject('config.json')
    global serverHost, serverPort, forwarderHost, forwarderPort
    serverHost = myConfig.serverHost
    serverPort = myConfig.serverPort
    forwarderHost = myConfig.forwarderHost
    forwarderPort = myConfig.forwarderPort

    # Create forwarder
    forwarder()

class configObject:
    def __init__(self, configFile):
        with open(configFile) as config_file:
            data = json.load((config_file))
            self.serverHost = data['server']['host']
            self.serverPort = data['server']['port']
            self.forwarderHost = data['forwarder']['host']
            self.forwarderPort = data['forwarder']['port']

def forwarder():
    print("Server host: ", serverHost)
    print("Server port ", serverPort)
    print("Forwarder host: ", forwarderHost)
    print("Forwarder port: ", forwarderPort)

    
    # Create server socket
    serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Create epoll object
    e = select.epoll()

    # Associate with server socket file descriptor to the epoll object
    e.register(serverSock.fileno(), select.EPOLLIN)

    
    serverSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serverSock.bind((serverHost, serverPort))
    serverSock.listen(5)
    serverSock.setblocking(0)
    serverSock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    print("Listening")

    # Insta





if __name__ == "__main__":
    main()
