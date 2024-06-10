# import os
# import comtypes
# from comtypes.client import CreateObject
# from comtypes.gen import searchManager
# comtypes.CoInitialize()
# searchManager = CreateObject(searchManager.SearchManager)
# folderPath = os.path.join("C:", "Users", "your_username", "Documents")
# searchData = searchManager.FolderSearchData(searchFolder=folderPath)
# searchQuery = searchManager.SearchFolderQuery(text="notpa")
# # Add additional properties like file types, size restrictions, etc.
# searchFolder = searchManager.CreateSearchFolder(searchData, searchQuery)
# searchFolder.DoSearch()
# for resultItem in searchFolder.Results:
#     # Access file properties like path, name, size, etc.
#     print(resultItem.Properties.Path)
# searchFolder.Close()
# comtypes.CoUninitialize()
