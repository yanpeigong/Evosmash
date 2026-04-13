import React, { useState } from 'react';
import {
    User, Divide as Device, Settings, LogOut, ToggleLeft, ToggleRight, Database,
} from 'lucide-react';
import { useGame } from '../context/GameContext';
import '../styles/Profile.css';

const Profile = () => {
    const { loadMockData, clearData, debugMode, setDebugMode } = useGame();
    const [height, setHeight] = useState(175);

    return (
        <div className="profile-container">
            <div className="profile-header">
                <div className="profile-avatar">
                    <User size={40} />
                </div>
                <div className="profile-name">
                    <h3>Player One</h3>
                    <span>Competitive Amateur</span>
                </div>
            </div>

            <div className="settings-section">
                <label className="section-label">Player Metrics</label>

                <div className="setting-item">
                    <div className="setting-icon"><User size={18} /></div>
                    <div className="setting-info">
                        <span className="setting-title">Height (cm)</span>
                        <span className="setting-desc">Used to calibrate motion and physics estimates.</span>
                    </div>
                    <input
                        type="number"
                        className="setting-input"
                        value={height}
                        onChange={(e) => setHeight(e.target.value)}
                        min="100"
                        max="240"
                    />
                </div>
            </div>

            <div className="settings-section">
                <label className="section-label">System Settings</label>

                <div className="setting-item" onClick={() => setDebugMode(!debugMode)}>
                    <div className="setting-icon"><Device size={18} /></div>
                    <div className="setting-info">
                        <span className="setting-title">HUD Debug Mode</span>
                        <span className="setting-desc">Enable quick demo analysis without the live backend.</span>
                    </div>
                    <div className={`toggle-switch ${debugMode ? 'on' : ''}`}>
                        {debugMode ? <ToggleRight size={24} color="var(--color-primary)" /> : <ToggleLeft size={24} color="#666" />}
                    </div>
                </div>

                {debugMode && (
                    <div className="debug-panel">
                        <button className="debug-btn" onClick={() => { loadMockData(); alert('Loaded 5 sample rally clips.'); }}>
                            <Database size={14} style={{ marginRight: 4 }} /> Load Sample Data
                        </button>
                        <button className="debug-btn destructive" onClick={() => { clearData(); alert('Local sample data cleared.'); }}>
                            Clear Data
                        </button>
                    </div>
                )}

                <div className="setting-item">
                    <div className="setting-icon"><Settings size={18} /></div>
                    <div className="setting-info">
                        <span className="setting-title">Preferences</span>
                    </div>
                </div>
            </div>

            <button className="logout-btn">
                <LogOut size={16} /> Sign Out
            </button>

            <div className="app-version">
                EvoSmash v1.0.0 (Build 2026.1)
            </div>
        </div>
    );
};

export default Profile;
