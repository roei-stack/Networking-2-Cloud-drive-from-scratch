import os
import time
import socket
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

import Utils

HOST_IP = Utils.HOST_IP
HOST_PORT = Utils.HOST_PORT
LOCAL_DIRECTORY_PATH = './local'

# connect to host
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST_IP, HOST_PORT))


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


# here we can modify what the observer will do whenever it detects a change
def on_created(event):
    print(f'DETECTED: {event.src_path} has been created!')
    # todo send file with path


def on_deleted(event):
    print(f'DETECTED: {event.src_path} has been deleted!')
    # todo send path


def on_modified(event):
    print(f'DETECTED: {event.src_path} has been modified!')
    # todo send file with path


def on_moved(event):
    print(f'DETECTED: {event.src_path} was moved to {event.dest_path}')
    # todo send old path and new path

# starting simple -> 1 server and 1 client
def main():
    # start observer
    # make sure to call Observer in right order => path, create, delete, modified, moved
    observer = FilesObserver(LOCAL_DIRECTORY_PATH, on_created, on_deleted, on_modified, on_moved)
    observer.start()


if __name__ == '__main__':
    main()
