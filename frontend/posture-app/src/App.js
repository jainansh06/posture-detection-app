import React, { useState, useRef, useCallback, useEffect } from 'react';
import Webcam from 'react-webcam';
import axios from 'axios';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

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
  
  const fileInputRef = useRef(null);
  const webcamRef = useRef(null);

  useEffect(() => {
    const checkBackend = async () => {
      try {
        setBackendStatus('checking');
        await axios.get(`${API_BASE_URL}/`);
        setBackendStatus('connected');
      } catch (err) {
        setBackendStatus('disconnected');
        console.error('Backend connection failed:', err);
      }
    };

    checkBackend();
  }, []);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      if (file.size > 10 * 1024 * 1024) {
        setError('File too large. Please select a file smaller than 10MB.');
        return;
      }

      const isImage = file.type.startsWith('image/');
      const isVideo = file.type.startsWith('video/');

      if (analysisType === 'image' && !isImage) {
        setError('Please select an image file');
        return;
      }

      if (analysisType === 'video' && !isVideo) {
        setError('Please select a video file');
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
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 30000,
    });
    return response.data;
  }, [postureType]);

  const analyzeVideo = useCallback(async (file) => {
    const formData = new FormData();
    formData.append('video', file);
    formData.append('posture_type', postureType);

    const response = await axios.post(`${API_BASE_URL}/analyze_video`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
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
      setError('Failed to capture image');
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
      console.error('Error:', err);
      setError('Analysis failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [analyzeImage]);

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
      console.error('Error:', err);
      setError('Analysis failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const toggleWebcam = () => {
    setWebcamActive(!webcamActive);
    setResults(null);
    setError(null);
  };

  const renderImageResults = (results) => {
    if (!results.success) {
      return (
        <div className="error-message">
          <h4>Analysis Failed</h4>
          <p>{results.error || 'Unknown error occurred'}</p>
        </div>
      );
    }

    if (!results.landmarks_detected) {
      return (
        <div className="results-section">
          <h3>Analysis Results</h3>
          <p>No person detected in the image. Please try a different image.</p>
        </div>
      );
    }

    const analysis = results.analysis;
    
    return (
      <div className="results-section">
        <h3>Posture Analysis Results</h3>
        <div className={`posture-status ${analysis.bad_posture ? 'bad' : 'good'}`}>
          <h4>Overall Status: {analysis.bad_posture ? 'Poor Posture' : 'Good Posture'}</h4>
        </div>
        
        {analysis.problems && analysis.problems.length > 0 && (
          <div className="problems-list">
            <h4>Issues Found:</h4>
            <ul>
              {analysis.problems.map((problem, index) => (
                <li key={index}>{problem}</li>
              ))}
            </ul>
          </div>
        )}

        {analysis.knee_angle && (
          <div className="angle-info">
            <p><strong>Knee Angle:</strong> {analysis.knee_angle.toFixed(1)}°</p>
          </div>
        )}
      </div>
    );
  };

  const renderVideoResults = (results) => {
    if (!results.analyzed_frames || results.analyzed_frames === 0) {
      return (
        <div className="results-section">
          <h3>Video Analysis Results</h3>
          <p>No frames could be analyzed. Please try a different video.</p>
        </div>
      );
    }

    return (
      <div className="results-section">
        <h3>Video Analysis Results</h3>
        <div className="video-stats">
          <p><strong>Total Frames:</strong> {results.total_frames}</p>
          <p><strong>Analyzed Frames:</strong> {results.analyzed_frames}</p>
          <p><strong>Bad Posture:</strong> {results.bad_posture_percentage}%</p>
        </div>
        
        <div className={`overall-rating ${results.summary.overall_rating === 'Good' ? 'good' : 'bad'}`}>
          <h4>Overall Rating: {results.summary.overall_rating}</h4>
        </div>

        {results.summary.main_issues && results.summary.main_issues.length > 0 && (
          <div className="main-issues">
            <h4>Main Issues:</h4>
            <ul>
              {results.summary.main_issues.map(([issue, count], index) => (
                <li key={index}>{issue} ({count} times)</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
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

          {inputMode === 'upload' && (
            <div className="file-upload">
              <input
                type="file"
                accept={analysisType === 'image' ? 'image/*' : 'video/*'}
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
              (inputMode === 'upload' && !selectedFile) || 
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
