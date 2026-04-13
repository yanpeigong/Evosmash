import React, { useState } from 'react';
import { PlayCircle, Trophy } from 'lucide-react';
import { useGame } from '../context/GameContext';
import '../styles/Library.css';

const Library = () => {
    const { history } = useGame();
    const [filter, setFilter] = useState('all');

    const filteredVideos = history.filter((video) => {
        if (filter === 'win') return video.result === 'WIN';
        if (filter === 'smash') return video.type === 'Smash';
        return true;
    });

    return (
        <div className="library-container">
            <header className="library-header">
                <h2>Highlights</h2>
                <div className="filter-scroll">
                    <button
                        className={filter === 'all' ? 'active' : ''}
                        onClick={() => setFilter('all')}
                    >
                        All
                    </button>
                    <button
                        className={filter === 'win' ? 'active' : ''}
                        onClick={() => setFilter('win')}
                    >
                        <Trophy size={14} /> Wins
                    </button>
                    <button
                        className={filter === 'smash' ? 'active' : ''}
                        onClick={() => setFilter('smash')}
                    >
                        Smashes Only
                    </button>
                </div>
            </header>

            <div className="video-grid">
                {filteredVideos.length === 0 && (
                    <div style={{ gridColumn: 'span 2', textAlign: 'center', color: '#666', padding: '40px' }}>
                        No rally clips yet. Record a session in Arena to start building your library.
                    </div>
                )}
                {filteredVideos.map((video) => (
                    <div
                        key={video.id}
                        className="video-card"
                        onClick={() => video.video && window.open(video.video, '_blank', 'noopener,noreferrer')}
                    >
                        <div className="video-thumbnail">
                            {video.thumbnail ? (
                                <img src={video.thumbnail} alt="cover" className="thumb-img" />
                            ) : (
                                <video
                                    src={`${video.video}#t=0.1`}
                                    className="thumb-img"
                                    preload="metadata"
                                    muted
                                    playsInline
                                    style={{ objectFit: 'cover' }}
                                />
                            )}
                            <div className="play-overlay">
                                <PlayCircle size={32} />
                            </div>
                            <span className="duration">{video.duration}</span>
                        </div>
                        <div className="video-info">
                            <span className="video-date">{video.date}</span>
                            <div className="video-tags">
                                <span className={`tag ${video.result}`}>{video.result}</span>
                                <span className="tag type">{video.type}</span>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default Library;
