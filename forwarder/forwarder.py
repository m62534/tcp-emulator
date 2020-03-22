#!/usr/bin/python3

import json
import socket
import select
import logging

def main():
    print("hello")

    # Read static variables from json
    myConfig = configObject('config.json')
    global serverHost, serverPort, finalHost, finalPort
    serverHost = myConfig.serverHost
    serverPort = myConfig.serverPort
    finalHost = myConfig.finalHost
    finalPort = myConfig.finalPort

    # Create forwarder
    forwarder()

class configObject:
    def __init__(self, configFile):
        with open(configFile) as config_file:
            data = json.load((config_file))
            self.serverHost = data['server']['host']
            self.serverPort = data['server']['port']
            self.finalHost = data['final']['host']
            self.finalPort = data['final']['port']

def forwarder():
    print("Server host: ", serverHost)
    print("Server port ", serverPort)
    print("final host: ", finalHost)
    print("final port: ", finalPort)

    
    # Create server socket
    serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Create epoll object
    epol = select.epoll()

    # Associate with server socket file descriptor to the epoll object
    epol.register(serverSock.fileno(), select.EPOLLIN)
    print("server associated with epoll object")

    
    serverSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serverSock.bind((serverHost, serverPort))
    serverSock.listen(5)
    serverSock.setblocking(0) # non-blocking

    # Instantiate
    connections, serverSock_fd = {}, serverSock.fileno()

    # Instantiate final dict for final host fd tracking
    limbo = {}
    #trackClient, trackFinal = {}, {}


    # Continue listening
    try:
        while True:

            events = epol.poll(1)

            for fd, event in events:
                if fd == serverSock_fd:
                    print("new Connection")
                    # initialize connection with client
                    clientConn, _ = serverSock.accept()
                    clientConn.setblocking(0)
                    client_fd = clientConn.fileno()

                    # Register client conn to track
                    epol.register(client_fd, select.EPOLLIN) # Switch to reading
                    connections[client_fd] = clientConn
                    print("Created connection for client")


                    ## send connection request to FINAL host (Store state somewhere. possibly another dict)
                    finalConn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    finalConn.connect((finalHost, finalPort))
                    finalConn.setblocking(0)
                    final_fd = finalConn.fileno()
                    
                    ## Register final host conn to track
                    epol.register(final_fd, select.EPOLLIN)
                    connections[final_fd] = finalConn
                    print("Created connection to final dest")

                    ## Added to limbo dict
                    limbo[client_fd], limbo[final_fd] = finalConn, clientConn
                    
                    ## testing
                    print(connections[client_fd])
                    print(connections[final_fd])


                elif event & select.EPOLLIN:
                    # Forward data
                    print("reading data")
                    buffer = connections[fd].recv(1024)
                    print(buffer)
                    connections[fd].send(buffer)

                elif event & select.EPOLLHUP:
                    # deregister
                    print("deregistering...")
                    epol.unregister(limbo[fd])
                    epol.unregister(fd)

                    # close
                    print("closing...")
                    connections[limbo[fd]].close()
                    connections[fd].close()
                    
                    # Release from dicts
                    del connections[fd], connections[limbo[fd]], limbo[fd], limbo[limbo[fd]]
        
    finally:
        # Close main socket and epoll
        epol.unregister(serverSock.fileno())
        epol.close()
        serverSock.close()

if __name__ == "__main__":
    main()
