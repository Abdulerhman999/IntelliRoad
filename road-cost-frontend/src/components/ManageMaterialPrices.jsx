import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Save, DollarSign, Search } from 'lucide-react';

const ManageMaterialPrices = ({ user }) => {
  const navigate = useNavigate();
  const [materials, setMaterials] = useState([]);
  const [filteredMaterials, setFilteredMaterials] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [changes, setChanges] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (user.role !== 'admin') {
      navigate('/dashboard');
      return;
    }
    loadMaterials();
  }, []);

  useEffect(() => {
    if (searchTerm) {
      setFilteredMaterials(
        materials.filter(m => 
          m.material_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          m.category?.toLowerCase().includes(searchTerm.toLowerCase())
        )
      );
    } else {
      setFilteredMaterials(materials);
    }
  }, [searchTerm, materials]);

  const loadMaterials = async () => {
    try {
      const response = await axios.get(
        `http://localhost:8000/api/admin/materials-prices?admin_id=${user.user_id}`
      );
      setMaterials(response.data);
      setFilteredMaterials(response.data);
    } catch (error) {
      console.error('Error loading materials:', error);
      alert('Failed to load materials');
    } finally {
      setLoading(false);
    }
  };

  const handlePriceChange = (materialId, newPrice) => {
    setChanges({
      ...changes,
      [materialId]: parseFloat(newPrice) || 0
    });
  };

  const handleSave = async () => {
    if (Object.keys(changes).length === 0) {
      alert('No changes to save');
      return;
    }

    if (!window.confirm(`Save ${Object.keys(changes).length} price changes?`)) {
      return;
    }

    setSaving(true);
    try {
      const updates = Object.entries(changes).map(([material_id, price_current]) => ({
        material_id: parseInt(material_id),
        price_current: price_current
      }));

      await axios.post(
        `http://localhost:8000/api/admin/update-material-prices?admin_id=${user.user_id}`,
        updates
      );

      alert('Prices updated successfully!');
      setChanges({});
      loadMaterials();
    } catch (error) {
      console.error('Error saving prices:', error);
      alert('Failed to save prices: ' + error.response?.data?.detail);
    } finally {
      setSaving(false);
    }
  };

  const getCurrentPrice = (material) => {
    return changes[material.material_id] !== undefined 
      ? changes[material.material_id] 
      : material.price_current;
  };

  const hasChanges = Object.keys(changes).length > 0;

  // Group materials by category
  const groupedMaterials = filteredMaterials.reduce((acc, material) => {
    const category = material.category || 'Uncategorized';
    if (!acc[category]) acc[category] = [];
    acc[category].push(material);
    return acc;
  }, {});

  if (loading) {
    return <div className="loading">Loading materials...</div>;
  }

  return (
    <div className="form-container">
      <div className="form-card" style={{ maxWidth: '1200px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
          <button 
            className="btn-secondary" 
            style={{ width: 'auto', padding: '0.5rem 1rem' }}
            onClick={() => navigate('/admin/dashboard')}
          >
            <ArrowLeft size={20} />
          </button>
          <h2 className="form-title" style={{ marginBottom: 0 }}>
            <DollarSign size={28} />
            Manage Material Prices
          </h2>
        </div>

        {/* Search Bar */}
        <div className="search-bar" style={{ marginBottom: '2rem' }}>
          <Search size={20} />
          <input
            type="text"
            placeholder="Search materials by name or category..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ 
              flex: 1, 
              border: '2px solid #c8e6c9', 
              borderRadius: '8px', 
              padding: '0.8rem',
              fontSize: '1rem'
            }}
          />
        </div>

        {/* Changes Summary */}
        {hasChanges && (
          <div className="changes-summary" style={{ 
            background: '#fff3e0', 
            padding: '1rem', 
            borderRadius: '8px', 
            marginBottom: '2rem',
            border: '2px solid #ff9800'
          }}>
            <strong>Unsaved Changes:</strong> {Object.keys(changes).length} material(s)
            <button 
              className="btn-primary" 
              onClick={handleSave}
              disabled={saving}
              style={{ marginLeft: '1rem', width: 'auto', padding: '0.5rem 1.5rem' }}
            >
              {saving ? 'Saving...' : (
                <>
                  <Save size={18} style={{ marginRight: '0.5rem' }} />
                  Save All Changes
                </>
              )}
            </button>
          </div>
        )}

        {/* Materials by Category */}
        <div className="materials-list">
          {Object.entries(groupedMaterials).map(([category, categoryMaterials]) => (
            <div key={category} className="category-section" style={{ marginBottom: '3rem' }}>
              <h3 style={{ 
                color: '#2e7d32', 
                borderBottom: '2px solid #e8f5e9', 
                paddingBottom: '0.5rem',
                marginBottom: '1rem'
              }}>
                {category}
              </h3>
              
              <div className="materials-table">
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: '#f5f5f5' }}>
                      <th style={{ padding: '1rem', textAlign: 'left' }}>Material Name</th>
                      <th style={{ padding: '1rem', textAlign: 'left' }}>Unit</th>
                      <th style={{ padding: '1rem', textAlign: 'right' }}>2023 Price</th>
                      <th style={{ padding: '1rem', textAlign: 'right' }}>2024 Price</th>
                      <th style={{ padding: '1rem', textAlign: 'right', width: '200px' }}>Current Price (PKR)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {categoryMaterials.map(material => (
                      <tr 
                        key={material.material_id}
                        style={{ 
                          borderBottom: '1px solid #e0e0e0',
                          background: changes[material.material_id] !== undefined ? '#fff8e1' : 'white'
                        }}
                      >
                        <td style={{ padding: '1rem' }}>{material.material_name}</td>
                        <td style={{ padding: '1rem' }}>{material.unit}</td>
                        <td style={{ padding: '1rem', textAlign: 'right', color: '#666' }}>
                          {material.price_2023.toLocaleString()}
                        </td>
                        <td style={{ padding: '1rem', textAlign: 'right', color: '#666' }}>
                          {material.price_2024.toLocaleString()}
                        </td>
                        <td style={{ padding: '1rem' }}>
                          <input
                            type="number"
                            value={getCurrentPrice(material)}
                            onChange={(e) => handlePriceChange(material.material_id, e.target.value)}
                            style={{
                              width: '100%',
                              padding: '0.5rem',
                              border: '2px solid #c8e6c9',
                              borderRadius: '6px',
                              fontSize: '1rem',
                              textAlign: 'right'
                            }}
                            step="0.01"
                            min="0"
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>

        {/* Save Button at Bottom */}
        {hasChanges && (
          <div style={{ 
            position: 'sticky', 
            bottom: '20px', 
            textAlign: 'center',
            padding: '1rem',
            background: 'white',
            borderRadius: '10px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
          }}>
            <button 
              className="btn-primary" 
              onClick={handleSave}
              disabled={saving}
              style={{ maxWidth: '400px' }}
            >
              {saving ? 'Saving Changes...' : (
                <>
                  <Save size={20} style={{ marginRight: '0.5rem' }} />
                  Save {Object.keys(changes).length} Price Change(s)
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ManageMaterialPrices;