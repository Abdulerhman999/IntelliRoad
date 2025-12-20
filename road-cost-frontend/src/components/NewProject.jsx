import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, TrendingUp, CheckCircle, Download, Eye } from 'lucide-react';

const NewProject = ({ user }) => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    project_name: '',
    location: '',
    location_type: 'plain',
    max_budget_pkr: '',
    parent_company: '',
    road_length_km: '',
    road_width_m: '',
    project_type: 'highway',
    soil_type: 'normal',
    traffic_volume: 'medium',
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const projectData = {
        project_name: formData.project_name,
        location: formData.location,
        location_type: formData.location_type,
        max_budget_pkr: parseFloat(formData.max_budget_pkr),
        parent_company: formData.parent_company,
        road_length_km: parseFloat(formData.road_length_km),
        road_width_m: parseFloat(formData.road_width_m),
        project_type: formData.project_type,
        soil_type: formData.soil_type,
        traffic_volume: formData.traffic_volume,
      };

      const response = await axios.post(
        `http://localhost:8000/api/predict?user_id=${user.user_id}`,
        projectData
      );
      
      setResult(response.data);
    } catch (err) {
      console.error('Prediction error:', err);
      setError(err.response?.data?.detail || 'Prediction failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleViewReport = () => {
    navigate(`/project/${result.project_id}/details`);
  };

  if (result) {
    return (
      <div className="form-container">
        <div className="form-card" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>
            <CheckCircle size={80} color="#43a047" />
          </div>
          <h2 className="form-title" style={{ justifyContent: 'center' }}>
            Prediction Generated Successfully!
          </h2>
          <div style={{ marginTop: '2rem', marginBottom: '2rem', padding: '1.5rem', background: '#e8f5e9', borderRadius: '10px' }}>
            <h3 style={{ color: '#2e7d32', marginBottom: '1rem', fontSize: '1.3rem' }}>
              {result.project_name}
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
              <div>
                <p style={{ color: '#66bb6a', fontSize: '0.9rem' }}>Predicted Cost</p>
                <p style={{ color: '#2e7d32', fontSize: '1.5rem', fontWeight: '700' }}>
                  PKR {result.predicted_cost?.toLocaleString() || '0'}
                </p>
              </div>
              <div>
                <p style={{ color: '#66bb6a', fontSize: '0.9rem' }}>CO₂ Emissions</p>
                <p style={{ color: '#2e7d32', fontSize: '1.5rem', fontWeight: '700' }}>
                  {result.co2_emissions_tons?.toFixed(2) || '0'} tons
                </p>
              </div>
              <div>
                <p style={{ color: '#66bb6a', fontSize: '0.9rem' }}>Budget Status</p>
                <p style={{ 
                  color: result.within_budget ? '#2e7d32' : '#c62828', 
                  fontSize: '1.3rem', 
                  fontWeight: '700' 
                }}>
                  {result.within_budget ? '✓ Within Budget' : '✗ Over Budget'}
                </p>
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
            <button className="btn-primary" style={{ maxWidth: '300px' }} onClick={handleViewReport}>
              <Eye size={20} style={{ display: 'inline', marginRight: '0.5rem' }} />
              View Full Details
            </button>
            <button className="btn-secondary" style={{ maxWidth: '200px' }} onClick={() => navigate('/dashboard')}>
              Back to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

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
            <TrendingUp size={28} />
            New Project Prediction
          </h2>
        </div>

        {error && <div className="error-message">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            <div className="form-group">
              <label className="form-label">Project Name *</label>
              <input
                type="text"
                name="project_name"
                className="form-input"
                placeholder="e.g., M-2 Highway Expansion"
                value={formData.project_name}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Location *</label>
              <input
                type="text"
                name="location"
                className="form-input"
                placeholder="e.g., Lahore to Islamabad"
                value={formData.location}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Location Type *</label>
              <select
                name="location_type"
                className="form-select"
                value={formData.location_type}
                onChange={handleChange}
                required
              >
                <option value="plain">Plain Terrain</option>
                <option value="mountainous">Mountainous Terrain</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Max Budget (PKR) *</label>
              <input
                type="number"
                name="max_budget_pkr"
                className="form-input"
                placeholder="e.g., 50000000"
                value={formData.max_budget_pkr}
                onChange={handleChange}
                min="0"
                step="1000"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Parent Company *</label>
              <input
                type="text"
                name="parent_company"
                className="form-input"
                placeholder="e.g., National Highway Authority"
                value={formData.parent_company}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Road Length (KM) *</label>
              <input
                type="number"
                name="road_length_km"
                className="form-input"
                placeholder="e.g., 50"
                value={formData.road_length_km}
                onChange={handleChange}
                min="0.1"
                step="0.1"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Road Width (Meters) *</label>
              <input
                type="number"
                name="road_width_m"
                className="form-input"
                placeholder="e.g., 12"
                value={formData.road_width_m}
                onChange={handleChange}
                min="1"
                step="0.5"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Project Type *</label>
              <select
                name="project_type"
                className="form-select"
                value={formData.project_type}
                onChange={handleChange}
                required
              >
                <option value="highway">Highway</option>
                <option value="urban_road">Urban Road</option>
                <option value="rural_road">Rural Road</option>
                <option value="expressway">Expressway</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Soil Type</label>
              <select
                name="soil_type"
                className="form-select"
                value={formData.soil_type}
                onChange={handleChange}
              >
                <option value="normal">Normal</option>
                <option value="sandy">Sandy</option>
                <option value="clayey">Clayey</option>
                <option value="rocky">Rocky</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Expected Traffic Volume</label>
              <select
                name="traffic_volume"
                className="form-select"
                value={formData.traffic_volume}
                onChange={handleChange}
              >
                <option value="low">Low Traffic</option>
                <option value="medium">Medium Traffic</option>
                <option value="high">High Traffic</option>
              </select>
            </div>
          </div>

          <div className="form-actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => navigate('/dashboard')}
            >
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Generating Prediction...' : 'Predict Cost'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default NewProject;