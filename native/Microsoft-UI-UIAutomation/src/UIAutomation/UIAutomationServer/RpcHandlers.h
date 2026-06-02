#pragma once
#include "json.hpp"
#include <string>
#include <map>
#include <wil/com.h>
#include <UIAutomation.h>

using json = nlohmann::json;

class RpcHandlers {
public:
    static json GetElement(const json& params);
    static json SetElement(const json& params);
    static json GetFocusedElement();
    static json FindElement(const json& params);
    static json FindAllElements(const json& params);
    static json GetElementTree(const json& params);
    static json GetChildrenElements(const json& params);
    static json GetParentElement(const json& params);
    static json GetSiblingElements(const json& params);

    static void Initialize(IUIAutomation* automation);
    static std::string wstring_to_utf8(const std::wstring& str);
    static std::wstring utf8_to_wstring(const std::string& str);
    static std::string CacheElement(wil::com_ptr<IUIAutomationElement> element);
    
private:
    static std::map<std::string, wil::com_ptr<IUIAutomationElement>> elementCache;
    static int nextElementId;
    static wil::com_ptr<IUIAutomation> g_automation;
};
