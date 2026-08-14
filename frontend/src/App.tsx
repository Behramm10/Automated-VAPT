import { Routes, Route, NavLink } from 'react-router-dom';
import { LayoutDashboard, Target, Play, ShieldAlert, FileText, Settings, Shield } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import Targets from './pages/Targets';
import Runs from './pages/Runs';
import Findings from './pages/Findings';
import Reports from './pages/Reports';
import AttackGraph from './pages/AttackGraph';

function App() {
  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <div className="logo-icon">
              <Shield size={20} color="white" />
            </div>
            <div>
              <div className="logo-text">Agentic VAPT</div>
              <div className="logo-sub">Security Framework</div>
            </div>
          </div>
        </div>
        
        <nav className="sidebar-nav">
          <div className="nav-section">
            <div className="nav-section-title">Overview</div>
            <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <div className="nav-icon"><LayoutDashboard size={16} /></div>
              Dashboard
            </NavLink>
          </div>
          
          <div className="nav-section">
            <div className="nav-section-title">Assessments</div>
            <NavLink to="/targets" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <div className="nav-icon"><Target size={16} /></div>
              Targets
            </NavLink>
            <NavLink to="/runs" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <div className="nav-icon"><Play size={16} /></div>
              Test Runs
            </NavLink>
          </div>

          <div className="nav-section">
            <div className="nav-section-title">Results</div>
            <NavLink to="/findings" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <div className="nav-icon"><ShieldAlert size={16} /></div>
              Findings
            </NavLink>
            <NavLink to="/reports" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <div className="nav-icon"><FileText size={16} /></div>
              Reports
            </NavLink>
          </div>

          <div className="nav-section">
            <div className="nav-section-title">System</div>
            <NavLink to="/settings" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <div className="nav-icon"><Settings size={16} /></div>
              Settings
            </NavLink>
          </div>
        </nav>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <header className="topbar">
          <div className="topbar-title">VAPT Framework</div>
          <div className="topbar-actions">
            <div className="chip">v1.0.0</div>
            <div className="chip" style={{ background: 'rgba(34,197,94,0.1)', color: '#4ade80' }}>● System Online</div>
          </div>
        </header>
        
        <div className="page">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/targets" element={<Targets />} />
            <Route path="/runs" element={<Runs />} />
            <Route path="/findings" element={<Findings />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/runs/:runId/graph" element={<AttackGraph />} />
            <Route path="/settings" element={<div className="empty-state">Settings coming soon</div>} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

export default App;
