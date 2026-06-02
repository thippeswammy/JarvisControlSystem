#include "RpcHandlers.h"
#include "../UiaOperationAbstraction/UiaOperationAbstraction.h"
#include <wil/com.h>
#include <wil/resource.h>
#include <iostream>
#include <vector>

using namespace UiaOperationAbstraction;

std::map<std::string, wil::com_ptr<IUIAutomationElement>> RpcHandlers::elementCache;
int RpcHandlers::nextElementId = 1;
wil::com_ptr<IUIAutomation> RpcHandlers::g_automation = nullptr;

void RpcHandlers::Initialize(IUIAutomation* automation) {
    g_automation = automation;
}


std::string RpcHandlers::CacheElement(wil::com_ptr<IUIAutomationElement> element) {
    if (!element) return "";
    
    // De-duplicate: check if this element is already cached
    for (const auto& pair : elementCache) {
        BOOL isSame = FALSE;
        // Querying IUIAutomationElement compare function if available or check raw pointers
        if (pair.second.get() == element.get()) {
            return pair.first;
        }
    }
    
    std::string id = "elem_" + std::to_string(nextElementId++);
    elementCache[id] = element;
    return id;
}

std::string RpcHandlers::wstring_to_utf8(const std::wstring& str) {
    if (str.empty()) return "";
    int size_needed = WideCharToMultiByte(CP_UTF8, 0, &str[0], (int)str.size(), NULL, 0, NULL, NULL);
    std::string strTo(size_needed, 0);
    WideCharToMultiByte(CP_UTF8, 0, &str[0], (int)str.size(), &strTo[0], size_needed, NULL, NULL);
    return strTo;
}

std::wstring RpcHandlers::utf8_to_wstring(const std::string& str) {
    if (str.empty()) return L"";
    int size_needed = MultiByteToWideChar(CP_UTF8, 0, &str[0], (int)str.size(), NULL, 0);
    std::wstring strTo(size_needed, 0);
    MultiByteToWideChar(CP_UTF8, 0, &str[0], (int)str.size(), &strTo[0], size_needed);
    return strTo;
}

// Struct to map UIA Property IDs to native strings
struct PropertyDef {
    UiaPropertyId id;
    const char* name;
};

static const PropertyDef standardProperties[] = {
    { UIA_RuntimeIdPropertyId, "RuntimeId" },
    { UIA_BoundingRectanglePropertyId, "BoundingRectangle" },
    { UIA_ProcessIdPropertyId, "ProcessId" },
    { UIA_ControlTypePropertyId, "ControlType" },
    { UIA_LocalizedControlTypePropertyId, "LocalizedControlType" },
    { UIA_NamePropertyId, "Name" },
    { UIA_AcceleratorKeyPropertyId, "AcceleratorKey" },
    { UIA_AccessKeyPropertyId, "AccessKey" },
    { UIA_HasKeyboardFocusPropertyId, "HasKeyboardFocus" },
    { UIA_IsKeyboardFocusablePropertyId, "IsKeyboardFocusable" },
    { UIA_IsEnabledPropertyId, "IsEnabled" },
    { UIA_AutomationIdPropertyId, "AutomationId" },
    { UIA_ClassNamePropertyId, "ClassName" },
    { UIA_HelpTextPropertyId, "HelpText" },
    { UIA_CulturePropertyId, "Culture" },
    { UIA_IsControlElementPropertyId, "IsControlElement" },
    { UIA_IsContentElementPropertyId, "IsContentElement" },
    { UIA_IsPasswordPropertyId, "IsPassword" },
    { UIA_NativeWindowHandlePropertyId, "NativeWindowHandle" },
    { UIA_ItemTypePropertyId, "ItemType" },
    { UIA_IsOffscreenPropertyId, "IsOffscreen" },
    { UIA_OrientationPropertyId, "Orientation" },
    { UIA_FrameworkIdPropertyId, "FrameworkId" },
    { UIA_IsRequiredForFormPropertyId, "IsRequiredForForm" },
    { UIA_ItemStatusPropertyId, "ItemStatus" },
    { UIA_AriaRolePropertyId, "AriaRole" },
    { UIA_AriaPropertiesPropertyId, "AriaProperties" },
    { UIA_IsDataValidForFormPropertyId, "IsDataValidForForm" },
    { UIA_ProviderDescriptionPropertyId, "ProviderDescription" },
    { UIA_OptimizeForVisualContentPropertyId, "OptimizeForVisualContent" },
    { UIA_LiveSettingPropertyId, "LiveSetting" },
    { UIA_IsPeripheralPropertyId, "IsPeripheral" },
    { UIA_PositionInSetPropertyId, "PositionInSet" },
    { UIA_SizeOfSetPropertyId, "SizeOfSet" },
    { UIA_LevelPropertyId, "Level" },
    { UIA_LandmarkTypePropertyId, "LandmarkType" },
    { UIA_LocalizedLandmarkTypePropertyId, "LocalizedLandmarkType" },
    { UIA_FullDescriptionPropertyId, "FullDescription" },
    { UIA_HeadingLevelPropertyId, "HeadingLevel" },
    { UIA_IsDialogPropertyId, "IsDialog" }
};

static const PropertyDef patternAvailableProperties[] = {
    { UIA_IsInvokePatternAvailablePropertyId, "InvokePattern" },
    { UIA_IsSelectionPatternAvailablePropertyId, "SelectionPattern" },
    { UIA_IsValuePatternAvailablePropertyId, "ValuePattern" },
    { UIA_IsRangeValuePatternAvailablePropertyId, "RangeValuePattern" },
    { UIA_IsScrollPatternAvailablePropertyId, "ScrollPattern" },
    { UIA_IsExpandCollapsePatternAvailablePropertyId, "ExpandCollapsePattern" },
    { UIA_IsGridPatternAvailablePropertyId, "GridPattern" },
    { UIA_IsGridItemPatternAvailablePropertyId, "GridItemPattern" },
    { UIA_IsMultipleViewPatternAvailablePropertyId, "MultipleViewPattern" },
    { UIA_IsWindowPatternAvailablePropertyId, "WindowPattern" },
    { UIA_IsSelectionItemPatternAvailablePropertyId, "SelectionItemPattern" },
    { UIA_IsDockPatternAvailablePropertyId, "DockPattern" },
    { UIA_IsTablePatternAvailablePropertyId, "TablePattern" },
    { UIA_IsTableItemPatternAvailablePropertyId, "TableItemPattern" },
    { UIA_IsTextPatternAvailablePropertyId, "TextPattern" },
    { UIA_IsTogglePatternAvailablePropertyId, "TogglePattern" },
    { UIA_IsTransformPatternAvailablePropertyId, "TransformPattern" },
    { UIA_IsScrollItemPatternAvailablePropertyId, "ScrollItemPattern" },
    { UIA_IsLegacyIAccessiblePatternAvailablePropertyId, "LegacyIAccessiblePattern" },
    { UIA_IsItemContainerPatternAvailablePropertyId, "ItemContainerPattern" },
    { UIA_IsVirtualizedItemPatternAvailablePropertyId, "VirtualizedItemPattern" },
    { UIA_IsSynchronizedInputPatternAvailablePropertyId, "SynchronizedInputPattern" },
    { UIA_IsAnnotationPatternAvailablePropertyId, "AnnotationPattern" },
    { UIA_IsTextPattern2AvailablePropertyId, "TextPattern2" },
    { UIA_IsStylesPatternAvailablePropertyId, "StylesPattern" },
    { UIA_IsSpreadsheetPatternAvailablePropertyId, "SpreadsheetPattern" },
    { UIA_IsSpreadsheetItemPatternAvailablePropertyId, "SpreadsheetItemPattern" },
    { UIA_IsTransformPattern2AvailablePropertyId, "TransformPattern2" },
    { UIA_IsTextChildPatternAvailablePropertyId, "TextChildPattern" },
    { UIA_IsDragPatternAvailablePropertyId, "DragPattern" },
    { UIA_IsDropTargetPatternAvailablePropertyId, "DropTargetPattern" },
    { UIA_IsTextEditPatternAvailablePropertyId, "TextEditPattern" },
    { UIA_IsCustomNavigationPatternAvailablePropertyId, "CustomNavigationPattern" },
    { UIA_IsSelectionPattern2AvailablePropertyId, "SelectionPattern2" }
};

// Unified helper to deserialize raw resolved VARIANT to JSON
json VariantToJson(const VARIANT& val) {
    switch (val.vt) {
        case VT_EMPTY:
        case VT_NULL:
            return nullptr;
        case VT_BOOL:
            return (val.boolVal == VARIANT_TRUE);
        case VT_I4:
            return val.lVal;
        case VT_UI4:
            return val.ulVal;
        case VT_I2:
            return val.iVal;
        case VT_R8:
            return val.dblVal;
        case VT_R4:
            return val.fltVal;
        case VT_BSTR:
            return val.bstrVal ? RpcHandlers::wstring_to_utf8(val.bstrVal) : "";
        case VT_UNKNOWN: {
            if (!val.punkVal) return nullptr;
            wil::com_ptr<IUIAutomationElement> elem;
            if (SUCCEEDED(val.punkVal->QueryInterface(IID_PPV_ARGS(&elem))) && elem) {
                return RpcHandlers::CacheElement(elem);
            }
            return "__COM_OBJECT__";
        }
        default:
            if (val.vt == (VT_ARRAY | VT_I4)) {
                json arr = json::array();
                long lBound = 0, uBound = 0;
                SafeArrayGetLBound(val.parray, 1, &lBound);
                SafeArrayGetUBound(val.parray, 1, &uBound);
                for (long i = lBound; i <= uBound; i++) {
                    int valInt = 0;
                    SafeArrayGetElement(val.parray, &i, &valInt);
                    arr.push_back(valInt);
                }
                return arr;
            }
            if (val.vt == (VT_ARRAY | VT_R8)) {
                json arr = json::array();
                long lBound = 0, uBound = 0;
                SafeArrayGetLBound(val.parray, 1, &lBound);
                SafeArrayGetUBound(val.parray, 1, &uBound);
                for (long i = lBound; i <= uBound; i++) {
                    double valDouble = 0;
                    SafeArrayGetElement(val.parray, &i, &valDouble);
                    arr.push_back(valDouble);
                }
                return arr;
            }
            return "__UNSUPPORTED_VT_TYPE_" + std::to_string(val.vt) + "__";
    }
}

json RpcHandlers::GetElement(const json& params) {
    try {
        if (!params.contains("element_id") || !elementCache.count(params["element_id"])) {
            return { {"error", "Invalid or missing element_id"} };
        }
        wil::com_ptr<IUIAutomationElement> target = elementCache[params["element_id"]];
        if (!target) {
            return { {"error", "Cached element pointer is null"} };
        }

        auto scope = UiaOperationScope::StartNew();
        UiaElement element = target.get();
    try {
        scope.BindInput(element);
    } catch (const std::exception& e) {
        std::string errMsg = "Exception in BindInput: " + std::string(e.what());
        throw std::runtime_error(errMsg);
    }

    // Bind standard UIA properties
    std::vector<UiaVariant> remoteProps;
    remoteProps.reserve(sizeof(standardProperties) / sizeof(standardProperties[0]));
    for (const auto& prop : standardProperties) {
        try {
            remoteProps.push_back(element.GetPropertyValue(prop.id));
            scope.BindResult(remoteProps.back());
        } catch (const std::exception& e) {
            std::string errMsg = "Exception binding property " + std::string(prop.name) + ": " + e.what();
            throw std::runtime_error(errMsg);
        }
    }

    // Bind pattern availability flags
    std::vector<UiaVariant> remotePatterns;
    remotePatterns.reserve(sizeof(patternAvailableProperties) / sizeof(patternAvailableProperties[0]));
    for (const auto& pat : patternAvailableProperties) {
        try {
            remotePatterns.push_back(element.GetPropertyValue(pat.id));
            scope.BindResult(remotePatterns.back());
        } catch (const std::exception& e) {
            std::string errMsg = "Exception binding pattern " + std::string(pat.name) + ": " + e.what();
            throw std::runtime_error(errMsg);
        }
    }

    HRESULT hr = S_OK;
    try {
        hr = scope.ResolveHr();
    } catch (const std::exception& e) {
        std::string errMsg = "Exception in ResolveHr: " + std::string(e.what());
        throw std::runtime_error(errMsg);
    }
    if (FAILED(hr)) {
        return { {"error", "Failed to resolve element properties via remote operation, hr=" + std::to_string(hr)} };
    }

    json properties_json = json::object();
    for (size_t i = 0; i < remoteProps.size(); ++i) {
        try {
            VARIANT val = remoteProps[i].get();
            properties_json[standardProperties[i].name] = VariantToJson(val);
        } catch (const std::exception& e) {
            std::string errMsg = "Exception getting property " + std::string(standardProperties[i].name) + ": " + e.what();
            throw std::runtime_error(errMsg);
        }
    }

    // Dynamic ControlType Int to String translation
    if (properties_json.contains("ControlType") && properties_json["ControlType"].is_number()) {
        int cTypeId = properties_json["ControlType"].get<int>();
        std::string cTypeStr = "ControlType.Unknown";
        switch (cTypeId) {
            case UIA_ButtonControlTypeId: cTypeStr = "ControlType.Button"; break;
            case UIA_CalendarControlTypeId: cTypeStr = "ControlType.Calendar"; break;
            case UIA_CheckBoxControlTypeId: cTypeStr = "ControlType.CheckBox"; break;
            case UIA_ComboBoxControlTypeId: cTypeStr = "ControlType.ComboBox"; break;
            case UIA_EditControlTypeId: cTypeStr = "ControlType.Edit"; break;
            case UIA_HyperlinkControlTypeId: cTypeStr = "ControlType.Hyperlink"; break;
            case UIA_ImageControlTypeId: cTypeStr = "ControlType.Image"; break;
            case UIA_ListItemControlTypeId: cTypeStr = "ControlType.ListItem"; break;
            case UIA_ListControlTypeId: cTypeStr = "ControlType.List"; break;
            case UIA_MenuControlTypeId: cTypeStr = "ControlType.Menu"; break;
            case UIA_MenuBarControlTypeId: cTypeStr = "ControlType.MenuBar"; break;
            case UIA_MenuItemControlTypeId: cTypeStr = "ControlType.MenuItem"; break;
            case UIA_ProgressBarControlTypeId: cTypeStr = "ControlType.ProgressBar"; break;
            case UIA_RadioButtonControlTypeId: cTypeStr = "ControlType.RadioButton"; break;
            case UIA_ScrollBarControlTypeId: cTypeStr = "ControlType.ScrollBar"; break;
            case UIA_SliderControlTypeId: cTypeStr = "ControlType.Slider"; break;
            case UIA_SpinnerControlTypeId: cTypeStr = "ControlType.Spinner"; break;
            case UIA_StatusBarControlTypeId: cTypeStr = "ControlType.StatusBar"; break;
            case UIA_TabControlTypeId: cTypeStr = "ControlType.Tab"; break;
            case UIA_TabItemControlTypeId: cTypeStr = "ControlType.TabItem"; break;
            case UIA_TextControlTypeId: cTypeStr = "ControlType.Text"; break;
            case UIA_ToolBarControlTypeId: cTypeStr = "ControlType.ToolBar"; break;
            case UIA_ToolTipControlTypeId: cTypeStr = "ControlType.ToolTip"; break;
            case UIA_TreeControlTypeId: cTypeStr = "ControlType.TreeView"; break;
            case UIA_TreeItemControlTypeId: cTypeStr = "ControlType.TreeItem"; break;
            case UIA_CustomControlTypeId: cTypeStr = "ControlType.Custom"; break;
            case UIA_GroupControlTypeId: cTypeStr = "ControlType.Group"; break;
            case UIA_ThumbControlTypeId: cTypeStr = "ControlType.Thumb"; break;
            case UIA_DataGridControlTypeId: cTypeStr = "ControlType.DataGrid"; break;
            case UIA_DataItemControlTypeId: cTypeStr = "ControlType.DataItem"; break;
            case UIA_DocumentControlTypeId: cTypeStr = "ControlType.Document"; break;
            case UIA_SplitButtonControlTypeId: cTypeStr = "ControlType.SplitButton"; break;
            case UIA_WindowControlTypeId: cTypeStr = "ControlType.Window"; break;
            case UIA_PaneControlTypeId: cTypeStr = "ControlType.Pane"; break;
            case UIA_HeaderControlTypeId: cTypeStr = "ControlType.Header"; break;
            case UIA_HeaderItemControlTypeId: cTypeStr = "ControlType.HeaderItem"; break;
            case UIA_TableControlTypeId: cTypeStr = "ControlType.Table"; break;
            case UIA_TitleBarControlTypeId: cTypeStr = "ControlType.TitleBar"; break;
            case UIA_SeparatorControlTypeId: cTypeStr = "ControlType.Separator"; break;
            case UIA_SemanticZoomControlTypeId: cTypeStr = "ControlType.SemanticZoom"; break;
            case UIA_AppBarControlTypeId: cTypeStr = "ControlType.AppBar"; break;
        }
        properties_json["ControlTypeString"] = cTypeStr;
    }

    // Dynamic BoundingRectangle SafeArray [x, y, w, h] list translation
    if (properties_json.contains("BoundingRectangle") && properties_json["BoundingRectangle"].is_array()) {
        auto arr = properties_json["BoundingRectangle"];
        if (arr.size() == 4) {
            double left = arr[0].get<double>();
            double top = arr[1].get<double>();
            double width = arr[2].get<double>();
            double height = arr[3].get<double>();
            properties_json["BoundingRectangle"] = { left, top, width, height };
        }
    } else {
        UiaOperationAbstraction::UiaRect rect = element.GetBoundingRectangle();
        auto scope2 = UiaOperationScope::StartNew();
        scope2.BindInput(element);
        scope2.BindResult(rect);
        if (SUCCEEDED(scope2.ResolveHr())) {
            auto bounds = static_cast<winrt::Windows::Foundation::Rect>(rect);
            properties_json["BoundingRectangle"] = { bounds.X, bounds.Y, bounds.Width, bounds.Height };
        }
    }

    json patterns_json = json::array();
    for (size_t i = 0; i < remotePatterns.size(); ++i) {
        try {
            VARIANT val = remotePatterns[i].get();
            if (val.vt == VT_BOOL && val.boolVal == VARIANT_TRUE) {
                patterns_json.push_back(patternAvailableProperties[i].name);
            }
        } catch (const std::exception& e) {
            std::string errMsg = "Exception getting pattern " + std::string(patternAvailableProperties[i].name) + ": " + e.what();
            throw std::runtime_error(errMsg);
        }
    }

        return {
            {"element_id", params["element_id"]},
            {"Properties", properties_json},
            {"Patterns", patterns_json}
        };
    } catch (const std::exception& e) {
        return { {"error", "Exception in GetElement: " + std::string(e.what())} };
    } catch (...) {
        return { {"error", "Unknown exception in GetElement"} };
    }
}

json RpcHandlers::SetElement(const json& params) {
    if (!params.contains("element_id") || !elementCache.count(params["element_id"])) {
        return { {"error", "Invalid or missing element_id"} };
    }
    if (!params.contains("action")) {
        return { {"error", "Missing action parameter"} };
    }
    std::string action = params["action"].get<std::string>();
    wil::com_ptr<IUIAutomationElement> target = elementCache[params["element_id"]];
    if (!target) {
        return { {"error", "Cached element pointer is null"} };
    }

    auto scope = UiaOperationScope::StartNew();
    UiaElement element = target.get();
    scope.BindInput(element);

    if (action == "invoke") {
        UiaInvokePattern pattern = element.GetInvokePattern();
        pattern.Invoke();
    }
    else if (action == "set_value") {
        if (!params.contains("value")) {
            return { {"error", "Missing value parameter for set_value action"} };
        }
        std::string valStr = params["value"].get<std::string>();
        std::wstring valW = utf8_to_wstring(valStr);
        UiaValuePattern pattern = element.GetValuePattern();
        pattern.SetValue(UiaString(valW.c_str()));
    }
    else if (action == "toggle") {
        UiaTogglePattern pattern = element.GetTogglePattern();
        pattern.Toggle();
    }
    else if (action == "select") {
        UiaSelectionItemPattern pattern = element.GetSelectionItemPattern();
        pattern.Select();
    }
    else if (action == "expand") {
        UiaExpandCollapsePattern pattern = element.GetExpandCollapsePattern();
        pattern.Expand();
    }
    else if (action == "collapse") {
        UiaExpandCollapsePattern pattern = element.GetExpandCollapsePattern();
        pattern.Collapse();
    }
    else if (action == "scroll") {
        UiaScrollPattern pattern = element.GetScrollPattern();
        double hPercent = params.contains("horizontal_percent") ? params["horizontal_percent"].get<double>() : UIA_ScrollPatternNoScroll;
        double vPercent = params.contains("vertical_percent") ? params["vertical_percent"].get<double>() : UIA_ScrollPatternNoScroll;
        pattern.SetScrollPercent(UiaDouble(hPercent), UiaDouble(vPercent));
    }
    else {
        return { {"error", "Unknown action: " + action} };
    }

    HRESULT hr = scope.ResolveHr();
    if (FAILED(hr)) {
        return { {"error", "Failed to execute action " + action + " via remote operation, hr=" + std::to_string(hr)} };
    }

    return { {"success", true} };
}

json RpcHandlers::GetFocusedElement() {
    try {
        if (!g_automation) {
            return { {"error", "UIA Automation instance is uninitialized"} };
        }
        
        wil::com_ptr<IUIAutomationElement> focusedElement;
        HRESULT hr = g_automation->GetFocusedElement(&focusedElement);
        if (FAILED(hr) || !focusedElement) {
            return { {"error", "Failed to get focused element, hr=" + std::to_string(hr)} };
        }
        
        std::string id = CacheElement(focusedElement);
        json getParams = { {"element_id", id} };
        return GetElement(getParams);
    } catch (const std::exception& e) {
        return { {"error", "Exception in GetFocusedElement: " + std::string(e.what())} };
    } catch (...) {
        return { {"error", "Unknown exception in GetFocusedElement"} };
    }
}

json RpcHandlers::FindElement(const json& params) {
    if (!g_automation) {
        return { {"error", "UIA Automation instance is uninitialized"} };
    }
    
    wil::com_ptr<IUIAutomationElement> root;
    g_automation->GetRootElement(&root);
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
        
        if (by == "Name" || by == "name") {
            g_automation->CreatePropertyCondition(UIA_NamePropertyId, var, &condition);
        } else if (by == "AutomationId" || by == "id" || by == "uia_id") {
            g_automation->CreatePropertyCondition(UIA_AutomationIdPropertyId, var, &condition);
        } else if (by == "ClassName" || by == "class_name") {
            g_automation->CreatePropertyCondition(UIA_ClassNamePropertyId, var, &condition);
        }
    }
    
    if (!condition) {
        return { {"error", "Must provide valid 'by' ('Name', 'AutomationId', 'ClassName') and 'value' to find_element"} };
    }
    
    wil::com_ptr<IUIAutomationElement> foundElement;
    root->FindFirst(TreeScope_Subtree, condition.get(), &foundElement);
    if (!foundElement) {
        return { {"error", "Element not found"} };
    }
    
    std::string id = CacheElement(foundElement);
    json getParams = { {"element_id", id} };
    return GetElement(getParams);
}

json RpcHandlers::FindAllElements(const json& params) {
    if (!g_automation) {
        return { {"error", "UIA Automation instance is uninitialized"} };
    }
    
    wil::com_ptr<IUIAutomationElement> root;
    g_automation->GetRootElement(&root);
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
        
        if (by == "Name" || by == "name") {
            g_automation->CreatePropertyCondition(UIA_NamePropertyId, var, &condition);
        } else if (by == "AutomationId" || by == "id" || by == "uia_id") {
            g_automation->CreatePropertyCondition(UIA_AutomationIdPropertyId, var, &condition);
        } else if (by == "ClassName" || by == "class_name") {
            g_automation->CreatePropertyCondition(UIA_ClassNamePropertyId, var, &condition);
        }
    }
    
    if (!condition) {
        return { {"error", "Must provide valid 'by' ('Name', 'AutomationId', 'ClassName') and 'value'"} };
    }
    
    wil::com_ptr<IUIAutomationElementArray> foundElements;
    root->FindAll(TreeScope_Subtree, condition.get(), &foundElements);
    if (!foundElements) {
        return { {"elements", json::array()} };
    }
    
    int length = 0;
    foundElements->get_Length(&length);
    json elements = json::array();
    for (int i = 0; i < length; ++i) {
        wil::com_ptr<IUIAutomationElement> element;
        foundElements->GetElement(i, &element);
        if (element) {
            std::string id = CacheElement(element);
            json getParams = { {"element_id", id} };
            elements.push_back(GetElement(getParams));
        }
    }
    return { {"elements", elements} };
}

// Recursive helper for tree walking
json WalkElementTreeRecursive(wil::com_ptr<IUIAutomationElement> current, wil::com_ptr<IUIAutomationTreeWalker> walker, int maxDepth, int currentDepth) {
    if (!current || currentDepth > maxDepth) return nullptr;
    
    std::string id = RpcHandlers::CacheElement(current);
    json getParams = { {"element_id", id} };
    json elementProfile = RpcHandlers::GetElement(getParams);
    
    json children = json::array();
    wil::com_ptr<IUIAutomationElement> child;
    walker->GetFirstChildElement(current.get(), &child);
    while (child) {
        json childNode = WalkElementTreeRecursive(child, walker, maxDepth, currentDepth + 1);
        if (!childNode.is_null()) {
            children.push_back(childNode);
        }
        wil::com_ptr<IUIAutomationElement> next;
        walker->GetNextSiblingElement(child.get(), &next);
        child = next;
    }
    
    elementProfile["children"] = children;
    return elementProfile;
}

json RpcHandlers::GetElementTree(const json& params) {
    if (!g_automation) {
        return { {"error", "UIA Automation instance is uninitialized"} };
    }
    
    wil::com_ptr<IUIAutomationElement> root;
    if (params.contains("element_id") && elementCache.count(params["element_id"])) {
        root = elementCache[params["element_id"]];
    } else {
        g_automation->GetRootElement(&root);
    }
    
    int depth = params.contains("depth") ? params["depth"].get<int>() : 3;
    std::string viewType = params.contains("view_type") ? params["view_type"].get<std::string>() : "control";
    
    wil::com_ptr<IUIAutomationTreeWalker> walker;
    if (viewType == "raw") {
        g_automation->get_RawViewWalker(&walker);
    } else if (viewType == "content") {
        g_automation->get_ContentViewWalker(&walker);
    } else {
        g_automation->get_ControlViewWalker(&walker);
    }
    
    if (!walker) {
        return { {"error", "Failed to retrieve tree walker"} };
    }
    
    json tree = WalkElementTreeRecursive(root, walker, depth, 1);
    return { {"tree", tree} };
}

json RpcHandlers::GetChildrenElements(const json& params) {
    if (!params.contains("element_id") || !elementCache.count(params["element_id"])) {
        return { {"error", "Invalid or missing element_id"} };
    }
    wil::com_ptr<IUIAutomationElement> target = elementCache[params["element_id"]];
    if (!target) return { {"children", json::array()} };
    
    if (!g_automation) {
        return { {"error", "UIA Automation instance is uninitialized"} };
    }
    
    wil::com_ptr<IUIAutomationTreeWalker> walker;
    std::string viewType = params.contains("view_type") ? params["view_type"].get<std::string>() : "control";
    if (viewType == "raw") {
        g_automation->get_RawViewWalker(&walker);
    } else if (viewType == "content") {
        g_automation->get_ContentViewWalker(&walker);
    } else {
        g_automation->get_ControlViewWalker(&walker);
    }
    
    json children = json::array();
    wil::com_ptr<IUIAutomationElement> child;
    walker->GetFirstChildElement(target.get(), &child);
    while (child) {
        std::string id = CacheElement(child);
        json getParams = { {"element_id", id} };
        children.push_back(GetElement(getParams));
        wil::com_ptr<IUIAutomationElement> next;
        walker->GetNextSiblingElement(child.get(), &next);
        child = next;
    }
    return { {"children", children} };
}

json RpcHandlers::GetParentElement(const json& params) {
    if (!params.contains("element_id") || !elementCache.count(params["element_id"])) {
        return { {"error", "Invalid or missing element_id"} };
    }
    wil::com_ptr<IUIAutomationElement> target = elementCache[params["element_id"]];
    if (!target) return nullptr;
    
    if (!g_automation) {
        return { {"error", "UIA Automation instance is uninitialized"} };
    }
    
    wil::com_ptr<IUIAutomationTreeWalker> walker;
    std::string viewType = params.contains("view_type") ? params["view_type"].get<std::string>() : "control";
    if (viewType == "raw") {
        g_automation->get_RawViewWalker(&walker);
    } else if (viewType == "content") {
        g_automation->get_ContentViewWalker(&walker);
    } else {
        g_automation->get_ControlViewWalker(&walker);
    }
    
    wil::com_ptr<IUIAutomationElement> parent;
    walker->GetParentElement(target.get(), &parent);
    if (!parent) return nullptr;
    
    std::string id = CacheElement(parent);
    json getParams = { {"element_id", id} };
    return GetElement(getParams);
}

json RpcHandlers::GetSiblingElements(const json& params) {
    if (!params.contains("element_id") || !elementCache.count(params["element_id"])) {
        return { {"error", "Invalid or missing element_id"} };
    }
    wil::com_ptr<IUIAutomationElement> target = elementCache[params["element_id"]];
    if (!target) return { {"siblings", json::array()} };
    
    if (!g_automation) {
        return { {"error", "UIA Automation instance is uninitialized"} };
    }
    
    wil::com_ptr<IUIAutomationTreeWalker> walker;
    std::string viewType = params.contains("view_type") ? params["view_type"].get<std::string>() : "control";
    if (viewType == "raw") {
        g_automation->get_RawViewWalker(&walker);
    } else if (viewType == "content") {
        g_automation->get_ContentViewWalker(&walker);
    } else {
        g_automation->get_ControlViewWalker(&walker);
    }
    
    wil::com_ptr<IUIAutomationElement> parent;
    walker->GetParentElement(target.get(), &parent);
    if (!parent) return { {"siblings", json::array()} };
    
    json siblings = json::array();
    wil::com_ptr<IUIAutomationElement> child;
    walker->GetFirstChildElement(parent.get(), &child);
    while (child) {
        if (child.get() != target.get()) {
            std::string id = CacheElement(child);
            json getParams = { {"element_id", id} };
            siblings.push_back(GetElement(getParams));
        }
        wil::com_ptr<IUIAutomationElement> next;
        walker->GetNextSiblingElement(child.get(), &next);
        child = next;
    }
    return { {"siblings", siblings} };
}
