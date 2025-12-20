import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, FileText, Leaf, Lightbulb, Trash2, CheckCircle, XCircle, DollarSign } from 'lucide-react';

const ProjectDetailsWithTabs = ({ user }) => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('overview'); // overview, boq, climate, recommendations
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    loadProjectDetails();
  }, [projectId]);

  const loadProjectDetails = async () => {
    try {
      const response = await axios.get(`http://localhost:8000/api/project/${projectId}/details`);
      setData(response.data);
    } catch (error) {
      console.error('Error loading project:', error);
      alert('Failed to load project details');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this project? This action cannot be undone.')) {
      return;
    }

    setDeleting(true);
    try {
      await axios.delete(`http://localhost:8000/api/project/${projectId}?user_id=${user.user_id}`);
      alert('Project deleted successfully');
      navigate('/dashboard');
    } catch (error) {
      console.error('Error deleting project:', error);
      alert('Failed to delete project: ' + error.response?.data?.detail);
      setDeleting(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading project details...</div>;
  }

  if (!data || !data.project) {
    return <div className="error-message">Project not found</div>;
  }

  const { project, boq, climate_impact, recommendations } = data;

  // Group BOQ by category
  const boqByCategory = boq.reduce((acc, item) => {
    const cat = item.category || 'Other';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(item);
    return acc;
  }, {});

  // Group recommendations by group
  const recsByGroup = recommendations.reduce((acc, rec) => {
    if (!acc[rec.group]) acc[rec.group] = [];
    acc[rec.group].push(rec);
    return acc;
  }, {});

  const totalBoqCost = boq.reduce((sum, item) => sum + item.total_cost, 0);
  const totalCO2 = climate_impact.reduce((sum, item) => sum + item.co2_kg, 0) / 1000; // tons

  return (
    <div className="dashboard-container">
      {/* Header */}
      <div className="dashboard-header">
        <div>
          <button 
            className="btn-secondary" 
            style={{ width: 'auto', padding: '0.5rem 1rem', marginBottom: '1rem' }}
            onClick={() => navigate('/dashboard')}
          >
            <ArrowLeft size={20} />
            Back
          </button>
          <h1 className="dashboard-title">{project.project_name}</h1>
          <p style={{ color: '#666', marginTop: '0.5rem' }}>
            {project.location} ({project.location_type})
          </p>
        </div>
        <button 
          className="btn-delete" 
          onClick={handleDelete}
          disabled={deleting}
          style={{
            background: '#c62828',
            color: 'white',
            padding: '0.8rem 1.5rem',
            borderRadius: '8px',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}
        >
          <Trash2 size={18} />
          {deleting ? 'Deleting...' : 'Delete Project'}
        </button>
      </div>

      {/* Summary Cards */}
      <div className="summary-cards" style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', 
        gap: '1.5rem',
        marginBottom: '2rem'
      }}>
        <div className="summary-card" style={{
          background: 'white',
          padding: '1.5rem',
          borderRadius: '10px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          borderLeft: '4px solid #43a047'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <DollarSign size={20} color="#43a047" />
            <span style={{ color: '#666', fontSize: '0.9rem' }}>Total Cost</span>
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '700', color: '#2e7d32' }}>
            PKR {project.predicted_cost_pkr.toLocaleString()}
          </div>
        </div>

        <div className="summary-card" style={{
          background: 'white',
          padding: '1.5rem',
          borderRadius: '10px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          borderLeft: '4px solid #ff9800'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <Leaf size={20} color="#ff9800" />
            <span style={{ color: '#666', fontSize: '0.9rem' }}>CO₂ Emissions</span>
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: '700', color: '#e65100' }}>
            {project.co2_emissions_tons.toFixed(2)} tons
          </div>
        </div>

        <div className="summary-card" style={{
          background: 'white',
          padding: '1.5rem',
          borderRadius: '10px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          borderLeft: `4px solid ${project.budget_status === 'Within Budget' ? '#43a047' : '#c62828'}`
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            {project.budget_status === 'Within Budget' ? (
              <CheckCircle size={20} color="#43a047" />
            ) : (
              <XCircle size={20} color="#c62828" />
            )}
            <span style={{ color: '#666', fontSize: '0.9rem' }}>Budget Status</span>
          </div>
          <div style={{ 
            fontSize: '1.3rem', 
            fontWeight: '700', 
            color: project.budget_status === 'Within Budget' ? '#2e7d32' : '#c62828'
          }}>
            {project.budget_status}
          </div>
          <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '0.5rem' }}>
            {project.budget_status === 'Within Budget' 
              ? `PKR ${project.budget_difference.toLocaleString()} under budget`
              : `PKR ${Math.abs(project.budget_difference).toLocaleString()} over budget`
            }
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="project-tabs" style={{
        display: 'flex',
        gap: '0.5rem',
        borderBottom: '2px solid #e0e0e0',
        marginBottom: '2rem'
      }}>
        {[
          { id: 'overview', label: 'Overview', icon: FileText },
          { id: 'boq', label: 'BOQ & Prices', icon: DollarSign },
          { id: 'climate', label: 'Climate Impact', icon: Leaf },
          { id: 'recommendations', label: 'Recommendations', icon: Lightbulb }
        ].map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              className={`project-tab ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '1rem 1.5rem',
                background: activeTab === tab.id ? '#f1f8e9' : 'transparent',
                border: 'none',
                borderBottom: activeTab === tab.id ? '3px solid #43a047' : '3px solid transparent',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                color: activeTab === tab.id ? '#2e7d32' : '#666',
                fontWeight: activeTab === tab.id ? '600' : '400'
              }}
            >
              <Icon size={18} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="tab-content" style={{ background: 'white', padding: '2rem', borderRadius: '10px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="overview-content">
            <h3 style={{ color: '#2e7d32', marginBottom: '1.5rem' }}>Project Information</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1.5rem' }}>
              <div><strong>Company:</strong> {project.parent_company}</div>
              <div><strong>Project Type:</strong> {project.project_type.replace('_', ' ').toUpperCase()}</div>
              <div><strong>Road Length:</strong> {project.road_length_km} km</div>
              <div><strong>Road Width:</strong> {project.road_width_m} m</div>
              <div><strong>Area:</strong> {project.area_hectares.toFixed(2)} hectares</div>
              <div><strong>Traffic Volume:</strong> {project.traffic_volume.toUpperCase()}</div>
              <div><strong>Soil Type:</strong> {project.soil_type.toUpperCase()}</div>
              <div><strong>Max Budget:</strong> PKR {project.max_budget_pkr.toLocaleString()}</div>
            </div>
          </div>
        )}

        {/* BOQ Tab */}
        {activeTab === 'boq' && (
          <div className="boq-content">
            <h3 style={{ color: '#2e7d32', marginBottom: '1.5rem' }}>Bill of Quantities (BOQ)</h3>
            {Object.entries(boqByCategory).map(([category, items]) => (
              <div key={category} style={{ marginBottom: '2rem' }}>
                <h4 style={{ 
                  color: '#555', 
                  borderBottom: '1px solid #e0e0e0', 
                  paddingBottom: '0.5rem',
                  marginBottom: '1rem'
                }}>
                  {category}
                </h4>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: '#f5f5f5' }}>
                      <th style={{ padding: '0.75rem', textAlign: 'left' }}>Material</th>
                      <th style={{ padding: '0.75rem', textAlign: 'right' }}>Quantity</th>
                      <th style={{ padding: '0.75rem', textAlign: 'left' }}>Unit</th>
                      <th style={{ padding: '0.75rem', textAlign: 'right' }}>Unit Price</th>
                      <th style={{ padding: '0.75rem', textAlign: 'right' }}>Total Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((item, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #f0f0f0' }}>
                        <td style={{ padding: '0.75rem' }}>{item.material_name}</td>
                        <td style={{ padding: '0.75rem', textAlign: 'right' }}>{item.quantity.toFixed(2)}</td>
                        <td style={{ padding: '0.75rem' }}>{item.unit}</td>
                        <td style={{ padding: '0.75rem', textAlign: 'right' }}>PKR {item.unit_price.toLocaleString()}</td>
                        <td style={{ padding: '0.75rem', textAlign: 'right', fontWeight: '600' }}>
                          PKR {item.total_cost.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
            <div style={{ 
              marginTop: '2rem', 
              padding: '1rem', 
              background: '#e8f5e9', 
              borderRadius: '8px',
              textAlign: 'right'
            }}>
              <strong style={{ fontSize: '1.2rem', color: '#2e7d32' }}>
                Total BOQ Cost: PKR {totalBoqCost.toLocaleString()}
              </strong>
            </div>
          </div>
        )}

        {/* Climate Tab */}
        {activeTab === 'climate' && (
          <div className="climate-content">
            <h3 style={{ color: '#2e7d32', marginBottom: '1.5rem' }}>Climate Impact Breakdown</h3>
            <div style={{ 
              background: '#fff3e0', 
              padding: '1.5rem', 
              borderRadius: '8px',
              marginBottom: '2rem',
              borderLeft: '4px solid #ff9800'
            }}>
              <div style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>
                <strong>Total CO₂ Emissions:</strong> {totalCO2.toFixed(2)} tons
              </div>
              <div style={{ fontSize: '0.9rem', color: '#666' }}>
                Equivalent to planting {Math.ceil(totalCO2 * 20)} trees to offset
              </div>
            </div>
            
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f5f5f5' }}>
                  <th style={{ padding: '0.75rem', textAlign: 'left' }}>Material</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right' }}>Quantity (kg)</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right' }}>CO₂ (kg)</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right' }}>% of Total</th>
                </tr>
              </thead>
              <tbody>
                {climate_impact
                  .sort((a, b) => b.co2_kg - a.co2_kg)
                  .map((item, idx) => {
                    const percent = (item.co2_kg / (totalCO2 * 1000)) * 100;
                    return (
                      <tr key={idx} style={{ borderBottom: '1px solid #f0f0f0' }}>
                        <td style={{ padding: '0.75rem' }}>{item.material_name}</td>
                        <td style={{ padding: '0.75rem', textAlign: 'right' }}>{item.quantity_kg.toFixed(2)}</td>
                        <td style={{ padding: '0.75rem', textAlign: 'right', fontWeight: '600' }}>
                          {item.co2_kg.toFixed(2)}
                        </td>
                        <td style={{ padding: '0.75rem', textAlign: 'right' }}>{percent.toFixed(1)}%</td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        )}

        {/* Recommendations Tab */}
        {activeTab === 'recommendations' && (
          <div className="recommendations-content">
            <h3 style={{ color: '#2e7d32', marginBottom: '1.5rem' }}>Ways to Reduce Climate Impact</h3>
            {Object.entries(recsByGroup).map(([group, recs]) => (
              <div key={group} style={{ marginBottom: '2rem' }}>
                <h4 style={{ 
                  color: '#555', 
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  marginBottom: '1rem'
                }}>
                  <Lightbulb size={20} color="#ff9800" />
                  {group}
                </h4>
                <ul style={{ paddingLeft: '1.5rem' }}>
                  {recs.map((rec, idx) => (
                    <li key={idx} style={{ marginBottom: '0.75rem', lineHeight: '1.6' }}>
                      {rec.text}
                      {rec.reduction_percent > 0 && (
                        <span style={{ 
                          marginLeft: '0.5rem',
                          background: '#e8f5e9',
                          color: '#2e7d32',
                          padding: '0.2rem 0.5rem',
                          borderRadius: '4px',
                          fontSize: '0.85rem',
                          fontWeight: '600'
                        }}>
                          -{rec.reduction_percent}% CO₂
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ProjectDetailsWithTabs;