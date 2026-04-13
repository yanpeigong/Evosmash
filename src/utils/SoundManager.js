let audioContext;

const getAudioContext = () => {
    if (typeof window === 'undefined') {
        return null;
    }

    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) {
        return null;
    }

    if (!audioContext) {
        audioContext = new AudioContextClass();
    }

    return audioContext;
};

const playTone = (frequency, duration, volume, type = 'triangle') => {
    const context = getAudioContext();
    if (!context) {
        return;
    }

    if (context.state === 'suspended') {
        context.resume().catch(() => {});
    }

    const oscillator = context.createOscillator();
    const gainNode = context.createGain();

    oscillator.type = type;
    oscillator.frequency.value = frequency;
    gainNode.gain.value = volume;

    oscillator.connect(gainNode);
    gainNode.connect(context.destination);

    oscillator.start();
    gainNode.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + duration);
    oscillator.stop(context.currentTime + duration);
};

export const soundManager = {
    playClick() {
        playTone(540, 0.05, 0.015);
    },
    playConfirm() {
        playTone(660, 0.08, 0.02);
    },
    playSuccess() {
        playTone(880, 0.1, 0.025, 'sine');
    },
};
