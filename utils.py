import socket
import os

USER_ID_LENGTH = 128
COMMAND_LEN_SIZE = 8
COMMAND_ID_LEN = 1
PATH_LEN_SIZE = 3
DEFAULT_USER_ID = '0' * USER_ID_LENGTH
DEFAULT_CLIENT_ID = '-1'
MAX_CHUNK_SIZE = 1000
CONNECTION_TIMEOUT_VAL = 3
SPECIAL_TIMEOUT = 30


def send_in_chunks(sock: socket.socket, message: str):
    # large files are sent in chunks
    chunks = [message[i:i + MAX_CHUNK_SIZE] for i in range(0, len(message), MAX_CHUNK_SIZE)]
    for chunk in chunks:
        sock.sendall(chunk.encode())


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
    # if the folder does not exist, create an empty folder
    if os.path.isdir(folder):
        os.makedirs(folder, exist_ok=True)
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


def receive_folder(receiver_folder: str, receiver: socket.socket):
    # creating the folder
    os.makedirs(receiver_folder, exist_ok=True)
    # reading from the socket as a file, with 'b' encoding
    with receiver, receiver.makefile('rb') as client_socket_file:
        for data_line in client_socket_file:
            # the file's size in bytes
            bytes_remaining = int(client_socket_file.readline())
            file_name = data_line.strip().decode()
            # calculate path to currently downloaded file
            file_path = os.path.join(receiver_folder, file_name)
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


def remove_folder(folder_path: str):
    # iterate over all files of folder and delete them all
    # deleting from the bottom up
    for root_dir, folders, files in os.walk(folder_path, topdown=False):
        # delete all files in folder
        for file_name in files:
            os.remove(os.path.join(root_dir, file_name))
        # delete the empty folders
        for empty_folder in folders:
            os.rmdir(os.path.join(root_dir, empty_folder))


def send_requests(sock: socket.socket, reqs: list):
    # first 2 characters = number of requests
    sock.sendall(str(len(reqs)).zfill(2).encode())
    for req in reqs:
        send_in_chunks(sock, req)


def receive_requests(sock: socket.socket) -> list:
    """
    Parse the message sent to a list of commands according to the sending protocol
    THE PROTOCOL: "user_id" + "client_id" + "number_of_commands(2 bytes) + commands"
    Each command contains : "command_length + command_id + other info (e.g. file path)"
    :param sock: the socket we will read from
    :return: a list of commands
    """
    commands = []
    # the first 2 bytes are the amount of commands
    size = int(read_x_bytes(sock, 2))
    for _ in range(size):
        # read the command's length, fixed to 8 bytes
        length = int(read_x_bytes(sock, COMMAND_LEN_SIZE))
        # get the command
        commands.append(read_x_bytes(sock, length - COMMAND_LEN_SIZE))
    return commands


def create_cmd(command: str, folder: str):
    # if file => create at path
    rel_path = os.path.join(folder, command[2::])
    if command[1] == '0':
        # create necessary folders
        os.makedirs(os.path.dirname(os.path.abspath(rel_path)), exist_ok=True)
        # create file at path
        with open(rel_path, 'a'):
            pass
    # if dir => call mkdir
    else:
        # create folder
        os.makedirs(rel_path, exist_ok=True)


def delete_cmd(command: str, folder: str):
    path = os.path.join(folder, command[2::])
    if command[1] == '0':
        # delete file at path
        os.remove(path)
    else:
        # remove folder
        remove_folder(path)


def modify_cmd(command: str, folder: str):
    path_len = int(command[1:1 + PATH_LEN_SIZE])
    path = os.path.join(folder, command[4:4 + path_len])
    new_content = command[4 + path_len::]
    # opening the file to update with 'w' => erasing old data
    with open(path, 'w') as file:
        # replacing old content with new content
        file.write(new_content)


def move_cmd(command: str, folder: str):
    old_path_len = int(command[1:1 + PATH_LEN_SIZE])
    old_path = os.path.join(folder, command[4:4 + old_path_len])
    new_path = os.path.join(folder, command[4 + old_path_len::])
    # move the file at old_path to new_path
    # moving a file
    try:
        # moving the file to new_path
        os.replace(old_path, new_path)
    except FileNotFoundError:
        # do nothing : if the file is no longer at old_path => it was moved before
        pass


def execute_command(command: str, folder: str):
    # the first character is the command type
    cid = command[0]
    if cid == '1':
        # CREATE: format = '1' + is_directory + path
        create_cmd(command, folder)
    elif cid == '2':
        # DELETE: format = '2' + is_directory + path
        delete_cmd(command, folder)
    elif cid == '3':
        # MODIFIED: format = '3' + path_len + path + file
        modify_cmd(command, folder)
    elif cid == '4':
        # MOVED: format = '4' + old_path_len + old_path + new_path
        move_cmd(command, folder)
    else:
        raise ValueError(f'Error: {cid} is not a valid command id')
