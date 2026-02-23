import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchFriends,
  sendFriendRequest,
  acceptFriendRequest,
  removeFriend,
  fetchFriendSquads,
  type FriendInfo,
  type SavedSquad,
} from "../api/client";
import { NavBar } from "./NavBar";
import "./Dashboard.css";

export function FriendsPage() {
  const [friends, setFriends] = useState<FriendInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [sendError, setSendError] = useState<string | null>(null);
  const [sendSuccess, setSendSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // For viewing a friend's squads
  const [viewingSquads, setViewingSquads] = useState<{
    friendName: string;
    squads: SavedSquad[];
  } | null>(null);

  useEffect(() => {
    loadFriends();
  }, []);

  function loadFriends() {
    fetchFriends()
      .then(setFriends)
      .catch((e) => setActionError(e instanceof Error ? e.message : "Failed to load friends"))
      .finally(() => setLoading(false));
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    setSendError(null);
    setSendSuccess(null);
    try {
      const f = await sendFriendRequest(email);
      setFriends((prev) => [f, ...prev]);
      setSendSuccess(`Request sent to ${f.display_name}`);
      setEmail("");
    } catch (err) {
      setSendError(err instanceof Error ? err.message : "Failed");
    }
  }

  async function handleAccept(friendshipId: number) {
    setActionError(null);
    try {
      const updated = await acceptFriendRequest(friendshipId);
      setFriends((prev) =>
        prev.map((f) => (f.friendship_id === friendshipId ? updated : f))
      );
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to accept request");
    }
  }

  async function handleRemove(friendshipId: number) {
    if (!confirm("Remove this friend?")) return;
    setActionError(null);
    try {
      await removeFriend(friendshipId);
      setFriends((prev) => prev.filter((f) => f.friendship_id !== friendshipId));
      setViewingSquads(null);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to remove friend");
    }
  }

  async function handleViewSquads(friendUserId: number, friendName: string) {
    setActionError(null);
    try {
      const squads = await fetchFriendSquads(friendUserId);
      setViewingSquads({ friendName, squads });
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to load friend's squads");
    }
  }

  const accepted = friends.filter((f) => f.status === "accepted");
  const pendingReceived = friends.filter(
    (f) => f.status === "pending" && f.direction === "received"
  );
  const pendingSent = friends.filter(
    (f) => f.status === "pending" && f.direction === "sent"
  );

  return (
    <div className="dashboard-page">
      <NavBar active="friends" />

      <div className="dashboard-content">
        <h1>Friends</h1>
        {actionError && <p className="dashboard-error">{actionError}</p>}

        {/* Add friend form */}
        <form className="friend-add-form" onSubmit={handleSend}>
          <input
            type="email"
            placeholder="Friend's email address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <button type="submit">Send request</button>
        </form>
        {sendError && <p className="dashboard-error">{sendError}</p>}
        {sendSuccess && <p className="dashboard-success">{sendSuccess}</p>}

        {loading && <p className="dashboard-info">Loading…</p>}

        {/* Pending received */}
        {pendingReceived.length > 0 && (
          <section className="friend-section">
            <h2>Pending Requests</h2>
            {pendingReceived.map((f) => (
              <div key={f.friendship_id} className="friend-row">
                <div>
                  <strong>{f.display_name}</strong>
                  <span className="friend-email">{f.email}</span>
                </div>
                <div className="friend-actions">
                  <button className="accept-btn" onClick={() => handleAccept(f.friendship_id)}>
                    Accept
                  </button>
                  <button className="remove-btn" onClick={() => handleRemove(f.friendship_id)}>
                    Decline
                  </button>
                </div>
              </div>
            ))}
          </section>
        )}

        {/* Pending sent */}
        {pendingSent.length > 0 && (
          <section className="friend-section">
            <h2>Sent Requests</h2>
            {pendingSent.map((f) => (
              <div key={f.friendship_id} className="friend-row">
                <div>
                  <strong>{f.display_name}</strong>
                  <span className="friend-email">{f.email}</span>
                </div>
                <span className="friend-pending-badge">Pending</span>
              </div>
            ))}
          </section>
        )}

        {/* Accepted friends */}
        <section className="friend-section">
          <h2>Your Friends ({accepted.length})</h2>
          {accepted.length === 0 && !loading && (
            <p className="dashboard-info">No friends yet. Send a request above!</p>
          )}
          {accepted.map((f) => (
            <div key={f.friendship_id} className="friend-row">
              <div>
                <strong>{f.display_name}</strong>
                <span className="friend-email">{f.email}</span>
              </div>
              <div className="friend-actions">
                <button onClick={() => handleViewSquads(f.user_id, f.display_name)}>
                  View squads
                </button>
                <button className="remove-btn" onClick={() => handleRemove(f.friendship_id)}>
                  Remove
                </button>
              </div>
            </div>
          ))}
        </section>

        {/* Friend squads overlay */}
        {viewingSquads && (
          <div className="friend-squads-overlay">
            <div className="friend-squads-panel">
              <div className="friend-squads-header">
                <h2>{viewingSquads.friendName}'s Squads</h2>
                <button onClick={() => setViewingSquads(null)}>✕</button>
              </div>
              {viewingSquads.squads.length === 0 ? (
                <p className="dashboard-info">No saved squads yet.</p>
              ) : (
                <div className="squad-grid">
                  {viewingSquads.squads.map((s) => (
                    <Link
                      key={s.id}
                      to={`/squads/${s.id}`}
                      className="squad-card squad-card-link"
                    >
                      <h3>{s.name}</h3>
                      <p className="squad-card-meta">
                        {s.player_ids.length} players ·{" "}
                        {new Date(s.created_at).toLocaleDateString()}
                      </p>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
