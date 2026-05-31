#pragma once
#include "json.hpp"
#include <string>

using json = nlohmann::json;

class RpcHandlers {
public:
    static json GetFocusedElement();
    static json FindElement(const json& params);
    static json GetElementProperties(const json& params);
    static json GetElementPatterns(const json& params);
    static json GetElementRect(const json& params);
};
