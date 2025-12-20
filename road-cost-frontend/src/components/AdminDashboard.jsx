// AdminDashboard.jsx - COMPLETE REDESIGN
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Plus, Users, DollarSign, Database, Filter, X, TrendingUp, 
  FolderOpen, UserPlus, Settings, Activity, BarChart3, Eye, Shield
} from 'lucide-react';

const AdminDashboard = ({ user }) => {
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState('overview'); // overview, projects, employees, materials, training
    const [projects, setProjects] = useState([]);
    const [employees, setEmployees] = useState([]);
    const [stats, setStats] = useState({
        totalProjects: 0,
        totalEmployees: 0,
        totalBudget: 0,
        activeProjects: 0
    });
    const [loading, setLoading] = useState(true);

    // Filters
    const [locationFilter, setLocationFilter] = useState('');
    const [minBudget, setMinBudget] = useState('');
    const [maxBudget, setMaxBudget] = useState('');
    const [showFilters, setShowFilters] = useState(false);

    useEffect(() => {
        if (user.role !== 'admin') {
            navigate('/dashboard');
            return;
        }
        loadData();
    }, [activeTab, locationFilter, minBudget, maxBudget]);

    const loadData = async () => {
        setLoading(true);
        try {
            if (activeTab === 'overview' || activeTab === 'projects') {
                const params = new URLSearchParams();
                params.append('admin_id', user.user_id);
                if (locationFilter) params.append('location_type', locationFilter);
                if (minBudget) params.append('min_budget', minBudget);
                if (maxBudget) params.append('max_budget', maxBudget);

                const response = await axios.get(`http://localhost:8000/api/admin/all-projects?${params}`);
                setProjects(response.data);

                // Calculate stats
                setStats({
                    totalProjects: response.data.length,
                    totalEmployees: employees.length,
                    totalBudget: response.data.reduce((sum, p) => sum + p.max_budget, 0),
                    activeProjects: response.data.filter(p => p.budget_status === 'Within Budget').length
                });
            }

            if (activeTab === 'overview' || activeTab === 'employees') {
                const response = await axios.get(`http://localhost:8000/api/admin/users?admin_id=${user.user_id}`);
                setEmployees(response.data);
            }
        } catch (error) {
            console.error('Error loading data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteEmployee = async (userId) => {
        if (!window.confirm('Are you sure you want to delete this employee?')) {
            return;
        }

        try {
            await axios.delete(`http://localhost:8000/api/admin/delete-user/${userId}?admin_id=${user.user_id}`);
            loadData();
        } catch (error) {
            alert('Failed to delete employee: ' + error.response?.data?.detail);
        }
    };

    const clearFilters = () => {
        setLocationFilter('');
        setMinBudget('');
        setMaxBudget('');
    };

    const QuickActionCard = ({ icon: Icon, title, description, onClick, color = '#43a047', bgColor = '#e8f5e9' }) => (
        <div
            onClick={onClick}
            style={{
                background: 'white',
                padding: '2rem',
                borderRadius: '15px',
                boxShadow: '0 4px 15px rgba(0,0,0,0.08)',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
                border: `2px solid ${bgColor}`,
                position: 'relative',
                overflow: 'hidden'
            }}
            onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-5px)';
                e.currentTarget.style.boxShadow = '0 8px 25px rgba(67, 160, 71, 0.2)';
            }}
            onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 4px 15px rgba(0,0,0,0.08)';
            }}
        >
            <div style={{ position: 'absolute', top: -20, right: -20, opacity: 0.1 }}>
                <Icon size={120} color={color} />
            </div>
            <div style={{ position: 'relative', zIndex: 1 }}>
                <div style={{
                    width: '60px',
                    height: '60px',
                    background: bgColor,
                    borderRadius: '15px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginBottom: '1rem'
                }}>
                    <Icon size={28} color={color} />
                </div>
                <h3 style={{ color: '#333', marginBottom: '0.5rem', fontSize: '1.3rem', fontWeight: '700' }}>
                    {title}
                </h3>
                <p style={{ color: '#666', fontSize: '0.95rem', margin: 0, lineHeight: '1.5' }}>
                    {description}
                </p>
            </div>
        </div>
    );

    const StatCard = ({ icon: Icon, label, value, color = '#43a047', bgColor = '#e8f5e9' }) => (
        <div style={{
            background: 'white',
            padding: '1.5rem',
            borderRadius: '12px',
            boxShadow: '0 2px 10px rgba(0,0,0,0.06)',
            borderLeft: `4px solid ${color}`
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <div style={{
                    width: '50px',
                    height: '50px',
                    background: bgColor,
                    borderRadius: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                }}>
                    <Icon size={24} color={color} />
                </div>
                <div>
                    <div style={{ color: '#666', fontSize: '0.9rem', marginBottom: '0.3rem' }}>{label}</div>
                    <div style={{ color: '#333', fontSize: '1.8rem', fontWeight: '700' }}>{value}</div>
                </div>
            </div>
        </div>
    );

    return (
        <div className="dashboard-container">
            {/* Header */}
            <div className="dashboard-header" style={{ marginBottom: '3rem' }}>
                <div>
                    <h1 className="dashboard-title" style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>
                        Admin Dashboard
                    </h1>
                    <p style={{ color: '#666', fontSize: '1.1rem' }}>
                        Manage projects, employees, and system settings
                    </p>
                </div>
                {/* Note: Admins can only view and manage projects, not create them */}
                <div style={{
                    background: '#fff3e0',
                    padding: '1rem 1.5rem',
                    borderRadius: '10px',
                    border: '2px solid #ff9800',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    maxWidth: '400px'
                }}>
                    <Shield size={20} color="#f57c00" />
                    <div style={{ fontSize: '0.9rem', color: '#e65100' }}>
                        <strong>Admin View Only:</strong> Employees create projects
                    </div>
                </div>
            </div>

            {/* Navigation Tabs */}
            <div style={{
                display: 'flex',
                gap: '0.5rem',
                marginBottom: '3rem',
                background: 'white',
                padding: '0.5rem',
                borderRadius: '15px',
                boxShadow: '0 2px 10px rgba(0,0,0,0.06)'
            }}>
                {[
                    { id: 'overview', label: 'Overview', icon: BarChart3 },
                    { id: 'projects', label: 'All Projects', icon: FolderOpen },
                    { id: 'employees', label: 'Employees', icon: Users },
                    { id: 'materials', label: 'Material Prices', icon: DollarSign },
                    { id: 'training', label: 'ML Training', icon: TrendingUp }
                ].map(tab => {
                    const Icon = tab.icon;
                    return (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            style={{
                                flex: 1,
                                padding: '1rem 1.5rem',
                                background: activeTab === tab.id ? 'linear-gradient(135deg, #43a047 0%, #66bb6a 100%)' : 'transparent',
                                color: activeTab === tab.id ? 'white' : '#666',
                                border: 'none',
                                borderRadius: '12px',
                                cursor: 'pointer',
                                fontWeight: '600',
                                fontSize: '1rem',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '0.5rem',
                                transition: 'all 0.3s ease'
                            }}
                            onMouseEnter={(e) => {
                                if (activeTab !== tab.id) {
                                    e.currentTarget.style.background = '#f5f5f5';
                                }
                            }}
                            onMouseLeave={(e) => {
                                if (activeTab !== tab.id) {
                                    e.currentTarget.style.background = 'transparent';
                                }
                            }}
                        >
                            <Icon size={20} />
                            {tab.label}
                        </button>
                    );
                })}
            </div>

            {/* Tab Content */}
            {loading ? (
                <div className="loading">Loading...</div>
            ) : (
                <>
                    {/* Overview Tab */}
                    {activeTab === 'overview' && (
                        <div>
                            {/* Stats Cards */}
                            <div style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                                gap: '1.5rem',
                                marginBottom: '3rem'
                            }}>
                                <StatCard
                                    icon={FolderOpen}
                                    label="Total Projects"
                                    value={stats.totalProjects}
                                    color="#43a047"
                                    bgColor="#e8f5e9"
                                />
                                <StatCard
                                    icon={Users}
                                    label="Total Employees"
                                    value={stats.totalEmployees}
                                    color="#2196f3"
                                    bgColor="#e3f2fd"
                                />
                                <StatCard
                                    icon={DollarSign}
                                    label="Total Budget"
                                    value={`PKR ${(stats.totalBudget / 1000000).toFixed(1)}M`}
                                    color="#ff9800"
                                    bgColor="#fff3e0"
                                />
                                <StatCard
                                    icon={Activity}
                                    label="Active Projects"
                                    value={stats.activeProjects}
                                    color="#4caf50"
                                    bgColor="#f1f8e9"
                                />
                            </div>

                            {/* Quick Actions */}
                            <h2 style={{ color: '#2e7d32', marginBottom: '1.5rem', fontSize: '1.8rem' }}>
                                Quick Actions
                            </h2>
                            <div style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                                gap: '2rem'
                            }}>
                                <QuickActionCard
                                    icon={UserPlus}
                                    title="Create Employee"
                                    description="Add a new employee account with access credentials"
                                    onClick={() => navigate('/admin/create-user')}
                                    color="#2196f3"
                                    bgColor="#e3f2fd"
                                />
                                <QuickActionCard
                                    icon={DollarSign}
                                    title="Update Prices"
                                    description="Manage and update material prices for accurate predictions"
                                    onClick={() => navigate('/admin/manage-prices')}
                                    color="#ff9800"
                                    bgColor="#fff3e0"
                                />
                                <QuickActionCard
                                    icon={Database}
                                    title="Add Training Data"
                                    description="Import historical project data to improve ML model accuracy"
                                    onClick={() => navigate('/admin/add-training-data')}
                                    color="#9c27b0"
                                    bgColor="#f3e5f5"
                                />
                                <QuickActionCard
                                    icon={TrendingUp}
                                    title="Retrain ML Model"
                                    description="Update the prediction model with latest training data"
                                    onClick={() => navigate('/admin/model-training')}
                                    color="#43a047"
                                    bgColor="#e8f5e9"
                                />
                                <QuickActionCard
                                    icon={Settings}
                                    title="Change Password"
                                    description="Update your admin account password for security"
                                    onClick={() => navigate('/change-password')}
                                    color="#f44336"
                                    bgColor="#ffebee"
                                />
                                <QuickActionCard
                                    icon={Eye}
                                    title="View All Projects"
                                    description="Monitor and analyze projects created by employees"
                                    onClick={() => setActiveTab('projects')}
                                    color="#00bcd4"
                                    bgColor="#e0f7fa"
                                />
                            </div>
                        </div>
                    )}

                    {/* Projects Tab */}
                    {activeTab === 'projects' && (
                        <div>
                            {/* Filters */}
                            <div style={{
                                background: 'white',
                                padding: '1.5rem',
                                borderRadius: '15px',
                                boxShadow: '0 2px 10px rgba(0,0,0,0.06)',
                                marginBottom: '2rem'
                            }}>
                                <button
                                    onClick={() => setShowFilters(!showFilters)}
                                    style={{
                                        background: '#e8f5e9',
                                        border: '2px solid #43a047',
                                        padding: '0.75rem 1.5rem',
                                        borderRadius: '10px',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.5rem',
                                        fontWeight: '600',
                                        color: '#2e7d32',
                                        fontSize: '1rem'
                                    }}
                                >
                                    <Filter size={20} />
                                    {showFilters ? 'Hide Filters' : 'Show Filters'}
                                </button>

                                {showFilters && (
                                    <div style={{
                                        display: 'grid',
                                        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                                        gap: '1rem',
                                        marginTop: '1.5rem',
                                        alignItems: 'end'
                                    }}>
                                        <div>
                                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#2e7d32' }}>
                                                Location Type
                                            </label>
                                            <select value={locationFilter} onChange={(e) => setLocationFilter(e.target.value)} className="form-select">
                                                <option value="">All Locations</option>
                                                <option value="plain">Plain</option>
                                                <option value="mountainous">Mountainous</option>
                                            </select>
                                        </div>
                                        <div>
                                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#2e7d32' }}>
                                                Min Budget (PKR)
                                            </label>
                                            <input
                                                type="number"
                                                value={minBudget}
                                                onChange={(e) => setMinBudget(e.target.value)}
                                                placeholder="e.g., 1000000"
                                                className="form-input"
                                            />
                                        </div>
                                        <div>
                                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '600', color: '#2e7d32' }}>
                                                Max Budget (PKR)
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
                                            onClick={clearFilters}
                                            style={{
                                                background: '#ff9800',
                                                color: 'white',
                                                border: 'none',
                                                padding: '0.75rem 1.5rem',
                                                borderRadius: '10px',
                                                cursor: 'pointer',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '0.5rem',
                                                justifyContent: 'center',
                                                fontWeight: '600',
                                                fontSize: '1rem'
                                            }}
                                        >
                                            <X size={18} />
                                            Clear
                                        </button>
                                    </div>
                                )}
                            </div>

                            {/* Projects Grid */}
                            <div style={{ display: 'grid', gap: '1.5rem' }}>
                                {projects.length === 0 ? (
                                    <div className="empty-state">
                                        <p>No projects found</p>
                                    </div>
                                ) : (
                                    projects.map(project => (
                                        <div
                                            key={project.project_id}
                                            style={{
                                                background: 'white',
                                                padding: '2rem',
                                                borderRadius: '15px',
                                                boxShadow: '0 4px 15px rgba(0,0,0,0.08)',
                                                display: 'grid',
                                                gridTemplateColumns: '1fr auto',
                                                gap: '2rem',
                                                alignItems: 'center',
                                                transition: 'all 0.3s ease',
                                                borderLeft: '5px solid #66bb6a'
                                            }}
                                        >
                                            <div>
                                                <h3 style={{ fontSize: '1.5rem', color: '#2e7d32', fontWeight: '700', marginBottom: '0.5rem' }}>
                                                    {project.project_name}
                                                </h3>
                                                <p style={{ color: '#66bb6a', fontSize: '0.95rem', marginBottom: '1rem' }}>
                                                    By: {project.user_name} • {project.created_at}
                                                </p>
                                                <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
                                                    <div>
                                                        <span style={{ color: '#666', fontSize: '0.9rem' }}>Location</span>
                                                        <p style={{ color: '#333', fontWeight: '600', margin: '0.2rem 0' }}>
                                                            {project.location} ({project.location_type})
                                                        </p>
                                                    </div>
                                                    <div>
                                                        <span style={{ color: '#666', fontSize: '0.9rem' }}>Budget</span>
                                                        <p style={{ color: '#333', fontWeight: '600', margin: '0.2rem 0' }}>
                                                            PKR {project.max_budget.toLocaleString()}
                                                        </p>
                                                    </div>
                                                    <div>
                                                        <span style={{ color: '#666', fontSize: '0.9rem' }}>Predicted Cost</span>
                                                        <p style={{ color: '#333', fontWeight: '600', margin: '0.2rem 0' }}>
                                                            PKR {project.predicted_cost.toLocaleString()}
                                                        </p>
                                                    </div>
                                                    <div>
                                                        <span style={{ color: '#666', fontSize: '0.9rem' }}>Status</span>
                                                        <p style={{ margin: '0.2rem 0' }}>
                                                            <span className={project.budget_status === 'Within Budget' ? 'badge-success' : 'badge-danger'}>
                                                                {project.budget_status}
                                                            </span>
                                                        </p>
                                                    </div>
                                                </div>
                                            </div>
                                            <button
                                                onClick={() => navigate(`/project/${project.project_id}/details`)}
                                                style={{
                                                    background: 'linear-gradient(135deg, #43a047 0%, #66bb6a 100%)',
                                                    color: 'white',
                                                    border: 'none',
                                                    padding: '1rem 2rem',
                                                    borderRadius: '10px',
                                                    cursor: 'pointer',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.5rem',
                                                    fontWeight: '600',
                                                    fontSize: '1rem',
                                                    transition: 'all 0.3s ease'
                                                }}
                                            >
                                                <Eye size={20} />
                                                View Details
                                            </button>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    )}

                    {/* Employees Tab */}
                    {activeTab === 'employees' && (
                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                                <h2 style={{ color: '#2e7d32', fontSize: '1.8rem' }}>Employee Management</h2>
                                <button
                                    className="btn-new-project"
                                    onClick={() => navigate('/admin/create-user')}
                                >
                                    <UserPlus size={20} />
                                    Create Employee
                                </button>
                            </div>

                            <div style={{
                                background: 'white',
                                borderRadius: '15px',
                                boxShadow: '0 4px 15px rgba(0,0,0,0.08)',
                                overflow: 'hidden'
                            }}>
                                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                    <thead style={{ background: '#2e7d32', color: 'white' }}>
                                        <tr>
                                            <th style={{ padding: '1.2rem', textAlign: 'left', fontWeight: '600' }}>Name</th>
                                            <th style={{ padding: '1.2rem', textAlign: 'left', fontWeight: '600' }}>Email</th>
                                            <th style={{ padding: '1.2rem', textAlign: 'left', fontWeight: '600' }}>Phone</th>
                                            <th style={{ padding: '1.2rem', textAlign: 'left', fontWeight: '600' }}>Username</th>
                                            <th style={{ padding: '1.2rem', textAlign: 'left', fontWeight: '600' }}>Created</th>
                                            <th style={{ padding: '1.2rem', textAlign: 'center', fontWeight: '600' }}>Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {employees.map(emp => (
                                            <tr key={emp.user_id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                                                <td style={{ padding: '1.2rem' }}>{emp.name}</td>
                                                <td style={{ padding: '1.2rem' }}>{emp.email}</td>
                                                <td style={{ padding: '1.2rem' }}>{emp.phone}</td>
                                                <td style={{ padding: '1.2rem' }}>{emp.username}</td>
                                                <td style={{ padding: '1.2rem' }}>{emp.created_at}</td>
                                                <td style={{ padding: '1.2rem', textAlign: 'center' }}>
                                                    <button
                                                        onClick={() => handleDeleteEmployee(emp.user_id)}
                                                        style={{
                                                            background: '#c62828',
                                                            color: 'white',
                                                            border: 'none',
                                                            padding: '0.5rem 1rem',
                                                            borderRadius: '8px',
                                                            cursor: 'pointer',
                                                            fontWeight: '600'
                                                        }}
                                                    >
                                                        Delete
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* Materials Tab */}
                    {activeTab === 'materials' && (
                        <div style={{ textAlign: 'center', padding: '4rem 2rem' }}>
                            <div style={{
                                background: 'white',
                                padding: '3rem',
                                borderRadius: '20px',
                                boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
                                maxWidth: '600px',
                                margin: '0 auto'
                            }}>
                                <DollarSign size={80} color="#ff9800" style={{ marginBottom: '1rem' }} />
                                <h3 style={{ color: '#2e7d32', fontSize: '2rem', marginBottom: '1rem' }}>
                                    Material Price Management
                                </h3>
                                <p style={{ color: '#666', marginBottom: '2rem', fontSize: '1.1rem', lineHeight: '1.6' }}>
                                    Update and manage material prices to ensure accurate project cost predictions
                                </p>
                                <button
                                    className="btn-primary"
                                    onClick={() => navigate('/admin/manage-prices')}
                                    style={{ maxWidth: '300px', margin: '0 auto' }}
                                >
                                    <DollarSign size={20} style={{ marginRight: '0.5rem' }} />
                                    Go to Price Management
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Training Tab */}
                    {activeTab === 'training' && (
                        <div style={{ textAlign: 'center', padding: '4rem 2rem' }}>
                            <div style={{
                                background: 'white',
                                padding: '3rem',
                                borderRadius: '20px',
                                boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
                                maxWidth: '600px',
                                margin: '0 auto'
                            }}>
                                <TrendingUp size={80} color="#43a047" style={{ marginBottom: '1rem' }} />
                                <h3 style={{ color: '#2e7d32', fontSize: '2rem', marginBottom: '1rem' }}>
                                    ML Model Training
                                </h3>
                                <p style={{ color: '#666', marginBottom: '2rem', fontSize: '1.1rem', lineHeight: '1.6' }}>
                                    Add historical project data and retrain the machine learning model for improved predictions
                                </p>
                                <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
                                    <button
                                        className="btn-secondary"
                                        onClick={() => navigate('/admin/add-training-data')}
                                        style={{ width: 'auto' }}
                                    >
                                        <Database size={20} style={{ marginRight: '0.5rem' }} />
                                        Add Training Data
                                    </button>
                                    <button
                                        className="btn-primary"
                                        onClick={() => navigate('/admin/model-training')}
                                        style={{ width: 'auto' }}
                                    >
                                        <TrendingUp size={20} style={{ marginRight: '0.5rem' }} />
                                        Retrain Model
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
};

export default AdminDashboard;