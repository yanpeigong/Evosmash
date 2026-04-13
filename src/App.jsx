import React from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import BottomNavigation from './components/BottomNavigation';
import PageTransition from './components/PageTransition';
import Arena from './pages/Arena';
import Evolution from './pages/Evolution';
import Library from './pages/Library';
import Profile from './pages/Profile';

function App() {
  const location = useLocation();

  return (
    <div className="app-container">
      <div className="content-area">
        <AnimatePresence mode="wait">
          <Routes location={location} key={location.pathname}>
            <Route path="/" element={<PageTransition><Arena /></PageTransition>} />
            <Route path="/evolution" element={<PageTransition><Evolution /></PageTransition>} />
            <Route path="/library" element={<PageTransition><Library /></PageTransition>} />
            <Route path="/profile" element={<PageTransition><Profile /></PageTransition>} />
          </Routes>
        </AnimatePresence>
      </div>
      <BottomNavigation />
    </div>
  );
}

export default App;
