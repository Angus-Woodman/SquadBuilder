import { Link } from "react-router-dom";
import { NavBar } from "./NavBar";
import "./Dashboard.css";
import "./LandingPage.css";

export function LandingPage() {
  return (
    <div className="dashboard-page landing">
      <NavBar />

      {/* Hero */}
      <section className="hero">
        <p className="hero-eyebrow">England · 2026 World Cup</p>
        <h1 className="hero-title">
          Put yourself in
          <br />
          <span className="hero-highlight">Thomas Tuchel's</span> shoes
        </h1>
        <p className="hero-sub">
          Pick your 26-player World Cup squad — then see how your picks compare to the crowd.
        </p>
        <Link to="/builder" className="cta-primary">
          Build your squad →
        </Link>
      </section>

      {/* Stat cards */}
      <section className="stats-section">
        <div className="stat-card">
          <span className="stat-icon">🏆</span>
          <h3>Most Selected Squad</h3>
          <span className="stat-value">Coming soon</span>
        </div>

        <div className="stat-card">
          <span className="stat-icon">⭐</span>
          <h3>Most Selected Player</h3>
          <span className="stat-value">Coming soon</span>
        </div>

        <div className="stat-card">
          <span className="stat-icon">📊</span>
          <h3>Your History</h3>
          <span className="stat-value">Coming soon</span>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        Data from{" "}
        <a href="https://www.football-data.org/" target="_blank" rel="noreferrer">
          football-data.org
        </a>{" "}
        · Built for fun, not profit
      </footer>
    </div>
  );
}
