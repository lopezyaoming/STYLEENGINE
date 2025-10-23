import requests

url = 'https://api.runcomfy.net/prod/v1/deployments/f0c32b81-8ea3-40bf-887f-d41c9a4d5ef5/inference'
headers = {
  'Authorization': 'Bearer YOUR_API_TOKEN',
  'Content-Type': 'application/json'
}
payload = { 'overrides': {
  "15": {
    "inputs": {
      "image": "https://example.com/new-image.jpg or data:image/jpeg;base64,/9j/4AAQSkZJRgA..."
    }
  },
  "39": {
    "inputs": {
      "value": "Nighttime view of a dense dystopian gotham city, dramatic lighting, dark hues and sketchy corridors, noir, damp after heavy rain, photorrealistic"
    }
  }
} }
requests.post(url, headers=headers, json=payload)