import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getUserProjects, downloadPDF } from '../services/api';
import { Plus, Download, Calendar, DollarSign, Leaf, CheckCircle, XCircle, FileText } from 'lucide-react';

const Dashboard = ({ user }) => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }
    fetchProjects();
  }, [user, navigate]);

  const fetchProjects = async () => {
    try {
      const data = await getUserProjects(user.user_id);
      setProjects(data);
    } catch (error) {
      console.error('Error fetching projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = (projectId) => {
    window.open(downloadPDF(projectId), '_blank');
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

      {projects.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📊</div>
          <h2 className="empty-state-title">No Projects Yet</h2>
          <p className="empty-state-text">
            Start by creating your first project prediction
          </p>
          <button className="btn-primary" style={{ maxWidth: '300px', margin: '0 auto' }} onClick={() => navigate('/new-project')}>
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
                    <span>PKR {project.predicted_cost.toLocaleString()}</span>
                  </div>
                  <div className="stat-item">
                    <Leaf size={18} />
                    <span>{project.climate_score.toFixed(2)} tons CO₂</span>
                  </div>
                  <div className="stat-item">
                    {project.within_budget ? (
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
              <button 
                className="btn-download" 
                onClick={() => handleDownload(project.project_id)}
              >
                <Download size={20} />
                Download PDF
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Dashboard;