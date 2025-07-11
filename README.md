# Posture Detection App

**Deployed App:** [https://posture-detection-app-dun.vercel.app](https://posture-detection-app-dun.vercel.app)  
**Demo Video:** [https://youtu.be/nZ2zzf7IOgA](https://youtu.be/nZ2zzf7IOgA)

## Tech Stack

### Frontend
- **React (18.x):** User interface framework
- **Axios:** HTTP client for API requests
- **React-Webcam:** Webcam integration
- **CSS3:** Styling and responsive design
- **Vercel:** Frontend deployment platform

### Backend
- **Python (3.8+):** Backend programming language
- **Flask:** Web framework
- **MediaPipe:** Google’s pose detection library
- **OpenCV:** Computer vision processing
- **NumPy:** Numerical computations
- **Pillow:** Image processing
- **Gunicorn:** WSGI HTTP server
- **Flask-CORS:** Cross-origin resource sharing
- **Amazon Web Services (AWS):** Backend deployment services

### Computer Vision
- **MediaPipe Pose:** 33-point pose landmark detection
- **Custom Angle Calculations:** Rule-based posture assessment
- **Real-time Processing:** Efficient frame-by-frame analysis

---

## Local Setup Instructions

### Prerequisites
- Node.js (v14+ recommended)
- Python 3.8+
- `pip` (Python package manager)

---

## Backend Setup

1. **Clone the repository:**
    ```bash
    git clone [your-repo-url]
    cd posture-detection-app
    ```

2. **Navigate to backend directory:**
    ```bash
    cd backend
    ```

3. **Create a virtual environment:**
    ```bash
    python -m venv venv
    ```

    - **On Windows:**
        ```bash
        venv\Scripts\activate
        ```
    - **On macOS/Linux:**
        ```bash
        source venv/bin/activate
        ```

4. **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5. **Run the Flask server:**
    ```bash
    python app.py
    ```

The backend will be available at: [http://localhost:5000](http://localhost:5000)

---

## Frontend Setup

1. **Navigate to frontend directory:**
    ```bash
    cd frontend/posture-app
    ```

2. **Install Node.js dependencies:**
    ```bash
    npm install
    ```

3. **Start the development server:**
    ```bash
    npm start
    ```

The frontend will be available at: [http://localhost:3000](http://localhost:3000)

---

## Environment Configuration

Create a `.env` file in the `frontend/posture-app` directory:

```env
REACT_APP_API_URL=http://localhost:5000
