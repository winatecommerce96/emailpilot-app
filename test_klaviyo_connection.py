import requests

url = "http://127.0.0.1:8000/api/mcp/clients/klaviyo-client-1/test"

try:
    response = requests.post(url, json={})
    response.raise_for_status()  # Raise an exception for bad status codes
    if response.status_code == 200:
        print("Successfully connected to the Klaviyo API via MCP.")
        print("Response JSON:")
        print(response.json())
    else:
        print(f"Failed to connect. Status code: {response.status_code}")
        print("Response Text:")
        print(response.text)

except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")
