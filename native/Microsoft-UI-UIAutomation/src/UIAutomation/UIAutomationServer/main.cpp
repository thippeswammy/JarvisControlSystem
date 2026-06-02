#include <iostream>
#include <string>
#include "json.hpp"
#include <windows.h>
#include <uiautomation.h>
#include <wil/com.h>
#include "../UiaOperationAbstraction/UiaOperationAbstraction.h"
#include "RpcHandlers.h"

using json = nlohmann::json;

int main()
{
    std::cout << "Server starting..." << std::endl;
    std::cout.flush();
    try {
        // Initialize COM as Multi-Threaded Apartment (MTA)
        auto initCOM = wil::CoInitializeEx(COINIT_MULTITHREADED);

        // We need IUIAutomation. Let's create it.
        wil::com_ptr<IUIAutomation> automation;
        HRESULT hr = CoCreateInstance(__uuidof(CUIAutomation8), nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&automation));
        if (FAILED(hr)) {
            std::cerr << "Failed to initialize IUIAutomation" << std::endl;
            return 1;
        }

        bool useRemoteOperations = false;
        UiaOperationAbstraction::Initialize(useRemoteOperations, automation.get());
        RpcHandlers::Initialize(automation.get());

        // Main JSON-RPC loop over stdio
        std::string line;
        while (std::getline(std::cin, line)) {
            if (line.empty()) continue;

            try {
                json request = json::parse(line);
                
                if (!request.contains("method")) continue;
                
                std::string method = request["method"];
                json params = request.contains("params") ? request["params"] : json::object();
                
                json response;
                response["jsonrpc"] = "2.0";
                if (request.contains("id")) {
                    response["id"] = request["id"];
                }

                // Dispatch to new generic GetElement/SetElement UIA handlers
                if (method == "initialize") {
                    bool remote = params.contains("use_remote_operations") ? params["use_remote_operations"].get<bool>() : false;
                    UiaOperationAbstraction::Initialize(remote, automation.get());
                    response["result"] = { {"success", true}, {"remote", remote} };
                }
                else if (method == "get_element") {
                    response["result"] = RpcHandlers::GetElement(params);
                }
                else if (method == "set_element") {
                    response["result"] = RpcHandlers::SetElement(params);
                }
                else if (method == "get_focused_element") {
                    response["result"] = RpcHandlers::GetFocusedElement();
                }
                else if (method == "find_element") {
                    response["result"] = RpcHandlers::FindElement(params);
                }
                else if (method == "find_all_elements") {
                    response["result"] = RpcHandlers::FindAllElements(params);
                }
                else if (method == "get_element_tree") {
                    response["result"] = RpcHandlers::GetElementTree(params);
                }
                else if (method == "get_element_children") {
                    response["result"] = RpcHandlers::GetChildrenElements(params);
                }
                else if (method == "get_element_parent") {
                    response["result"] = RpcHandlers::GetParentElement(params);
                }
                else if (method == "get_element_siblings") {
                    response["result"] = RpcHandlers::GetSiblingElements(params);
                }
                else {
                    response["error"] = { {"code", -32601}, {"message", "Method not found"} };
                }

                std::cout << response.dump() << "\n";
                std::cout.flush();

            } catch (const std::exception& e) {
                json error_response;
                error_response["jsonrpc"] = "2.0";
                error_response["error"] = { {"code", -32700}, {"message", std::string("Parse error: ") + e.what()} };
                if (json::accept(line)) {
                    json req = json::parse(line);
                    if (req.contains("id")) error_response["id"] = req["id"];
                }
                std::cout << error_response.dump() << "\n";
                std::cout.flush();
            } catch (const winrt::hresult_error& e) {
                json error_response;
                error_response["jsonrpc"] = "2.0";
                std::wstring msgW = e.message().c_str();
                int size_needed = WideCharToMultiByte(CP_UTF8, 0, &msgW[0], (int)msgW.size(), NULL, 0, NULL, NULL);
                std::string msg(size_needed, 0);
                WideCharToMultiByte(CP_UTF8, 0, &msgW[0], (int)msgW.size(), &msg[0], size_needed, NULL, NULL);
                error_response["error"] = { {"code", -32700}, {"message", std::string("WinRT error: ") + msg} };
                if (json::accept(line)) {
                    json req = json::parse(line);
                    if (req.contains("id")) error_response["id"] = req["id"];
                }
                std::cout << error_response.dump() << "\n";
                std::cout.flush();
            } catch (...) {
                json error_response;
                error_response["jsonrpc"] = "2.0";
                error_response["error"] = { {"code", -32700}, {"message", "Unknown error occurred"} };
                if (json::accept(line)) {
                    json req = json::parse(line);
                    if (req.contains("id")) error_response["id"] = req["id"];
                }
                std::cout << error_response.dump() << "\n";
                std::cout.flush();
            }
        }

        UiaOperationAbstraction::Cleanup();
    } catch (const std::exception& e) {
        FILE* f = nullptr;
        if (fopen_s(&f, "error.log", "w") == 0 && f) {
            fprintf(f, "Exception in main: %s\n", e.what());
            fclose(f);
        }
    } catch (...) {
        FILE* f = nullptr;
        if (fopen_s(&f, "error.log", "w") == 0 && f) {
            fprintf(f, "Unknown exception in main\n");
            fclose(f);
        }
    }
    return 0;
}
