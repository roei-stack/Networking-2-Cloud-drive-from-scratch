import socket

import Utils as U

QUEUE_SIZE = 5
REMOTE_DIRECTORY_PATH = './remote'


def parse_command(command: str):
    pass


def read_x_bytes(sock: socket.socket, x: int) -> str:
    """
    Reads x bytes from tcp socket, and converts to string
    """
    cr = 0
    buff = bytearray(x)
    pos = 0
    while pos < x:
        cr = sock.recv_into(memoryview(buff)[pos:])
        if cr == 0:
            raise EOFError
    pos += cr
    return buff.decode()


def receive_commands(sock: socket.socket) -> list:
    """
    Parse the message sent to a list of commands according to the sending protocol
    THE PROTOCOL: "number_of_commands(2 bytes) + commands"
    Each command contains : "command_length + command_id + other info (e.g. file path)"
    :param sock: the socket we will read from
    :return: a list of commands
    """
    commands = []
    # the first 2 bytes are the amount of commands
    size = int(read_x_bytes(sock, 2))
    for counter in range(size):
        # read the command's length, fixed to 8 bytes
        length = int(sock.recv(U.COMMAND_LEN_SIZE))
        # get the command
        commands.append(read_x_bytes(sock, length - U.COMMAND_ID_LEN))
    return commands


def main():
    # opening socket and listening for clients
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((U.HOST_IP, U.HOST_PORT))
    server.listen(QUEUE_SIZE)
    while True:
        # accept incoming client
        client_socket, client_address = server.accept()
        print(f'Connection from: {client_address}')
        # todo receive and execute all commands
        client_socket.send(b'A')
        client_socket.close()


if __name__ == '__main__':
    main()
