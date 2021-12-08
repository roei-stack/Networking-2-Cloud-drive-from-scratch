import os
import time
import socket
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import Utils as U

# This Unique id is for new clients
USER_ID = U.DEFAULT_USER_ID
# This is the client's serial number in case he connects from more than 1 pc
# -1 means this is a new computer
CLIENT_ID = U.DEFAULT_CLIENT_ID
# send the requests to the server every x seconds
requests = []
# the path for out local folder
LOCAL_DIRECTORY_PATH = os.path.abspath('local')
# how much time to wait on 'connect'
CONNECTION_TIMEOUT_VAL = 3
CONFIRMATION_TIMEOUT = 30


class FilesObserver:
    """
     This class is responsible for monitoring changes in a given folder
     When calling the start function (see below), it executes a given operation every X seconds
    """

    def __init__(self, path_to_folder: str, created_func: callable,
                 deleted_func: callable, modified_func: callable, moved_func: callable):
        """
        initiate the class with path to folder and 4 functions
        :param path_to_folder: path to folder to monitor
        :param created_func: call this function when we detect that a file was created
        :param deleted_func: call this function when we detect that a file was deleted
        :param modified_func: call this function when we detect that a file was modified
        :param moved_func: call this function when we detect that a file was moved
        """
        # check user input is valid callables
        if not os.path.exists(path_to_folder) or \
                created_func is None or deleted_func is None or modified_func is None or moved_func is None:
            print(f'Error: Path "{path_to_folder}" may be invalid, or at least one of the functions is undefined')
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

    def start(self, operation: callable, frequency: int):
        """
        while watchdog runs in background:
            wait X seconds
            do operation()
        """
        # starting the file's observer previously initiated
        self.__observer.start()
        # this method loops forever and observes for changes until user interrupts it
        # whenever it observes a change, it calls one of the 4 methods we supplied it with
        try:
            while True:
                # wait X seconds
                time.sleep(frequency)
                # call operation -> connect to server and send requests
                operation()
        except KeyboardInterrupt:
            self.__observer.stop()
        self.__observer.join()


def connect_tcp(sock: socket.socket, timeout: int):
    sock.settimeout(CONNECTION_TIMEOUT_VAL)
    # connect to host
    try:
        sock.connect((U.HOST_IP, U.HOST_PORT))
    except socket.timeout:
        # remotes server in busy
        print('Error: server is busy, cannot connect')
        sock.close()
        return


def talk_to_remote():
    """
    Connect to remotes and send all requests
    Then wait for conformation
    """
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connect_tcp(client_sock, CONNECTION_TIMEOUT_VAL)
    # sending user_id + client_id + the number of requests + all commands
    client_sock.send(USER_ID.encode() + str(CLIENT_ID).encode() + str(len(requests)).zfill(2).encode())
    # todo make thread safe
    for request in requests:
        client_sock.send(request.encode())
    # temporarily increase the timeout while waiting for confirmation
    client_sock.settimeout(CONFIRMATION_TIMEOUT)
    try:
        # A for ACK
        if client_sock.recv(1) == b'A':
            # server acked, success
            # clean the requests queue and return
            requests.clear()
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
    # command format: len(8 characters) + command_id(1 character) + path
    command = f'{str(len(event.src_path) + U.COMMAND_LEN_SIZE + U.COMMAND_ID_LEN).zfill(U.COMMAND_LEN_SIZE)}1' \
              f'{event.src_path}'
    requests.append(command)


def on_deleted(event):
    print(f'{event.src_path} has been deleted')
    # command id => "2"
    # command format: len(8 characters) + command_id(1 character) + path
    command = f'{str(len(event.src_path) + U.COMMAND_LEN_SIZE + U.COMMAND_ID_LEN).zfill(U.COMMAND_LEN_SIZE)}2' \
              f'{event.src_path}'
    requests.append(command)


def on_modified(event):
    print(f'{event.src_path} has been modified')
    # command id => "3"
    # ignore if the modified object is a directory
    if event.is_directory:
        return
    # command format: len(8 characters) + command_id(1 character) + path_size(3 character) + path + file
    path_length = len(event.src_path)
    command_length = os.path.getsize(event.src_path) + path_length \
                     + U.COMMAND_LEN_SIZE + U.COMMAND_ID_LEN + U.PATH_LEN_SIZE
    with open(event.src_path, 'r') as file:
        command = f'{str(command_length).zfill(U.COMMAND_LEN_SIZE)}3' \
                  f'{str(path_length).zfill(U.PATH_LEN_SIZE)}{event.src_path}{file.read()}'
        requests.append(command)


def on_moved(event):
    print(f'{"folder" if event.is_directory else "file"} {event.src_path} was moved to {event.dest_path}')
    # command id => "4"
    # command format: len(8 characters) + command_id(1 character) + old_path_size(3 characters) + old_path + new_path
    old_path_length = len(event.src_path)
    command_length = U.PATH_LEN_SIZE + U.COMMAND_ID_LEN + U.COMMAND_LEN_SIZE + old_path_length + len(event.dest_path)
    command = f'{str(command_length).zfill(U.COMMAND_LEN_SIZE)}4' \
              f'{str(old_path_length).zfill(U.PATH_LEN_SIZE)}{event.src_path}{event.dest_path}'
    requests.append(command)


def new_user():
    # this function modifies global variables
    global USER_ID, CLIENT_ID
    # connect to remote
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    connect_tcp(client_sock, 1000)
    # build a command from: user_id + client_id + 0 commands => id + '-1' + '00'
    client_sock.send(f'{U.DEFAULT_USER_ID}-100'.encode())
    USER_ID = client_sock.recv(U.USER_ID_LENGTH).decode()
    CLIENT_ID = 0


def new_client():
    # todo download remote
    pass


# start simple -> 1 server and 1 client
def main():
    print('Initializing...')
    # if new user => receive an id
    if USER_ID == U.DEFAULT_USER_ID:
        new_user()
    # if new client => download remote folder
    elif CLIENT_ID == U.DEFAULT_CLIENT_ID:
        new_client()
    # start observer
    # make sure to call Observer in right order => path, create, delete, modified, moved
    observer = FilesObserver(LOCAL_DIRECTORY_PATH, on_created, on_deleted, on_modified, on_moved)
    # every 10 seconds client attempts to connect
    print('Finished initializing')
    observer.start(talk_to_remote, 20)


if __name__ == '__main__':
    main()
