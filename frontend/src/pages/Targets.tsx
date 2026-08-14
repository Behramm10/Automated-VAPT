import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchTargets, registerTarget, discoverTarget } from '../api';
import { Target, Plus, Zap, Trash } from 'lucide-react';
import { format } from 'date-fns';

export default function Targets() {
  const queryClient = useQueryClient();
  const { data: targets, isLoading } = useQuery({ queryKey: ['targets'], queryFn: fetchTargets });
  
  const registerMut = useMutation({
    mutationFn: registerTarget,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['targets'] });
      setTargetModalOpen(false);
    }
  });

  const discoverMut = useMutation({
    mutationFn: discoverTarget,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['targets'] })
  });

  const [targetModalOpen, setTargetModalOpen] = useState(false);
  const [formData, setFormData] = useState({ name: '', description: '', adapter_type: 'mock', endpoint_url: '', model_name: '' });

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Targets</h1>
          <p className="page-subtitle">Manage AI agents and endpoints under test</p>
        </div>
        <button className="btn btn-primary" onClick={() => setTargetModalOpen(true)}>
          <Plus size={16} /> Register Target
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
                  <th>Name</th>
                  <th>Adapter</th>
                  <th>Status</th>
                  <th>Registered</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {targets?.length === 0 ? (
                  <tr><td colSpan={5} className="empty-state">No targets registered</td></tr>
                ) : (
                  targets?.map((t: any) => (
                    <tr key={t.id}>
                      <td>
                        <div style={{ fontWeight: 600 }}>{t.name}</div>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{t.description}</div>
                      </td>
                      <td><span className="chip">{t.adapter_type}</span></td>
                      <td><span className={`status-badge ${t.status === 'active' ? 'completed' : 'registered'}`}>{t.status}</span></td>
                      <td>{format(new Date(t.created_at), 'MMM d, yyyy HH:mm')}</td>
                      <td>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button 
                            className="btn btn-ghost btn-sm"
                            onClick={() => discoverMut.mutate(t.id)}
                            disabled={discoverMut.isPending}
                          >
                            <Zap size={14} /> Discover
                          </button>
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

      {targetModalOpen && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, backdropFilter: 'blur(4px)' }}>
          <div className="card" style={{ width: '450px', maxWidth: '90%' }}>
            <div className="card-header">
              <h3 className="card-title">Register Target</h3>
            </div>
            <div className="card-body">
              <div className="form-group">
                <label className="form-label">Name</label>
                <input type="text" className="form-input" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} placeholder="e.g., Customer Support Agent" />
              </div>
              <div className="form-group">
                <label className="form-label">Description</label>
                <input type="text" className="form-input" value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} />
              </div>
              <div className="form-group">
                <label className="form-label">Adapter Type</label>
                <select className="form-select" value={formData.adapter_type} onChange={e => setFormData({...formData, adapter_type: e.target.value})}>
                  <option value="mock">Mock/Sandbox (Local)</option>
                  <option value="local_python">Local Python Class</option>
                  <option value="rest">REST API</option>
                  <option value="openai_compatible">OpenAI Compatible API</option>
                </select>
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '24px' }}>
                <button className="btn btn-ghost" onClick={() => setTargetModalOpen(false)}>Cancel</button>
                <button className="btn btn-primary" onClick={() => registerMut.mutate(formData)} disabled={registerMut.isPending || !formData.name}>
                  {registerMut.isPending ? 'Registering...' : 'Register'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
