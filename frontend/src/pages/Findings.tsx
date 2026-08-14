import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchFindings, fetchFinding } from '../api';
import { ShieldAlert, X, Activity } from 'lucide-react';
import { format } from 'date-fns';

export default function Findings() {
  const { data: findings, isLoading } = useQuery({ queryKey: ['findings'], queryFn: fetchFindings });
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: detail, isLoading: loadingDetail } = useQuery({
    queryKey: ['finding', selectedId],
    queryFn: () => fetchFinding(selectedId!),
    enabled: !!selectedId,
  });

  const groupedFindings = useMemo(() => {
    if (!findings) return {};
    return findings.reduce((acc: any, finding: any) => {
      const runId = finding.run_id || 'Unknown Run';
      if (!acc[runId]) acc[runId] = [];
      acc[runId].push(finding);
      return acc;
    }, {} as Record<string, any[]>);
  }, [findings]);

  return (
    <div style={{ display: 'flex', gap: '20px', alignItems: 'flex-start' }}>
      <div style={{ flex: 1 }}>
        <div className="page-header">
          <div>
            <h1 className="page-title">Vulnerabilities & Findings</h1>
            <p className="page-subtitle">Security issues detected during assessment runs</p>
          </div>
        </div>

        {isLoading ? (
          <div className="loading-overlay"><div className="spinner"></div></div>
        ) : (
          <div className="card">
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Severity</th>
                    <th>Title</th>
                    <th>Score</th>
                    <th>Pipeline</th>
                    <th>Status</th>
                    <th>Detected</th>
                  </tr>
                </thead>
                <tbody>
                  {findings?.length === 0 ? (
                    <tr><td colSpan={6} className="empty-state">No findings detected</td></tr>
                  ) : (
                    Object.entries(groupedFindings).map(([runId, runFindings]: [string, any]) => (
                      <React.Fragment key={runId}>
                        <tr style={{ background: 'var(--bg-elevated)', borderTop: '1px solid var(--border-subtle)', borderBottom: '1px solid var(--border-subtle)' }}>
                          <td colSpan={6} style={{ padding: '8px 16px', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>
                            Run ID: <span style={{ fontFamily: 'monospace', color: 'var(--accent-blue-bright)' }}>{runId}</span>
                            <span style={{ marginLeft: '12px', color: 'var(--text-muted)' }}>({runFindings.length} finding{runFindings.length !== 1 ? 's' : ''})</span>
                          </td>
                        </tr>
                        {runFindings.map((f: any) => (
                          <tr 
                            key={f.id} 
                            onClick={() => setSelectedId(f.id)}
                            style={{ cursor: 'pointer', background: selectedId === f.id ? 'rgba(59, 130, 246, 0.1)' : 'transparent' }}
                          >
                            <td><span className={`sev-badge sev-${f.severity}`}>{f.severity}</span></td>
                            <td style={{ fontWeight: 500 }}>{f.title}</td>
                            <td>{f.risk_score.toFixed(1)}</td>
                            <td><span className="chip">{f.pipeline}</span></td>
                            <td>{f.status}</td>
                            <td>{format(new Date(f.first_seen), 'MMM d, yyyy')}</td>
                          </tr>
                        ))}
                      </React.Fragment>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {selectedId && (
        <div className="card" style={{ width: '450px', position: 'sticky', top: '80px' }}>
          {loadingDetail ? (
             <div className="loading-overlay"><div className="spinner"></div></div>
          ) : detail ? (
            <>
              <div className="card-header">
                <div>
                  <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                    <span className={`sev-badge sev-${detail.severity}`}>{detail.severity}</span>
                    <span className="chip">{detail.pipeline} pipeline</span>
                  </div>
                  <h3 className="card-title" style={{ fontSize: '16px' }}>{detail.title}</h3>
                </div>
                <button className="btn btn-ghost btn-sm" onClick={() => setSelectedId(null)}><X size={16}/></button>
              </div>
              <div className="card-body" style={{ maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' }}>
                <div style={{ marginBottom: '20px' }}>
                  <div className="metric-label" style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>Risk Score</div>
                  <div style={{ fontSize: '24px', fontWeight: 800, color: `var(--severity-${detail.severity})` }}>
                    {detail.risk_score.toFixed(1)} <span style={{ fontSize: '14px', color: 'var(--text-muted)' }}>/ 10</span>
                  </div>
                </div>

                <div style={{ marginBottom: '24px' }}>
                  <div className="metric-label" style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600, marginBottom: '8px' }}>Description</div>
                  <p style={{ fontSize: '13px', color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>{detail.description}</p>
                </div>

                <div style={{ marginBottom: '24px' }}>
                  <div className="metric-label" style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600, marginBottom: '8px' }}>Deterministic Signals</div>
                  {detail.deterministic_signals?.map((s: any, idx: number) => (
                    <div key={idx} style={{ background: 'var(--bg-secondary)', padding: '10px', borderRadius: '8px', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                        <span style={{ fontWeight: 600, fontSize: '12px', color: 'var(--accent-blue-bright)' }}>{s.type}</span>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Conf: {(s.confidence*100).toFixed(0)}%</span>
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{s.rationale}</div>
                    </div>
                  ))}
                </div>

                {detail.remediation && (
                  <div style={{ marginBottom: '24px' }}>
                    <div className="metric-label" style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600, marginBottom: '8px' }}>Remediation Guidance</div>
                    <div style={{ background: 'rgba(34,197,94,0.05)', border: '1px solid rgba(34,197,94,0.2)', padding: '12px', borderRadius: '8px', fontSize: '12px', color: 'var(--text-primary)' }}>
                      {detail.remediation}
                    </div>
                  </div>
                )}
                
                {detail.evidence_bundle && (
                  <div style={{ marginTop: '20px', paddingTop: '20px', borderTop: '1px solid var(--border-subtle)' }}>
                     <div className="metric-label" style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600, marginBottom: '8px' }}>Evidence Bundle</div>
                     <div className="json-viewer" style={{ fontSize: '10px' }}>
                       <pre>{JSON.stringify(detail.evidence_bundle, null, 2)}</pre>
                     </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="empty-state">Finding not found</div>
          )}
        </div>
      )}
    </div>
  );
}
