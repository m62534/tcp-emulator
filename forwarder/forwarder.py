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
                # initialize connection
                clientConn, clientAddr = serverSock.accept()
                clientConn.setblocking(0)
                client_fd = connection.fileno()
                e.register(client_fd, select.EPOLLIN)
                connections[client_fd] = clientConn
                
                #override old fd
                requests[client_fd] = ''
                responses[client_fd] = ''

            elif event & select.EPOLLIN:
                requests[fd] += connections[fd].recv(8) # add new connection with 8 byte buffer size
                if requests[fd] == 'quit\n' or requests[fd] == '': #Delete connection
                    
                elif '\n' in requests[fd]:
                    
            elif event & select.EPOLLOUT:
                # Send response 


if __name__ == "__main__":
    main()
