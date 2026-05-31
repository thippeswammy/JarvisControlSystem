#include "RpcHandlers.h"
#include "../UiaOperationAbstraction/UiaOperationAbstraction.h"
#include <wil/com.h>
#include <wil/resource.h>
#include <iostream>

using namespace UiaOperationAbstraction;

std::map<std::string, wil::com_ptr<IUIAutomationElement>> RpcHandlers::elementCache;
int RpcHandlers::nextElementId = 1;

std::string RpcHandlers::CacheElement(wil::com_ptr<IUIAutomationElement> element) {
    if (!element) return "";
    std::string id = "elem_" + std::to_string(nextElementId++);
    elementCache[id] = element;
    return id;
}

std::string wstring_to_utf8(const std::wstring& str) {
    if (str.empty()) return "";
    int size_needed = WideCharToMultiByte(CP_UTF8, 0, &str[0], (int)str.size(), NULL, 0, NULL, NULL);
    std::string strTo(size_needed, 0);
    WideCharToMultiByte(CP_UTF8, 0, &str[0], (int)str.size(), &strTo[0], size_needed, NULL, NULL);
    return strTo;
}

std::wstring utf8_to_wstring(const std::string& str) {
    if (str.empty()) return L"";
    int size_needed = MultiByteToWideChar(CP_UTF8, 0, &str[0], (int)str.size(), NULL, 0);
    std::wstring strTo(size_needed, 0);
    MultiByteToWideChar(CP_UTF8, 0, &str[0], (int)str.size(), &strTo[0], size_needed);
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
    
    std::string element_id = CacheElement(focusedElement);
    
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
    
    wil::shared_bstr nameBstr = static_cast<wil::shared_bstr>(remoteName);
    wil::shared_bstr idBstr = static_cast<wil::shared_bstr>(remoteId);
    
    std::wstring nameW = nameBstr.get() ? nameBstr.get() : L"";
    std::wstring idW = idBstr.get() ? idBstr.get() : L"";
    
    return {
        {"element_id", element_id},
        {"uia_id", wstring_to_utf8(idW)},
        {"name", wstring_to_utf8(nameW)},
        {"control_type", static_cast<int>(remoteControlType)}
    };
}

json RpcHandlers::FindElement(const json& params) {
    wil::com_ptr<IUIAutomation> automation;
    CoCreateInstance(__uuidof(CUIAutomation8), nullptr, CLSCTX_INPROC_SERVER, IID_PPV_ARGS(&automation));
    
    wil::com_ptr<IUIAutomationElement> root;
    automation->GetRootElement(&root);
    
    if (params.contains("element_id") && elementCache.count(params["element_id"])) {
        root = elementCache[params["element_id"]];
    }
    
    wil::com_ptr<IUIAutomationCondition> condition;
    
    if (params.contains("by") && params.contains("value")) {
        std::string by = params["by"].get<std::string>();
        std::wstring valueW = utf8_to_wstring(params["value"].get<std::string>());
        wil::unique_variant var;
        var.vt = VT_BSTR;
        var.bstrVal = SysAllocString(valueW.c_str());
        
        if (by == "name") {
            automation->CreatePropertyCondition(UIA_NamePropertyId, var, &condition);
        } else if (by == "id" || by == "uia_id") {
            automation->CreatePropertyCondition(UIA_AutomationIdPropertyId, var, &condition);
        }
    }
    
    if (!condition) {
        return { {"error", "Must provide valid 'by' ('name' or 'id') and 'value' to find_element"} };
    }
    
    wil::com_ptr<IUIAutomationElement> foundElement;
    root->FindFirst(TreeScope_Subtree, condition.get(), &foundElement);
    
    if (!foundElement) {
        return { {"error", "Element not found"} };
    }
    
    std::string element_id = CacheElement(foundElement);
    
    wil::unique_bstr name, aid;
    foundElement->get_CurrentName(&name);
    foundElement->get_CurrentAutomationId(&aid);
    CONTROLTYPEID cType = 0;
    foundElement->get_CurrentControlType(&cType);
    
    std::wstring nameW = name.get() ? name.get() : L"";
    std::wstring idW = aid.get() ? aid.get() : L"";
    
    return {
        {"element_id", element_id},
        {"uia_id", wstring_to_utf8(idW)},
        {"name", wstring_to_utf8(nameW)},
        {"control_type", cType}
    };
}

json RpcHandlers::GetElementProperties(const json& params) {
    if (!params.contains("element_id") || !elementCache.count(params["element_id"])) {
        return { {"error", "Invalid or missing element_id"} };
    }
    
    wil::com_ptr<IUIAutomationElement> target = elementCache[params["element_id"]];
    
    auto scope = UiaOperationScope::StartNew();
    UiaElement element = target.get();
    scope.BindInput(element);
    
    UiaString remoteName = element.GetName();
    UiaString remoteId = element.GetAutomationId();
    UiaInt remoteControlType = element.GetControlType();
    UiaBool remoteIsEnabled = element.GetIsEnabled();
    UiaBool remoteIsOffscreen = element.GetIsOffscreen();
    
    scope.BindResult(remoteName);
    scope.BindResult(remoteId);
    scope.BindResult(remoteControlType);
    scope.BindResult(remoteIsEnabled);
    scope.BindResult(remoteIsOffscreen);
    
    HRESULT hr = scope.ResolveHr();
    if (FAILED(hr)) {
        return { {"error", "Failed to resolve element properties via remote operation"} };
    }
    
    wil::shared_bstr nameBstr = static_cast<wil::shared_bstr>(remoteName);
    wil::shared_bstr idBstr = static_cast<wil::shared_bstr>(remoteId);
    
    std::wstring nameW = nameBstr.get() ? nameBstr.get() : L"";
    std::wstring idW = idBstr.get() ? idBstr.get() : L"";
    
    return {
        {"element_id", params["element_id"]},
        {"uia_id", wstring_to_utf8(idW)},
        {"name", wstring_to_utf8(nameW)},
        {"control_type", static_cast<int>(remoteControlType)},
        {"is_enabled", static_cast<bool>(remoteIsEnabled)},
        {"is_offscreen", static_cast<bool>(remoteIsOffscreen)}
    };
}

json RpcHandlers::GetElementPatterns(const json& params) {
    if (!params.contains("element_id") || !elementCache.count(params["element_id"])) {
        return { {"error", "Invalid or missing element_id"} };
    }
    
    wil::com_ptr<IUIAutomationElement> target = elementCache[params["element_id"]];
    
    json patterns = json::array();
    
    wil::com_ptr<IUnknown> pattern;
    if (SUCCEEDED(target->GetCurrentPattern(UIA_InvokePatternId, &pattern)) && pattern) {
        patterns.push_back("InvokePattern");
    }
    if (SUCCEEDED(target->GetCurrentPattern(UIA_ValuePatternId, &pattern)) && pattern) {
        patterns.push_back("ValuePattern");
    }
    
    return {
        {"patterns", patterns}
    };
}

json RpcHandlers::GetElementRect(const json& params) {
    if (!params.contains("element_id") || !elementCache.count(params["element_id"])) {
        return { {"error", "Invalid or missing element_id"} };
    }
    
    wil::com_ptr<IUIAutomationElement> target = elementCache[params["element_id"]];
    
    auto scope = UiaOperationScope::StartNew();
    UiaElement element = target.get();
    scope.BindInput(element);
    
    UiaOperationAbstraction::UiaRect rect = element.GetBoundingRectangle();
    scope.BindResult(rect);
    
    HRESULT hr = scope.ResolveHr();
    if (FAILED(hr)) {
        return { {"error", "Failed to resolve bounding rectangle via remote operation"} };
    }
    
    auto bounds = static_cast<winrt::Windows::Foundation::Rect>(rect);
    
    return {
        {"x", bounds.X},
        {"y", bounds.Y},
        {"width", bounds.Width},
        {"height", bounds.Height}
    };
}

json RpcHandlers::InvokeElement(const json& params) {
    if (!params.contains("element_id") || !elementCache.count(params["element_id"])) {
        return { {"error", "Invalid or missing element_id"} };
    }
    
    wil::com_ptr<IUIAutomationElement> target = elementCache[params["element_id"]];
    
    auto scope = UiaOperationScope::StartNew();
    UiaElement element = target.get();
    scope.BindInput(element);
    
    UiaInvokePattern invokePattern = element.GetInvokePattern();
    invokePattern.Invoke();
    
    HRESULT hr = scope.ResolveHr();
    if (FAILED(hr)) {
        return { {"error", "Failed to invoke element via remote operation"} };
    }
    
    return { {"status", "success"} };
}
