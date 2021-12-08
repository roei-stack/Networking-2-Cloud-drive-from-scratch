import socket
from time import sleep
import os

USER_ID_LENGTH = 128
HOST_IP = '127.0.0.1'
HOST_PORT = 12341
ENCODING = 'utf-8'
BUFFER = 2048
COMMAND_LEN_SIZE = 8
COMMAND_ID_LEN = 1
PATH_LEN_SIZE = 3
DEFAULT_USER_ID = '0' * USER_ID_LENGTH
DEFAULT_CLIENT_ID = '-1'
MAX_CHUNK_SIZE = 1000
CONNECTION_TIMEOUT_VAL = 3
SPECIAL_TIMEOUT = 30


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


def send_folder(folder: str, sender_sock: socket.socket):
    """
    Send a folder at a given path through the sender socket
    using the os. Walk method
    """
    # send folder using the walk method
    for parent_path, _, files_list in os.walk(folder):
        # iterate over all files in current folder
        for file in files_list:
            file_name_path = os.path.join(parent_path, file)
            # get relative path to file
            relative_path = os.path.relpath(file_name_path, folder)
            # open with binary encoding
            with open(file_name_path, 'rb') as file_to_send:
                # the sendall method throws an error if the message was not sent entirely
                sender_sock.sendall(f'{relative_path}\n{str(os.path.getsize(file_name_path))}\n'.encode())
                # sending in sub_packet sizes of 1000 bytes each
                while True:
                    data_chunk = file_to_send.read(MAX_CHUNK_SIZE)
                    # stop sending when finished
                    if not data_chunk:
                        break
                    # sending current chunk
                    sender_sock.sendall(data_chunk)


def receive_folder(client_folder: str, receiver: socket.socket):
    # reading from the socket as a file, with 'b' encoding
    with receiver, receiver.makefile('rb') as client_socket_file:
        for data_line in client_socket_file:
            # the file's size in bytes
            bytes_remaining = int(client_socket_file.readline())
            file_name = data_line.strip().decode()
            # calculate path to currently downloaded file
            file_path = os.path.join(client_folder, file_name)
            # create necessary directories if they do not exist yet
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            # receiving in chunks of 1000 bytes each
            # opening a new file and copying from remote
            with open(file_path, 'wb') as file_downloaded:
                while bytes_remaining > 0:
                    # chunk = min{chunk_size, remaining_bytes}
                    chunk_to_read = bytes_remaining if bytes_remaining <= MAX_CHUNK_SIZE else MAX_CHUNK_SIZE
                    data_chunk = client_socket_file.read(chunk_to_read)
                    # break if we could not read completely for some reason
                    if not data_chunk:
                        break
                    # writing the data downloaded to the file opened
                    file_downloaded.write(data_chunk)
                    # subtract to update how many bytes are remaining
                    bytes_remaining -= len(data_chunk)
                # this will run only if we exited the loop without breaking out due to an error
                else:
                    # wrote successfully
                    continue
            # if we reached here it means that the socket was closed due to an error
            print('Error: could not receive data correctly')
            exit(-1)