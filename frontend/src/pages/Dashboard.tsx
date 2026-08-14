import { useQuery } from '@tanstack/react-query';
import { fetchDashboardSummary } from '../api';
import { Shield, Target, Play, ShieldAlert, Activity, GitBranch } from 'lucide-react';
import { format } from 'date-fns';

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({ queryKey: ['dashboard'], queryFn: fetchDashboardSummary });

  if (isLoading) return <div className="loading-overlay"><div className="spinner"></div></div>;
  if (error) return <div className="alert alert-error">Failed to load dashboard data</div>;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Security posture overview and telemetry insights</p>
        </div>
      </div>

      <div className="metric-grid">
        <div className="metric-card metric-info">
          <div className="metric-glow" style={{ background: 'var(--accent-blue)' }}></div>
          <div className="metric-label">Assessments</div>
          <div className="metric-value">{data?.total_assessments || 0}</div>
          <div className="metric-sub">{data?.active_runs || 0} active currently</div>
        </div>
        <div className="metric-card metric-critical">
          <div className="metric-glow" style={{ background: 'var(--severity-critical)' }}></div>
          <div className="metric-label">Critical Findings</div>
          <div className="metric-value">{data?.critical_findings || 0}</div>
          <div className="metric-sub">Requires immediate action</div>
        </div>
        <div className="metric-card metric-high">
          <div className="metric-glow" style={{ background: 'var(--severity-high)' }}></div>
          <div className="metric-label">High Findings</div>
          <div className="metric-value">{data?.high_findings || 0}</div>
          <div className="metric-sub">Prioritized for remediation</div>
        </div>
        <div className="metric-card metric-medium">
          <div className="metric-glow" style={{ background: 'var(--severity-medium)' }}></div>
          <div className="metric-label">Attack Success Rate</div>
          <div className="metric-value">{((data?.attack_success_rate || 0) * 100).toFixed(1)}%</div>
          <div className="metric-sub">Across all pipelines</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Recent Findings</h2>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Title</th>
                  <th>Score</th>
                  <th>Pipeline</th>
                </tr>
              </thead>
              <tbody>
                {data?.recent_findings?.length === 0 ? (
                  <tr><td colSpan={4} style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)' }}>No findings yet</td></tr>
                ) : (
                  data?.recent_findings?.map((f: any) => (
                    <tr key={f.id}>
                      <td><span className={`sev-badge sev-${f.severity}`}>{f.severity}</span></td>
                      <td style={{ fontWeight: 500 }}>{f.title}</td>
                      <td>{f.risk_score.toFixed(1)}</td>
                      <td><span className="chip">{f.pipeline}</span></td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Recent Assessment Runs</h2>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th>Run Name</th>
                  <th>Status</th>
                  <th>Findings</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {data?.recent_runs?.length === 0 ? (
                  <tr><td colSpan={4} style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)' }}>No runs yet</td></tr>
                ) : (
                  data?.recent_runs?.map((r: any) => (
                    <tr key={r.id}>
                      <td style={{ fontWeight: 500 }}>{r.name}</td>
                      <td><span className={`status-badge ${r.status}`}>{r.status}</span></td>
                      <td>{r.findings_count}</td>
                      <td>{format(new Date(r.created_at), 'MMM d, HH:mm')}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
