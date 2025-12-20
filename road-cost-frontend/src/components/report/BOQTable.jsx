import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, ArrowUpDown, Filter, Download } from 'lucide-react';

const BOQTable = ({ projectId }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: 'total_cost_pkr', direction: 'desc' });
  const [categoryFilter, setCategoryFilter] = useState('all');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get(
          `http://localhost:8000/api/projects/${projectId}/boq`
        );
        setData(response.data);
      } catch (err) {
        setError('Failed to load BOQ data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [projectId]);

  if (loading) {
    return <div className="loading">Loading BOQ table...</div>;
  }

  if (error) {
    return <div className="error-message">{error}</div>;
  }

  if (!data || !data.items) {
    return <div className="error-message">No data available</div>;
  }

  const categories = ['all', ...new Set(data.items.map(item => item.category))];

  const handleSort = (key) => {
    setSortConfig({
      key,
      direction: sortConfig.key === key && sortConfig.direction === 'desc' ? 'asc' : 'desc'
    });
  };

  const filteredItems = data.items
    .filter(item => 
      (categoryFilter === 'all' || item.category === categoryFilter) &&
      (searchTerm === '' || item.material_name.toLowerCase().includes(searchTerm.toLowerCase()))
    )
    .sort((a, b) => {
      const aVal = a[sortConfig.key];
      const bVal = b[sortConfig.key];
      
      if (typeof aVal === 'string') {
        return sortConfig.direction === 'asc' 
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }
      
      return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal;
    });

  const exportToCSV = () => {
    const headers = ['Material Name', 'Quantity', 'Unit', 'Unit Price (PKR)', 'Total Cost (PKR)', 'Category'];
    const rows = filteredItems.map(item => [
      item.material_name,
      item.quantity,
      item.unit,
      item.unit_price_pkr,
      item.total_cost_pkr,
      item.category
    ]);
    
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `boq_project_${projectId}.csv`;
    a.click();
  };

  return (
    <div className="page-content">
      <div className="section-header">
        <h2>Bill of Quantities (BOQ)</h2>
        <p>Detailed material costs and quantities</p>
      </div>

      <div className="boq-controls">
        <div className="search-box">
          <Search size={20} />
          <input
            type="text"
            placeholder="Search materials..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="filter-box">
          <Filter size={20} />
          <select 
            value={categoryFilter} 
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            {categories.map(cat => (
              <option key={cat} value={cat}>
                {cat === 'all' ? 'All Categories' : cat}
              </option>
            ))}
          </select>
        </div>

        <button className="btn-export" onClick={exportToCSV}>
          <Download size={18} />
          Export CSV
        </button>
      </div>

      <div className="boq-table-container">
        <table className="boq-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('material_name')}>
                Material Name <ArrowUpDown size={14} className="sort-icon" />
              </th>
              <th onClick={() => handleSort('quantity')}>
                Quantity <ArrowUpDown size={14} className="sort-icon" />
              </th>
              <th>Unit</th>
              <th onClick={() => handleSort('unit_price_pkr')}>
                Unit Price <ArrowUpDown size={14} className="sort-icon" />
              </th>
              <th onClick={() => handleSort('total_cost_pkr')}>
                Total Cost <ArrowUpDown size={14} className="sort-icon" />
              </th>
              <th onClick={() => handleSort('category')}>
                Category <ArrowUpDown size={14} className="sort-icon" />
              </th>
            </tr>
          </thead>
          <tbody>
            {filteredItems.map((item, index) => (
              <tr key={index}>
                <td className="material-name">{item.material_name}</td>
                <td className="quantity">{item.quantity.toLocaleString()}</td>
                <td className="unit">{item.unit}</td>
                <td className="price">PKR {item.unit_price_pkr.toLocaleString()}</td>
                <td className="total-cost">PKR {item.total_cost_pkr.toLocaleString()}</td>
                <td className="category">
                  <span className="category-badge">{item.category}</span>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="total-row">
              <td colSpan="4"><strong>TOTAL MATERIALS COST (BOQ)</strong></td>
              <td colSpan="2">
                <strong>PKR {data.total_materials_cost.toLocaleString()}</strong>
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      <div className="boq-footer">
        <p className="boq-note">
          <strong>Note:</strong> This BOQ includes material costs only. Labor, machinery, 
          equipment, and contractor overhead are NOT included.
        </p>
        <p className="boq-count">
          Showing {filteredItems.length} of {data.items.length} items
        </p>
      </div>
    </div>
  );
};

export default BOQTable;