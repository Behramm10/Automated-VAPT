import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { fetchAttackGraph } from '../api';
import { ArrowLeft } from 'lucide-react';
import ForceGraph2D from 'react-force-graph-2d';
import { useEffect, useState, useRef } from 'react';

export default function AttackGraph() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const { data: graph, isLoading, error } = useQuery({ queryKey: ['graph', runId], queryFn: () => fetchAttackGraph(runId!) });
  
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  useEffect(() => {
    if (containerRef.current) {
      setDimensions({
        width: containerRef.current.clientWidth,
        height: window.innerHeight - 200
      });
    }
  }, []);

  useEffect(() => {
    if (graph) {
      const formattedNodes = graph.nodes.map((n: any) => ({
        id: n.id,
        name: n.label,
        val: n.type === 'finding' ? 15 : (n.type === 'injection_event' ? 12 : 8),
        color: n.metadata?.color || (
          n.type === 'injection_event' ? '#3b82f6' : 
          n.type === 'tool_execution' ? '#ea580c' : 
          n.type === 'behavioral_change' ? '#8b5cf6' : 
          '#64748b'
        ),
        type: n.type
      }));
      
      const formattedLinks = graph.edges.map((e: any) => ({
        source: e.source,
        target: e.target,
        label: e.label,
        color: 'rgba(148, 163, 184, 0.4)'
      }));

      setGraphData({ nodes: formattedNodes, links: formattedLinks } as any);
    }
  }, [graph]);

  if (isLoading) return <div className="loading-overlay"><div className="spinner"></div></div>;
  if (error || !graph) return <div className="alert alert-error">Graph not available or not generated yet</div>;

  return (
    <div>
      <div className="page-header" style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/runs')}><ArrowLeft size={16}/></button>
          <div>
            <h1 className="page-title">Attack Graph</h1>
            <p className="page-subtitle">Visual representation of attack flow for run {runId}</p>
          </div>
        </div>
      </div>

      <div className="graph-container" ref={containerRef} style={{ height: dimensions.height }}>
        {graphData.nodes.length > 0 ? (
          <ForceGraph2D
            width={dimensions.width}
            height={dimensions.height}
            graphData={graphData}
            nodeLabel="name"
            nodeColor="color"
            nodeRelSize={6}
            linkColor="color"
            linkDirectionalArrowLength={3.5}
            linkDirectionalArrowRelPos={1}
            linkCurvature={0.25}
            backgroundColor="#060b14"
          />
        ) : (
          <div className="empty-state" style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <p>No graph nodes found for this run.</p>
          </div>
        )}
      </div>
      
      <div style={{ display: 'flex', gap: '16px', marginTop: '16px', padding: '16px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
        <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}><strong>Nodes:</strong> {graph.node_count}</div>
        <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}><strong>Edges:</strong> {graph.edge_count}</div>
        <div style={{ flex: 1 }}></div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <span style={{ fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}><div style={{ width: 10, height: 10, borderRadius: '50%', background: '#3b82f6' }}></div> Injection</span>
          <span style={{ fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}><div style={{ width: 10, height: 10, borderRadius: '50%', background: '#ea580c' }}></div> Tool Exec</span>
          <span style={{ fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}><div style={{ width: 10, height: 10, borderRadius: '50%', background: '#dc2626' }}></div> Finding</span>
        </div>
      </div>
    </div>
  );
}
