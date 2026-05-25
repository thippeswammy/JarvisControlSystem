import socket

# Define the server (receiving laptop) IP address and port
SERVER_HOST = '172.22.232.45'  # Replace with the IP of the receiving laptop
SERVER_PORT = 12345  # Use the same port as defined in server.py
while True:

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((SERVER_HOST, SERVER_PORT))
        while True:
            message = input("Enter =")
            client_socket.send(message.encode())
            if message == "exit()":
                break
            print(f'Message sent to {SERVER_HOST}:{SERVER_PORT}')
