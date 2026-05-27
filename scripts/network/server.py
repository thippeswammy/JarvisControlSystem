import socket

# Define the IP address and port to listen on (use your receiving laptop's IP address)
HOST = '0.0.0.0'  # Allows connections from any network interface
PORT = 12345  # Choose any free port

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f'Server listening on {HOST}:{PORT}...')
    conn, addr = server_socket.accept()
    with conn:
        print(f'Connected by {addr}')
        while True:
            data = conn.recv(1024)
            if data == 'exit()':
                break
            print(f'Received message: {data.decode()}')
