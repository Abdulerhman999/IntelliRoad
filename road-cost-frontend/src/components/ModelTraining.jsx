import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Play, RefreshCw, CheckCircle, XCircle, Clock, Database, TrendingUp } from 'lucide-react';

const ModelTraining = ({ user }) => {
  const navigate = useNavigate();
  const [status, setStatus] = useState(null);
  const [training, setTraining] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [pollingInterval, setPollingInterval] = useState(null);

  useEffect(() => {
    if (user.role !== 'admin') {
      navigate('/dashboard');
      return;
    }
    loadStatus();
    
    // Poll status every 5 seconds when training
    const interval = setInterval(() => {
      if (training) {
        loadStatus();
      }
    }, 5000);
    
    setPollingInterval(interval);
    
    return () => clearInterval(interval);
  }, [training]);

  const loadStatus = async () => {
    try {
      const response = await axios.get(
        `http://localhost:8000/api/admin/training-status?admin_id=${user.user_id}`
      );
      setStatus(response.data);
      
      // Stop training state if completed or failed
      if (response.data.latest_training && 
          response.data.latest_training.status !== 'in_progress') {
        setTraining(false);
      }
    } catch (err) {
      console.error('Failed to load status:', err);
    }
  };

  const handleRetrain = async () => {
    if (!window.confirm(
      `Retrain the ML model with ${status.training_data_count} records? This will take 5-10 minutes.`
    )) {
      return;
    }

    setError('');
    setSuccess('');
    setTraining(true);

    try {
      const response = await axios.post(
        `http://localhost:8000/api/admin/retrain-model?admin_id=${user.user_id}`
      );
      
      setSuccess('Model retraining started! This will take several minutes...');
      loadStatus();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start retraining');
      setTraining(false);
    }
  };

  if (!status) {
    return <div className="loading">Loading training status...</div>;
  }

  const StatusBadge = ({ status }) => {
    const styles = {
      completed: { bg: '#e8f5e9', color: '#2e7d32', icon: CheckCircle },
      in_progress: { bg: '#fff3e0', color: '#f57c00', icon: Clock },
      failed: { bg: '#ffebee', color: '#c62828', icon: XCircle }
    };
    
    const style = styles[status] || styles.failed;
    const Icon = style.icon;
    
    return (
      <span style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.5rem 1rem',
        background: style.bg,
        color: style.color,
        borderRadius: '20px',
        fontWeight: '600'
      }}>
        <Icon size={16} />
        {status.replace('_', ' ').toUpperCase()}
      </span>
    );
  };

  return (
    <div className="form-container">
      <div className="form-card" style={{ maxWidth: '1000px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
          <button 
            className="btn-secondary" 
            style={{ width: 'auto', padding: '0.5rem 1rem' }}
            onClick={() => navigate('/dashboard')}
          >
            <ArrowLeft size={20} />
          </button>
          <h2 className="form-title" style={{ marginBottom: 0 }}>
            <TrendingUp size={28} />
            ML Model Training
          </h2>
        </div>

        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}

        {/* Training Data Status */}
        <div style={{
          background: status.can_retrain ? '#e8f5e9' : '#fff3e0',
          padding: '1.5rem',
          borderRadius: '10px',
          marginBottom: '2rem',
          borderLeft: `4px solid ${status.can_retrain ? '#43a047' : '#ff9800'}`
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ color: '#333', marginBottom: '0.5rem' }}>
                <Database size={20} style={{ display: 'inline', marginRight: '0.5rem' }} />
                Training Data Status
              </h3>
              <p style={{ color: '#666', margin: 0 }}>
                Current Records: <strong>{status.training_data_count}</strong> / 
                Minimum Required: <strong>{status.min_required}</strong>
              </p>
            </div>
            {status.can_retrain ? (
              <CheckCircle size={32} color="#43a047" />
            ) : (
              <XCircle size={32} color="#ff9800" />
            )}
          </div>
          
          {!status.can_retrain && (
            <div style={{ marginTop: '1rem', padding: '1rem', background: 'white', borderRadius: '8px' }}>
              <p style={{ margin: 0, color: '#666' }}>
                You need <strong>{status.min_required - status.training_data_count}</strong> more 
                training records to retrain the model.
              </p>
            </div>
          )}
        </div>

        {/* Latest Training Status */}
        {status.latest_training && (
          <div style={{
            background: 'white',
            padding: '1.5rem',
            borderRadius: '10px',
            marginBottom: '2rem',
            border: '2px solid #e0e0e0'
          }}>
            <h3 style={{ color: '#2e7d32', marginBottom: '1rem' }}>Latest Training Session</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', color: '#666', fontSize: '0.9rem', marginBottom: '0.3rem' }}>
                  Status
                </label>
                <StatusBadge status={status.latest_training.status} />
              </div>
              <div>
                <label style={{ display: 'block', color: '#666', fontSize: '0.9rem', marginBottom: '0.3rem' }}>
                  Records Used
                </label>
                <strong>{status.latest_training.training_data_count}</strong>
              </div>
              <div>
                <label style={{ display: 'block', color: '#666', fontSize: '0.9rem', marginBottom: '0.3rem' }}>
                  Started At
                </label>
                <span>{status.latest_training.started_at || 'N/A'}</span>
              </div>
              <div>
                <label style={{ display: 'block', color: '#666', fontSize: '0.9rem', marginBottom: '0.3rem' }}>
                  Completed At
                </label>
                <span>{status.latest_training.completed_at || 'In Progress...'}</span>
              </div>
              {status.latest_training.model_version && (
                <div style={{ gridColumn: '1 / -1' }}>
                  <label style={{ display: 'block', color: '#666', fontSize: '0.9rem', marginBottom: '0.3rem' }}>
                    Model Version
                  </label>
                  <strong>{status.latest_training.model_version}</strong>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Retrain Button */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <button
            className="btn-primary"
            onClick={handleRetrain}
            disabled={!status.can_retrain || training}
            style={{ 
              maxWidth: '400px',
              opacity: (!status.can_retrain || training) ? 0.6 : 1
            }}
          >
            {training ? (
              <>
                <RefreshCw size={20} className="spinning" style={{ marginRight: '0.5rem' }} />
                Training in Progress...
              </>
            ) : (
              <>
                <Play size={20} style={{ marginRight: '0.5rem' }} />
                Retrain ML Model
              </>
            )}
          </button>
          {training && (
            <p style={{ marginTop: '1rem', color: '#666' }}>
              This may take 5-10 minutes. Please don't close this page.
            </p>
          )}
        </div>

        {/* Training History */}
        <div>
          <h3 style={{ color: '#2e7d32', marginBottom: '1rem' }}>Training History</h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f5f5f5' }}>
                  <th style={{ padding: '1rem', textAlign: 'left' }}>Status</th>
                  <th style={{ padding: '1rem', textAlign: 'left' }}>Records</th>
                  <th style={{ padding: '1rem', textAlign: 'left' }}>Started</th>
                  <th style={{ padding: '1rem', textAlign: 'left' }}>Completed</th>
                  <th style={{ padding: '1rem', textAlign: 'left' }}>Version</th>
                </tr>
              </thead>
              <tbody>
                {status.training_history.map((log, idx) => (
                  <tr key={log.log_id} style={{ borderBottom: '1px solid #e0e0e0' }}>
                    <td style={{ padding: '1rem' }}>
                      <StatusBadge status={log.status} />
                    </td>
                    <td style={{ padding: '1rem' }}>{log.training_data_count}</td>
                    <td style={{ padding: '1rem' }}>{log.started_at}</td>
                    <td style={{ padding: '1rem' }}>{log.completed_at || 'In Progress'}</td>
                    <td style={{ padding: '1rem' }}>{log.model_version || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModelTraining;