import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getProjectFullDetails, downloadPDF } from '../services/api';
import { ArrowLeft, Download, AlertTriangle, CheckCircle, Leaf } from 'lucide-react';

const ProjectViewer = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [activePage, setActivePage] = useState(1);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const result = await getProjectFullDetails(id);
        setData(result);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, [id]);

  if (loading || !data || !data.project) return <div className="loading">Loading Project Details...</div>;

  const { project, boq, recommendations } = data;

  const renderContent = () => {
    switch (activePage) {
      case 1: // Project Details
        return (
          <div className="viewer-card animate-fade">
            <h3 className="section-title">Page 1: Project Details</h3>
            <div className="detail-grid">
              <div className="detail-item"><label>Project Name</label><p>{project.project_name}</p></div>
              <div className="detail-item"><label>Location</label><p>{project.location} ({project.location_type})</p></div>
              <div className="detail-item"><label>Company</label><p>{project.company}</p></div>
              <div className="detail-item"><label>Road Dimensions</label><p>{project.length_km} km × {project.width_m} m</p></div>
              <div className="detail-item"><label>Calculated Area</label><p>{project.area_hectares?.toFixed(2)} hectares</p></div>
              <div className="detail-item"><label>Road Type</label><p>{project.project_type}</p></div>
              <div className="detail-item"><label>Traffic Volume</label><p>{project.traffic_volume}</p></div>
              <div className="detail-item"><label>Soil Type</label><p>{project.soil_type}</p></div>
              <div className="detail-item full-width"><label>Specification</label><p>{project.road_spec_text}</p></div>
            </div>
          </div>
        );

      case 2: // Budget Analysis
        const remaining = project.max_budget - project.predicted_cost;
        const percent = (remaining / project.max_budget) * 100;
        
        return (
          <div className="viewer-card animate-fade">
            <h3 className="section-title">Page 2: Budget Analysis</h3>
            <div className="budget-summary">
                <div className="budget-item">
                    <span>Maximum Budget</span>
                    <span className="amount">PKR {project.max_budget.toLocaleString()}</span>
                </div>
                <div className="budget-item highlight">
                    <span>Predicted Material Cost</span>
                    <span className="amount">PKR {project.predicted_cost.toLocaleString()}</span>
                </div>
                <div className="budget-status-row">
                    <span className={`status-pill ${project.budget_status === 'Within Budget' ? 'success' : 'danger'}`}>
                        {project.budget_status === 'Within Budget' ? <CheckCircle size={18}/> : <AlertTriangle size={18}/>}
                        {project.budget_status}
                    </span>
                    <span className="budget-remaining">
                        Remaining: PKR {Math.abs(remaining).toLocaleString()} ({Math.abs(percent).toFixed(1)}%)
                    </span>
                </div>
                <div className="note-box">
                    <p><strong>Note:</strong> This cost represents material quantities only. Labor, machinery, and contractor profit are excluded.</p>
                    <p>Typical total project multiplier: 1.8x – 2.5x</p>
                </div>
            </div>
          </div>
        );

      case 3: // Detailed BOQ
        return (
          <div className="viewer-card animate-fade">
            <h3 className="section-title">Page 3: Detailed Material Cost (BOQ)</h3>
            <div className="table-responsive">
                <table className="boq-table">
                    <thead><tr><th>Material Name</th><th>Quantity</th><th>Unit</th><th>Unit Price</th><th>Total Cost</th></tr></thead>
                    <tbody>
                    {boq.map((item, idx) => (
                        <tr key={idx}>
                        <td>{item.material_name}</td>
                        <td>{item.quantity.toFixed(2)}</td>
                        <td>{item.unit}</td>
                        <td>{item.unit_price.toLocaleString()}</td>
                        <td>{item.total_cost.toLocaleString()}</td>
                        </tr>
                    ))}
                    <tr className="table-total">
                        <td colSpan="4">Final Materials Total</td>
                        <td>PKR {project.predicted_cost.toLocaleString()}</td>
                    </tr>
                    </tbody>
                </table>
            </div>
          </div>
        );

      case 4: // Categories
        const categories = boq.reduce((acc, item) => {
            acc[item.category_name] = acc[item.category_name] || [];
            acc[item.category_name].push(item);
            return acc;
        }, {});

        return (
          <div className="viewer-card animate-fade">
             <h3 className="section-title">Page 4: Material Breakdown by Category</h3>
             <div className="category-grid">
                {Object.keys(categories).map(cat => (
                    <div key={cat} className="category-card">
                        <h4 className="category-header">{cat}</h4>
                        <ul className="category-list">
                            {categories[cat].map((m, i) => (
                                <li key={i}>
                                    <span className="cat-name">{m.material_name}</span>
                                    <span className="cat-qty">{m.quantity.toFixed(2)} {m.unit}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                ))}
             </div>
          </div>
        );

      case 5: // Environmental
        const groupedRecs = recommendations.reduce((acc, item) => {
            acc[item.group_name] = acc[item.group_name] || [];
            acc[item.group_name].push(item);
            return acc;
        }, {});

        return (
          <div className="viewer-card animate-fade">
            <h3 className="section-title">Page 5: Environmental Recommendations</h3>
            <div className="env-score-card">
                <Leaf size={32} />
                <div>
                    <h4>Climate Impact Score</h4>
                    <p>{project.climate_score.toFixed(2)} tons CO2</p>
                </div>
            </div>
            {Object.keys(groupedRecs).map(group => (
                <div key={group} className="rec-group">
                    <h4>{group}</h4>
                    <ul>
                        {groupedRecs[group].map((r, i) => (
                            <li key={i}>
                                {r.recommendation_text}
                                {r.specific_metric_value && <span className="metric-tag">{r.specific_metric_value}</span>}
                            </li>
                        ))}
                    </ul>
                </div>
            ))}
          </div>
        );

      case 6: // Reports
        return (
          <div className="viewer-card text-center animate-fade">
             <h3 className="section-title">Page 6: Reports & Exports</h3>
             <div className="pdf-export-area">
                <div className="pdf-icon">📄</div>
                <h4>Final Project Report</h4>
                <p>Download the official PDF report containing all 6 sections formatted for print.</p>
                <button className="btn-primary btn-large" onClick={() => window.open(downloadPDF(project.project_id))}>
                    <Download size={24} style={{ marginRight: '10px' }} /> 
                    Generate & Download PDF
                </button>
             </div>
          </div>
        );
      default: return null;
    }
  };

  return (
    <div className="dashboard-container">
        <div className="viewer-header">
            <button onClick={() => navigate('/dashboard')} className="btn-secondary nav-back">
                <ArrowLeft size={18} /> Back to Dashboard
            </button>
            <h2>{project.project_name}</h2>
        </div>
        
        <div className="viewer-layout">
            <div className="sidebar-nav">
                {[
                    {id: 1, label: "Project Details"},
                    {id: 2, label: "Budget Analysis"},
                    {id: 3, label: "Detailed BOQ"},
                    {id: 4, label: "Categories"},
                    {id: 5, label: "Environmental"},
                    {id: 6, label: "PDF Export"}
                ].map(page => (
                    <button 
                        key={page.id} 
                        className={`nav-item ${activePage === page.id ? 'active' : ''}`} 
                        onClick={() => setActivePage(page.id)}
                    >
                        <span className="nav-num">{page.id}</span>
                        {page.label}
                    </button>
                ))}
            </div>

            <div className="content-area">
                {renderContent()}
            </div>
        </div>
    </div>
  );
};

export default ProjectViewer;