import socket
import os

USER_ID_LENGTH = 128
HOST_IP = '127.0.0.1'
HOST_PORT = 12345
ENCODING = 'utf-8'
BUFFER = 2048
COMMAND_LEN_SIZE = 8
COMMAND_ID_LEN = 1
PATH_LEN_SIZE = 3
DEFAULT_USER_ID = '0' * USER_ID_LENGTH
DEFAULT_CLIENT_ID = 'x'
MAX_CHUNK_SIZE = 1000


def read_x_bytes(sock: socket.socket, x: int) -> str:
    """
    Reads x bytes from tcp socket, and converts to string
    """
    buff = bytearray(x)
    pos = 0
    while pos < x:
        cr = sock.recv_into(memoryview(buff)[pos:])
        if cr == 0:
            raise EOFError
        pos += cr
    return buff.decode()


def send_folder(folder_path: str, sender_sock: socket.socket):
    """
    Send a folder at a given path through the sender socket
    using the os. Walk method
    """
    with sender_sock:
        for path, folders, files in os.walk(folder_path):
            for file in files:
                name_file = os.path.join(path, file)
                relative_path = os.path.relpath(name_file, folder_path)
                file_size = os.path.getsize(name_file)
                # opening and sending the file (open in binary encoding)
                with open(name_file, 'rb') as f:
                    # sending: path + size + file_contents
                    sender_sock.sendall(relative_path.encode() + b'\n' + str(file_size).encode() + b'\n')
                    # Sending the file in multiple packets, so we can send large files
                    while True:
                        data_chunk = f.read(MAX_CHUNK_SIZE)
                        # if no data is left, break
                        if not data_chunk:
                            break
                        # send all data
                        sender_sock.sendall(data_chunk)


def receive_folder(client_folder: str, receiver: socket.socket):
    # reading from the socket as a file
    with receiver, receiver.makefile('rb') as reading_file:
        # read from file until it's empty
        for data_line in reading_file:
            file_size = int(reading_file.readline())
            file_name = data_line.strip().decode()
            local_path = os.path.join(client_folder, file_name)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            # downloading the file
            with open(local_path, 'wb') as new_file:
                while file_size > 0:
                    # reading min(size, MAX_CHUNK_SIZE)
                    read_chunk_size = file_size if file_size <= MAX_CHUNK_SIZE else MAX_CHUNK_SIZE
                    data = read_x_bytes(receiver, read_chunk_size)
                    # stop writing if no data is left
                    if not data:
                        break
                    new_file.write(data.encode())
                    file_size -= read_chunk_size
                # if while breaks this statement will not be run
                else:
                    continue
            break
