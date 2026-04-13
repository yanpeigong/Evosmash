const API_BASE_URL = 'http://localhost:8000';

const normalizeAdvice = (advice) => {
    const text = typeof advice === 'string' ? advice : advice?.text;
    return text ? { text } : null;
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
        };
    });

const normalizeAnalysisResult = (result) => ({
    ...result,
    advice: normalizeAdvice(result?.advice),
    tactics: normalizeTactics(result?.tactics),
    physics: {
        ...result?.physics,
        description: result?.physics?.description || 'No analysis details available.',
    },
});

const createDebugResponse = (videoUrl, matchType) => ({
    videoUrl,
    physics: {
        event: 'Smash',
        max_speed_kmh: 235,
        duration: 4.5,
        description: `Mode: ${matchType === 'doubles' ? 'Doubles' : 'Singles'}. Max shuttle speed 235 km/h. Verdict: point won.`,
    },
    advice: {
        text: 'Clean overhead mechanics. Reach a little higher at contact to create a sharper finishing angle.',
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
        },
    ],
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
