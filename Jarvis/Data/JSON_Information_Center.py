import json

File_Name1 = r"F:/RunningProjects/JarvisControlSystem/Jarvis/Data\Data_Information_Value/data1"
data1 = {
    "activating_jarvis": ['hi', 'hi jarvis', 'jarvis', 'start jarvis', 'jarvis start'],
    "deactivating_jarvis": ['jarvis close', 'close jarvis', 'jarvis stop', 'stop jarvis'],

    "typing_jarvies": ['start typing', 'typing start', 'activate typing', 'typing activate'],
    "stop_typing_jarvies": ['stop typing', 'typing stop', 'deactivate typing', 'typing deactivateactivate'],

    "presskey_jarvis": ['press'],
    "presskey_jarvis1": ['press', 'press key', 'key press'],

    "holdkey_jarvis": ['hold', 'holdkey', 'hold key', 'keydown'],
    "relasekey_jarvis": ['release', 'releasekey', 'release key'],

    "OpenApp_jarvis": ['open', 'start', 'run'],
    "CloseApp_jarvis": ['close', 'exit', 'terminate'],

    "SearchApp_jarvis": ['search', 'find', 'windows search', 'window search', 'search windows', 'search window',
                         'search by windows', 'search by window'],

    "WindowsSearchBarAccess_jarvis": ['open by search', 'open by windows', 'open by windows search'],

    "closeByWindows_jarvis": ['stop by search', 'stop by windows', 'stop by windows search'],

    "windows_Set": ['set brightness level', 'set brightness', 'set light', 'increase brightness',
                    'increase brightness level',
                    'increase brightness in windows', 'increase brightness in windows', 'change brightness in windows',
                    'adjust brightness',
                    'reduce brightness'],

    "stop_typing_jarvies111": ["D1"],

}


# Saving as a JSON file:
def saveData(_fileName, data):
    with open(_fileName + ".json", "w") as f:
        json.dump(data, f, indent=4)


# Loading from a JSON file:
def loadDate(_fileName):
    try:
        with open(_fileName + ".json", "r") as f:
            data = json.load(f)
        return data
        # print(data)
    except Exception:
        with open(_fileName + ".json", "w") as f:
            json.dump({}, f)

        with open(_fileName + ".json", "r") as f:
            data = json.load(f)
        return data
    return data


# Adding a new key-value pair:
def AddDate(_fileName, _key, _value):
    _value = list(set(_value))
    data = loadDate(_fileName)
    if type([""]) == type(_value):
        if _key in data:
            data[_key] = list(set(_value + data[_key]))
        else:
            data[_key] = _value
        saveData(_fileName, data)
    else:
        if _key in data:
            if _value not in data[_key]:
                data[_key].append(_value)
                saveData(_fileName, data)
        else:
            data[_key] = [_value]
            saveData(_fileName, data)
    return data


def AddCountDate(_fileName, _key, _value):
    data = loadDate(_fileName)
    if type([""]) == type(_value):
        if _key in data:
            data[_key] = _value + data[_key]
        else:
            data[_key] = _value
        saveData(_fileName, data)
    else:
        if _key in data:
            if _value not in data[_key]:
                data[_key].append(_value)
                saveData(_fileName, data)
        else:
            data[_key] = [_value]
            saveData(_fileName, data)
    return data

# AddDate(_fileName=File_Name1, _key="abcd", _value=["0", 'sd'])
