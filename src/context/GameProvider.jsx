import React, { useState } from 'react';
import { GameContext } from './GameContext';

const initialTactics = [
    { id: 'T001', name: 'Counter Block', alpha: 15, beta: 3, status: 'proven' },
    { id: 'T002', name: 'Deep Lift Reset', alpha: 8, beta: 12, status: 'exploring' },
    { id: 'T003', name: 'Cross Drop Finish', alpha: 5, beta: 2, status: 'exploring' },
    { id: 'T004', name: 'Flat Drive Press', alpha: 20, beta: 5, status: 'proven' },
];

const initialSkills = [
    { subject: 'Attack', A: 120, fullMark: 150 },
    { subject: 'Defense', A: 98, fullMark: 150 },
    { subject: 'Net Play', A: 86, fullMark: 150 },
    { subject: 'Footwork', A: 99, fullMark: 150 },
    { subject: 'Composure', A: 85, fullMark: 150 },
];

export const GameProvider = ({ children }) => {
    const [tactics, setTactics] = useState(initialTactics);
    const [skills, setSkills] = useState(initialSkills);
    const [history, setHistory] = useState([]);
    const [debugMode, setDebugMode] = useState(false);

    const addMatchRecord = (record) => {
        const newRecord = {
            ...record,
            id: Date.now(),
            date: new Date().toISOString().split('T')[0],
        };
        setHistory((prev) => [newRecord, ...prev]);
    };

    const updateMatchResult = (id, newResult) => {
        setHistory((prev) =>
            prev.map((item) => {
                if (item.id === id) {
                    return { ...item, auto_result: newResult };
                }
                return item;
            }),
        );
    };

    const loadMockData = () => {
        const mockHistory = [
            { id: 1, date: '2023-11-20', type: 'Smash', result: 'WIN', duration: '0:15', auto_reward: 120, tactics: [{ name: 'Counter Block' }], thumbnail: '/samples/smash.png', video: '/samples/demo.mp4' },
            { id: 2, date: '2023-11-21', type: 'Defense', result: 'LOSS', duration: '0:22', auto_reward: 50, tactics: [{ name: 'Deep Lift Reset' }], thumbnail: '/samples/defense.png', video: '/samples/demo.mp4' },
            { id: 3, date: '2023-11-22', type: 'Drive', result: 'WIN', duration: '0:08', auto_reward: 90, tactics: [{ name: 'Flat Drive Press' }], thumbnail: '/samples/smash.png', video: '/samples/demo.mp4' },
            { id: 4, date: '2023-11-23', type: 'Net', result: 'WIN', duration: '0:05', auto_reward: 150, tactics: [{ name: 'Cross Drop Finish' }], thumbnail: '/samples/defense.png', video: '/samples/demo.mp4' },
            { id: 5, date: '2023-11-24', type: 'Smash', result: 'WIN', duration: '0:12', auto_reward: 130, tactics: [{ name: 'Counter Block' }], thumbnail: '/samples/smash.png', video: '/samples/demo.mp4' },
        ];

        setHistory(mockHistory);
    };

    const clearData = () => {
        setHistory([]);
        setTactics(initialTactics);
        setSkills(initialSkills);
    };

    const value = {
        tactics,
        skills,
        history,
        debugMode,
        setDebugMode,
        addMatchRecord,
        updateMatchResult,
        loadMockData,
        clearData,
    };

    return <GameContext.Provider value={value}>{children}</GameContext.Provider>;
};
