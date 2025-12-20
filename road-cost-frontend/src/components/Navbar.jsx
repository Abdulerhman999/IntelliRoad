// Navbar.jsx - Updated with dropdown menu for user settings
import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { TrendingUp, LogOut, User, Shield, Lock, ChevronDown } from 'lucide-react';

const Navbar = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    onLogout();
    navigate('/login');
  };

  const handleChangePassword = () => {
    setShowDropdown(false);
    navigate('/change-password');
  };

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <TrendingUp size={32} />
        Road Cost Predictor
      </div>
      {user && (
        <div className="navbar-user">
          {user.role === 'admin' && (
            <span className="badge-admin">
              <Shield size={14} style={{ marginRight: '4px' }} /> Admin
            </span>
          )}
          
          {/* User Dropdown Menu */}
          <div style={{ position: 'relative' }} ref={dropdownRef}>
            <button
              onClick={() => setShowDropdown(!showDropdown)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                background: 'rgba(255, 255, 255, 0.1)',
                border: '2px solid rgba(255, 255, 255, 0.3)',
                color: 'white',
                padding: '0.6rem 1rem',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '1rem',
                fontWeight: '600',
                transition: 'all 0.3s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.2)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
              }}
            >
              <User size={20} />
              <span>{user.name}</span>
              <ChevronDown 
                size={16} 
                style={{ 
                  transform: showDropdown ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.3s ease'
                }} 
              />
            </button>

            {/* Dropdown Menu */}
            {showDropdown && (
              <div style={{
                position: 'absolute',
                top: 'calc(100% + 0.5rem)',
                right: 0,
                background: 'white',
                borderRadius: '10px',
                boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
                minWidth: '220px',
                overflow: 'hidden',
                zIndex: 1000,
                animation: 'slideDown 0.3s ease'
              }}>
                {/* User Info Header */}
                <div style={{
                  padding: '1rem',
                  background: 'linear-gradient(135deg, #43a047 0%, #66bb6a 100%)',
                  color: 'white'
                }}>
                  <div style={{ fontWeight: '600', marginBottom: '0.2rem' }}>{user.name}</div>
                  <div style={{ fontSize: '0.85rem', opacity: 0.9 }}>{user.email}</div>
                  <div style={{ 
                    fontSize: '0.75rem', 
                    marginTop: '0.3rem',
                    padding: '0.2rem 0.5rem',
                    background: 'rgba(255, 255, 255, 0.2)',
                    borderRadius: '4px',
                    display: 'inline-block'
                  }}>
                    {user.role === 'admin' ? 'Administrator' : 'Employee'}
                  </div>
                </div>

                {/* Menu Items */}
                <div style={{ padding: '0.5rem 0' }}>
                  <button
                    onClick={handleChangePassword}
                    style={{
                      width: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.75rem',
                      padding: '0.75rem 1rem',
                      background: 'transparent',
                      border: 'none',
                      color: '#333',
                      cursor: 'pointer',
                      fontSize: '0.95rem',
                      fontWeight: '500',
                      transition: 'all 0.2s ease',
                      textAlign: 'left'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = '#f5f5f5';
                      e.currentTarget.style.color = '#43a047';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = '#333';
                    }}
                  >
                    <Lock size={18} />
                    <span>Change Password</span>
                  </button>

                  <div style={{
                    height: '1px',
                    background: '#e0e0e0',
                    margin: '0.5rem 0'
                  }} />

                  <button
                    onClick={handleLogout}
                    style={{
                      width: '100%',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.75rem',
                      padding: '0.75rem 1rem',
                      background: 'transparent',
                      border: 'none',
                      color: '#c62828',
                      cursor: 'pointer',
                      fontSize: '0.95rem',
                      fontWeight: '600',
                      transition: 'all 0.2s ease',
                      textAlign: 'left'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = '#ffebee';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    <LogOut size={18} />
                    <span>Logout</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <style jsx>{`
        @keyframes slideDown {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </nav>
  );
};

export default Navbar;