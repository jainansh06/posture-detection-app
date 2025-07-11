import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Upload, Camera, Video, User, Activity, AlertCircle, CheckCircle, Clock } from 'lucide-react';

const API_BASE_URL = process.env.REACT_APP_API_URL || 
  (process.env.NODE_ENV === 'production' 
    ? 'https://posture-detection-app-3ih3.onrender.com' 
    : 'http://localhost:5000');

// Mock Webcam component for demonstration
const Webcam = React.forwardRef(({ audio, screenshotFormat, className, videoConstraints, onUserMediaError }, ref) => {
  const videoRef = useRef(null);
  const [stream, setStream] = useState(null);

  useEffect(() => {
    const startWebcam = async () => {
      try {
        const mediaStream = await navigator.mediaDevices.getUserMedia({
          video: videoConstraints,
          audio: audio
        });
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
        }
        setStream(mediaStream);
      } catch (error) {
        if (onUserMediaError) {
          onUserMediaError(error);
        }
      }
    };

    startWebcam();

    return () => {
      if (stream) {
        stream.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  React.useImperativeHandle(ref, () => ({
    getScreenshot: () => {
      if (videoRef.current) {
        const canvas = document.createElement('canvas');
        canvas.width = videoRef.current.videoWidth;
        canvas.height = videoRef.current.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(videoRef.current, 0, 0);
        return canvas.toDataURL(screenshotFormat);
      }
      return null;
    }
  }));

  return <video ref={videoRef} className={className} autoPlay playsInline />;
});

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
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef(null);
  const webcamRef = useRef(null);

  useEffect(() => {
    const testBackendConnection = async () => {
      try {
        setBackendStatus('checking');
        const response = await fetch(`${API_BASE_URL}/`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          }
        });
        
        if (response.ok) {
          setBackendStatus('connected');
          console.log('Backend connection successful');
        } else {
          setBackendStatus('disconnected');
        }
      } catch (err) {
        setBackendStatus('disconnected');
        console.error('Backend connection failed:', err.message);
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

    const response = await fetch(`${API_BASE_URL}/analyze_pose`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Analysis failed');
    }

    return response.json();
  }, [postureType]);

  const analyzeVideo = useCallback(async (file) => {
    const formData = new FormData();
    formData.append('video', file);
    formData.append('posture_type', postureType);

    const response = await fetch(`${API_BASE_URL}/analyze_video`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Video analysis failed');
    }

    return response.json();
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
}, [analyzeImage]); // Add analyzeImage to the dependency array


  const getErrorMessage = (err) => {
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
      setSelectedFile(file);
    }
  };

  const renderImageResults = (results) => {
    if (!results) return null;

    const postureGood = results.posture_status === 'good' || results.overall_posture === 'good';
    const issues = results.issues || [];

    return (
      <div className="bg-white rounded-2xl shadow-lg p-6 mt-6">
        <h3 className="text-2xl font-bold text-gray-800 mb-6 text-center flex items-center justify-center">
          <Activity className="mr-2 text-blue-600" />
          Posture Analysis Results
        </h3>
        
        <div className="text-center mb-6 p-4 bg-blue-50 rounded-lg">
          <p className="text-gray-700">
            <span className="font-semibold">Analyzed Posture:</span>{' '}
            <span className="text-blue-600 font-bold capitalize">{postureType}</span>
          </p>
        </div>

        <div className="text-center mb-6 p-6 bg-gray-50 rounded-lg">
          <h4 className="text-xl font-semibold mb-2 flex items-center justify-center">
            {postureGood ? (
              <CheckCircle className="text-green-500 mr-2" />
            ) : (
              <AlertCircle className="text-red-500 mr-2" />
            )}
            Overall Status
          </h4>
          <p className={`text-2xl font-bold ${postureGood ? 'text-green-600' : 'text-red-600'}`}>
            {postureGood ? 'Good Posture' : 'Poor Posture'}
          </p>
        </div>

        {!postureGood && issues.length > 0 && (
          <div className="mt-6 p-4 bg-red-50 rounded-lg border-l-4 border-red-500">
            <h5 className="text-lg font-semibold text-red-700 mb-3 flex items-center">
              <AlertCircle className="mr-2" />
              Issues Detected
            </h5>
            <ul className="space-y-2">
              {issues.map((issue, index) => (
                <li key={index} className="text-red-600 flex items-start">
                  <span className="w-2 h-2 bg-red-500 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                  {issue}
                </li>
              ))}
            </ul>
          </div>
        )}

        {postureGood && (
          <div className="mt-6 p-4 bg-green-50 rounded-lg border-l-4 border-green-500">
            <div className="flex items-center text-green-700">
              <CheckCircle className="mr-2" />
              <h5 className="text-lg font-semibold">Excellent!</h5>
            </div>
            <p className="text-green-600 mt-2">
              Your posture looks great! Keep maintaining this position.
            </p>
          </div>
        )}

        {results.confidence && (
          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <h5 className="text-lg font-semibold text-gray-700 mb-2">Analysis Details</h5>
            <p className="text-gray-600">
              Confidence: <span className="font-semibold">{(results.confidence * 100).toFixed(1)}%</span>
            </p>
          </div>
        )}
      </div>
    );
  };

  const renderVideoResults = (results) => {
    if (!results) return null;

    const { summary, main_issues, frames_analyzed, good_frames, poor_frames } = results;
    const goodPercentage = frames_analyzed > 0 ? ((good_frames / frames_analyzed) * 100).toFixed(1) : 0;
    const poorPercentage = frames_analyzed > 0 ? ((poor_frames / frames_analyzed) * 100).toFixed(1) : 0;

    return (
      <div className="bg-white rounded-2xl shadow-lg p-6 mt-6">
        <h3 className="text-2xl font-bold text-gray-800 mb-6 text-center flex items-center justify-center">
          <Video className="mr-2 text-blue-600" />
          Video Analysis Results
        </h3>

        <div className="text-center mb-6 p-4 bg-blue-50 rounded-lg">
          <p className="text-gray-700">
            <span className="font-semibold">Analyzed Posture:</span>{' '}
            <span className="text-blue-600 font-bold capitalize">{postureType}</span>
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-6 mb-6">
          <div className="bg-gray-50 rounded-lg p-4">
            <h4 className="text-lg font-semibold text-gray-700 mb-3 flex items-center">
              <Clock className="mr-2" />
              Analysis Summary
            </h4>
            <div className="space-y-2 text-sm">
              <p><span className="font-semibold">Frames Analyzed:</span> {frames_analyzed}</p>
              <p><span className="font-semibold">Good Frames:</span> 
                <span className="text-green-600 font-bold ml-1">{good_frames} ({goodPercentage}%)</span>
              </p>
              <p><span className="font-semibold">Poor Frames:</span> 
                <span className="text-red-600 font-bold ml-1">{poor_frames} ({poorPercentage}%)</span>
              </p>
            </div>
          </div>

          <div className="bg-gray-50 rounded-lg p-4">
            <h4 className="text-lg font-semibold text-gray-700 mb-3">Overall Assessment</h4>
            <div className="text-center">
              <div className={`text-3xl font-bold ${goodPercentage > 70 ? 'text-green-600' : goodPercentage > 40 ? 'text-yellow-600' : 'text-red-600'}`}>
                {goodPercentage > 70 ? 'Good' : goodPercentage > 40 ? 'Fair' : 'Poor'}
              </div>
              <p className="text-sm text-gray-600 mt-1">Posture Quality</p>
            </div>
          </div>
        </div>

        {summary && (
          <div className="mb-6 p-4 bg-blue-50 rounded-lg">
            <h4 className="text-lg font-semibold text-blue-700 mb-2">Summary</h4>
            <p className="text-blue-600">{summary}</p>
          </div>
        )}

        {main_issues && main_issues.length > 0 && (
          <div className="p-4 bg-orange-50 rounded-lg border-l-4 border-orange-500">
            <h4 className="text-lg font-semibold text-orange-700 mb-3 flex items-center">
              <AlertCircle className="mr-2" />
              Main Issues Detected
            </h4>
            <ul className="space-y-2">
              {main_issues.map((issue, index) => (
                <li key={index} className="text-orange-600 flex items-start">
                  <span className="w-2 h-2 bg-orange-500 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                  {issue}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-6 grid grid-cols-2 gap-4">
          <div className="bg-green-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-green-600">{goodPercentage}%</div>
            <div className="text-sm text-green-700">Good Posture</div>
          </div>
          <div className="bg-red-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-red-600">{poorPercentage}%</div>
            <div className="text-sm text-red-700">Poor Posture</div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 via-purple-600 to-purple-800">
      <header className="bg-white bg-opacity-10 backdrop-blur-lg p-6 m-4 rounded-2xl shadow-lg">
        <h1 className="text-4xl font-bold text-white text-center mb-2">
          Posture Detection App
        </h1>
        <p className="text-white text-opacity-90 text-center text-lg">
          Upload an image/video or use webcam to analyze your posture
        </p>
        <div className="mt-4 text-center">
          <span className="text-white text-opacity-90">Status: </span>
          <span className={`font-semibold ${
            backendStatus === 'checking' ? 'text-yellow-300' :
            backendStatus === 'connected' ? 'text-green-300' :
            'text-red-300'
          }`}>
            {backendStatus === 'checking' && '⏳ Checking...'}
            {backendStatus === 'connected' && '✓ Connected'}
            {backendStatus === 'disconnected' && '✗ Disconnected'}
          </span>
        </div>
      </header>
      
      <main className="max-w-4xl mx-auto p-4">
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
          {/* Input Mode Selector */}
          <div className="mb-6 p-4 border-2 border-gray-200 rounded-lg bg-gray-50">
            <h4 className="text-lg font-semibold text-gray-700 mb-3">Input Method</h4>
            <div className="flex flex-wrap gap-3">
              <label className={`flex items-center px-4 py-2 rounded-full border-2 cursor-pointer transition-all ${
                inputMode === 'upload' 
                  ? 'bg-blue-600 text-white border-blue-600' 
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
              }`}>
                <input
                  type="radio"
                  value="upload"
                  checked={inputMode === 'upload'}
                  onChange={() => setInputMode('upload')}
                  className="hidden"
                />
                <Upload className="w-4 h-4 mr-2" />
                Upload File
              </label>
              <label className={`flex items-center px-4 py-2 rounded-full border-2 cursor-pointer transition-all ${
                inputMode === 'webcam' 
                  ? 'bg-blue-600 text-white border-blue-600' 
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
              }`}>
                <input
                  type="radio"
                  value="webcam"
                  checked={inputMode === 'webcam'}
                  onChange={() => setInputMode('webcam')}
                  className="hidden"
                />
                <Camera className="w-4 h-4 mr-2" />
                Use Webcam
              </label>
            </div>
          </div>

          {/* Analysis Type Selector */}
          <div className="mb-6 p-4 border-2 border-gray-200 rounded-lg bg-gray-50">
            <h4 className="text-lg font-semibold text-gray-700 mb-3">Analysis Type</h4>
            <div className="flex flex-wrap gap-3">
              <label className={`flex items-center px-4 py-2 rounded-full border-2 cursor-pointer transition-all ${
                analysisType === 'image' 
                  ? 'bg-blue-600 text-white border-blue-600' 
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
              }`}>
                <input
                  type="radio"
                  value="image"
                  checked={analysisType === 'image'}
                  onChange={handleAnalysisTypeChange}
                  className="hidden"
                />
                <Camera className="w-4 h-4 mr-2" />
                Image Analysis
              </label>
              <label className={`flex items-center px-4 py-2 rounded-full border-2 cursor-pointer transition-all ${
                analysisType === 'video' 
                  ? 'bg-blue-600 text-white border-blue-600' 
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
              }`}>
                <input
                  type="radio"
                  value="video"
                  checked={analysisType === 'video'}
                  onChange={handleAnalysisTypeChange}
                  className="hidden"
                />
                <Video className="w-4 h-4 mr-2" />
                Video Analysis
              </label>
            </div>
          </div>

          {/* Posture Type Selector */}
          <div className="mb-6 p-4 border-2 border-gray-200 rounded-lg bg-gray-50">
            <h4 className="text-lg font-semibold text-gray-700 mb-3">Posture Type</h4>
            <div className="flex flex-wrap gap-3">
              <label className={`flex items-center px-4 py-2 rounded-full border-2 cursor-pointer transition-all ${
                postureType === 'sitting' 
                  ? 'bg-blue-600 text-white border-blue-600' 
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
              }`}>
                <input
                  type="radio"
                  value="sitting"
                  checked={postureType === 'sitting'}
                  onChange={handlePostureTypeChange}
                  className="hidden"
                />
                <User className="w-4 h-4 mr-2" />
                Sitting Posture
              </label>
              <label className={`flex items-center px-4 py-2 rounded-full border-2 cursor-pointer transition-all ${
                postureType === 'squat' 
                  ? 'bg-blue-600 text-white border-blue-600' 
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
              }`}>
                <input
                  type="radio"
                  value="squat"
                  checked={postureType === 'squat'}
                  onChange={handlePostureTypeChange}
                  className="hidden"
                />
                <Activity className="w-4 h-4 mr-2" />
                Squat Posture
              </label>
            </div>
          </div>

          {/* File Upload Section */}
          {inputMode === 'upload' && (
            <div className="mb-6 p-4 border-2 border-dashed border-gray-300 rounded-lg bg-gray-50">
              <input
                type="file"
                accept={analysisType === 'image' ? 'image/*' : 'video/*'}
                onChange={analysisType === 'image' ? handleFileSelect : handleVideoUpload}
                ref={fileInputRef}
                className="w-full p-3 border-2 border-gray-300 rounded-lg bg-white cursor-pointer hover:border-blue-600 transition-colors"
              />
              {selectedFile && (
                <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                  <p className="text-sm text-gray-700">
                    <strong>Selected:</strong> {selectedFile.name}
                  </p>
                  <p className="text-sm text-gray-700">
                    <strong>Size:</strong> {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  <p className="text-sm text-gray-700">
                    <strong>Type:</strong> {selectedFile.type}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Webcam Section */}
          {inputMode === 'webcam' && (
            <div className="mb-6 p-4 border-2 border-gray-200 rounded-lg bg-gray-50">
              <button
                onClick={toggleWebcam}
                className="bg-blue-600 text-white px-6 py-3 rounded-full font-semibold hover:bg-blue-700 transition-colors mb-4"
                type="button"
              >
                {webcamActive ? 'Stop Webcam' : 'Start Webcam'}
              </button>
              {webcamActive && (
                <div className="mt-4 text-center">
                  <Webcam
                    audio={false}
                    ref={webcamRef}
                    screenshotFormat="image/jpeg"
                    className="w-full max-w-md mx-auto rounded-lg shadow-lg"
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
                  <p className="text-gray-600 mt-3 italic">
                    Position yourself in front of the webcam for analysis.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Upload Progress */}
          {uploadProgress > 0 && uploadProgress < 100 && (
            <div className="mb-6">
              <div className="bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
              <p className="text-sm text-gray-600 mt-1">Uploading: {uploadProgress}%</p>
            </div>
          )}

          {/* Analyze Button */}
          <button
            onClick={handleAnalyze}
            className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-4 px-8 rounded-full text-lg font-bold hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 transform hover:scale-105"
            disabled={
              loading || 
              backendStatus === 'disconnected' ||
              (inputMode === 'upload' && !selectedFile) || 
              (inputMode === 'webcam' && !webcamActive)
            }
            type="button"
          >
            {loading ? (
              <div className="flex items-center justify-center">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white mr-2"></div>
                Analyzing...
              </div>
            ) : (
              'Analyze Posture'
            )}
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border-2 border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-center">
              <AlertCircle className="text-red-500 mr-2" />
              <h4 className="text-red-700 font-semibold">Error</h4>
            </div>
            <p className="text-red-600 mt-1">{error}</p>
          </div>
        )}

        {/* Results */}
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
