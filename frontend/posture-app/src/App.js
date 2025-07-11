import React, { useState, useRef, useCallback, useEffect } from 'react';
import Webcam from 'react-webcam';
import axios from 'axios';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

console.log('Environment variables:', process.env);
console.log('API_BASE_URL being used:', API_BASE_URL);

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [analysisType, setAnalysisType] = useState('image');
  const [inputMode, setInputMode] = useState('upload');
  const [postureType, setPostureType] = useState('sitting');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [webcamActive, setWebcamActive] = useState(false);
  const fileInputRef = useRef(null);
  const webcamRef = useRef(null);

  useEffect(() => {
    console.log("Posture Analysis Results:", results);
  }, [results]);

  const handleFileSelect = (event) => {
    setSelectedFile(event.target.files[0]);
    setResults(null);
    setError(null);
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

  const analyzeImage = async (file) => {
    const formData = new FormData();
    formData.append('image', file);
    formData.append('posture_type', postureType);

    const response = await axios.post(`${API_BASE_URL}/analyze_pose`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  };

  const analyzeVideo = async (file) => {
    const formData = new FormData();
    formData.append('video', file);
    formData.append('posture_type', postureType);

    const response = await axios.post(`${API_BASE_URL}/analyze_video`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  };

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
      setError(err.response?.data?.error || err.message || 'Analysis failed');
    } finally {
      setLoading(false);
    }
  }, [postureType]);

  const handleAnalyze = async () => {
    if (inputMode === 'webcam') {
      await captureAndAnalyze();
      return;
    }

    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    const isImage = selectedFile.type.startsWith('image/');
    const isVideo = selectedFile.type.startsWith('video/');

    if (analysisType === 'image' && !isImage) {
      setError('Please select an image file for image analysis');
      return;
    }

    if (analysisType === 'video' && !isVideo) {
      setError('Please select a video file for video analysis');
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
      setError(err.response?.data?.error || err.message || 'Analysis failed');
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
    if (!results || !results.analysis) {
      return (
        <div className="results-container">
          <h3>Analysis Results</h3>
          <p>No analysis data available</p>
        </div>
      );
    }

    return (
      <div className="results-container">
        <h3>Analysis Results</h3>
        <div className="specified-posture">
          <h4>Analyzing for:
            <span className="posture-type"> {postureType.toUpperCase()} POSTURE</span>
          </h4>
        </div>
        <div className="posture-status">
          <h4>Overall Posture:
            <span className={results.analysis.bad_posture === false ? 'good' : 'bad'}>
              {results.analysis.bad_posture === false ? 'GOOD' :
               results.analysis.bad_posture === true ? 'BAD' : 'N/A'}
            </span>
          </h4>
        </div>
        {results.analysis.neck_angle !== undefined && (
          <p>Neck Angle: {results.analysis.neck_angle.toFixed(2)}°</p>
        )}
        {results.analysis.problems && results.analysis.problems.length > 0 && (
          <div className="issues">
            <h5>Issues Detected:</h5>
            <ul>
              {results.analysis.problems.map((problem, index) => (
                <li key={index}>{problem}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  const renderVideoResults = (results) => {
    if (!results) {
      return (
        <div className="results-container">
          <h3>Video Analysis Results</h3>
          <p>No analysis data available</p>
        </div>
      );
    }

    return (
      <div className="results-container">
        <h3>Video Analysis Results</h3>
        <div className="specified-posture">
          <h4>Analyzing for:
            <span className="posture-type">{postureType.toUpperCase()} POSTURE</span>
          </h4>
        </div>
        <div className="video-summary">
          <h4>Summary</h4>
          <p>Total Frames: {results.total_frames ?? 'N/A'}</p>
          <p>Analyzed Frames: {results.analyzed_frames ?? 'N/A'}</p>
          <p>
            Bad Posture:
            {typeof results.bad_posture_percentage === 'number'
              ? ` ${results.bad_posture_percentage.toFixed(1)}%`
              : ' N/A'}
          </p>
          {results.summary && (
            <p>Overall Rating:
              <span className={results.summary.overall_rating === 'good' ? 'good' : 'bad'}>
                {results.summary.overall_rating?.toUpperCase() || 'N/A'}
              </span>
            </p>
          )}
        </div>
        {results.summary && results.summary.main_issues && results.summary.main_issues.length > 0 && (
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
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Posture Detection App</h1>
        <p>Upload an image/video or use webcam to analyze your posture</p>
      </header>
      <main className="main-content">
        {/* Your existing upload section UI here */}
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
