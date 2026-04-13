const API_BASE_URL = 'http://localhost:8000';

const normalizeAdvice = (advice, fallbackTactics = []) => {
    const text = typeof advice === 'string' ? advice : advice?.text;
    const fallbackAction = fallbackTactics[0]?.recommended_action || 'Prepare for the next shot.';

    return {
        text: text || 'Stay balanced and prepare early.',
        headline: advice?.headline || 'Stay composed',
        focus: advice?.focus || 'Recovery',
        next_step: advice?.next_step || fallbackAction,
        confidence_label: advice?.confidence_label || fallbackTactics[0]?.confidence_label || 'medium',
        source: advice?.source || 'fallback',
    };
};

const normalizeTactics = (tactics = []) =>
    tactics.map((tactic, index) => {
        const name =
            tactic?.name ||
            tactic?.metadata?.name ||
            tactic?.content ||
            `Tactic ${index + 1}`;

        return {
            ...tactic,
            name,
            content: tactic?.content || name,
            score: tactic?.score || 0,
            semantic_score: tactic?.semantic_score || 0,
            bayesian_score: tactic?.bayesian_score || 0,
            context_score: tactic?.context_score || 0,
            quality_weight: tactic?.quality_weight || 1,
            expected_win_rate: tactic?.expected_win_rate || 50,
            confidence_label: tactic?.confidence_label || 'medium',
            recommended_action: tactic?.recommended_action || tactic?.content || name,
            reason: tactic?.reason || '',
            why_this_tactic: tactic?.why_this_tactic || '',
            risk_note: tactic?.risk_note || '',
        };
    });

const normalizeDiagnostics = (diagnostics = {}) => ({
    warnings: diagnostics?.warnings || [],
    pipeline: diagnostics?.pipeline || {},
    motion_feedback: diagnostics?.motion_feedback || 'Unavailable',
    trajectory_points: diagnostics?.trajectory_points || 0,
    analysis_quality: diagnostics?.analysis_quality || 'medium',
    policy_update: diagnostics?.policy_update || {},
});

const normalizeSummary = (summary = {}) => ({
    headline: summary?.headline || 'Rally captured',
    verdict: summary?.verdict || 'UNKNOWN',
    confidence_label: summary?.confidence_label || 'medium',
    key_takeaway: summary?.key_takeaway || 'Review the recommendation and prepare for the next exchange.',
});

const normalizeAnalysisResult = (result) => {
    const tactics = normalizeTactics(result?.tactics);

    return {
        ...result,
        advice: normalizeAdvice(result?.advice, tactics),
        tactics,
        summary: normalizeSummary(result?.summary),
        diagnostics: normalizeDiagnostics(result?.diagnostics),
        physics: {
            ...result?.physics,
            description: result?.physics?.description || 'No analysis details available.',
            referee_confidence: result?.physics?.referee_confidence ?? 0.72,
            trajectory_quality: result?.physics?.trajectory_quality ?? 0.78,
            referee_reason: result?.physics?.referee_reason || 'Referee explanation is unavailable.',
        },
    };
};

const createDebugResponse = (videoUrl, matchType) => ({
    videoUrl,
    physics: {
        event: 'Power Smash',
        max_speed_kmh: 235,
        duration: 4.5,
        description: `Mode: ${matchType === 'doubles' ? 'Doubles' : 'Singles'}. Event: Power Smash. Max shuttle speed 235 km/h. Verdict: point won.`,
        trajectory_quality: 0.84,
        referee_confidence: 0.87,
        referee_reason: 'Last hitter was inferred as the user with a stable downward finish, and the landing point was comfortably inside the court.',
        court_context: 'rear_channel',
        rally_state: {
            trajectory_quality: 0.84,
            landing_confidence: 0.9,
            direction_consistency: 0.82,
            speed_profile: {
                mean_speed_kmh: 118.4,
                max_speed_kmh: 235,
                end_speed_kmh: 58.2,
            },
            court_context: 'rear_channel',
        },
    },
    advice: {
        text: 'Keep leaning into the counter block and recover forward immediately after contact.',
        headline: 'Attack the reply',
        focus: 'Transition speed',
        next_step: 'Block soft to the forecourt, then step in aggressively.',
        confidence_label: 'high',
        source: 'debug',
    },
    tactics: [
        {
            name: 'Counter Block',
            content: 'Use a soft backhand block to pull the attacker forward after a heavy smash.',
            metadata: {
                tactic_id: 'T001',
                name: 'Counter Block',
                alpha: 5,
                beta: 1,
            },
            score: 0.91,
            semantic_score: 0.83,
            bayesian_score: 0.95,
            context_score: 0.88,
            quality_weight: 0.97,
            expected_win_rate: 83.3,
            confidence_label: 'high',
            recommended_action: 'Use a soft backhand block to pull the attacker forward after a heavy smash.',
            reason: 'Counter Block is the top recommendation because it fits a power-smash scenario at 235.0 km/h and carries a strong expected win rate.',
            why_this_tactic: 'This is the clearest match for a heavy rear-court attack because it converts the opponent’s pace into a front-court pressure opportunity.',
            risk_note: 'The shuttle pace is very high here, so the block only works if your racket face stays soft and stable at contact.',
        },
        {
            name: 'Deep Lift Reset',
            content: 'Lift high and deep to the rear court corners to reset the rally and buy recovery time.',
            metadata: {
                tactic_id: 'T002',
                name: 'Deep Lift Reset',
                alpha: 3,
                beta: 2,
            },
            score: 0.74,
            semantic_score: 0.71,
            bayesian_score: 0.69,
            context_score: 0.72,
            quality_weight: 0.94,
            expected_win_rate: 60,
            confidence_label: 'medium',
            recommended_action: 'Lift high and deep to the rear court corners to reset the rally and buy recovery time.',
            reason: 'Deep Lift Reset remains viable because it slows the exchange and rebuilds court balance.',
            why_this_tactic: 'It is a safer secondary option when you cannot control the block cleanly and need extra recovery time.',
            risk_note: 'If the lift sits short, you may give the attacker another full-power ball.',
        },
    ],
    summary: {
        headline: 'Winning pattern detected',
        verdict: 'WIN',
        confidence_label: 'high',
        key_takeaway: 'Primary tactical direction: Counter Block. Focus on transition speed in the next exchange.',
    },
    diagnostics: {
        warnings: [],
        pipeline: {
            court_detection: 'ok',
            tracking: 'ok',
            pose: 'ok',
            physics: 'ok',
            retrieval: 'ok',
            coach: 'ok',
        },
        motion_feedback: 'Base control is solid, but there is room for a lower defensive stance. | Contact point is well extended with strong striking structure.',
        trajectory_points: 18,
        analysis_quality: 'high',
        policy_update: {
            weighted_increment: 0.87,
            quality_weight: 0.91,
            confidence_weight: 0.96,
            exploration_guard: 0.85,
            adaptation_level: 'strong',
            policy_update_reason: 'Updated alpha using strong trajectory quality, high referee confidence, and high retrieval confidence.',
            reward_components: {
                raw_reward: 10,
                trajectory_quality: 0.84,
                referee_confidence: 0.87,
                retrieval_confidence: 0.91,
            },
        },
    },
    match_type: matchType,
    auto_result: 'WIN',
    auto_reward: 10,
});

export const api = {
    async uploadVideo(videoFile, options = {}) {
        const { isDebug = false, matchType = 'singles' } = options;

        if (isDebug) {
            const debugVideoUrl = videoFile ? URL.createObjectURL(videoFile) : '/samples/after.mp4';

            return new Promise((resolve) => {
                window.setTimeout(() => {
                    resolve(normalizeAnalysisResult(createDebugResponse(debugVideoUrl, matchType)));
                }, 1200);
            });
        }

        if (!videoFile) {
            throw new Error('Please select or record a clip before starting analysis.');
        }

        const formData = new FormData();
        formData.append('file', videoFile);
        formData.append('match_type', matchType);

        try {
            const localVideoUrl = URL.createObjectURL(videoFile);
            const response = await fetch(`${API_BASE_URL}/analyze_rally`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error('Analysis failed.');
            }

            const data = await response.json();

            return normalizeAnalysisResult({
                videoUrl: localVideoUrl,
                ...data,
            });
        } catch (error) {
            console.error('[API] Upload failed:', error);
            throw error;
        }
    },
};
