import { Routes, Route, Navigate } from "react-router-dom";
import "./App.css";

import { useAuth } from "./context/AuthContext";
import { LandingPage } from "./components/LandingPage";
import { BuilderPage } from "./components/BuilderPage";
import { LoginPage } from "./components/LoginPage";
import { RegisterPage } from "./components/RegisterPage";
import { MySquadsPage } from "./components/MySquadsPage";
import { SquadViewPage } from "./components/SquadViewPage";
import { FriendsPage } from "./components/FriendsPage";
import { AdminPage } from "./components/AdminPage";

/** Redirect to /login if not authenticated. */
function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return null; // still checking token
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

/** Redirect to / if not an admin. */
function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { user, loading, isAdmin } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (!isAdmin) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/builder" element={<BuilderPage />} />
      <Route
        path="/squads"
        element={
          <RequireAuth>
            <MySquadsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/squads/:id"
        element={
          <RequireAuth>
            <SquadViewPage />
          </RequireAuth>
        }
      />
      <Route
        path="/friends"
        element={
          <RequireAuth>
            <FriendsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/admin"
        element={
          <RequireAdmin>
            <AdminPage />
          </RequireAdmin>
        }
      />
    </Routes>
  );
}
