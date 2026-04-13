import React from 'react';
import { NavLink } from 'react-router-dom';
import { Sword, Dna, LayoutGrid, User } from 'lucide-react';
import '../styles/BottomNavigation.css';

const BottomNavigation = () => {
    return (
        <nav className="bottom-nav">
            <NavLink to="/" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
                <Sword size={24} />
                <span>Arena</span>
            </NavLink>
            <NavLink to="/evolution" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
                <Dna size={24} />
                <span>Evolution</span>
            </NavLink>
            <NavLink to="/library" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
                <LayoutGrid size={24} />
                <span>Library</span>
            </NavLink>
            <NavLink to="/profile" className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}>
                <User size={24} />
                <span>Profile</span>
            </NavLink>
        </nav>
    );
};

export default BottomNavigation;
