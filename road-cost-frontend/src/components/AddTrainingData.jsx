// AddTrainingData.jsx - Updated with Material Dropdowns
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Database, Plus, Trash2 } from 'lucide-react';

const AddTrainingData = ({ user }) => {
  const navigate = useNavigate();
  
  // State for available materials from database
  const [availableMaterials, setAvailableMaterials] = useState([]);
  const [loadingMaterials, setLoadingMaterials] = useState(true);
  
  const [formData, setFormData] = useState({
    tender_no: '',
    project_name: '',
    organization: '',
    location: '',
    location_type: 'plain',
    parent_company: '',
    road_length_km: '',
    road_width_m: '',
    project_type: 'highway',
    traffic_volume: 'medium',
    soil_type: 'normal',
    actual_cost_pkr: '',
  });

  const [boqItems, setBoqItems] = useState([
    { material_id: '', quantity: '', unit_price: '' }
  ]);

  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  // Load available materials from database
  useEffect(() => {
    loadMaterials();
  }, []);

  const loadMaterials = async () => {
    try {
      const response = await axios.get(
        `http://localhost:8000/api/admin/materials-prices?admin_id=${user.user_id}`
      );
      setAvailableMaterials(response.data);
      setLoadingMaterials(false);
    } catch (error) {
      console.error('Failed to load materials:', error);
      setError('Failed to load materials list');
      setLoadingMaterials(false);
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setError('');
  };

  const handleBoqChange = (index, field, value) => {
    const newBoqItems = [...boqItems];
    newBoqItems[index][field] = value;
    
    // If material_id changes, auto-populate unit from database
    if (field === 'material_id' && value) {
      const selectedMaterial = availableMaterials.find(m => m.material_id === parseInt(value));
      // Unit is read-only from database, no need to set it in state
    }
    
    setBoqItems(newBoqItems);
  };

  const addBoqItem = () => {
    setBoqItems([...boqItems, { material_id: '', quantity: '', unit_price: '' }]);
  };

  const removeBoqItem = (index) => {
    if (boqItems.length > 1) {
      setBoqItems(boqItems.filter((_, i) => i !== index));
    }
  };

  const getSelectedMaterial = (materialId) => {
    return availableMaterials.find(m => m.material_id === parseInt(materialId));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    // Validate BOQ items
    const validBoqItems = boqItems.filter(item => 
      item.material_id && item.quantity && item.unit_price
    );

    if (validBoqItems.length === 0) {
      setError('Please add at least one valid BOQ item');
      return;
    }

    setLoading(true);

    try {
      // Build BOQ items with material names and units from database
      const processedBoqItems = validBoqItems.map(item => {
        const material = getSelectedMaterial(item.material_id);
        return {
          material_name: material.material_name,
          quantity: parseFloat(item.quantity),
          unit: material.unit, // Use unit from database
          unit_price: parseFloat(item.unit_price)
        };
      });

      const trainingData = {
        ...formData,
        road_length_km: parseFloat(formData.road_length_km),
        road_width_m: parseFloat(formData.road_width_m),
        actual_cost_pkr: parseFloat(formData.actual_cost_pkr),
        boq_items: processedBoqItems
      };

      await axios.post(
        `http://localhost:8000/api/admin/add-training-data?admin_id=${user.user_id}`,
        trainingData
      );

      setSuccess('Training data added successfully! You can now retrain the model.');
      
      // Reset form
      setFormData({
        tender_no: '',
        project_name: '',
        organization: '',
        location: '',
        location_type: 'plain',
        parent_company: '',
        road_length_km: '',
        road_width_m: '',
        project_type: 'highway',
        traffic_volume: 'medium',
        soil_type: 'normal',
        actual_cost_pkr: '',
      });
      setBoqItems([{ material_id: '', quantity: '', unit_price: '' }]);

      setTimeout(() => navigate('/dashboard'), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add training data');
    } finally {
      setLoading(false);
    }
  };

  if (loadingMaterials) {
    return <div className="loading">Loading materials...</div>;
  }

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
            <Database size={28} />
            Add Historical Project Data
          </h2>
        </div>

        {/* Info Banner */}
        <div style={{
          background: '#e3f2fd',
          padding: '1rem',
          borderRadius: '8px',
          marginBottom: '2rem',
          borderLeft: '4px solid #2196f3'
        }}>
          <strong style={{ color: '#1565c0' }}>Important:</strong> Material names and units are 
          automatically loaded from the database to ensure data consistency for ML training.
        </div>

        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}

        <form onSubmit={handleSubmit}>
          <h3 style={{ color: '#2e7d32', marginBottom: '1rem' }}>Project Information</h3>
          <div className="form-grid">
            {/* Project fields - same as before */}
            <div className="form-group">
              <label className="form-label">Tender Number *</label>
              <input
                type="text"
                name="tender_no"
                className="form-input"
                placeholder="e.g., PPRA-2024-123"
                value={formData.tender_no}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Project Name *</label>
              <input
                type="text"
                name="project_name"
                className="form-input"
                placeholder="e.g., M-2 Highway Project"
                value={formData.project_name}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Organization *</label>
              <input
                type="text"
                name="organization"
                className="form-input"
                placeholder="e.g., NHA"
                value={formData.organization}
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
              <label className="form-label">Parent Company *</label>
              <input
                type="text"
                name="parent_company"
                className="form-input"
                placeholder="e.g., NHA"
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
              <label className="form-label">Traffic Volume</label>
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
              <label className="form-label">Actual Project Cost (PKR) *</label>
              <input
                type="number"
                name="actual_cost_pkr"
                className="form-input"
                placeholder="e.g., 50000000"
                value={formData.actual_cost_pkr}
                onChange={handleChange}
                min="0"
                step="1000"
                required
              />
            </div>
          </div>

          <div style={{ marginTop: '2rem', marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ color: '#2e7d32', marginBottom: 0 }}>Bill of Quantities (BOQ)</h3>
            <button
              type="button"
              className="btn-secondary"
              style={{ width: 'auto', padding: '0.5rem 1rem' }}
              onClick={addBoqItem}
            >
              <Plus size={18} style={{ marginRight: '0.5rem' }} />
              Add Item
            </button>
          </div>

          {/* BOQ Items with Dropdowns */}
          {boqItems.map((item, index) => {
            const selectedMaterial = getSelectedMaterial(item.material_id);
            
            return (
              <div key={index} style={{ 
                background: '#f9f9f9', 
                padding: '1rem', 
                borderRadius: '8px', 
                marginBottom: '1rem',
                border: '2px solid #e8f5e9'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                  <strong style={{ color: '#2e7d32' }}>Item {index + 1}</strong>
                  {boqItems.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeBoqItem(index)}
                      style={{ 
                        background: 'none', 
                        border: 'none', 
                        color: '#c62828', 
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.3rem'
                      }}
                    >
                      <Trash2 size={16} />
                      Remove
                    </button>
                  )}
                </div>
                
                <div className="form-grid">
                  {/* Material Dropdown */}
                  <div className="form-group">
                    <label className="form-label">Material Name *</label>
                    <select
                      className="form-select"
                      value={item.material_id}
                      onChange={(e) => handleBoqChange(index, 'material_id', e.target.value)}
                      required
                    >
                      <option value="">-- Select Material --</option>
                      {availableMaterials.map(material => (
                        <option key={material.material_id} value={material.material_id}>
                          {material.material_name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Unit Display (Read-only) */}
                  <div className="form-group">
                    <label className="form-label">Unit (Auto-filled)</label>
                    <input
                      type="text"
                      className="form-input"
                      value={selectedMaterial ? selectedMaterial.unit : ''}
                      disabled
                      style={{ background: '#e0e0e0', cursor: 'not-allowed' }}
                      placeholder="Select material first"
                    />
                  </div>

                  {/* Quantity */}
                  <div className="form-group">
                    <label className="form-label">Quantity *</label>
                    <input
                      type="number"
                      className="form-input"
                      placeholder="e.g., 1000"
                      value={item.quantity}
                      onChange={(e) => handleBoqChange(index, 'quantity', e.target.value)}
                      step="0.01"
                      min="0"
                      required
                    />
                  </div>

                  {/* Unit Price */}
                  <div className="form-group">
                    <label className="form-label">Unit Price (PKR) *</label>
                    <input
                      type="number"
                      className="form-input"
                      placeholder="e.g., 1550"
                      value={item.unit_price}
                      onChange={(e) => handleBoqChange(index, 'unit_price', e.target.value)}
                      step="0.01"
                      min="0"
                      required
                    />
                  </div>
                </div>

                {/* Material Info Display */}
                {selectedMaterial && (
                  <div style={{
                    marginTop: '0.5rem',
                    padding: '0.5rem',
                    background: '#e8f5e9',
                    borderRadius: '4px',
                    fontSize: '0.85rem',
                    color: '#2e7d32'
                  }}>
                    <strong>Selected:</strong> {selectedMaterial.material_name} 
                    ({selectedMaterial.unit}) - 
                    Current Price: PKR {selectedMaterial.price_current.toLocaleString()}
                  </div>
                )}
              </div>
            );
          })}

          <div className="form-actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => navigate('/dashboard')}
            >
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Saving Training Data...' : (
                <>
                  <Database size={20} style={{ display: 'inline', marginRight: '0.5rem' }} />
                  Add Training Data
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AddTrainingData;