import React, {
    useCallback, useEffect, useRef, useState,
} from 'react';
import {
    Upload,
    Activity,
    Shield,
    Zap,
    Camera,
    Video,
    TriangleAlert,
    Sparkles,
    Gauge,
    BrainCircuit,
    Radar,
    Siren,
    CircleAlert,
    Route,
    ScrollText,
    Swords,
    GitBranch,
    Flag,
    Target,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Webcam from 'react-webcam';
import { api } from '../utils/api';
import { useGame } from '../context/GameContext';
import { soundManager } from '../utils/SoundManager';
import '../styles/Arena.css';

const getModeLabel = (mode) => (mode === 'doubles' ? 'Doubles' : 'Singles');

const getConfidenceLabel = (label) => {
    if (label === 'high') return 'High Confidence';
    if (label === 'low') return 'Exploratory';
    return 'Balanced';
};

const getRiskLabel = (label) => {
    if (label === 'high') return 'High Duel Risk';
    if (label === 'medium') return 'Watch Duel';
    return 'Stable Duel';
};

const formatSignalLabel = (value) => {
    if (!value) {
        return 'Unknown';
    }

    return String(value)
        .split(/[_-]/)
        .filter(Boolean)
        .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
        .join(' ');
};

const toPercentLabel = (value) => `${Math.round((Number(value) || 0) * 100)}%`;

const toSignedPercentLabel = (value) => {
    const numericValue = Number(value) || 0;
    const prefix = numericValue > 0 ? '+' : '';
    return `${prefix}${Math.round(numericValue * 100)}%`;
};

const toFeedbackItems = (value) => {
    if (!value || typeof value !== 'string') {
        return [];
    }

    return value
        .split('|')
        .map((item) => item.trim())
        .filter(Boolean);
};

const toArray = (value) => (Array.isArray(value) ? value : []);

const metricCards = (analysisResult) => {
    const policyUpdate = analysisResult?.diagnostics?.policy_update || {};
    const rallyState = analysisResult?.physics?.rally_state || {};

    return [
        {
            label: 'Referee Confidence',
            value: toPercentLabel(analysisResult?.physics?.referee_confidence),
            icon: Gauge,
            tone: 'cyan',
        },
        {
            label: 'Landing Confidence',
            value: toPercentLabel(rallyState?.landing_confidence),
            icon: Shield,
            tone: 'green',
        },
        {
            label: 'Direction Consistency',
            value: toPercentLabel(rallyState?.direction_consistency),
            icon: Activity,
            tone: 'amber',
        },
        {
            label: 'Trajectory Quality',
            value: toPercentLabel(analysisResult?.physics?.trajectory_quality),
            icon: Radar,
            tone: 'cyan',
        },
        {
            label: 'Analysis Quality',
            value: (analysisResult?.diagnostics?.analysis_quality || 'medium').toUpperCase(),
            icon: BrainCircuit,
            tone: 'amber',
        },
        {
            label: 'Adaptation Level',
            value: (policyUpdate?.adaptation_level || 'n/a').toUpperCase(),
            icon: Sparkles,
            tone: 'violet',
        },
    ];
};

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

    const diagnostics = analysisResult?.diagnostics || {};
    const report = analysisResult?.report || {};
    const replayStory = analysisResult?.replay_story || {};
    const motionFeedbackItems = toFeedbackItems(diagnostics?.motion_feedback);
    const policyUpdate = diagnostics?.policy_update || {};
    const rewardComponents = policyUpdate?.reward_components || {};
    const rallyState = analysisResult?.physics?.rally_state || {};
    const courtContext = analysisResult?.physics?.court_context || rallyState?.court_context;
    const hasTrajectorySignals = Boolean(courtContext) || rallyState?.landing_confidence !== undefined || rallyState?.direction_consistency !== undefined;

    const sequenceContext = diagnostics?.sequence_context || {};
    const duelProjection = diagnostics?.duel_projection || report?.duel_snapshot || {};
    const trainingPlan = report?.training_plan || {};

    const sequenceTactics = toArray(sequenceContext?.recent_tactics);
    const sequenceTransitions = toArray(sequenceContext?.tactic_transitions);
    const sequenceSignals = [
        ...toArray(sequenceContext?.adaptation_signals),
        ...toArray(sequenceContext?.player_adjustment_signals),
    ];
    const sequenceTags = toArray(sequenceContext?.sequence_tags);

    const counterTactics = toArray(duelProjection?.counter_tactics);
    const exchangeScript = toArray(duelProjection?.exchange_script);

    const storyCards = toArray(replayStory?.storyline_cards);
    const turningPoints = toArray(replayStory?.turning_points);
    const adaptationCycles = toArray(replayStory?.adaptation_cycles);
    const criticalRallies = toArray(replayStory?.critical_rallies);
    const trainingBlocks = toArray(trainingPlan?.blocks);

    const hasSequencePanel = Boolean(sequenceContext?.has_content);
    const hasDuelPanel = Boolean(duelProjection?.has_content);
    const hasReplayPanel = Boolean(replayStory?.has_content);

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
                                    {courtContext && (
                                        <div className="hud-tag-chip">
                                            <Radar size={12} />
                                            <span>{formatSignalLabel(courtContext)}</span>
                                        </div>
                                    )}
                                    {analysisResult.physics?.max_speed_kmh > 200 && (
                                        <div className="hud-tag-chip highlight">
                                            <Zap size={12} />
                                            <span>Power Smash</span>
                                        </div>
                                    )}
                                    {sequenceTags.slice(0, 2).map((tag) => (
                                        <div key={tag} className="hud-tag-chip accent">
                                            <GitBranch size={12} />
                                            <span>{formatSignalLabel(tag)}</span>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {analysisResult?.summary && (
                                <motion.section
                                    className="hud-summary-panel"
                                    initial={{ opacity: 0, y: 18 }}
                                    animate={{ opacity: 1, y: 0 }}
                                >
                                    <div className="hud-summary-header">
                                        <div>
                                            <p className="hud-summary-kicker">RALLY SUMMARY</p>
                                            <h2>{analysisResult.summary.headline}</h2>
                                        </div>
                                        <span className={`intel-confidence ${analysisResult.summary.confidence_label || 'medium'}`}>
                                            {getConfidenceLabel(analysisResult.summary.confidence_label)}
                                        </span>
                                    </div>
                                    <p className="hud-summary-copy">{analysisResult.summary.key_takeaway}</p>
                                </motion.section>
                            )}

                            {analysisResult?.diagnostics && (
                                <motion.section
                                    className="hud-diagnostics-panel"
                                    initial={{ opacity: 0, y: 18 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.05 }}
                                >
                                    <div className="hud-diagnostics-header">
                                        <p className="hud-summary-kicker">DIAGNOSTICS</p>
                                        <span>{(analysisResult.diagnostics.analysis_quality || 'medium').toUpperCase()} SIGNAL</span>
                                    </div>

                                    <div className="hud-metric-grid">
                                        {metricCards(analysisResult).map((metric) => {
                                            const Icon = metric.icon;
                                            return (
                                                <div key={metric.label} className={`hud-metric-card ${metric.tone}`}>
                                                    <div className="hud-metric-icon"><Icon size={16} /></div>
                                                    <span className="hud-metric-label">{metric.label}</span>
                                                    <strong>{metric.value}</strong>
                                                </div>
                                            );
                                        })}
                                    </div>

                                    <div className="hud-notes-grid">
                                        <div className="hud-note-card">
                                            <strong><Siren size={14} /> Referee Reason</strong>
                                            <p>{analysisResult.physics?.referee_reason || 'No referee explanation available.'}</p>
                                        </div>

                                        <div className="hud-note-card">
                                            <strong><BrainCircuit size={14} /> Motion Feedback</strong>
                                            {motionFeedbackItems.length > 0 ? (
                                                <ul className="hud-note-list">
                                                    {motionFeedbackItems.map((item, index) => (
                                                        <li key={`${item}-${index}`}>{item}</li>
                                                    ))}
                                                </ul>
                                            ) : (
                                                <p>No motion feedback available.</p>
                                            )}
                                        </div>

                                        {hasTrajectorySignals && (
                                            <div className="hud-note-card">
                                                <strong><Radar size={14} /> Trajectory Signals</strong>
                                                <div className="hud-note-meta">
                                                    {courtContext && <span>{formatSignalLabel(courtContext)}</span>}
                                                    {rallyState?.landing_confidence !== undefined && (
                                                        <span>Landing {toPercentLabel(rallyState.landing_confidence)}</span>
                                                    )}
                                                    {rallyState?.direction_consistency !== undefined && (
                                                        <span>Direction {toPercentLabel(rallyState.direction_consistency)}</span>
                                                    )}
                                                </div>
                                                <p>
                                                    {analysisResult.physics?.description || 'Trajectory-level analysis is available for this rally.'}
                                                </p>
                                            </div>
                                        )}

                                        {policyUpdate?.policy_update_reason && (
                                            <div className="hud-note-card emphasis">
                                                <strong><Sparkles size={14} /> Policy Update</strong>
                                                <p>{policyUpdate.policy_update_reason}</p>
                                                <div className="hud-note-inline">
                                                    {rewardComponents?.raw_reward !== undefined && <span>Reward {rewardComponents.raw_reward}</span>}
                                                    {rewardComponents?.trajectory_quality !== undefined && (
                                                        <span>Trajectory {toPercentLabel(rewardComponents.trajectory_quality)}</span>
                                                    )}
                                                    {rewardComponents?.referee_confidence !== undefined && (
                                                        <span>Referee {toPercentLabel(rewardComponents.referee_confidence)}</span>
                                                    )}
                                                    {rewardComponents?.retrieval_confidence !== undefined && (
                                                        <span>Retrieval {toPercentLabel(rewardComponents.retrieval_confidence)}</span>
                                                    )}
                                                </div>
                                            </div>
                                        )}

                                        {analysisResult.diagnostics?.warnings?.length > 0 && (
                                            <div className="hud-note-card warning">
                                                <strong><CircleAlert size={14} /> Warnings</strong>
                                                <ul>
                                                    {analysisResult.diagnostics.warnings.map((warning, index) => (
                                                        <li key={`${warning}-${index}`}>{warning}</li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}
                                    </div>
                                </motion.section>
                            )}

                            {(hasSequencePanel || hasDuelPanel) && (
                                <section className="hud-intelligence-grid">
                                    {hasSequencePanel && (
                                        <motion.article
                                            className="hud-intel-panel sequence-panel"
                                            initial={{ opacity: 0, y: 18 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: 0.08 }}
                                        >
                                            <div className="hud-intel-header-row">
                                                <div>
                                                    <p className="hud-summary-kicker">SEQUENCE MEMORY</p>
                                                    <h3>Multi-Rally Tactical Drift</h3>
                                                </div>
                                                <span className="intel-badge neutral">
                                                    <Route size={12} />
                                                    {toPercentLabel(sequenceContext?.adaptation_score)}
                                                </span>
                                            </div>

                                            <p className="hud-intel-copy">
                                                {sequenceContext?.memory_summary || 'No multi-rally memory was generated for this clip.'}
                                            </p>

                                            {sequenceTags.length > 0 && (
                                                <div className="hud-chip-row">
                                                    {sequenceTags.map((tag) => (
                                                        <span key={tag} className="hud-chip">
                                                            {formatSignalLabel(tag)}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}

                                            <div className="hud-sequence-stats">
                                                <div className="hud-mini-stat">
                                                    <span>Streak</span>
                                                    <strong>{formatSignalLabel(sequenceContext?.streak_context?.state)}</strong>
                                                </div>
                                                <div className="hud-mini-stat">
                                                    <span>Pressure Swing</span>
                                                    <strong>{formatSignalLabel(sequenceContext?.pressure_swing?.label)}</strong>
                                                    <small>{toSignedPercentLabel(sequenceContext?.pressure_swing?.delta)}</small>
                                                </div>
                                                <div className="hud-mini-stat">
                                                    <span>Preferred Family</span>
                                                    <strong>{formatSignalLabel(sequenceContext?.preferred_style_family)}</strong>
                                                </div>
                                            </div>

                                            {sequenceTactics.length > 0 && (
                                                <div className="memory-lane">
                                                    {sequenceTactics.map((snapshot, index) => (
                                                        <div key={`${snapshot.name}-${index}`} className="memory-rally-card">
                                                            <span className="memory-rally-index">R{snapshot.rally_index}</span>
                                                            <strong>{snapshot.name}</strong>
                                                            <small>{formatSignalLabel(snapshot.style_family)}</small>
                                                            <span>{toPercentLabel(snapshot.score)}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}

                                            {sequenceTransitions.length > 0 && (
                                                <div className="transition-rail">
                                                    {sequenceTransitions.map((transition, index) => (
                                                        <div key={`${transition.from}-${transition.to}-${index}`} className="transition-item">
                                                            <div className="transition-route">
                                                                <span>{transition.from}</span>
                                                                <GitBranch size={14} />
                                                                <span>{transition.to}</span>
                                                            </div>
                                                            <small>{formatSignalLabel(transition.style_shift)}</small>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}

                                            {sequenceSignals.length > 0 && (
                                                <ul className="intel-signal-list">
                                                    {sequenceSignals.map((signal, index) => (
                                                        <li key={`${signal}-${index}`}>{signal}</li>
                                                    ))}
                                                </ul>
                                            )}
                                        </motion.article>
                                    )}

                                    {hasDuelPanel && (
                                        <motion.article
                                            className="hud-intel-panel duel-panel"
                                            initial={{ opacity: 0, y: 18 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: 0.1 }}
                                        >
                                            <div className="hud-intel-header-row">
                                                <div>
                                                    <p className="hud-summary-kicker">TACTICAL DUEL</p>
                                                    <h3>{duelProjection?.primary_plan || 'Neutral reset'}</h3>
                                                </div>
                                                <span className={`intel-badge ${duelProjection?.duel_risk_label || 'low'}`}>
                                                    <Swords size={12} />
                                                    {getRiskLabel(duelProjection?.duel_risk_label)}
                                                </span>
                                            </div>

                                            <p className="hud-intel-copy">
                                                {duelProjection?.duel_explanation || duelProjection?.likely_response || 'No duel projection is available for this clip.'}
                                            </p>

                                            <div className="hud-chip-row">
                                                <span className="hud-chip emphasis">{formatSignalLabel(duelProjection?.counter_window)}</span>
                                                <span className="hud-chip">{toPercentLabel(duelProjection?.duel_risk)}</span>
                                            </div>

                                            {exchangeScript.length > 0 && (
                                                <ol className="exchange-script">
                                                    {exchangeScript.map((step, index) => (
                                                        <li key={`${step}-${index}`}>{step}</li>
                                                    ))}
                                                </ol>
                                            )}

                                            {counterTactics.length > 0 && (
                                                <div className="duel-counter-grid">
                                                    {counterTactics.map((counter, index) => (
                                                        <div key={`${counter.name}-${index}`} className="duel-counter-card">
                                                            <div className="duel-counter-topline">
                                                                <strong>{counter.name}</strong>
                                                                <span>{toPercentLabel(counter.fit_score)}</span>
                                                            </div>
                                                            <small>{formatSignalLabel(counter.family)}</small>
                                                            <p>{counter.reason}</p>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}

                                            {duelProjection?.pressure_gate && (
                                                <div className="duel-pressure-gate">
                                                    <TriangleAlert size={14} />
                                                    <span>{duelProjection.pressure_gate}</span>
                                                </div>
                                            )}
                                        </motion.article>
                                    )}
                                </section>
                            )}

                            {analysisResult?.tactics?.length > 0 && (
                                <div className="hud-tactics-panel">
                                    {analysisResult.tactics.map((tactic, index) => (
                                        <motion.article
                                            key={`${tactic.name}-${index}`}
                                            className={`tactic-intel-card ${tactic.confidence_label || 'medium'}`}
                                            initial={{ opacity: 0, y: 16 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: 0.08 * index }}
                                        >
                                            <div className="tactic-intel-header">
                                                <div>
                                                    <p className="tactic-intel-kicker">TACTIC OPTION {index + 1}</p>
                                                    <h3>{tactic.name}</h3>
                                                </div>
                                                <span className={`intel-confidence ${tactic.confidence_label || 'medium'}`}>
                                                    {getConfidenceLabel(tactic.confidence_label)}
                                                </span>
                                            </div>

                                            <div className="tactic-intel-action">
                                                <Sparkles size={14} />
                                                <span>{tactic.recommended_action || tactic.content}</span>
                                            </div>

                                            <div className="tactic-intel-metrics">
                                                <span>Rerank {toPercentLabel(tactic.rerank_score)}</span>
                                                <span>Continuity {toPercentLabel(tactic.continuity_score)}</span>
                                                <span>Coverage {toPercentLabel(tactic.coverage_score)}</span>
                                            </div>

                                            {tactic.why_this_tactic && (
                                                <div className="tactic-intel-copy">
                                                    <strong>Why this tactic</strong>
                                                    <p>{tactic.why_this_tactic}</p>
                                                </div>
                                            )}

                                            {tactic.rank_reason && (
                                                <div className="tactic-intel-copy subdued">
                                                    <strong><Target size={14} /> Selection logic</strong>
                                                    <p>{tactic.rank_reason}</p>
                                                </div>
                                            )}

                                            {tactic.frontier_hint && (
                                                <div className="tactic-intel-copy subdued">
                                                    <strong><GitBranch size={14} /> Frontier hint</strong>
                                                    <p>{tactic.frontier_hint}</p>
                                                </div>
                                            )}

                                            {tactic.evolution_replay?.development_stage && (
                                                <div className="tactic-evolution-panel">
                                                    <div className="tactic-evolution-header">
                                                        <strong><Route size={14} /> Evolution replay</strong>
                                                        <span>{formatSignalLabel(tactic.evolution_replay.development_stage)}</span>
                                                    </div>
                                                    <p>{tactic.evolution_replay.why_now}</p>
                                                    {toArray(tactic.evolution_replay.upgrade_path).length > 0 && (
                                                        <ul className="tactic-evolution-steps">
                                                            {toArray(tactic.evolution_replay.upgrade_path).map((step, stepIndex) => (
                                                                <li key={`${step}-${stepIndex}`}>{step}</li>
                                                            ))}
                                                        </ul>
                                                    )}
                                                </div>
                                            )}

                                            {tactic.risk_note && (
                                                <div className="tactic-intel-copy caution">
                                                    <strong><TriangleAlert size={14} /> Risk note</strong>
                                                    <p>{tactic.risk_note}</p>
                                                </div>
                                            )}
                                        </motion.article>
                                    ))}
                                </div>
                            )}

                            {hasReplayPanel && (
                                <motion.section
                                    className="hud-replay-panel"
                                    initial={{ opacity: 0, y: 18 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.16 }}
                                >
                                    <div className="hud-replay-header">
                                        <div>
                                            <p className="hud-summary-kicker">REPLAY STORY</p>
                                            <h3>{replayStory?.opening_phase?.headline || 'Replay storyboard'}</h3>
                                        </div>
                                        <span className="intel-badge neutral">
                                            <ScrollText size={12} />
                                            Storyline
                                        </span>
                                    </div>

                                    <p className="hud-intel-copy">
                                        {replayStory?.replay_summary || 'No replay story is available for this clip.'}
                                    </p>

                                    {storyCards.length > 0 && (
                                        <div className="storyline-grid">
                                            {storyCards.map((card, index) => (
                                                <div key={`${card.title}-${index}`} className={`storyline-card ${card.stage || 'neutral'}`}>
                                                    <span className="storyline-stage">{formatSignalLabel(card.stage || 'stage')}</span>
                                                    <strong>{card.title}</strong>
                                                    <p>{card.body}</p>
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    <div className="replay-columns">
                                        {turningPoints.length > 0 && (
                                            <div className="replay-column">
                                                <div className="replay-column-header">
                                                    <Flag size={14} />
                                                    <strong>Turning points</strong>
                                                </div>
                                                <div className="replay-list">
                                                    {turningPoints.map((turn, index) => (
                                                        <div key={`${turn.rally_index}-${index}`} className="replay-list-item">
                                                            <span>R{turn.rally_index}</span>
                                                            <div>
                                                                <strong>{turn.summary || 'Rally shift'}</strong>
                                                                <p>{turn.trigger}</p>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {adaptationCycles.length > 0 && (
                                            <div className="replay-column">
                                                <div className="replay-column-header">
                                                    <GitBranch size={14} />
                                                    <strong>Adaptation cycles</strong>
                                                </div>
                                                <div className="replay-list">
                                                    {adaptationCycles.map((cycle, index) => (
                                                        <div key={`${cycle.from}-${cycle.to}-${index}`} className="replay-list-item">
                                                            <span>{index + 1}</span>
                                                            <div>
                                                                <strong>{cycle.from} -> {cycle.to}</strong>
                                                                <p>{cycle.summary}</p>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {criticalRallies.length > 0 && (
                                            <div className="replay-column">
                                                <div className="replay-column-header">
                                                    <Target size={14} />
                                                    <strong>Critical rallies</strong>
                                                </div>
                                                <div className="replay-critical-grid">
                                                    {criticalRallies.map((critical) => (
                                                        <div key={critical.rally_index} className="critical-rally-card">
                                                            <span>R{critical.rally_index}</span>
                                                            <strong>{critical.headline}</strong>
                                                            <p>{critical.takeaway}</p>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    {replayStory?.closing_state?.summary && (
                                        <div className="closing-state-card">
                                            <div className="replay-column-header">
                                                <Flag size={14} />
                                                <strong>Closing state</strong>
                                            </div>
                                            <p>{replayStory.closing_state.summary}</p>
                                        </div>
                                    )}
                                </motion.section>
                            )}

                            {analysisResult?.advice && (
                                <div className="hud-coach-section">
                                    {trainingBlocks.length > 0 && (
                                        <div className="hud-training-strip">
                                            {trainingBlocks.map((block, index) => (
                                                <div key={`${block.label}-${index}`} className="hud-training-block">
                                                    <span>{block.label}</span>
                                                    <strong>{block.duration_min} min</strong>
                                                    <small>{block.goal}</small>
                                                </div>
                                            ))}
                                        </div>
                                    )}

                                    <motion.div
                                        className="hud-coach-bubble"
                                        initial={{ y: 50, opacity: 0 }}
                                        animate={{ y: 0, opacity: 1 }}
                                    >
                                        <div className="avatar-circle">AI</div>
                                        <div className="coach-text">
                                            <p>{analysisResult.advice.text}</p>
                                            <small>{report?.coach_takeaway || analysisResult.physics?.description}</small>
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
