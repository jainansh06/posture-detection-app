import React, { useState, useRef, useCallback } from 'react';
import Webcam from 'react-webcam';
import axios from 'axios';
import './App.css';

const API_BASE_URL = 'http://13.53.126.177:5000';

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [analysisType, setAnalysisType] = useState('image');
  const [inputMode, setInputMode] = useState('upload'); // 'upload' or 'webcam'
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [webcamActive, setWebcamActive] = useState(false);
  const fileInputRef = useRef(null);
  const webcamRef = useRef(null);

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    setSelectedFile(file);
    setResults(null);
    setError(null);
  };

  const analyzeImage = async (file) => {
    const formData = new FormData();
    formData.append('image', file);

    const response = await axios.post(`${API_BASE_URL}/analyze_pose`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  };

  const analyzeVideo = async (file) => {
    const formData = new FormData();
    formData.append('video', file);

    const response = await axios.post(`${API_BASE_URL}/analyze_video`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  };

  const captureAndAnalyze = useCallback(async () => {
    if (!webcamRef.current) return;

    const imageSrc = webcamRef.current.getScreenshot();
    
    if (!imageSrc) {
      setError('Failed to capture image from webcam');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Convert base64 to blob
      const response = await fetch(imageSrc);
      const blob = await response.blob();
      
      // Create a File object
      const file = new File([blob], 'webcam-capture.jpg', { type: 'image/jpeg' });
      
      const result = await analyzeImage(file);
      setResults(result);
    } catch (err) {
      setError(err.response?.data?.error || 'Analysis failed');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleAnalyze = async () => {
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

    try {
      let result;
      if (analysisType === 'image') {
        result = await analyzeImage(selectedFile);
      } else {
        result = await analyzeVideo(selectedFile);
      }
      
      setResults(result);
    } catch (err) {
      setError(err.response?.data?.error || 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const toggleWebcam = () => {
    setWebcamActive(!webcamActive);
    setResults(null);
    setError(null);
  };

  const renderImageResults = (results) => (
    <div className="results-container">
      <h3>Analysis Results</h3>
      
      <div className="posture-status">
        <h4>Overall Posture: 
          <span className={results.analysis.overall_posture === 'good' ? 'good' : 'bad'}>
            {results.analysis.overall_posture.toUpperCase()}
          </span>
        </h4>
      </div>

      <div className="analysis-details">
        <div className="sitting-analysis">
          <h5>Sitting Analysis</h5>
          {results.analysis.sitting_analysis.bad_posture ? (
            <div className="issues">
              <p>❌ Bad posture detected</p>
              <ul>
                {results.analysis.sitting_analysis.problems.map((problem, index) => (
                  <li key={index}>{problem}</li>
                ))}
              </ul>
            </div>
          ) : (
            <p>✅ Good sitting posture</p>
          )}
        </div>

        <div className="squat-analysis">
          <h5>Squat Analysis</h5>
          {results.analysis.squat_analysis.bad_posture ? (
            <div className="issues">
              <p>❌ Bad posture detected</p>
              <ul>
                {results.analysis.squat_analysis.problems.map((problem, index) => (
                  <li key={index}>{problem}</li>
                ))}
              </ul>
            </div>
          ) : (
            <p>✅ Good squat posture</p>
          )}
        </div>
      </div>
    </div>
  );

  const renderVideoResults = (results) => (
    <div className="results-container">
      <h3>Video Analysis Results</h3>
      
      <div className="video-summary">
        <h4>Summary</h4>
        <p>Total Frames: {results.total_frames}</p>
        <p>Analyzed Frames: {results.analyzed_frames}</p>
        <p>Bad Posture: {results.bad_posture_percentage.toFixed(1)}%</p>
        <p>Overall Rating: 
          <span className={results.summary.overall_rating === 'good' ? 'good' : 'bad'}>
            {results.summary.overall_rating.toUpperCase()}
          </span>
        </p>
      </div>

      {results.summary.main_issues.length > 0 && (
        <div className="main-issues">
          <h4>Main Issues Found</h4>
          <ul>
            {results.summary.main_issues.map(([issue, count], index) => (
              <li key={index}>{issue} (occurred {count} times)</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );

  return (
    <div className="App">
      <header className="App-header">
        <h1>Posture Detection App</h1>
        <p>Upload an image/video or use webcam to analyze your posture</p>
      </header>

      <main className="main-content">
        <div className="upload-section">
          <div className="input-mode-selector">
            <label>
              <input
                type="radio"
                value="upload"
                checked={inputMode === 'upload'}
                onChange={(e) => setInputMode(e.target.value)}
              />
              Upload File
            </label>
            <label>
              <input
                type="radio"
                value="webcam"
                checked={inputMode === 'webcam'}
                onChange={(e) => setInputMode(e.target.value)}
              />
              Use Webcam
            </label>
          </div>

          {inputMode === 'upload' && (
            <>
              <div className="analysis-type-selector">
                <label>
                  <input
                    type="radio"
                    value="image"
                    checked={analysisType === 'image'}
                    onChange={(e) => setAnalysisType(e.target.value)}
                  />
                  Image Analysis
                </label>
                <label>
                  <input
                    type="radio"
                    value="video"
                    checked={analysisType === 'video'}
                    onChange={(e) => setAnalysisType(e.target.value)}
                  />
                  Video Analysis
                </label>
              </div>

              <div className="file-upload">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={analysisType === 'image' ? 'image/*' : 'video/*'}
                  onChange={handleFileSelect}
                  className="file-input"
                />
                
                {selectedFile && (
                  <div className="file-info">
                    <p>Selected: {selectedFile.name}</p>
                    <p>Size: {(selectedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                )}
              </div>
            </>
          )}

          {inputMode === 'webcam' && (
            <div className="webcam-section">
              <button
                onClick={toggleWebcam}
                className="webcam-toggle-button"
              >
                {webcamActive ? 'Stop Webcam' : 'Start Webcam'}
              </button>

              {webcamActive && (
                <div className="webcam-container">
                  <Webcam
                    ref={webcamRef}
                    audio={false}
                    screenshotFormat="image/jpeg"
                    width={640}
                    height={480}
                    className="webcam-feed"
                  />
                  <p className="webcam-instructions">
                    Position yourself in front of the camera and click "Analyze Posture"
                  </p>
                </div>
              )}
            </div>
          )}

          <button
            onClick={handleAnalyze}
            disabled={
              loading || 
              (inputMode === 'upload' && !selectedFile) ||
              (inputMode === 'webcam' && !webcamActive)
            }
            className="analyze-button"
          >
            {loading ? 'Analyzing...' : 'Analyze Posture'}
          </button>
        </div>

        {error && (
          <div className="error-message">
            <p>Error: {error}</p>
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
