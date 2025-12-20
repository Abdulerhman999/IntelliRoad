// ChangePassword.jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Lock, Key, Shield } from 'lucide-react';

const ChangePassword = ({ user }) => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setError('');
    setSuccess('');
  };

  const validatePassword = () => {
    if (formData.newPassword.length < 6) {
      setError('New password must be at least 6 characters long');
      return false;
    }

    if (formData.newPassword !== formData.confirmPassword) {
      setError('New passwords do not match');
      return false;
    }

    if (formData.oldPassword === formData.newPassword) {
      setError('New password must be different from old password');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!validatePassword()) {
      return;
    }

    setLoading(true);

    try {
      await axios.post(
        `http://localhost:8000/api/auth/change-password?user_id=${user.user_id}`,
        {
          old_password: formData.oldPassword,
          new_password: formData.newPassword
        }
      );

      setSuccess('Password changed successfully! Redirecting to dashboard...');
      
      // Reset form
      setFormData({
        oldPassword: '',
        newPassword: '',
        confirmPassword: '',
      });

      setTimeout(() => navigate('/dashboard'), 2000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to change password');
    } finally {
      setLoading(false);
    }
  };

  // Password strength indicator
  const getPasswordStrength = (password) => {
    if (!password) return { strength: 0, label: '', color: '' };
    
    let strength = 0;
    if (password.length >= 6) strength++;
    if (password.length >= 8) strength++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
    if (/\d/.test(password)) strength++;
    if (/[^a-zA-Z0-9]/.test(password)) strength++;

    const levels = [
      { strength: 1, label: 'Weak', color: '#c62828' },
      { strength: 2, label: 'Fair', color: '#ff9800' },
      { strength: 3, label: 'Good', color: '#fdd835' },
      { strength: 4, label: 'Strong', color: '#66bb6a' },
      { strength: 5, label: 'Very Strong', color: '#43a047' }
    ];

    return levels.find(l => l.strength === strength) || levels[0];
  };

  const passwordStrength = getPasswordStrength(formData.newPassword);

  return (
    <div className="form-container">
      <div className="form-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
          <button 
            className="btn-secondary" 
            style={{ width: 'auto', padding: '0.5rem 1rem' }}
            onClick={() => navigate('/dashboard')}
          >
            <ArrowLeft size={20} />
          </button>
          <h2 className="form-title" style={{ marginBottom: 0 }}>
            <Lock size={28} />
            Change Password
          </h2>
        </div>

        {/* Security Notice */}
        <div style={{
          background: '#e3f2fd',
          padding: '1rem',
          borderRadius: '8px',
          marginBottom: '2rem',
          borderLeft: '4px solid #2196f3',
          display: 'flex',
          gap: '1rem',
          alignItems: 'flex-start'
        }}>
          <Shield size={20} color="#2196f3" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <strong style={{ color: '#1565c0', display: 'block', marginBottom: '0.3rem' }}>
              Password Security Tips:
            </strong>
            <ul style={{ margin: 0, paddingLeft: '1.2rem', color: '#1976d2', fontSize: '0.9rem' }}>
              <li>Use at least 8 characters</li>
              <li>Include uppercase and lowercase letters</li>
              <li>Add numbers and special characters</li>
              <li>Don't reuse old passwords</li>
            </ul>
          </div>
        </div>

        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">
              <Key size={16} style={{ display: 'inline', marginRight: '0.5rem' }} />
              Current Password *
            </label>
            <input
              type="password"
              name="oldPassword"
              className="form-input"
              placeholder="Enter your current password"
              value={formData.oldPassword}
              onChange={handleChange}
              required
              autoComplete="current-password"
            />
          </div>

          <div className="form-group">
            <label className="form-label">
              <Lock size={16} style={{ display: 'inline', marginRight: '0.5rem' }} />
              New Password *
            </label>
            <input
              type="password"
              name="newPassword"
              className="form-input"
              placeholder="Enter new password (min. 6 characters)"
              value={formData.newPassword}
              onChange={handleChange}
              required
              autoComplete="new-password"
            />
            
            {/* Password Strength Indicator */}
            {formData.newPassword && (
              <div style={{ marginTop: '0.5rem' }}>
                <div style={{
                  height: '4px',
                  background: '#e0e0e0',
                  borderRadius: '2px',
                  overflow: 'hidden'
                }}>
                  <div style={{
                    height: '100%',
                    width: `${(passwordStrength.strength / 5) * 100}%`,
                    background: passwordStrength.color,
                    transition: 'all 0.3s ease'
                  }} />
                </div>
                <div style={{
                  fontSize: '0.85rem',
                  color: passwordStrength.color,
                  marginTop: '0.3rem',
                  fontWeight: '600'
                }}>
                  Password Strength: {passwordStrength.label}
                </div>
              </div>
            )}
          </div>

          <div className="form-group">
            <label className="form-label">
              <Lock size={16} style={{ display: 'inline', marginRight: '0.5rem' }} />
              Confirm New Password *
            </label>
            <input
              type="password"
              name="confirmPassword"
              className="form-input"
              placeholder="Re-enter new password"
              value={formData.confirmPassword}
              onChange={handleChange}
              required
              autoComplete="new-password"
            />
            {formData.confirmPassword && formData.newPassword !== formData.confirmPassword && (
              <div style={{
                fontSize: '0.85rem',
                color: '#c62828',
                marginTop: '0.3rem'
              }}>
                ✗ Passwords do not match
              </div>
            )}
            {formData.confirmPassword && formData.newPassword === formData.confirmPassword && (
              <div style={{
                fontSize: '0.85rem',
                color: '#43a047',
                marginTop: '0.3rem'
              }}>
                ✓ Passwords match
              </div>
            )}
          </div>

          <div className="form-actions" style={{ marginTop: '2rem' }}>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => navigate('/dashboard')}
            >
              Cancel
            </button>
            <button 
              type="submit" 
              className="btn-primary" 
              disabled={loading || !formData.oldPassword || !formData.newPassword || !formData.confirmPassword}
            >
              {loading ? 'Changing Password...' : (
                <>
                  <Lock size={20} style={{ display: 'inline', marginRight: '0.5rem' }} />
                  Change Password
                </>
              )}
            </button>
          </div>
        </form>

        {/* Additional Info */}
        <div style={{
          marginTop: '2rem',
          padding: '1rem',
          background: '#f9f9f9',
          borderRadius: '8px',
          fontSize: '0.9rem',
          color: '#666'
        }}>
          <strong style={{ color: '#333' }}>Note:</strong> After changing your password, 
          you will be redirected to the dashboard. Please use your new password for future logins.
        </div>
      </div>
    </div>
  );
};

export default ChangePassword;