function Dashboard() {
  return (
    <div className="dashboard">

      {/* Sidebar */}
      <aside className="sidebar">
        <div className="logo">
          Analyse Retain
        </div>

        <nav>
          <a className="active">Dashboard</a>
          <a>Contributors</a>
          <a>Insights</a>
        </nav>
      </aside>


      {/* Main Content */}
      <main className="main-content">

        {/* Top Bar */}
        <header className="topbar">
          <div>
            <h1>Welcome back 👋</h1>
            <p>Here's what's happening with your contributors.</p>
          </div>

          <div className="profile">
            🔔 &nbsp; 👤
          </div>
        </header>


        {/* Statistics */}
        <section className="stats">

          <div className="stat-card">
            <p>Total Contributors</p>
            <h2>128</h2>
            <span>Active contributors</span>
          </div>

          <div className="stat-card">
            <p>Return Rate</p>
            <h2>64%</h2>
            <span>Contributors who returned</span>
          </div>

          <div className="stat-card">
            <p>Drop-off Rate</p>
            <h2>36%</h2>
            <span>First-time contributors</span>
          </div>

        </section>


        {/* Retention Section */}
        <section className="retention-card">

          <div className="section-header">
            <div>
              <h2>Contributor Retention</h2>
              <p>Track how contributors return over time.</p>
            </div>

            <select>
              <option>Last 30 days</option>
              <option>Last 90 days</option>
              <option>Last 6 months</option>
            </select>
          </div>


          {/* Temporary chart area */}
          <div className="chart-placeholder">
            <p>Retention Chart</p>
            <span>Chart will be added here</span>
          </div>

        </section>

      </main>

    </div>
  );
}

export default Dashboard;