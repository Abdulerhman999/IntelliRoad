import React, { useState } from 'react';
import { Download, FileText, CheckCircle, AlertCircle } from 'lucide-react';
import { downloadPDF } from '../../services/api';

const PDFExport = ({ projectId }) => {
  const [downloading, setDownloading] = useState(false);
  const [downloadStatus, setDownloadStatus] = useState(null);

  const handleDownload = async () => {
    setDownloading(true);
    setDownloadStatus(null);

    try {
      // Open PDF in new tab (existing functionality - UNCHANGED)
      window.open(downloadPDF(projectId), '_blank');
      
      setDownloadStatus('success');
      setTimeout(() => setDownloadStatus(null), 5000);
    } catch (error) {
      console.error('Download failed:', error);
      setDownloadStatus('error');
      setTimeout(() => setDownloadStatus(null), 5000);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="page-content">
      <div className="section-header">
        <h2>PDF Report Export</h2>
        <p>Download complete project report as PDF</p>
      </div>

      <div className="pdf-export-container">
        <div className="pdf-info-section">
          <div className="pdf-icon">
            <FileText size={64} />
          </div>
          
          <h3>Comprehensive Project Report</h3>
          <p className="pdf-description">
            Generate and download a complete PDF report containing all project details, 
            cost analysis, material breakdown, and environmental impact assessment.
          </p>

          <div className="pdf-contents">
            <h4>Report Contents:</h4>
            <ul className="contents-list">
              <li>
                <CheckCircle size={18} className="check-icon" />
                <span>Project Details & Specifications</span>
              </li>
              <li>
                <CheckCircle size={18} className="check-icon" />
                <span>ML Model Prediction Analysis</span>
              </li>
              <li>
                <CheckCircle size={18} className="check-icon" />
                <span>Budget Analysis & Cost Breakdown</span>
              </li>
              <li>
                <CheckCircle size={18} className="check-icon" />
                <span>Detailed Bill of Quantities (BOQ)</span>
              </li>
              <li>
                <CheckCircle size={18} className="check-icon" />
                <span>Material Breakdown by Category</span>
              </li>
              <li>
                <CheckCircle size={18} className="check-icon" />
                <span>Environmental Impact Assessment</span>
              </li>
              <li>
                <CheckCircle size={18} className="check-icon" />
                <span>Sustainability Recommendations</span>
              </li>
              <li>
                <CheckCircle size={18} className="check-icon" />
                <span>Risk Factors & Validity Notes</span>
              </li>
            </ul>
          </div>

          <div className="pdf-action-section">
            <button 
              className="btn-download-pdf"
              onClick={handleDownload}
              disabled={downloading}
            >
              {downloading ? (
                <>
                  <div className="spinner"></div>
                  Generating PDF...
                </>
              ) : (
                <>
                  <Download size={24} />
                  Download PDF Report
                </>
              )}
            </button>

            {downloadStatus === 'success' && (
              <div className="status-message success">
                <CheckCircle size={20} />
                <span>PDF opened successfully!</span>
              </div>
            )}

            {downloadStatus === 'error' && (
              <div className="status-message error">
                <AlertCircle size={20} />
                <span>Download failed. Please try again.</span>
              </div>
            )}
          </div>
        </div>

        <div className="pdf-notes-section">
          <h4>Important Notes:</h4>
          <div className="note-box">
            <div className="note-item">
              <strong>Report Format:</strong> Multi-page professional PDF document 
              with detailed analysis and formatted tables.
            </div>
            <div className="note-item">
              <strong>File Size:</strong> Typically 3-5 MB depending on project complexity.
            </div>
            <div className="note-item">
              <strong>Viewing:</strong> Requires PDF viewer (Adobe Reader, browser PDF viewer, etc.)
            </div>
            <div className="note-item">
              <strong>Printing:</strong> Optimized for A4 paper size with proper margins.
            </div>
          </div>

          <div className="info-box">
            <AlertCircle size={20} />
            <div>
              <strong>Data Consistency:</strong> The PDF report contains the same data 
              displayed in the web interface pages, formatted for print and offline use. 
              All calculations and recommendations are identical to what you see online.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PDFExport;