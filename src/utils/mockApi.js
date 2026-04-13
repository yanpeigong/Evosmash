export const mockAnalyzeRally = (file, matchType) => {
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve({
                physics: {
                    event: 'Smash',
                    max_speed_kmh: 214.5,
                    description: `Mode: ${matchType === 'doubles' ? 'Doubles' : 'Singles'}. Opponent applied heavy pressure. [Motion: stance too upright]`,
                },
                advice: {
                    text: 'Lower your base on contact. A soft backhand block to the front court is the highest-value reply.',
                },
                auto_result: 'WIN',
                auto_reward: 10.0,
                session_id: 'T001',
                tactics: [
                    {
                        name: 'Counter Block',
                        content: 'Use a soft backhand block to pull the attacker forward.',
                        metadata: {
                            tactic_id: 'T001',
                            name: 'Counter Block',
                            alpha: 5.0,
                            beta: 1.0,
                        },
                        score: 0.85,
                    },
                    {
                        name: 'Deep Lift Reset',
                        content: 'Lift high and deep to the baseline to recover court balance.',
                        metadata: {
                            tactic_id: 'T002',
                            name: 'Deep Lift Reset',
                            alpha: 2.0,
                            beta: 3.0,
                        },
                        score: 0.45,
                    },
                ],
                match_type: matchType,
            });
        }, 2000);
    });
};
