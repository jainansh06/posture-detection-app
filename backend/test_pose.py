import requests
import json

def test_with_image(image_path):
    url = 'http://localhost:5000/analyze_pose'
    
    try:
        with open(image_path, 'rb') as f:
            files = {'image': f}
            response = requests.post(url, files=files)
        
        print("Status Code:", response.status_code)
        print("Response:", json.dumps(response.json(), indent=2))
        
    except FileNotFoundError:
        print(f"Image file '{image_path}' not found!")
        print("Make sure your image is in the same folder as this script")
    except Exception as e:
        print(f"Error: {e}")

def test_health():
    """Test if the server is running"""
    try:
        response = requests.get('http://localhost:5000/health')
        print("Health check:", response.json())
        return True
    except Exception as e:
        print(f"Server not running: {e}")
        return False

if __name__ == "__main__":
    print("Testing server health...")
    if test_health():
        print("\nTesting pose detection...")
        # Replace 'test_image.jpg' with your actual image filename
        test_with_image('test_image.jpg')