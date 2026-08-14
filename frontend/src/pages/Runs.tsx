import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchRuns, createRun, startRun, fetchTargets } from '../api';
import { Play, Plus, Network, CheckCircle2 } from 'lucide-react';
import { format } from 'date-fns';
import { useNavigate } from 'react-router-dom';

export default function Runs() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: runs, isLoading } = useQuery({ queryKey: ['runs'], queryFn: fetchRuns });
  const { data: targets } = useQuery({ queryKey: ['targets'], queryFn: fetchTargets });
  
  const createMut = useMutation({
    mutationFn: createRun,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['runs'] });
      setModalOpen(false);
    }
  });

  const startMut = useMutation({
    mutationFn: startRun,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['runs'] })
  });

  const [modalOpen, setModalOpen] = useState(false);
  const [formData, setFormData] = useState({ name: '', description: '', target_id: '', pipelines: ['direct', 'indirect'] });

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Test Runs</h1>
          <p className="page-subtitle">Execute and monitor automated security assessments</p>
        </div>
        <button className="btn btn-primary" onClick={() => setModalOpen(true)}>
          <Plus size={16} /> New Assessment Run
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
                  <th>Run Name</th>
                  <th>Status</th>
                  <th>Progress</th>
                  <th>Findings (C/H/M)</th>
                  <th>Attack Success</th>
                  <th>Started</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {runs?.length === 0 ? (
                  <tr><td colSpan={7} className="empty-state">No assessment runs executed</td></tr>
                ) : (
                  runs?.map((r: any) => (
                    <tr key={r.id}>
                      <td style={{ fontWeight: 600 }}>{r.name}</td>
                      <td><span className={`status-badge ${r.status}`}>{r.status}</span></td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div style={{ flex: 1, background: 'var(--bg-elevated)', height: '6px', borderRadius: '3px' }}>
                            <div style={{ width: r.status === 'completed' ? '100%' : '50%', background: 'var(--accent-blue)', height: '100%', borderRadius: '3px' }}></div>
                          </div>
                        </div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '4px' }}>
                          {r.critical_findings > 0 && <span className="sev-badge sev-critical">{r.critical_findings}</span>}
                          {r.high_findings > 0 && <span className="sev-badge sev-high">{r.high_findings}</span>}
                          {r.medium_findings > 0 && <span className="sev-badge sev-medium">{r.medium_findings}</span>}
                          {r.critical_findings === 0 && r.high_findings === 0 && r.medium_findings === 0 && <span className="text-muted">None</span>}
                        </div>
                      </td>
                      <td>{r.status === 'completed' ? `${((r.attack_success_rate || 0)*100).toFixed(0)}%` : '-'}</td>
                      <td>{r.started_at ? format(new Date(r.started_at), 'MMM d, HH:mm') : '-'}</td>
                      <td>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          {r.status === 'registered' || r.status === 'planned' ? (
                            <button className="btn btn-ghost btn-sm" onClick={() => startMut.mutate(r.id)}><Play size={14} /> Start</button>
                          ) : r.status === 'completed' ? (
                            <button className="btn btn-ghost btn-sm" onClick={() => navigate(`/runs/${r.id}/graph`)}><Network size={14} /> Graph</button>
                          ) : null}
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
          <div className="card" style={{ width: '500px', maxWidth: '90%' }}>
            <div className="card-header">
              <h3 className="card-title">Create Assessment Run</h3>
            </div>
            <div className="card-body">
              <div className="form-group">
                <label className="form-label">Run Name</label>
                <input type="text" className="form-input" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} placeholder="e.g., Q3 Security Sweep" />
              </div>
              <div className="form-group">
                <label className="form-label">Target Agent</label>
                <select className="form-select" value={formData.target_id} onChange={e => setFormData({...formData, target_id: e.target.value})}>
                  <option value="">Select a target...</option>
                  {targets?.map((t: any) => (
                    <option key={t.id} value={t.id}>{t.name} ({t.adapter_type})</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Pipelines (Select multiple)</label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                  {['direct', 'indirect', 'multiturn', 'tool_output'].map(p => (
                    <label key={p} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
                      <input 
                        type="checkbox" 
                        checked={formData.pipelines.includes(p)}
                        onChange={(e) => {
                          if (e.target.checked) setFormData({...formData, pipelines: [...formData.pipelines, p]});
                          else setFormData({...formData, pipelines: formData.pipelines.filter(x => x !== p)});
                        }}
                      />
                      {p.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </label>
                  ))}
                </div>
              </div>
              <div className="alert alert-info" style={{ marginTop: '20px' }}>
                Note: By default, runs against mock adapters bypass the authorization gate. Real endpoints require an explicit authorization record.
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '24px' }}>
                <button className="btn btn-ghost" onClick={() => setModalOpen(false)}>Cancel</button>
                <button className="btn btn-primary" onClick={() => createMut.mutate(formData)} disabled={createMut.isPending || !formData.name || !formData.target_id}>
                  {createMut.isPending ? 'Creating...' : 'Create & Plan'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
