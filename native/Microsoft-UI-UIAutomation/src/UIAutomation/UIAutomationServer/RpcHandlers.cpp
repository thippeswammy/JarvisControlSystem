#include "RpcHandlers.h"
#include "../UiaOperationAbstraction/UiaOperationAbstraction.h"
#include <wil/com.h>
#include <wil/resource.h>
#include <locale>
#include <codecvt>

using namespace UiaOperationAbstraction;

std::string wstring_to_utf8(const std::wstring& str) {
    if (str.empty()) return "";
    int size_needed = WideCharToMultiByte(CP_UTF8, 0, &str[0], (int)str.size(), NULL, 0, NULL, NULL);
    std::string strTo(size_needed, 0);
    WideCharToMultiByte(CP_UTF8, 0, &str[0], (int)str.size(), &strTo[0], size_needed, NULL, NULL);
    return strTo;
}

json RpcHandlers::GetFocusedElement() {
    auto scope = UiaOperationScope::StartNew();
    
    wil::com_ptr<IUIAutomation> automation;
    CoCreateInstance(__uuidof(CUIAutomation8), nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&automation));
    
    wil::com_ptr<IUIAutomationElement> focusedElement;
    HRESULT hr = automation->GetFocusedElement(&focusedElement);
    
    if (FAILED(hr) || !focusedElement) {
        return { {"error", "Failed to get focused element"} };
    }
    
    UiaElement element = focusedElement.get();
    scope.BindInput(element);
    
    UiaString remoteName = element.GetName();
    UiaString remoteId = element.GetAutomationId();
    UiaInt remoteControlType = element.GetControlType();
    
    scope.BindResult(remoteName);
    scope.BindResult(remoteId);
    scope.BindResult(remoteControlType);
    
    hr = scope.ResolveHr();
    if (FAILED(hr)) {
        return { {"error", "Failed to resolve focused element properties"} };
    }
    
    std::wstring nameW = static_cast<wil::shared_bstr>(remoteName).get() ? static_cast<wil::shared_bstr>(remoteName).get() : L"";
    std::wstring idW = static_cast<wil::shared_bstr>(remoteId).get() ? static_cast<wil::shared_bstr>(remoteId).get() : L"";
    
    return {
        {"element_id", wstring_to_utf8(idW)},
        {"name", wstring_to_utf8(nameW)},
        {"control_type", static_cast<int>(remoteControlType)}
    };
}

json RpcHandlers::FindElement(const json& params) {
    return {
        {"element_id", "stub_id"},
        {"name", "stub_name"},
        {"control_type", 50000}
    };
}

json RpcHandlers::GetElementProperties(const json& params) {
    return {
        {"element_id", params.value("element_id", "unknown")},
        {"name", "Mock Element"},
        {"control_type", 50000},
        {"is_enabled", true},
        {"is_offscreen", false}
    };
}

json RpcHandlers::GetElementPatterns(const json& params) {
    return {
        {"patterns", {"ValuePattern", "InvokePattern"}}
    };
}

json RpcHandlers::GetElementRect(const json& params) {
    return {
        {"x", 100}, {"y", 100}, {"width", 200}, {"height", 50}
    };
}
