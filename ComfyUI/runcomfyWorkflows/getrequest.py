import requests

url = 'https://api.runcomfy.net/prod/v1/deployments/1c6fa9a6-f60a-4e89-863d-40b03ad2564e/requests/{request_id}/result'
headers = { 'Authorization': 'Bearer YOUR_API_TOKEN' }
requests.get(url, headers=headers)