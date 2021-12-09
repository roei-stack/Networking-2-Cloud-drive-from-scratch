import os
import socket
import sys
from random import choice
import utils as u

PORT = int(sys.argv[1])
REMOTE_DIRECTORIES_PATH = './remotes'
# this dictionary : the client's database
users_book = {}
QUEUE_SIZE = 7


def generate_user_id() -> str:
    length = u.USER_ID_LENGTH
    characters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't',
                  'u', 'v', 'w', 'x', 'y', 'z', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N',
                  'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '0', '1', '2', '3', '4', '5', '6', '7',
                  '8', '9']
    return ''.join(choice(characters) for _ in range(length))


def read_ids(sock: socket.socket) -> (str, int):
    user_id = u.read_x_bytes(sock, 128)
    client_id = int(u.read_x_bytes(sock, 2))
    return user_id, client_id


def new_user() -> (bytes, str):
    # new client has connected, generate a unique id
    user_id = generate_user_id()
    # creating remote folder for client
    path_to_folder = os.path.join(REMOTE_DIRECTORIES_PATH, user_id)
    os.mkdir(path_to_folder)
    # adding the user to the client's book
    users_book[user_id] = (path_to_folder, [[]])
    print(f'Client: {user_id}\nConnected to remote folder at {path_to_folder}')
    # return user's id
    return user_id.encode(), path_to_folder


def new_client(user_id: str, client: socket.socket):
    remote_folder_path, clients = users_book[user_id]
    # getting a new client id
    client_id = len(clients)
    # adding the new client to the list
    clients.append([])
    # send the client id
    client.send(str(client_id).encode())
    # send the remote folder
    u.send_folder(remote_folder_path, client)


def main():
    # create 'remotes' folder if it does not exist yet
    os.makedirs(REMOTE_DIRECTORIES_PATH)
    # opening socket and listening for clients
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('', PORT))
    server.listen(QUEUE_SIZE)
    while True:
        # accept incoming client
        client_socket, client_address = server.accept()
        print(f'Connection from: {client_address}')
        user_id, client_id = read_ids(client_socket)
        commands = u.receive_requests(client_socket)
        # check if this is a new user
        if user_id == u.DEFAULT_USER_ID:
            # generate and send id
            user_id, path = new_user()
            client_socket.send(user_id)
            # receive client's folder
            u.receive_folder(path, client_socket)
        # new client : check if a known user connected from a new pc
        elif client_id == u.DEFAULT_CLIENT_ID:
            new_client(user_id, client_socket)
        else:
            # normal call with existing user id with existing client id
            # execute all commands
            print(f'todo => {commands}')
            for x in commands:
                u.execute_command(x, os.path.join(REMOTE_DIRECTORIES_PATH, user_id))
            # update every client's todo_list, except for the current client
            _, clients = users_book[user_id]
            current_client_updates = []
            for index, item in enumerate(clients):
                if index != client_id:
                    item.extand(commands)
                else:
                    current_client_updates = item
            # push updates to client
            u.send_requests(client_socket, current_client_updates)
            # send A for "ACK"
            client_socket.send(b'A')
        client_socket.close()


if __name__ == '__main__':
    main()
