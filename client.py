import os
import sys
import time
import socket
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import utils as u


IP = sys.argv[1]
PORT = int(sys.argv[2])
LOCAL_DIRECTORY_PATH = os.path.abspath(sys.argv[3])
FREQUENCY = int(sys.argv[4]) if sys.argv[4].isnumeric() and len(sys.argv[4]) == u.USER_ID_LENGTH else 10
# OPTIONAL : user's id
USER_ID = sys.argv[5] if len(sys.argv) >= 6 else u.DEFAULT_USER_ID
# This is the client's serial number in case he connects from more than 1 pc
# -1 means this is a new computer
CLIENT_ID = u.DEFAULT_CLIENT_ID
# send the requests to the server every x seconds
requests = []


class FilesObserver:
    """
     This class is responsible for monitoring changes in a given folder
     When calling the start function (see below), it executes a given operation every X seconds
    """

    def __init__(self, path_to_folder: str, created_func: callable,
                 deleted_func: callable, modified_func: callable, moved_func: callable):
        # create folder if not exist yet
        os.makedirs(path_to_folder, exist_ok=True)
        """
        initiate the class with path to folder and 4 functions
        :param path_to_folder: path to folder to monitor
        :param created_func: call this function when we detect that a file was created
        :param deleted_func: call this function when we detect that a file was deleted
        :param modified_func: call this function when we detect that a file was modified
        :param moved_func: call this function when we detect that a file was moved
        """
        # check user input is valid callables
        if created_func is None or deleted_func is None or modified_func is None or moved_func is None:
            print(f'Error: one of the functions is undefined')
            print('Aborted')
            exit(-1)

        # some important watchdog constants
        patterns = ["*"]
        recursively = True
        ignore_patterns = None
        ignore_directories = False
        case_sensitive = True
        # creating the handler and giving it the functions
        handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
        handler.on_created = created_func
        handler.on_deleted = deleted_func
        handler.on_modified = modified_func
        handler.on_moved = moved_func
        # creating and setting the observer without starting it
        self.__observer = Observer()
        self.__observer.schedule(handler, path_to_folder, recursive=recursively)

    def start(self, init: callable, operation: callable, frequency: int):
        """
        1. execute init function
        while watchdog runs in background:
            wait X seconds
            do operation()
        """
        # starting the file's observer previously initiated
        self.__observer.start()
        # this method loops forever and observes for changes until user interrupts it
        # whenever it observes a change, it calls one of the 4 methods we supplied it with
        try:
            init()
            while True:
                # wait X seconds
                time.sleep(frequency)
                # call operation -> connect to server and send requests
                operation()
        except KeyboardInterrupt:
            self.__observer.stop()
        self.__observer.join()


def normalize_path_to_local_folder(path: str) -> str:
    return os.path.relpath(path, LOCAL_DIRECTORY_PATH)


def connect_tcp(sock: socket.socket, timeout: int):
    sock.settimeout(timeout)
    # connect to host
    try:
        sock.connect((IP, PORT))
    except socket.timeout:
        # remotes server in busy
        print('Error: server is busy, cannot connect')
        sock.close()
        return


def talk_to_remote():
    global requests
    print(requests)
    """
    Connect to remotes and send all requests
    Then wait for conformation
    """
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connect_tcp(client_sock, u.CONNECTION_TIMEOUT_VAL)
    # sending user_id + client_id
    client_sock.sendall(USER_ID.encode() + str(CLIENT_ID).zfill(2).encode())
    # todo make thread safe
    # sending num_commands + commands
    old_requests = requests.copy()
    u.send_requests(client_sock, requests)
    # temporarily increase the timeout while waiting for confirmation
    client_sock.settimeout(u.SPECIAL_TIMEOUT)
    try:
        # receive all updates from server
        server_requests = u.receive_requests(client_sock)
        # execute server requests
        for cmd in server_requests:
            u.execute_command(cmd, LOCAL_DIRECTORY_PATH)
        # A for ACK
        if client_sock.recv(1) == b'A':
            # server acked, success
            # clean the requests send to remote
            # only contain requests not sent
            requests = [request for request in requests if request not in old_requests]
            return
    except socket.timeout:
        # server could not complete operation in time
        print('Error: server had trouble managing requests')
        exit(-1)
    finally:
        client_sock.close()
    # if we reached here it means the server sent an error code
    print('Error: unknown error occurred')
    exit(-1)


# here we can modify what the observer will do whenever it detects a change
def on_created(event):
    print(f'{event.src_path} has been created')
    # command id => "1"
    # command format: len(8 characters) + command_id(1 character) + is_folder(1 character) + path
    command = f'{str(len(normalize_path_to_local_folder(event.src_path)) + u.COMMAND_LEN_SIZE + u.COMMAND_ID_LEN + 1).zfill(u.COMMAND_LEN_SIZE)}' \
              f'1{str(int(event.is_directory))}{normalize_path_to_local_folder(event.src_path)}'
    requests.append(command)


def on_deleted(event):
    print(f'{event.src_path} has been deleted')
    # command id => "2"
    # command format: len(8 characters) + command_id(1 character) + is_folder(1 character) + path
    command = f'{str(len(normalize_path_to_local_folder(event.src_path)) + u.COMMAND_LEN_SIZE + u.COMMAND_ID_LEN + 1).zfill(u.COMMAND_LEN_SIZE)}' \
              f'2{str(int(event.is_directory))}{normalize_path_to_local_folder(event.src_path)}'
    requests.append(command)


def on_modified(event):
    # command id => "3"
    # ignore if the modified object is a directory
    if event.is_directory:
        return
    # todo handle big files
    # command format: len(8 characters) + command_id(1 character) + path_size(3 character) + path + file
    path = normalize_path_to_local_folder(event.src_path)
    path_length = len(path)
    command_length = os.path.getsize(event.src_path) + \
                     path_length + u.COMMAND_LEN_SIZE + u.COMMAND_ID_LEN + u.PATH_LEN_SIZE
    with open(event.src_path, 'r') as file:
        command = f'{str(command_length).zfill(u.COMMAND_LEN_SIZE)}3' \
                  f'{str(path_length).zfill(u.PATH_LEN_SIZE)}{path}{file.read()}'
        print(f'{event.src_path} has been modified  ==>  {command}')
        requests.append(command)


def on_moved(event):
    print(f'{"folder" if event.is_directory else "file"} {event.src_path} was moved to {event.dest_path}')
    # command id => "4"
    # command format: len(8 characters) + command_id(1 character) + old_path_size(3 characters) + old_path + new_path
    old_path = normalize_path_to_local_folder(event.src_path)
    new_path = normalize_path_to_local_folder(event.dest_path)
    old_path_length = len(old_path)
    command_length = u.COMMAND_LEN_SIZE + u.COMMAND_ID_LEN + u.PATH_LEN_SIZE + old_path_length + len(new_path)
    command = f'{str(command_length).zfill(u.COMMAND_LEN_SIZE)}4' \
              f'{str(old_path_length).zfill(u.PATH_LEN_SIZE)}{old_path}{new_path}'
    requests.append(command)


def new_user():
    # this function modifies global variables
    global USER_ID, CLIENT_ID
    # connect to remote
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connect_tcp(client_socket, 1000)
    # build a command from: user_id + client_id + 0 commands => id + '-1' + '00'
    client_socket.send(f'{u.DEFAULT_USER_ID}{u.DEFAULT_CLIENT_ID}00'.encode())
    USER_ID = u.read_x_bytes(client_socket, u.USER_ID_LENGTH)
    # uploading folder to server
    u.send_folder(LOCAL_DIRECTORY_PATH, client_socket)
    CLIENT_ID = 0
    client_socket.close()


def new_client():
    # this function modifies global variables
    global CLIENT_ID
    # connect to remote
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connect_tcp(client_socket, 1000)
    # command: user_id + default_client_id + 0 commands
    client_socket.send(f'{USER_ID}{u.DEFAULT_CLIENT_ID}00'.encode())
    # get client id
    CLIENT_ID = u.read_x_bytes(client_socket, 2)
    # download folder
    u.receive_folder(LOCAL_DIRECTORY_PATH, client_socket)
    client_socket.close()


def initialize():
    print('Initializing...')
    # if new user => receive an id and upload folder
    if USER_ID == u.DEFAULT_USER_ID:
        new_user()
    # if new client => download remote folder
    elif CLIENT_ID == u.DEFAULT_CLIENT_ID:
        new_client()
    print('Finished initializing')


def main():
    # start observer
    # make sure to call Observer in right order => path, create, delete, modified, moved
    observer = FilesObserver(LOCAL_DIRECTORY_PATH, on_created, on_deleted, on_modified, on_moved)
    # every 20 seconds client attempts to connect
    observer.start(initialize, talk_to_remote, FREQUENCY)


if __name__ == '__main__':
    main()
