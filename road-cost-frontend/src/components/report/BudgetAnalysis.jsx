import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { DollarSign, CheckCircle, XCircle, AlertTriangle, Info } from 'lucide-react';

const BudgetAnalysis = ({ projectId }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get(
          `http://localhost:8000/api/projects/${projectId}/budget-analysis`
        );
        setData(response.data);
      } catch (err) {
        setError('Failed to load budget analysis');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [projectId]);

  if (loading) {
    return <div className="loading">Loading budget analysis...</div>;
  }

  if (error) {
    return <div className="error-message">{error}</div>;
  }

  if (!data) {
    return <div className="error-message">No data available</div>;
  }

  const utilizationPercent = (data.predicted_cost_pkr / data.max_budget_pkr) * 100;

  return (
    <div className="page-content">
      <div className="section-header">
        <h2>Budget Analysis</h2>
        <p>Detailed budget breakdown and utilization</p>
      </div>

      <div className="budget-overview">
        <div className="budget-card">
          <div className="budget-card-header">
            <DollarSign size={28} />
            <span>Maximum Budget</span>
          </div>
          <div className="budget-card-amount">
            PKR {data.max_budget_pkr.toLocaleString()}
          </div>
        </div>

        <div className="budget-card">
          <div className="budget-card-header">
            <DollarSign size={28} />
            <span>Predicted Cost (Materials BOQ)</span>
          </div>
          <div className="budget-card-amount predicted">
            PKR {data.predicted_cost_pkr.toLocaleString()}
          </div>
        </div>

        <div className={`budget-card ${data.within_budget ? 'success' : 'danger'}`}>
          <div className="budget-card-header">
            {data.within_budget ? <CheckCircle size={28} /> : <XCircle size={28} />}
            <span>Budget Status</span>
          </div>
          <div className="budget-card-status">
            {data.within_budget ? '✓ WITHIN BUDGET' : '✗ OVER BUDGET'}
          </div>
        </div>
      </div>

      <div className="detail-section">
        <h3 className="section-title">Budget Utilization</h3>
        <div className="budget-progress-container">
          <div className="budget-progress-bar">
            <div
              className={`budget-progress-fill ${
                utilizationPercent > 100 ? 'over-budget' : 
                utilizationPercent > 90 ? 'warning' : 'success'
              }`}
              style={{ width: `${Math.min(utilizationPercent, 100)}%` }}
            >
              <span className="budget-progress-text">
                {utilizationPercent.toFixed(1)}%
              </span>
            </div>
          </div>
          <div className="budget-progress-labels">
            <span>0%</span>
            <span>50%</span>
            <span>100%</span>
          </div>
        </div>
      </div>

      {data.within_budget ? (
        <div className="detail-section">
          <h3 className="section-title">Budget Remaining</h3>
          <div className="budget-remaining-card success">
            <div className="budget-remaining-amount">
              PKR {data.budget_remaining_pkr.toLocaleString()}
            </div>
            <div className="budget-remaining-percent">
              {data.budget_remaining_percent.toFixed(1)}% of total budget remaining
            </div>
          </div>
        </div>
      ) : (
        <div className="detail-section">
          <h3 className="section-title">Budget Excess</h3>
          <div className="budget-remaining-card danger">
            <div className="budget-remaining-amount">
              PKR {data.budget_excess_pkr.toLocaleString()}
            </div>
            <div className="budget-remaining-percent">
              {data.budget_excess_percent.toFixed(1)}% over budget
            </div>
          </div>
        </div>
      )}

      <div className="detail-section">
        <h3 className="section-title">
          <Info size={20} style={{ display: 'inline', marginRight: '0.5rem' }} />
          Important Notes
        </h3>
        <div className="notes-container">
          <div className="note-card success">
            <div className="note-title">✓ What's Included</div>
            <div className="note-content">{data.notes.includes}</div>
          </div>
          <div className="note-card warning">
            <div className="note-title">⚠ What's NOT Included</div>
            <div className="note-content">{data.notes.excludes}</div>
          </div>
          <div className="note-card info">
            <div className="note-title">📊 Total Project Cost Estimate</div>
            <div className="note-content">
              Typical total project cost ranges from <strong>{data.notes.multiplier_range}</strong> of 
              this material cost estimate.
            </div>
          </div>
        </div>
      </div>

      <div className="detail-section">
        <div className="alert-box info">
          <AlertTriangle size={24} />
          <div>
            <strong>Cost Breakdown Disclaimer:</strong> This analysis represents material 
            quantities and BOQ estimated prices only. For complete project costing, additional 
            costs for labor (25-40%), equipment (15-25%), contractor overhead (15-30%), and 
            contingency (10-15%) should be added.
          </div>
        </div>
      </div>
    </div>
  );
};

export default BudgetAnalysis;