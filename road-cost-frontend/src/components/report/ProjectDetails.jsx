import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { MapPin, Building, Ruler, TrendingUp, Mountain, Users, Layers } from 'lucide-react';

const ProjectDetails = ({ projectId }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get(
          `http://localhost:8000/api/projects/${projectId}/details`
        );
        setData(response.data);
      } catch (err) {
        setError('Failed to load project details');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [projectId]);

  if (loading) {
    return <div className="loading">Loading project details...</div>;
  }

  if (error) {
    return <div className="error-message">{error}</div>;
  }

  if (!data) {
    return <div className="error-message">No data available</div>;
  }

  const InfoCard = ({ icon: Icon, label, value, unit }) => (
    <div className="info-card">
      <div className="info-card-icon">
        <Icon size={24} />
      </div>
      <div className="info-card-content">
        <div className="info-card-label">{label}</div>
        <div className="info-card-value">
          {value} {unit && <span className="info-card-unit">{unit}</span>}
        </div>
      </div>
    </div>
  );

  return (
    <div className="page-content">
      <div className="section-header">
        <h2>Project Overview</h2>
        <p>Complete project information and specifications</p>
      </div>

      <div className="detail-section">
        <h3 className="section-title">Basic Information</h3>
        <div className="info-grid">
          <InfoCard
            icon={Building}
            label="Project Name"
            value={data.project_name}
          />
          <InfoCard
            icon={MapPin}
            label="Location"
            value={`${data.location} (${data.location_type})`}
          />
          <InfoCard
            icon={Building}
            label="Company"
            value={data.parent_company}
          />
          <InfoCard
            icon={TrendingUp}
            label="Project Type"
            value={data.project_type.replace('_', ' ').toUpperCase()}
          />
        </div>
      </div>

      <div className="detail-section">
        <h3 className="section-title">Road Dimensions</h3>
        <div className="info-grid">
          <InfoCard
            icon={Ruler}
            label="Road Length"
            value={data.road_length_km}
            unit="km"
          />
          <InfoCard
            icon={Ruler}
            label="Road Width"
            value={data.road_width_m}
            unit="meters"
          />
          <InfoCard
            icon={Layers}
            label="Total Area"
            value={data.area_hectares}
            unit="hectares"
          />
        </div>
      </div>

      <div className="detail-section">
        <h3 className="section-title">Technical Specifications</h3>
        <div className="info-grid">
          <InfoCard
            icon={Mountain}
            label="Terrain Type"
            value={data.location_type.charAt(0).toUpperCase() + data.location_type.slice(1)}
          />
          <InfoCard
            icon={Users}
            label="Traffic Volume"
            value={data.traffic_volume.charAt(0).toUpperCase() + data.traffic_volume.slice(1)}
          />
          <InfoCard
            icon={Layers}
            label="Soil Type"
            value={data.soil_type.charAt(0).toUpperCase() + data.soil_type.slice(1)}
          />
        </div>
      </div>

      <div className="detail-section">
        <h3 className="section-title">Road Specification</h3>
        <div className="spec-box">
          <p>{data.road_specification}</p>
        </div>
      </div>

      <div className="detail-section">
        <h3 className="section-title">Budget Allocation</h3>
        <div className="budget-highlight">
          <div className="budget-label">Maximum Allocated Budget</div>
          <div className="budget-amount">
            PKR {data.max_budget_pkr.toLocaleString()}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProjectDetails;