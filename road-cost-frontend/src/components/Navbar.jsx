import React from 'react';
import { useNavigate } from 'react-router-dom';
import { TrendingUp, LogOut, User } from 'lucide-react';

const Navbar = ({ user, onLogout }) => {
  const navigate = useNavigate();

  const handleLogout = () => {
    onLogout();
    navigate('/login');
  };

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <TrendingUp size={32} />
        Road Cost Predictor
      </div>
      {user && (
        <div className="navbar-user">
          <User size={20} />
          <span>{user.name}</span>
          <button className="btn-logout" onClick={handleLogout}>
            <LogOut size={18} style={{ display: 'inline', marginRight: '0.3rem' }} />
            Logout
          </button>
        </div>
      )}
    </nav>
  );
};

export default Navbar;