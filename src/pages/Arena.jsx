import React, {
    useCallback, useEffect, useRef, useState,
} from 'react';
import {
    Upload, Activity, Shield, Zap, Camera, Video,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Webcam from 'react-webcam';
import { api } from '../utils/api';
import { useGame } from '../context/GameContext';
import { soundManager } from '../utils/SoundManager';
import '../styles/Arena.css';

const getModeLabel = (mode) => (mode === 'doubles' ? 'Doubles' : 'Singles');

const Arena = () => {
    const { addMatchRecord, debugMode } = useGame();
    const [mode, setMode] = useState('singles');
    const [status, setStatus] = useState('idle');
    const [analysisResult, setAnalysisResult] = useState(null);
    const [videoUrl, setVideoUrl] = useState(null);
    const [isCameraMode, setIsCameraMode] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const [timeLeft, setTimeLeft] = useState(0);

    const fileInputRef = useRef(null);
    const webcamRef = useRef(null);
    const timerRef = useRef(null);
    const mediaRecorderRef = useRef(null);
    const recordedChunksRef = useRef([]);
    const isMountedRef = useRef(true);

    const speakAdvice = useCallback((text) => {
        if (!text || !('speechSynthesis' in window)) {
            return;
        }

        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-US';
        utterance.rate = 1;
        window.speechSynthesis.speak(utterance);
    }, []);

    const clearTimer = useCallback(() => {
        if (timerRef.current) {
            clearInterval(timerRef.current);
            timerRef.current = null;
        }
    }, []);

    const revokeVideoUrl = useCallback((url) => {
        if (url?.startsWith('blob:')) {
            URL.revokeObjectURL(url);
        }
    }, []);

    const processAnalysis = useCallback(async (file) => {
        if (!isMountedRef.current) {
            return;
        }

        setStatus('analyzing');

        try {
            const result = await api.uploadVideo(file, { isDebug: debugMode, matchType: mode });
            if (!isMountedRef.current) {
                revokeVideoUrl(result.videoUrl);
                return;
            }

            setAnalysisResult(result);
            setVideoUrl((previousUrl) => {
                revokeVideoUrl(previousUrl);
                return result.videoUrl;
            });
            setStatus('complete');

            if (result.advice?.text) {
                speakAdvice(result.advice.text);
            }

            addMatchRecord({
                video: result.videoUrl,
                type: result.physics?.event || 'Session',
                result: result.auto_result || 'DONE',
                duration: result.physics?.duration ? `${result.physics.duration}s` : 'Clip',
                tactics: result.tactics,
            });
            soundManager.playSuccess();
        } catch (error) {
            console.error(error);
            setStatus('idle');
            alert("Analysis failed.\n1. Confirm the backend is running on localhost:8000.\n2. Or enable HUD Debug Mode in Profile for demo data.");
        }
    }, [addMatchRecord, debugMode, mode, revokeVideoUrl, speakAdvice]);

    const handleFileSelect = async (event) => {
        soundManager.playConfirm();
        const file = event.target.files?.[0];
        if (!file) {
            return;
        }

        await processAnalysis(file);
        event.target.value = '';
    };

    const handleCameraCapture = useCallback(() => {
        soundManager.playConfirm();

        if (typeof MediaRecorder === 'undefined') {
            alert('Camera recording is not available in this browser.');
            return;
        }

        if (isRecording) {
            mediaRecorderRef.current?.stop();
            return;
        }

        const stream = webcamRef.current?.stream || webcamRef.current?.video?.srcObject;
        if (!stream) {
            alert('Camera stream is not ready yet. Please try again in a moment.');
            return;
        }

        const preferredTypes = [
            'video/webm;codecs=vp9',
            'video/webm;codecs=vp8',
            'video/webm',
        ];
        const mimeType = preferredTypes.find((type) => MediaRecorder.isTypeSupported(type)) || '';

        try {
            const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);

            recordedChunksRef.current = [];
            mediaRecorderRef.current = recorder;

            recorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    recordedChunksRef.current.push(event.data);
                }
            };

            recorder.onstop = async () => {
                clearTimer();
                setIsRecording(false);

                const recordedBlob = recordedChunksRef.current.length
                    ? new Blob(recordedChunksRef.current, { type: recorder.mimeType || 'video/webm' })
                    : null;

                recordedChunksRef.current = [];

                if (!recordedBlob) {
                    alert('No camera clip was captured. Please try recording again.');
                    return;
                }

                await processAnalysis(recordedBlob);
            };

            recorder.start();
            setIsRecording(true);
            setTimeLeft(0);
            clearTimer();
            timerRef.current = setInterval(() => {
                setTimeLeft((previous) => previous + 1);
            }, 1000);
        } catch (error) {
            console.error(error);
            alert('Camera recording is not supported in this browser.');
        }
    }, [clearTimer, isRecording, processAnalysis]);

    useEffect(() => {
        isMountedRef.current = true;

        return () => {
            isMountedRef.current = false;
            clearTimer();
            if (mediaRecorderRef.current) {
                mediaRecorderRef.current.onstop = null;
            }
            if (mediaRecorderRef.current?.state === 'recording') {
                mediaRecorderRef.current.stop();
            }
            window.speechSynthesis?.cancel?.();
            revokeVideoUrl(videoUrl);
        };
    }, [clearTimer, revokeVideoUrl, videoUrl]);

    const handleReset = () => {
        clearTimer();
        window.speechSynthesis?.cancel?.();
        setStatus('idle');
        setAnalysisResult(null);
        setIsRecording(false);
        setTimeLeft(0);
        setVideoUrl((previousUrl) => {
            revokeVideoUrl(previousUrl);
            return null;
        });
    };

    const toggleResult = () => {
        soundManager.playClick();
        if (!analysisResult) {
            return;
        }

        const newResult = analysisResult.auto_result === 'WIN' ? 'LOSS' : 'WIN';
        setAnalysisResult({
            ...analysisResult,
            auto_result: newResult,
        });
    };

    return (
        <div className="arena-container">
            <AnimatePresence mode="wait">
                {status === 'idle' && (
                    <motion.div
                        key="idle"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="arena-idle"
                    >
                        {isCameraMode && (
                            <div className="webcam-bg">
                                <Webcam
                                    audio={false}
                                    ref={webcamRef}
                                    screenshotFormat="image/jpeg"
                                    style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: 0.6 }}
                                    videoConstraints={{ facingMode: { ideal: 'environment' } }}
                                />
                            </div>
                        )}

                        <header className={`arena-header ${isCameraMode ? 'overlay-mode' : ''}`}>
                            <h1 className="glitch-text">EVO<span className="text-primary">SMASH</span></h1>
                            <p className="subtitle">VISION-DRIVEN AR COACHING SYSTEM</p>
                        </header>

                        <div className="mode-switch">
                            <button onClick={() => { soundManager.playClick(); setMode('singles'); }} className={mode === 'singles' ? 'active' : ''}>Singles</button>
                            <button onClick={() => { soundManager.playClick(); setMode('doubles'); }} className={mode === 'doubles' ? 'active' : ''}>Doubles</button>
                        </div>

                        <div className="input-toggle">
                            <button
                                className={!isCameraMode ? 'active' : ''}
                                onClick={() => { soundManager.playClick(); setIsCameraMode(false); }}
                            >
                                <Upload size={14} /> File Upload
                            </button>
                            <button
                                className={isCameraMode ? 'active' : ''}
                                onClick={() => { soundManager.playClick(); setIsCameraMode(true); }}
                            >
                                <Camera size={14} /> AR Camera
                            </button>
                        </div>

                        <motion.div
                            className={`upload-trigger ${isRecording ? 'recording' : ''}`}
                            onClick={isCameraMode ? handleCameraCapture : () => { soundManager.playClick(); fileInputRef.current?.click(); }}
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                        >
                            <div className="trigger-ring"></div>
                            <div className="trigger-icon">
                                {isCameraMode ? <Video size={48} /> : <Upload size={48} />}
                            </div>
                            <span className="trigger-text">
                                {isRecording
                                    ? `STOP ${timeLeft < 10 ? '0' : ''}${timeLeft}s`
                                    : isCameraMode
                                        ? 'Start Recording'
                                        : 'Upload Clip'}
                            </span>
                        </motion.div>

                        <input
                            type="file"
                            ref={fileInputRef}
                            onChange={handleFileSelect}
                            accept="video/*"
                            style={{ display: 'none' }}
                        />

                        <div className="capability-badges">
                            <div className="badge"><Activity size={16} /><span>Motion Analysis</span></div>
                            <div className="badge"><Zap size={16} /><span>Speed Tracking</span></div>
                            <div className="badge"><Shield size={16} /><span>Tactical Coaching</span></div>
                        </div>
                    </motion.div>
                )}

                {status === 'analyzing' && (
                    <motion.div
                        key="analyzing"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="arena-analyzing"
                    >
                        <motion.div
                            className="scanner"
                            animate={{ y: [-100, 100, -100], opacity: [0.5, 1, 0.5] }}
                            transition={{ repeat: Infinity, duration: 2 }}
                        ></motion.div>
                        <p>Scanning shuttle path and player motion...</p>
                    </motion.div>
                )}

                {status === 'complete' && videoUrl && (
                    <motion.div
                        key="complete"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="arena-hud"
                    >
                        <video
                            src={videoUrl}
                            className="hud-video"
                            autoPlay
                            loop
                            muted
                            playsInline
                            controls
                        />

                        <div className="hud-overlay">
                            {analysisResult?.physics && (
                                <div className="hud-top-bar">
                                    <div className="hud-stat">
                                        <span className="hud-label">MAX SPEED</span>
                                        <span className="hud-value text-primary">
                                            {Math.round(analysisResult.physics.max_speed_kmh || 0)} <span style={{ fontSize: '0.8rem' }}>KM/H</span>
                                        </span>
                                    </div>

                                    <div className="hud-stat" onClick={toggleResult}>
                                        <span className="hud-label">RESULT</span>
                                        <div className={`result-badge ${analysisResult.auto_result}`}>
                                            {analysisResult.auto_result || 'N/A'}
                                        </div>
                                    </div>
                                </div>
                            )}

                            {analysisResult && (
                                <div className="hud-tags-bar">
                                    <div className="hud-tag-chip highlight">
                                        <Activity size={12} />
                                        <span>{getModeLabel(analysisResult.match_type)}</span>
                                    </div>
                                    {analysisResult.physics?.event && (
                                        <div className="hud-tag-chip">
                                            <Video size={12} />
                                            <span>{analysisResult.physics.event}</span>
                                        </div>
                                    )}
                                    {analysisResult.tactics?.map((tactic, index) => (
                                        <div key={`${tactic.name}-${index}`} className="hud-tag-chip">
                                            <Shield size={12} />
                                            <span>{tactic.name}</span>
                                        </div>
                                    ))}
                                    {analysisResult.physics?.max_speed_kmh > 200 && (
                                        <div className="hud-tag-chip highlight">
                                            <Zap size={12} />
                                            <span>Power Smash</span>
                                        </div>
                                    )}
                                </div>
                            )}

                            {analysisResult?.advice && (
                                <div className="hud-coach-section">
                                    <motion.div
                                        className="hud-coach-bubble"
                                        initial={{ y: 50, opacity: 0 }}
                                        animate={{ y: 0, opacity: 1 }}
                                    >
                                        <div className="avatar-circle">AI</div>
                                        <div className="coach-text">
                                            <p>{analysisResult.advice.text}</p>
                                            <small>{analysisResult.physics?.description}</small>
                                        </div>
                                    </motion.div>

                                    <div className="hud-actions">
                                        <button className="close-btn" onClick={handleReset}>Back to Capture</button>
                                    </div>
                                </div>
                            )}

                            {!analysisResult && (
                                <div className="hud-actions solo">
                                    <button className="close-btn" onClick={handleReset}>Back to Capture</button>
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default Arena;
