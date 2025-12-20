import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Plus, Calendar, DollarSign, Leaf, CheckCircle, XCircle, Eye, Filter, X } from 'lucide-react';

const Dashboard = ({ user }) => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Filters
  const [locationFilter, setLocationFilter] = useState('');
  const [minBudget, setMinBudget] = useState('');
  const [maxBudget, setMaxBudget] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }
    fetchProjects();
  }, [user, navigate, locationFilter, minBudget, maxBudget]);

  const fetchProjects = async () => {
    try {
      const params = new URLSearchParams();
      if (locationFilter) params.append('location_type', locationFilter);
      if (minBudget) params.append('min_budget', minBudget);
      if (maxBudget) params.append('max_budget', maxBudget);
      
      const url = `http://localhost:8000/api/projects/${user.user_id}${params.toString() ? '?' + params.toString() : ''}`;
      const response = await axios.get(url);
      setProjects(response.data);
    } catch (error) {
      console.error('Error fetching projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetails = (projectId) => {
    navigate(`/project/${projectId}/details`);
  };

  const clearFilters = () => {
    setLocationFilter('');
    setMinBudget('');
    setMaxBudget('');
  };

  if (loading) {
    return <div className="loading">Loading your projects...</div>;
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <h1 className="dashboard-title">My Projects</h1>
        <button className="btn-new-project" onClick={() => navigate('/new-project')}>
          <Plus size={24} />
          New Project
        </button>
      </div>

      {/* Filters Section */}
      <div className="filters-section" style={{ marginBottom: '2rem' }}>
        <button 
          className="btn-filter-toggle"
          onClick={() => setShowFilters(!showFilters)}
          style={{
            background: '#e8f5e9',
            border: '2px solid #43a047',
            padding: '0.75rem 1.5rem',
            borderRadius: '8px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontWeight: '600',
            color: '#2e7d32'
          }}
        >
          <Filter size={18} />
          {showFilters ? 'Hide Filters' : 'Show Filters'}
        </button>
        
        {showFilters && (
          <div className="filters-panel" style={{
            background: 'white',
            padding: '1.5rem',
            borderRadius: '10px',
            marginTop: '1rem',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '1rem',
            alignItems: 'end'
          }}>
            <div className="filter-group">
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#2e7d32' }}>
                Location Type:
              </label>
              <select 
                value={locationFilter} 
                onChange={(e) => setLocationFilter(e.target.value)}
                className="form-select"
              >
                <option value="">All Locations</option>
                <option value="plain">Plain</option>
                <option value="mountainous">Mountainous</option>
              </select>
            </div>
            
            <div className="filter-group">
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#2e7d32' }}>
                Min Budget (PKR):
              </label>
              <input 
                type="number" 
                value={minBudget} 
                onChange={(e) => setMinBudget(e.target.value)}
                placeholder="e.g., 1000000"
                className="form-input"
              />
            </div>
            
            <div className="filter-group">
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#2e7d32' }}>
                Max Budget (PKR):
              </label>
              <input 
                type="number" 
                value={maxBudget} 
                onChange={(e) => setMaxBudget(e.target.value)}
                placeholder="e.g., 50000000"
                className="form-input"
              />
            </div>
            
            <button 
              className="btn-clear-filters"
              onClick={clearFilters}
              style={{
                background: '#ff9800',
                color: 'white',
                border: 'none',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                justifyContent: 'center',
                fontWeight: '600'
              }}
            >
              <X size={16} />
              Clear Filters
            </button>
          </div>
        )}
      </div>

      {projects.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📊</div>
          <h2 className="empty-state-title">No Projects Yet</h2>
          <p className="empty-state-text">
            Start by creating your first project prediction
          </p>
          <button 
            className="btn-primary" 
            style={{ maxWidth: '300px', margin: '0 auto' }} 
            onClick={() => navigate('/new-project')}
          >
            <Plus size={20} style={{ display: 'inline', marginRight: '0.5rem' }} />
            Create First Project
          </button>
        </div>
      ) : (
        <div className="projects-grid">
          {projects.map((project) => (
            <div key={project.project_id} className="project-card">
              <div className="project-info">
                <h3 className="project-name">{project.project_name}</h3>
                <div className="project-date">
                  <Calendar size={16} style={{ display: 'inline', marginRight: '0.3rem' }} />
                  {project.created_at}
                </div>
                <div className="project-stats">
                  <div className="stat-item">
                    <DollarSign size={18} />
                    <span>PKR {(project.predicted_cost || 0).toLocaleString()}</span>
                  </div>
                  <div className="stat-item">
                    <Leaf size={18} />
                    <span>{(project.co2_emissions || 0).toFixed(2)} tons CO₂</span>
                  </div>
                  <div className="stat-item">
                    {project.budget_status === 'Within Budget' ? (
                      <>
                        <CheckCircle size={18} color="#43a047" />
                        <span className="badge-success">Within Budget</span>
                      </>
                    ) : (
                      <>
                        <XCircle size={18} color="#c62828" />
                        <span className="badge-danger">Over Budget</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
              <div className="project-actions" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <button 
                  className="btn-download" 
                  onClick={() => handleViewDetails(project.project_id)}
                  style={{ width: '100%' }}
                >
                  <Eye size={18} />
                  View Details
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Dashboard;