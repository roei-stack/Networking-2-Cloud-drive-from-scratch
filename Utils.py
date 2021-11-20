import socket

HOST_IP = '127.0.0.1'
HOST_PORT = 12347
ENCODING = 'utf-8'
BUFFER = 2048
CONFORMATION_CODE = 'OK'
ERROR_CODE = 'ERROR'


# do not invoke this function out of the module
def __check_response(response: str):
    if response != CONFORMATION_CODE:
        raise ValueError(f'receiver had trouble: {response}, input may be invalid')


def sendfile(filepath: str, sock: socket.socket):
    with open(filepath, 'r') as f:
        # sending file path and waiting on conformation
        sock.send(filepath.encode(ENCODING))
        __check_response(sock.recv(BUFFER).decode(ENCODING))
        # sending file's content and waiting on conformation
        sock.send(f.read().encode())
        __check_response(sock.recv(BUFFER).decode(ENCODING))
