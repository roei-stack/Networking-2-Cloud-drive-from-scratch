import socket

import Utils

QUEUE_SIZE = 5
REMOTE_DIRECTORY_PATH = './remote'


def main():
    # opening socket and listening for clients
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((Utils.HOST_IP, Utils.HOST_PORT))
    server.listen(QUEUE_SIZE)
    while True:
        # accept incoming client
        client_socket, client_address = server.accept()
        print(f'Connection from: {client_address}')
        data = client_socket.recv(2048)
        print(f'REQUEST: {data.decode(Utils.ENCODING)}')
        # todo request

        client_socket.close()


if __name__ == '__main__':
    main()
