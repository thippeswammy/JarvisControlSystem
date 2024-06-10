import socket

# Define the IP address and port to listen on (use your laptop's IP address)
HOST = '0.0.0.0'  # Listen on all network interfaces
PORT = 12345      # Choose any free port

# Create a socket object
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
    # Bind the socket to the host and port
    server_socket.bind((HOST, PORT))
    # Listen for incoming connections
    server_socket.listen()

    print(f'Server listening on {HOST}:{PORT}...')

    # Accept connections from clients
    conn, addr = server_socket.accept()
    with conn:
        print(f'Connected by {addr}')

        while True:
            # Receive data from the client
            data = conn.recv(1024)
            if not data:
                break
            # Print the received message
            print(f'Received message: {data.decode()}')
