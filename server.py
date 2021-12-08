import os
import socket
import random
import sys
import Utils as U

QUEUE_SIZE = 5
REMOTE_DIRECTORIES_PATH = 'remotes'
# this dictionary is the client's database
users_book = {}


def generate_user_id() -> str:
    length = U.USER_ID_LENGTH
    characters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
                  'u', 'v', 'w', 'x', 'y', 'z', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N',
                  'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '0', '1', '2', '3', '4', '5', '6', '7',
                  '8', '9']
    return ''.join(random.choice(characters) for _ in range(length))


def parse_command(command: str):
    # the first character is the command type
    cid = command[0]
    if cid == '1':
        pass
    elif cid == '2':
        pass
    elif cid == '3':
        pass
    elif cid == '4':
        pass
    else:
        raise ValueError(f'{cid} is not a valid command id')


def receive_requests(sock: socket.socket) -> (str, int, list):
    """
    Parse the message sent to a list of commands according to the sending protocol
    THE PROTOCOL: "user_id" + "client_id" + "number_of_commands(2 bytes) + commands"
    Each command contains : "command_length + command_id + other info (e.g. file path)"
    :param sock: the socket we will read from
    :return: a list of commands
    """
    user_id = U.read_x_bytes(sock, 128)
    client_id = int(U.read_x_bytes(sock, 2))
    commands = []
    # the first 2 bytes are the amount of commands
    size = int(U.read_x_bytes(sock, 2))
    for _ in range(size):
        # read the command's length, fixed to 8 bytes
        length = int(U.read_x_bytes(sock, U.COMMAND_LEN_SIZE))
        # get the command
        commands.append(U.read_x_bytes(sock, length - U.COMMAND_LEN_SIZE))
    return user_id, client_id, commands


def new_user() -> bytes:
    # new client has connected, generate a unique id
    user_id = generate_user_id()
    # creating remote folder for client
    path_to_folder = os.path.join(REMOTE_DIRECTORIES_PATH, user_id)
    os.mkdir(path_to_folder)
    # adding the user to the client's book
    users_book[user_id] = (path_to_folder, [[]])
    print(f'Client: {user_id}\nConnected to remote folder at {path_to_folder}')
    # return user's id
    return user_id.encode()


def new_client(user_id: str, client: socket.socket):
    remote_folder_path, clients = users_book[user_id]
    # getting a new client id
    client_id = len(clients)
    # adding the new client to the list
    clients.append([])
    # send the client id
    client.send(str(client_id).encode())
    # send the remote folder
    U.send_folder(remote_folder_path, client)


def main():
    # opening socket and listening for clients
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((U.HOST_IP, U.HOST_PORT))
    server.listen(QUEUE_SIZE)
    while True:
        # accept incoming client
        client_socket, client_address = server.accept()
        print(f'Connection from: {client_address}')
        user_id, client_id, commands = receive_requests(client_socket)
        # check if this is a new user
        if user_id == U.DEFAULT_USER_ID:
            # generate and send id
            user_id = new_user()
            client_socket.send(user_id)
        # check if a known user connected from a new pc => new client
        elif client_id == U.DEFAULT_CLIENT_ID:
            new_client(user_id, client_socket)
        else:
            # normal call
            print(f'requests -> {commands}')
            # todo execute all commands
            # todo push updates to client
            client_socket.send(b'A')
            client_socket.close()


if __name__ == '__main__':
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((U.HOST_IP, U.HOST_PORT))
    server.listen(QUEUE_SIZE)
    client_sock, _ = server.accept()
    U.send_folder('remotes', client_sock)
    client_sock.close()
    #main()
