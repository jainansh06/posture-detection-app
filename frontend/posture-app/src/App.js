import React, { useState, useRef, useEffect } from 'react';
import './App.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [backendStatus, setBackendStatus] = useState('checking');
  const [useWebcam, setUseWebcam] = useState(false);
  const [stream, setStream] = useState(null);
  
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    checkBackendStatus();
  }, []);

  const checkBackendStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/health`);
      if (response.ok) {
        setBackendStatus('connected');
      } else {
        setBackendStatus('disconnected');
      }
    } catch (error) {
      setBackendStatus('disconnected');
    }
  };

  const startWebcam = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 }
      });
      
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        setStream(mediaStream);
        setUseWebcam(true);
        setError(null);
      }
    } catch (err) {
      setError('Failed to access webcam. Please check permissions.');
    }
  };

  const stopWebcam = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
    }
    setUseWebcam(false);
  };

  const captureImage = () => {
    if (videoRef.current && canvasRef.current) {
      const canvas = canvasRef.current;
      const video = videoRef.current;
      
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0);
      
      return canvas.toDataURL('image/jpeg');
    }
    return null;
  };

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        setError('File too large. Please select a file smaller than 5MB.');
        return;
      }
      
      if (!file.type.startsWith('image/')) {
        setError('Please select an image file.');
        return;
      }
      
      setSelectedFile(file);
      setResults(null);
      setError(null);
    }
  };

  const analyzeImage = async (imageData = null) => {
    setLoading(true);
    setError(null);
    setResults(null);

    try {
      let response;
      
      if (imageData) {
        // Webcam capture - use base64 endpoint
        response = await fetch(`${API_URL}/analyze_base64`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ image: imageData })
        });
      } else {
        // File upload
        if (!selectedFile) {
          setError('Please select an image first.');
          return;
        }
        
        const formData = new FormData();
        formData.append('image', selectedFile);
        
        response = await fetch(`${API_URL}/analyze`, {
          method: 'POST',
          body: formData
        });
      }

      const result = await response.json();
      
      if (result.success) {
        setResults(result);
      } else {
        setError(result.error || 'Analysis failed');
      }
    } catch (err) {
      setError('Failed to analyze image. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleWebcamAnalyze = () => {
    const imageData = captureImage();
    if (imageData) {
      analyzeImage(imageData);
    } else {
      setError('Failed to capture image from webcam.');
    }
  };

  const resetApp = () => {
    setSelectedFile(null);
    setResults(null);
    setError(null);
    stopWebcam();
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🧘‍♂️ Posture Checker</h1>
        <p>Upload an image or use webcam to analyze your posture</p>
        <div className={`status ${backendStatus}`}>
          Status: {backendStatus === 'connected' ? '✅ Connected' : '❌ Disconnected'}
        </div>
      </header>

      <main className="main-content">
        <div className="upload-section">
          <div className="mode-selector">
            <button 
              onClick={() => setUseWebcam(false)}
              className={!useWebcam ? 'active' : ''}
            >
              📁 Upload Image
            </button>
            <button 
              onClick={() => setUseWebcam(true)}
              className={useWebcam ? 'active' : ''}
            >
              📷 Use Webcam
            </button>
          </div>

          {!useWebcam ? (
            <div className="file-upload">
              <input
                type="file"
                accept="image/*"
                onChange={handleFileSelect}
                ref={fileInputRef}
                className="file-input"
              />
              {selectedFile && (
                <div className="file-info">
                  <p>✅ {selectedFile.name}</p>
                  <p>Size: {(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
              )}
              <button
                onClick={() => analyzeImage()}
                disabled={!selectedFile || loading || backendStatus !== 'connected'}
                className="analyze-btn"
              >
                {loading ? '🔄 Analyzing...' : '🔍 Analyze Posture'}
              </button>
            </div>
          ) : (
            <div className="webcam-section">
              {!stream ? (
                <button onClick={startWebcam} className="webcam-btn">
                  📹 Start Webcam
                </button>
              ) : (
                <div className="webcam-container">
                  <video ref={videoRef} autoPlay playsInline className="webcam-video" />
                  <canvas ref={canvasRef} style={{ display: 'none' }} />
                  <div className="webcam-controls">
                    <button onClick={handleWebcamAnalyze} disabled={loading} className="analyze-btn">
                      {loading ? '🔄 Analyzing...' : '📸 Capture & Analyze'}
                    </button>
                    <button onClick={stopWebcam} className="stop-btn">
                      ⏹️ Stop
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {(selectedFile || results) && (
            <button onClick={resetApp} className="reset-btn">
              🔄 Reset
            </button>
          )}
        </div>

        {error && (
          <div className="error-message">
            <h3>❌ Error</h3>
            <p>{error}</p>
          </div>
        )}

        {results && (
          <div className="results-section">
            <h3>📊 Analysis Results</h3>
            <div className={`score-card ${results.posture_rating.toLowerCase()}`}>
              <div className="score">
                <span className="score-number">{results.posture_score}</span>
                <span className="score-label">Posture Score</span>
              </div>
              <div className="rating">
                <span className="rating-label">Rating:</span>
                <span className="rating-value">{results.posture_rating}</span>
              </div>
            </div>
            
            {results.issues && results.issues.length > 0 && (
              <div className="issues-section">
                <h4>⚠️ Issues Found:</h4>
                <ul>
                  {results.issues.map((issue, index) => (
                    <li key={index}>{issue}</li>
                  ))}
                </ul>
              </div>
            )}
            
            {results.issues && results.issues.length === 0 && (
              <div className="good-posture">
                <h4>✅ Great! No major posture issues detected.</h4>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
