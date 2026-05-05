#include <iostream>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <string>

#pragma comment(lib, "ws2_32.lib")

bool isPortOpen(const char* ip, int port) {
    WSADATA wsaData;
    if (WSAStartup(MAKEWORD(2, 2), &wsaData) != 0) {
        return false;
    }

    SOCKET sock = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (sock == INVALID_SOCKET) {
        WSACleanup();
        return false;
    }

    struct sockaddr_in clientService;
    clientService.sin_family = AF_INET;
    inet_pton(AF_INET, ip, &clientService.sin_addr.s_addr);
    clientService.sin_port = htons(port);

    // Set non-blocking mode for timeout
    u_long iMode = 1;
    ioctlsocket(sock, FIONBIO, &iMode);

    connect(sock, (struct sockaddr*)&clientService, sizeof(clientService));

    fd_set WriteFDs, ExceptFDs;
    FD_ZERO(&WriteFDs);
    FD_ZERO(&ExceptFDs);
    FD_SET(sock, &WriteFDs);
    FD_SET(sock, &ExceptFDs);

    struct timeval timeout;
    timeout.tv_sec = 1; // 1 second timeout
    timeout.tv_usec = 0;

    int res = select(sock + 1, NULL, &WriteFDs, &ExceptFDs, &timeout);

    bool connected = false;
    if (res > 0 && FD_ISSET(sock, &WriteFDs)) {
        connected = true;
    }

    closesocket(sock);
    WSACleanup();
    return connected;
}

void startOllama() {
    STARTUPINFO si;
    PROCESS_INFORMATION pi;

    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE; // Hide the window
    ZeroMemory(&pi, sizeof(pi));

    // Command line to run
    char cmd[] = "ollama serve";

    if (!CreateProcess(NULL, cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
        std::cerr << "CreateProcess failed (" << GetLastError() << ").\n";
        return;
    }

    // Close process and thread handles. 
    // The process will continue to run in the background.
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
}

int main(int argc, char* argv[]) {
    const char* ip = "127.0.0.1";
    int port = 11434;

    if (argc > 1) {
        // Optional: take port or command from args
    }

    if (isPortOpen(ip, port)) {
        std::cout << "Ollama is already running.\n";
        return 0;
    }

    std::cout << "Ollama not found. Starting service...\n";
    startOllama();
    
    return 0;
}
