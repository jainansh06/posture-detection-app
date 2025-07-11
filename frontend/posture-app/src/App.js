import React, { useState, useRef, useCallback, useEffect } from 'react';
import Webcam from 'react-webcam';
import axios from 'axios';
import { Upload } from 'lucide-react';

const API_BASE_URL = process.env.REACT_APP_API_URL || 
  (process.env.NODE_ENV === 'production' 
    ? 'https://posture-detection-app-3ih3.onrender.com' 
    : 'http://localhost:5000');

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [analysisType, setAnalysisType] = useState('image');
  const [inputMode, setInputMode] = useState('upload');
  const [postureType, setPostureType] = useState('sitting');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [webcamActive, setWebcamActive] = useState(false);
  const [backendStatus, setBackendStatus] = useState('checking');
  const [uploadedVideo, setUploadedVideo] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const fileInputRef = useRef(null);
  const webcamRef = useRef(null);

  useEffect(() => {
    const testBackendConnection = async () => {
      try {
        setBackendStatus('checking');
        const response = await axios.get(`${API_BASE_URL}/`, {
          timeout: 10000,
          headers: {
            'Content-Type': 'application/json',
          }
        });
        setBackendStatus('connected');
        console.log('Backend connection successful:', response.data);
      } catch (err) {
        setBackendStatus('disconnected');
        console.error('Backend connection failed:', err.message);
        
        if (err.code === 'ECONNABORTED') {
          console.error('Request timed out - backend might be starting up');
        } else if (err.code === 'ERR_NETWORK') {
          console.error('Network error - check if backend is running');
        }
      }
    };

    testBackendConnection();
  }, []);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      if (file.size > 10 * 1024 * 1024) {
        setError('File size too large. Please select a file smaller than 10MB.');
        return;
      }

      const isImage = file.type.startsWith('image/');
      const isVideo = file.type.startsWith('video/');

      if (analysisType === 'image' && !isImage) {
        setError('Please select an image file for image analysis');
        return;
      }

      if (analysisType === 'video' && !isVideo) {
        setError('Please select a video file for video analysis');
        return;
      }

      setSelectedFile(file);
      setResults(null);
      setError(null);
    }
  };

  const handleAnalysisTypeChange = (event) => {
    setAnalysisType(event.target.value);
    setSelectedFile(null);
    setResults(null);
    setError(null);
    setUploadedVideo(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handlePostureTypeChange = (event) => {
    setPostureType(event.target.value);
    setResults(null);
    setError(null);
  };

  const analyzeImage = useCallback(async (file) => {
    const formData = new FormData();
    formData.append('image', file);
    formData.append('posture_type', postureType);

    const response = await axios.post(`${API_BASE_URL}/analyze_pose`, formData, {
      headers: { 
        'Content-Type': 'multipart/form-data',
      },
      timeout: 30000,
      withCredentials: false,
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        console.log(`Upload Progress: ${percentCompleted}%`);
      }
    });
    return response.data;
  }, [postureType]);

  const analyzeVideo = useCallback(async (file) => {
    const formData = new FormData();
    formData.append('video', file);
    formData.append('posture_type', postureType);

    const response = await axios.post(`${API_BASE_URL}/analyze_video`, formData, {
      headers: { 
        'Content-Type': 'multipart/form-data',
      },
      timeout: 120000,
      withCredentials: false,
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        console.log(`Upload Progress: ${percentCompleted}%`);
      }
    });
    return response.data;
  }, [postureType]);

  const captureAndAnalyze = useCallback(async () => {
    if (!webcamRef.current) {
      setError('Webcam not available');
      return;
    }

    const imageSrc = webcamRef.current.getScreenshot();
    if (!imageSrc) {
      setError('Failed to capture image from webcam');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await fetch(imageSrc);
      const blob = await response.blob();
      const file = new File([blob], 'webcam-capture.jpg', { type: 'image/jpeg' });
      const result = await analyzeImage(file);
      setResults(result);
    } catch (err) {
      console.error('Capture and analyze error:', err);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [analyzeImage]);

  const getErrorMessage = (err) => {
    if (err.response?.data?.error) {
      return err.response.data.error;
    }

    if (err.code === 'ECONNABORTED') {
      return 'Request timed out. Please try again.';
    }

    if (err.code === 'ERR_NETWORK') {
      return 'Network error. Please check your connection and ensure the backend is running.';
    }

    if (err.message) {
      return err.message;
    }

    return 'Analysis failed. Please try again.';
  };

  const handleAnalyze = async () => {
    if (backendStatus === 'disconnected') {
      setError('Backend is not connected. Please check if the server is running.');
      return;
    }

    if (inputMode === 'webcam') {
      await captureAndAnalyze();
      return;
    }

    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const result = analysisType === 'image'
        ? await analyzeImage(selectedFile)
        : await analyzeVideo(selectedFile);
      setResults(result);
    } catch (err) {
      console.error('Analysis error:', err);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const toggleWebcam = () => {
    setWebcamActive(!webcamActive);
    setResults(null);
    setError(null);
  };

  const handleVideoUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      setUploadedVideo(file);
    }
  };

  const analyzeUploadedVideo = async () => {
    if (!uploadedVideo) return;

    setIsAnalyzing(true);
    const formData = new FormData();
    formData.append('video', uploadedVideo);
    formData.append('posture_type', postureType);

    try {
      const response = await fetch(`${API_BASE_URL}/analyze_video`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Analysis result:', result);
        setResults(result);
        setError(null);
      } else {
        console.error('Upload failed');
        setError('Video upload failed.');
      }
    } catch (error) {
      console.error('Error:', error);
      setError('An error occurred during video analysis.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const renderImageResults = (results) => {
    // unchanged
  };

  const renderVideoResults = (results) => {
    // unchanged
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Posture Detection App</h1>
        <p>Upload an image/video or use webcam to analyze your posture</p>
        <div className="backend-status">
          Status: 
          <span className={`status-${backendStatus}`}>
            {backendStatus === 'checking' && ' Checking...'}
            {backendStatus === 'connected' && ' ✓ Connected'}
            {backendStatus === 'disconnected' && ' ✗ Disconnected'}
          </span>
        </div>
      </header>
      
      <main className="main-content">
        <div className="upload-section">
          <div className="input-mode-selector">
                       <label>
              <input
                type="radio"
                value="upload"
                checked={inputMode === 'upload'}
                onChange={() => setInputMode('upload')}
              />
              Upload File
            </label>
            <label>
              <input
                type="radio"
                value="webcam"
                checked={inputMode === 'webcam'}
                onChange={() => setInputMode('webcam')}
              />
              Use Webcam
            </label>
          </div>

          <div className="analysis-type-selector">
            <label>
              <input
                type="radio"
                value="image"
                checked={analysisType === 'image'}
                onChange={handleAnalysisTypeChange}
              />
              Image Analysis
            </label>
            <label>
              <input
                type="radio"
                value="video"
                checked={analysisType === 'video'}
                onChange={handleAnalysisTypeChange}
              />
              Video Analysis
            </label>
          </div>

          <div className="posture-type-selector">
            <h4>Select Posture Type:</h4>
            <label>
              <input
                type="radio"
                value="sitting"
                checked={postureType === 'sitting'}
                onChange={handlePostureTypeChange}
              />
              Sitting Posture
            </label>
            <label>
              <input
                type="radio"
                value="squat"
                checked={postureType === 'squat'}
                onChange={handlePostureTypeChange}
              />
              Squat Posture
            </label>
          </div>

          {inputMode === 'upload' && analysisType === 'video' && (
            <div className="mb-6 p-4 border-2 border-dashed border-gray-300 rounded-lg">
              <input
                type="file"
                accept="video/*"
                onChange={handleVideoUpload}
                className="hidden"
                id="video-upload"
              />
              <label
                htmlFor="video-upload"
                className="cursor-pointer flex flex-col items-center justify-center py-4"
              >
                <Upload className="w-12 h-12 text-gray-400 mb-2" />
                <span className="text-gray-600">Click to upload video</span>
              </label>

              {uploadedVideo && (
                <div className="mt-4">
                  <p className="text-sm text-gray-600 mb-2">Uploaded: {uploadedVideo.name}</p>
                  <button
                    onClick={analyzeUploadedVideo}
                    disabled={isAnalyzing}
                    className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-50"
                  >
                    {isAnalyzing ? 'Analyzing...' : 'Analyze Video'}
                  </button>
                </div>
              )}
            </div>
          )}

          {inputMode === 'upload' && analysisType === 'image' && (
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
                  <p><strong>Selected:</strong> {selectedFile.name}</p>
                  <p><strong>Size:</strong> {(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                  <p><strong>Type:</strong> {selectedFile.type}</p>
                </div>
              )}
            </div>
          )}

          {inputMode === 'webcam' && (
            <div className="webcam-section">
              <button
                onClick={toggleWebcam}
                className="webcam-toggle-button"
                type="button"
              >
                {webcamActive ? 'Stop Webcam' : 'Start Webcam'}
              </button>
              {webcamActive && (
                <div className="webcam-container">
                  <Webcam
                    audio={false}
                    ref={webcamRef}
                    screenshotFormat="image/jpeg"
                    className="webcam-feed"
                    videoConstraints={{
                      width: 640,
                      height: 480,
                      facingMode: "user"
                    }}
                    onUserMediaError={(error) => {
                      console.error('Webcam error:', error);
                      setError('Failed to access webcam. Please check permissions.');
                    }}
                  />
                  <p className="webcam-instructions">
                    Position yourself in front of the webcam for analysis.
                  </p>
                </div>
              )}
            </div>
          )}

          <button
            onClick={handleAnalyze}
            className="analyze-button"
            disabled={
              loading || 
              backendStatus === 'disconnected' ||
              (inputMode === 'upload' && analysisType === 'image' && !selectedFile) || 
              (inputMode === 'webcam' && !webcamActive)
            }
            type="button"
          >
            {loading ? 'Analyzing...' : 'Analyze Posture'}
          </button>
        </div>

        {error && (
          <div className="error-message">
            <h4>Error</h4>
            <p>{error}</p>
          </div>
        )}

        {results && (
          analysisType === 'image' || inputMode === 'webcam'
            ? renderImageResults(results)
            : renderVideoResults(results)
        )}
      </main>
    </div>
  );
}

export default App;

