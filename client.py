import time
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler


class FilesObserver:
    # wrapping watchdog methods in this class
    def __init__(self, path_to_folder: str, created_func: callable,
                 deleted_func: callable, modified_func: callable, moved_func: callable):
        # checking that user entered valid callables
        if created_func is None or deleted_func is None or modified_func is None or moved_func is None:
            # todo better error handling
            raise ValueError('Well Well Well......')
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


# here we modify what the observer will do whenever it detects a change
def on_created(event):
    print(f"hey, {event.src_path} has been created!")


def on_deleted(event):
    print(f"what the f**k! Someone deleted {event.src_path}!")


def on_modified(event):
    print(f"hey buddy, {event.src_path} has been modified")


def on_moved(event):
    print(f"ok ok ok, someone moved {event.src_path} to {event.dest_path}")


if __name__ == '__main__':
    # make sure to call Observer in right order => path, create, delete, modified, moved
    observer = FilesObserver('.', on_created, on_deleted, on_modified, on_moved)
    observer.start()
