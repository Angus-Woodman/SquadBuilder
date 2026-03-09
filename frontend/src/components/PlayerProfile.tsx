import type { Player } from "../types/player";
import "./PlayerProfile.css";

export function PlayerProfile(props: {
  player: Player;
  onClose: () => void;
}) {
  const p = props.player;

  const age = p.date_of_birth ? calcAge(p.date_of_birth) : null;

  return (
    <div className="profile-overlay" onClick={props.onClose}>
      <div className="profile-modal" onClick={(e) => e.stopPropagation()}>
        <button className="profile-close" onClick={props.onClose}>
          ✕
        </button>

        {/* ── Hero section ──────────────────────────────── */}
        <div className="profile-hero">
          {p.photo_url ? (
            <img src={p.photo_url} alt={p.name} className="profile-photo" />
          ) : (
            <div className="profile-photo-placeholder">
              {p.name.charAt(0)}
            </div>
          )}
          <div className="profile-hero-info">
            <h2 className="profile-name">{p.name}</h2>
            <div className="profile-subtitle">
              {[p.position, p.club].filter(Boolean).join(" · ") || "—"}
            </div>
            {p.shirt_number != null && (
              <span className="profile-shirt">#{p.shirt_number}</span>
            )}
          </div>
        </div>

        {/* ── Bio details ───────────────────────────────── */}
        <div className="profile-details-grid">
          <Detail label="Nationality" value={p.nationality} />
          <Detail label="Date of birth" value={formatDob(p.date_of_birth)} />
          <Detail label="Age" value={age != null ? String(age) : null} />
          <Detail label="Preferred foot" value={p.preferred_foot} />
        </div>

        {/* ── International record ──────────────────────── */}
        <section className="profile-section">
          <h3 className="profile-section-title">International record</h3>
          {p.england_caps != null || p.england_goals != null ? (
            <div className="profile-stat-row">
              <StatCard label="Caps" value={p.england_caps} />
              <StatCard label="Goals" value={p.england_goals} />
              <StatCard label="Assists" value="Coming soon" />
            </div>
          ) : (
            <div className="profile-no-extra">
              No international caps recorded.
            </div>
          )}
        </section>

        {/* ── Season stats ──────────────────────────────── */}
        {hasSeasonStats(p) && (
          <section className="profile-section">
            <h3 className="profile-section-title">
              2024/25 club season
            </h3>
            <div className="profile-stat-row">
              <StatCard label="Games" value={p.season_games} />
              <StatCard label="Minutes" value={p.season_minutes} />
              <StatCard label="Goals" value={p.season_goals} />
              <StatCard label="Assists" value={p.season_assists} />
            </div>
            <div className="profile-stat-row">
              <StatCard label="xG" value={fmtDec(p.season_xg)} />
              <StatCard label="xA" value={fmtDec(p.season_xa)} />
              <StatCard label="Key passes" value={p.season_key_passes} />
              <StatCard label="Shots" value={p.season_shots} />
            </div>
            <div className="profile-stat-row">
              <StatCard
                label="Yellow cards"
                value={p.season_yellow_cards}
                accent="yellow"
              />
              <StatCard
                label="Red cards"
                value={p.season_red_cards}
                accent="red"
              />
            </div>
          </section>
        )}

        {/* ── Fallback when minimal data ────────────────── */}
        {!hasSeasonStats(p) && (
            <div className="profile-no-extra">
              No additional club stats available for this player.
            </div>
          )}
      </div>
    </div>
  );
}

/* ── helpers ─────────────────────────────────────────── */

function Detail(props: { label: string; value: string | null | undefined }) {
  if (!props.value) return null;
  return (
    <div className="profile-detail">
      <span className="profile-detail-label">{props.label}</span>
      <span className="profile-detail-value">{props.value}</span>
    </div>
  );
}

function StatCard(props: {
  label: string;
  value: number | string | null | undefined;
  accent?: "yellow" | "red";
}) {
  return (
    <div className={`profile-stat-card${props.accent ? ` accent-${props.accent}` : ""}`}>
      <span className="profile-stat-value">
        {props.value != null ? props.value : "—"}
      </span>
      <span className="profile-stat-label">{props.label}</span>
    </div>
  );
}

function hasSeasonStats(p: Player): boolean {
  return (
    p.season_games != null ||
    p.season_minutes != null ||
    p.season_goals != null ||
    p.season_assists != null
  );
}

function fmtDec(v: string | null | undefined): string | null {
  if (v == null) return null;
  const n = parseFloat(v);
  return isNaN(n) ? v : n.toFixed(2);
}

function calcAge(dob: string): number | null {
  const d = new Date(dob);
  if (isNaN(d.getTime())) return null;
  const today = new Date();
  let age = today.getFullYear() - d.getFullYear();
  const m = today.getMonth() - d.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < d.getDate())) age--;
  return age;
}

function formatDob(dob: string | null | undefined): string | null {
  if (!dob) return null;
  const d = new Date(dob);
  if (isNaN(d.getTime())) return dob;
  return d.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
