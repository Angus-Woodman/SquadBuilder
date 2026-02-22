import "./LandingPage.css";

export function LandingPage(props: { onStart: () => void }) {
  return (
    <div className="landing">
      {/* Top nav */}
      <nav className="landing-nav">
        <div className="landing-nav-brand">⚽ Squad Builder</div>
        <button className="login-btn" onClick={() => alert("Login coming soon!")}>
          Log in
        </button>
      </nav>

      {/* Hero */}
      <section className="hero">
        <p className="hero-eyebrow">England · 2026 World Cup</p>
        <h1 className="hero-title">
          Put yourself in
          <br />
          <span className="hero-highlight">Thomas Tuchel's</span> shoes
        </h1>
        <p className="hero-sub">
          Pick your 26-player squad for the World Cup. Choose your goalkeeper,
          defenders, midfielders and forwards — then see how your picks compare
          to the crowd.
        </p>
        <button className="cta-primary" onClick={props.onStart}>
          Build your squad →
        </button>
      </section>

      {/* Stat cards (dummy for now) */}
      <section className="stats-section">
        <div className="stat-card">
          <div className="stat-icon">🏆</div>
          <h3>Most Selected Squad</h3>
          <p className="stat-value">Coming soon</p>
          <p className="stat-desc">
            See which 26-player lineup the community agrees on most.
          </p>
          <button className="cta-secondary" disabled>
            View squad
          </button>
        </div>

        <div className="stat-card">
          <div className="stat-icon">⭐</div>
          <h3>Most Selected Player</h3>
          <p className="stat-value">Coming soon</p>
          <p className="stat-desc">
            Find out which player appears in the most user-built squads.
          </p>
          <button className="cta-secondary" disabled>
            View stats
          </button>
        </div>

        <div className="stat-card">
          <div className="stat-icon">📊</div>
          <h3>Your History</h3>
          <p className="stat-value">Coming soon</p>
          <p className="stat-desc">
            Log in to save multiple squads and track how your picks evolve.
          </p>
          <button className="cta-secondary" disabled>
            Log in to unlock
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <p>
          Data from{" "}
          <a
            href="https://www.football-data.org/"
            target="_blank"
            rel="noreferrer"
          >
            football-data.org
          </a>{" "}
          · Built for fun, not profit
        </p>
      </footer>
    </div>
  );
}
