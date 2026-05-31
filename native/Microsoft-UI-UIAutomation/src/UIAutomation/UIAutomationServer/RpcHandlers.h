#pragma once
#include "json.hpp"
#include <string>
#include <map>
#include <wil/com.h>
#include <UIAutomation.h>

using json = nlohmann::json;

class RpcHandlers {
public:
    static json GetFocusedElement();
    static json FindElement(const json& params);
    static json GetElementProperties(const json& params);
    static json GetElementPatterns(const json& params);
    static json GetElementRect(const json& params);
    static json InvokeElement(const json& params);
    
private:
    static std::map<std::string, wil::com_ptr<IUIAutomationElement>> elementCache;
    static int nextElementId;
    static std::string CacheElement(wil::com_ptr<IUIAutomationElement> element);
};
