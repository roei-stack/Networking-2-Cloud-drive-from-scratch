import socket

HOST_IP = '127.0.0.1'
HOST_PORT = 12347
ENCODING = 'utf-8'
BUFFER = 2048
CONFORMATION_CODE = 'OK'
ERROR_CODE = 'ERROR'
# protocol codes for all possible operations
MODIFY_CODE = 'MOD'
DELETE_CODE = 'DEL'
MOVE_CODE = 'MOV'


# do not invoke this function out of the module
def __check_response(response: str):
    if response != CONFORMATION_CODE:
        raise ValueError(f'receiver had trouble: {response}, input may be invalid')


def send_file_request(sock: socket.socket, filepath: str):
    sock.send(MODIFY_CODE.encode(ENCODING))
    # waiting on receiver's response
    __check_response(sock.recv(BUFFER).decode(ENCODING))
    with open(filepath, 'r') as f:
        # sending file path and waiting on conformation
        sock.send(filepath.encode(ENCODING))
        __check_response(sock.recv(BUFFER).decode(ENCODING))
        # sending file's content and waiting on conformation
        sock.send(f.read().encode())
        __check_response(sock.recv(BUFFER).decode(ENCODING))


def send_delete_request(sock: socket.socket, filepath: str):
    # send delete request with the file's path
    sock.send(DELETE_CODE.encode(ENCODING))
    # waiting on receiver's response
    __check_response(sock.recv(BUFFER).decode(ENCODING))
    # sending path
    sock.send(filepath.encode(ENCODING))
    __check_response(sock.recv(BUFFER).decode(ENCODING))


def send_move_request(sock: socket.socket, old_path: str, new_path: str):
    # send delete request with the file's path
    sock.send(MODIFY_CODE.encode(ENCODING))
    # waiting on receiver's response
    __check_response(sock.recv(BUFFER).decode(ENCODING))
    # sending old path followed by new path
    sock.send(old_path.encode(ENCODING))
    __check_response(sock.recv(BUFFER).decode(ENCODING))
    sock.send(new_path.encode(ENCODING))
    __check_response(sock.recv(BUFFER).decode(ENCODING))
