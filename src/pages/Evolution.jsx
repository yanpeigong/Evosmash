import React from 'react';
import {
    Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer,
} from 'recharts';
import { useGame } from '../context/GameContext';
import '../styles/Evolution.css';

const Evolution = () => {
    const { tactics, skills } = useGame();

    return (
        <div className="evolution-container">
            <header className="page-header">
                <h2>Evolution <span className="text-secondary">DNA</span></h2>
            </header>

            <div className="chart-section">
                <div className="hex-bg"></div>
                <ResponsiveContainer width="100%" height={300}>
                    <RadarChart cx="50%" cy="50%" outerRadius="80%" data={skills}>
                        <PolarGrid stroke="#333" />
                        <PolarAngleAxis dataKey="subject" tick={{ fill: '#aaa', fontSize: 12 }} />
                        <PolarRadiusAxis angle={30} domain={[0, 150]} tick={false} axisLine={false} />
                        <Radar
                            name="Skill Profile"
                            dataKey="A"
                            stroke="#0aff00"
                            strokeWidth={3}
                            fill="#0aff00"
                            fillOpacity={0.3}
                        />
                    </RadarChart>
                </ResponsiveContainer>
            </div>

            <div className="tactics-section">
                <h3>Tactical Genome</h3>
                <div className="tactics-list">
                    {tactics.map((tactic) => {
                        const total = tactic.alpha + tactic.beta;
                        const winRate = total > 0 ? (tactic.alpha / total) * 100 : 0;
                        const statusLabel = tactic.status === 'proven' ? 'Proven' : 'Exploring';

                        return (
                            <div key={tactic.id} className="tactic-card">
                                <div className="tactic-header">
                                    <span className="tactic-name">{tactic.name}</span>
                                    <span className={`status-badge ${tactic.status}`}>{statusLabel}</span>
                                </div>

                                <div className="progress-container">
                                    <div
                                        className="progress-bar win"
                                        style={{ width: `${winRate}%` }}
                                    ></div>
                                </div>

                                <div className="tactic-meta">
                                    <small className="text-muted">Samples: {total}</small>
                                    <small className="text-secondary">{Math.round(winRate)}% win rate</small>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default Evolution;
