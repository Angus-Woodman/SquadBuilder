import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

interface NavBarProps {
  /** Which nav link to highlight as active, e.g. "builder", "squads", "friends", "admin" */
  active?: string;
}

export function NavBar({ active }: NavBarProps) {
  const { user, logout, isAdmin } = useAuth();

  return (
    <nav className="dashboard-nav">
      <Link to="/" className="dashboard-brand">⚽ Squad Builder</Link>
      <div className="dashboard-nav-links">
        <Link to="/builder" className={active === "builder" ? "active" : ""}>
          Builder
        </Link>
        {user ? (
          <>
            <Link to="/squads" className={active === "squads" ? "active" : ""}>
              My Squads
            </Link>
            <Link to="/friends" className={active === "friends" ? "active" : ""}>
              Friends
            </Link>
            {isAdmin && (
              <Link to="/admin" className={active === "admin" ? "active" : ""}>
                Admin
              </Link>
            )}
            <span className="dashboard-user">{user.display_name}</span>
            <button className="dashboard-logout" onClick={logout}>Log out</button>
          </>
        ) : (
          <Link to="/login">Log in</Link>
        )}
      </div>
    </nav>
  );
}
