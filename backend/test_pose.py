import requests
import json

def test_with_image(image_path):
    # Use your actual deployed backend URL
    url = 'https://13.53.126.177:5000/analyze_pose'
    
    try:
        with open(image_path, 'rb') as f:
            files = {'image': f}
            response = requests.post(url, files=files)
        
        print("Status Code:", response.status_code)
        print("Response:", json.dumps(response.json(), indent=2))
        
    except FileNotFoundError:
        print(f"Image file '{image_path}' not found!")
    except Exception as e:
        print(f"Error: {e}")

def test_health():
    """Test if the deployed server is running"""
    try:
        response = requests.get('https://13.53.126.177:5000/health')
        print("Health check:", response.json())
        return True
    except Exception as e:
        print(f"Server not running: {e}")
        return False

if __name__ == "__main__":
    print("Testing deployed server health...")
    if test_health():
        print("\nTesting pose detection...")
        test_with_image('test_image.jpg')
