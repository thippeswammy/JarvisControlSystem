import requests

# Specify the URL of your Windows_icon device's Device Portal
device_portal_url = 'http://<device-ip-address>/api'

# Specify the username and password for authentication
username = 'thipp'
password = '9900'

# Disable Wi-Fi using the Device Portal API
url = f'{device_portal_url}/interfaces/wifi/state'
headers = {'Content-Type': 'application/json'}
data = {'state': False}
response = requests.post(url, headers=headers, auth=(username, password), json=data)

# Check the response status
if response.status_code == 200:
    print('Wi-Fi disabled successfully.')
else:
    print('Failed to disable Wi-Fi.')
    print('Response:', response.text)
