    import React, { useState, useEffect } from 'react';
    import axios from 'axios';
    import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
    import { ChevronDown, ChevronUp, Package } from 'lucide-react';

    const MaterialCategories = ({ projectId }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [expandedCategories, setExpandedCategories] = useState({});

    useEffect(() => {
        const fetchData = async () => {
        try {
            const response = await axios.get(
            `http://localhost:8000/api/projects/${projectId}/material-categories`
            );
            setData(response.data);
            
            // Expand all categories by default
            const expanded = {};
            Object.keys(response.data).forEach(cat => {
            expanded[cat] = true;
            });
            setExpandedCategories(expanded);
        } catch (err) {
            setError('Failed to load material categories');
            console.error(err);
        } finally {
            setLoading(false);
        }
        };
        fetchData();
    }, [projectId]);

    if (loading) {
        return <div className="loading">Loading material categories...</div>;
    }

    if (error) {
        return <div className="error-message">{error}</div>;
    }

    if (!data) {
        return <div className="error-message">No data available</div>;
    }

    const toggleCategory = (category) => {
        setExpandedCategories(prev => ({
        ...prev,
        [category]: !prev[category]
        }));
    };

    const COLORS = [
        '#43a047', '#66bb6a', '#81c784', '#a5d6a7',
        '#2e7d32', '#388e3c', '#4caf50', '#8bc34a'
    ];

    const chartData = Object.entries(data).map(([category, catData]) => ({
        name: category,
        value: catData.total_cost_pkr,
        percentage: catData.percentage
    }));

    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
        return (
            <div className="custom-tooltip">
            <p className="tooltip-label">{payload[0].name}</p>
            <p className="tooltip-value">
                PKR {payload[0].value.toLocaleString()}
            </p>
            <p className="tooltip-percent">
                {payload[0].payload.percentage}% of total
            </p>
            </div>
        );
        }
        return null;
    };

    return (
        <div className="page-content">
        <div className="section-header">
            <h2>Material Categories</h2>
            <p>Materials organized by construction category</p>
        </div>

        <div className="detail-section">
            <h3 className="section-title">Cost Distribution by Category</h3>
            <div className="chart-container">
            <ResponsiveContainer width="100%" height={400}>
                <PieChart>
                <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percentage }) => `${name}: ${percentage}%`}
                    outerRadius={120}
                    fill="#8884d8"
                    dataKey="value"
                >
                    {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                </PieChart>
            </ResponsiveContainer>
            </div>
        </div>

        <div className="detail-section">
            <h3 className="section-title">Category Breakdown</h3>
            <div className="categories-list">
            {Object.entries(data).map(([category, catData]) => (
                <div key={category} className="category-card">
                <div 
                    className="category-header"
                    onClick={() => toggleCategory(category)}
                >
                    <div className="category-title">
                    <Package size={20} />
                    <span>{category}</span>
                    <span className="category-count">({catData.items.length} items)</span>
                    </div>
                    <div className="category-summary">
                    <span className="category-cost">
                        PKR {catData.total_cost_pkr.toLocaleString()}
                    </span>
                    <span className="category-percentage">
                        {catData.percentage}%
                    </span>
                    {expandedCategories[category] ? (
                        <ChevronUp size={20} />
                    ) : (
                        <ChevronDown size={20} />
                    )}
                    </div>
                </div>

                {expandedCategories[category] && (
                    <div className="category-items">
                    <table className="items-table">
                        <thead>
                        <tr>
                            <th>Material</th>
                            <th>Quantity</th>
                            <th>Unit</th>
                        </tr>
                        </thead>
                        <tbody>
                        {catData.items.map((item, index) => (
                            <tr key={index}>
                            <td>{item.name}</td>
                            <td>{item.quantity.toLocaleString()}</td>
                            <td>{item.unit}</td>
                            </tr>
                        ))}
                        </tbody>
                    </table>
                    </div>
                )}
                </div>
            ))}
            </div>
        </div>

        <div className="detail-section">
            <h3 className="section-title">Category Summary</h3>
            <div className="summary-grid">
            {Object.entries(data).map(([category, catData]) => (
                <div key={category} className="summary-card">
                <div className="summary-category">{category}</div>
                <div className="summary-cost">
                    PKR {catData.total_cost_pkr.toLocaleString()}
                </div>
                <div className="summary-bar">
                    <div 
                    className="summary-bar-fill"
                    style={{ width: `${catData.percentage}%` }}
                    ></div>
                </div>
                <div className="summary-percentage">{catData.percentage}% of total</div>
                </div>
            ))}
            </div>
        </div>
        </div>
    );
    };

    export default MaterialCategories;