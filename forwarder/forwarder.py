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
    serverSock.setblocking(0) # non-blocking
    serverSock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    # Instantiate 4 dicts
    connections, requests, responses, serverSock_fd = {}, {}, {}, serverSock.fileno()
    
    # Continue listening
    while True:
        events = e.poll(1)
        for fd, event in events:
            if fd == serverSock_fd:
                # initialize connection with client

                ## send connection request to FINAL host (Store state somewhere. possibly another dict)
                clientConn, clientAddr = serverSock.accept()
                clientConn.setblocking(0)
                client_fd = clientConn.fileno()
                e.register(client_fd, select.EPOLLIN) # Switch to reading
                connections[client_fd] = clientConn

                # Empty old connection socket, also from FINAL host tracker
                requests[client_fd] = ''
                responses[client_fd] = ''

            elif event & select.EPOLLIN:

                requests[fd] += connections[fd].recv(8) # What should recv be for ssh?
                
                # some condition for closing connection (what would it be for ssh?)
                if requests[fd] == '':
                    # delete connection
                    e.unregister(fd)
                    connections[fd].close()
                    del connections[fd], requests[fd], responses[fd]
                    ##  send connection close for FINAL host, remove from tracker


                #Specify condition for reading (may not need one)
                else: 
                    e.modify(fd, select.EPOLLOUT) # Flip to writing
                    print("more requests coming in. Forwarding")

            # send response back to original client
            elif event & select.EPOLLOUT:
                written = connections[fd].send(responses[fd])
                responses[fd] = responses[fd][written:]
                e.modify(fd, select.EPOLLIN) # Flip to reading

            elif event & select.EPOLLHUP:
                # close

if __name__ == "__main__":
    main()
