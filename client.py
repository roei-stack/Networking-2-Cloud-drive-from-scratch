import logging
import os
import time
import socket
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import Utils


class FilesObserver:
    # wrapping watchdog methods in this class
    def __init__(self, path_to_folder: str, created_func: callable,
                 deleted_func: callable, modified_func: callable, moved_func: callable):
        # checking that user entered valid callables
        if not os.path.exists(path_to_folder) or \
                created_func is None or deleted_func is None or modified_func is None or moved_func is None:
            print(f'Error: Invalid path {path_to_folder}, or at least one of the functions may be undefined')
            print('aborted')
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

    def start(self):
        # starting the files observer previously initiated
        self.__observer.start()
        # this method loops forever and observes for changes until user interrupts it
        # whenever it observes a change, it calls one of the 4 methods we supplied it with
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.__observer.stop()
            self.__observer.join()


LOCAL_DIRECTORY_PATH = 'local'
commands = []
# connect to host
#client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#client_sock.connect((Utils.HOST_IP, Utils.HOST_PORT))


# here we can modify what the observer will do whenever it detects a change
def on_created(event):
    # command id => "1"
    # print(f'DETECTED: {event.src_path} has been created!')
    # message = f'new folder at {event.src_path}' if event.is_directory else f'new file at {event.src_path}'
    # command format: len(4 bytes) + command_id(1 byte) + path
    length = len(event.src_path) + 5
    command = f'{length.to_bytes(4, byteorder="little", signed=True).decode()}1{event.src_path}'
    # command[:4] = length, command[4:5] = command id, command[5:length] = path
    # client_sock.send(message.encode())


def on_deleted(event):
    # command id => "2"
    # print(f'DETECTED: {event.src_path} has been deleted!')
    # message = f'removed folder at {event.src_path}' if event.is_directory else f'removed file at {event.src_path}'
    # command format: len(4 bytes) + command_id(1 byte) + path
    length = len(event.src_path) + 5
    command = f'{length.to_bytes(4, byteorder="little", signed=True).decode()}2{event.src_path}'
    # client_sock.send(message.encode())


def on_modified(event):
    # command id => "3"
    # ignore when the modified object is a directory
    if event.is_directory:
        return
    # print(f'DETECTED: {event.src_path} has been modified!')
    # message = f'modified file at {event.src_path}'
    # command format: len(4 bytes) + command_id(1 byte) + path_size(1 byte) + path + file
    path_length = len(event.src_path)
    command_length = os.path.getsize(event.src_path) + path_length + 6
    with open(event.src_path, 'r') as file:
        command = f'{command_length.to_bytes(4, byteorder="little", signed=True).decode()}3' \
                  f'{path_length.to_bytes(1, byteorder="little", signed=True).decode()}{event.src_path}{file.read()}'
    # client_sock.send(message.encode())


def on_moved(event):
    # command id => "4"
    # print(f'DETECTED: {event.src_path} was moved to {event.dest_path}')
    # message = ('folder' if event.is_directory else 'file') + f' {event.src_path} was moved to {event.dest_path}'
    # command: len(4 bytes) + command_id(1 byte) + old_path_size(1 byte) + old_path + new_path
    old_path_length = len(event.src_path)
    command_length = 6 + old_path_length + len(event.dest_path)
    command = f'{command_length.to_bytes(4, byteorder="little", signed=True).decode()}4' \
              f'{old_path_length.to_bytes(1, byteorder="little", signed=True).decode()}' \
              f'{event.src_path}{event.dest_path}'
    # client_sock.send(message.encode())


# starting simple -> 1 server and 1 client
def main():
    # for parent_dir, dirs, files in os.walk('.'):
    #    for file_name in files:
    #        print(os.path.join(parent_dir, file_name))

    # start observer
    # make sure to call Observer in right order => path, create, delete, modified, moved
    observer = FilesObserver(LOCAL_DIRECTORY_PATH, on_created, on_deleted, on_modified, on_moved)
    observer.start()


if __name__ == '__main__':
    main()
