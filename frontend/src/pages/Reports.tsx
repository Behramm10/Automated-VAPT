import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchReports, generateReport, fetchRuns } from '../api';
import { FileText, Download, Plus } from 'lucide-react';
import { format } from 'date-fns';
import { useState } from 'react';

export default function Reports() {
  const queryClient = useQueryClient();
  const { data: reports, isLoading } = useQuery({ queryKey: ['reports'], queryFn: fetchReports });
  const { data: runs } = useQuery({ queryKey: ['runs'], queryFn: fetchRuns });
  
  const generateMut = useMutation({
    mutationFn: generateReport,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] });
      setModalOpen(false);
    }
  });

  const [modalOpen, setModalOpen] = useState(false);
  const [selectedRun, setSelectedRun] = useState('');

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Reports</h1>
          <p className="page-subtitle">Generated assessment reports with LLM narratives</p>
        </div>
        <button className="btn btn-primary" onClick={() => setModalOpen(true)}>
          <Plus size={16} /> Generate Report
        </button>
      </div>

      {isLoading ? (
         <div className="loading-overlay"><div className="spinner"></div></div>
      ) : (
        <div className="card">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Report Name</th>
                  <th>Status</th>
                  <th>AI Narrative</th>
                  <th>Generated Date</th>
                  <th>Downloads</th>
                </tr>
              </thead>
              <tbody>
                {reports?.length === 0 ? (
                  <tr><td colSpan={5} className="empty-state">No reports generated</td></tr>
                ) : (
                  reports?.map((r: any) => (
                    <tr key={r.id}>
                      <td style={{ fontWeight: 600 }}>{r.name}</td>
                      <td><span className={`status-badge ${r.status === 'complete' ? 'completed' : 'running'}`}>{r.status}</span></td>
                      <td>
                        {r.llm_available ? (
                          <span className="chip" style={{ background: 'rgba(139,92,246,0.1)', color: '#a78bfa', borderColor: 'rgba(139,92,246,0.3)' }}>Llama 3B Included</span>
                        ) : (
                          <span className="text-muted">Deterministic Only</span>
                        )}
                      </td>
                      <td>{format(new Date(r.created_at), 'MMM d, yyyy HH:mm')}</td>
                      <td>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <a 
                            href={`/api/v1/reports/${r.id}/download?format=pdf`}
                            className="btn btn-ghost btn-sm"
                            target="_blank"
                            rel="noreferrer"
                            style={{ pointerEvents: r.status === 'complete' ? 'auto' : 'none', opacity: r.status === 'complete' ? 1 : 0.5 }}
                          >
                            <Download size={14} /> PDF
                          </a>
                          <a 
                            href={`/api/v1/reports/${r.id}/download?format=html`}
                            className="btn btn-ghost btn-sm"
                            target="_blank"
                            rel="noreferrer"
                            style={{ pointerEvents: r.status === 'complete' ? 'auto' : 'none', opacity: r.status === 'complete' ? 1 : 0.5 }}
                          >
                            <Download size={14} /> HTML
                          </a>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {modalOpen && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, backdropFilter: 'blur(4px)' }}>
          <div className="card" style={{ width: '450px', maxWidth: '90%' }}>
            <div className="card-header">
              <h3 className="card-title">Generate Report</h3>
            </div>
            <div className="card-body">
              <div className="form-group">
                <label className="form-label">Select Assessment Run</label>
                <select className="form-select" value={selectedRun} onChange={e => setSelectedRun(e.target.value)}>
                  <option value="">Select a run...</option>
                  {runs?.filter((r: any) => r.status === 'completed').map((r: any) => (
                    <option key={r.id} value={r.id}>{r.name} ({r.findings_count} findings)</option>
                  ))}
                </select>
              </div>
              
              <div className="alert alert-info" style={{ marginTop: '20px' }}>
                Report generation runs in the background. It will automatically attempt to use local Ollama (Llama 3B) to write the narrative sections. If unavailable, it falls back to deterministic summaries.
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '24px' }}>
                <button className="btn btn-ghost" onClick={() => setModalOpen(false)}>Cancel</button>
                <button className="btn btn-primary" onClick={() => generateMut.mutate(selectedRun)} disabled={generateMut.isPending || !selectedRun}>
                  {generateMut.isPending ? 'Starting...' : 'Generate'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
