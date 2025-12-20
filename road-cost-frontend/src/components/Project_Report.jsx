import React, { useState } from 'react';    
import { useParams, NavLink, Routes, Route, Navigate } from 'react-router-dom';
import { FileText, DollarSign, Package, Leaf, FileDown, Info } from 'lucide-react';
import ProjectDetails from './report/ProjectDetails';
import BudgetAnalysis from './report/BudgetAnalysis';
import BOQTable from './report/BOQTable';
import MaterialCategories from './report/MaterialCategories';
import EnvironmentalReport from './report/EnvironmentalReport';
import PDFExport from './report/PDFExport';
import './ProjectReport.css';

const ProjectReport = ({ user }) => {
  const { projectId } = useParams();

  const tabs = [
    { path: 'details', label: 'Project Details', icon: Info },
    { path: 'budget', label: 'Budget Analysis', icon: DollarSign },
    { path: 'boq', label: 'BOQ Table', icon: FileText },
    { path: 'materials', label: 'Material Categories', icon: Package },
    { path: 'environmental', label: 'Environmental', icon: Leaf },
    { path: 'export', label: 'PDF Export', icon: FileDown },
  ];

  return (
    <div className="report-container">
      <div className="report-header">
        <h1 className="report-title">Project Report</h1>
        <p className="report-subtitle">Detailed cost analysis and materials breakdown</p>
      </div>

      <div className="report-tabs">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <NavLink
              key={tab.path}
              to={`/project/${projectId}/report/${tab.path}`}
              className={({ isActive }) =>
                `report-tab ${isActive ? 'report-tab-active' : ''}`
              }
            >
              <Icon size={18} />
              <span>{tab.label}</span>
            </NavLink>
          );
        })}
      </div>

      <div className="report-content">
        <Routes>
          <Route path="details" element={<ProjectDetails projectId={projectId} />} />
          <Route path="budget" element={<BudgetAnalysis projectId={projectId} />} />
          <Route path="boq" element={<BOQTable projectId={projectId} />} />
          <Route path="materials" element={<MaterialCategories projectId={projectId} />} />
          <Route path="environmental" element={<EnvironmentalReport projectId={projectId} />} />
          <Route path="export" element={<PDFExport projectId={projectId} />} />
          <Route index element={<Navigate to="details" replace />} />
        </Routes>
      </div>
    </div>
  );
};

export default ProjectReport;