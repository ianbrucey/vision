"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Plus, X, Check, Shield, User, Building2 } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";
import { listUsers, createUser, updateUser, type AdminUser } from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Constants                                                          */
/* ------------------------------------------------------------------ */

const ROLE_OPTIONS = [
  { value: "user", label: "User" },
  { value: "vendor", label: "Vendor" },
  { value: "admin", label: "Admin" },
] as const;

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function SettingsPage() {
  const { user, ready } = useAuth();
  const router = useRouter();

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Add user modal
  const [showAdd, setShowAdd] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newRole, setNewRole] = useState("user");
  const [saving, setSaving] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  // Editing state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editEmail, setEditEmail] = useState("");
  const [editRole, setEditRole] = useState("");
  const [editActive, setEditActive] = useState(true);

  /* ---- auth guard ---- */
  useEffect(() => {
    if (ready && (!user || user.role !== "admin")) {
      router.replace("/");
    }
  }, [user, ready, router]);

  /* ---- fetch ---- */
  const fetchUsers = useCallback(async () => {
    try {
      const data = await listUsers();
      setUsers(data.users);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user?.role === "admin") fetchUsers();
  }, [user, fetchUsers]);

  /* ---- handlers ---- */
  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < 6) {
      setAddError("Password must be at least 6 characters");
      return;
    }
    setSaving(true);
    setAddError(null);
    try {
      await createUser({
        username: newUsername.trim(),
        password: newPassword,
        email: newEmail.trim() || undefined,
        role: newRole,
      });
      setShowAdd(false);
      setNewUsername("");
      setNewPassword("");
      setNewEmail("");
      setNewRole("user");
      fetchUsers();
    } catch (err) {
      setAddError(err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (u: AdminUser) => {
    setEditingId(u.id);
    setEditEmail(u.email || "");
    setEditRole(u.role);
    setEditActive(u.is_active);
  };

  const cancelEdit = () => {
    setEditingId(null);
  };

  const saveEdit = async (userId: string) => {
    try {
      await updateUser(userId, {
        email: editEmail.trim() || undefined,
        role: editRole,
        is_active: editActive,
      });
      setEditingId(null);
      fetchUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update user");
    }
  };

  /* ---- render ---- */
  if (!ready || (user && user.role !== "admin")) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-text-disabled" size={24} />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-semibold text-text-primary">Settings</h1>
          <p className="text-xs text-text-disabled mt-1">
            Manage user accounts and permissions.
          </p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm bg-brand text-white rounded-lg hover:opacity-90 transition-opacity"
        >
          <Plus size={14} />
          Add User
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 px-3 py-2 text-xs text-danger bg-danger-bg rounded-lg">
          {error}
        </div>
      )}

      {/* Add User Modal */}
      {showAdd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-surface-1 rounded-xl shadow-lg border border-border w-full max-w-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-text-primary">Add User</h2>
              <button
                onClick={() => { setShowAdd(false); setAddError(null); }}
                className="text-text-disabled hover:text-text-primary"
              >
                <X size={16} />
              </button>
            </div>
            {addError && (
              <div className="mb-3 px-3 py-2 text-xs text-danger bg-danger-bg rounded">{addError}</div>
            )}
            <form onSubmit={handleAdd} className="space-y-3">
              <label className="block">
                <span className="text-xs text-text-secondary">Username *</span>
                <input
                  type="text"
                  value={newUsername}
                  onChange={e => setNewUsername(e.target.value)}
                  required
                  className="mt-1 w-full px-3 py-2 text-sm bg-surface-2 border border-border rounded-lg text-text-primary outline-none focus:border-brand"
                />
              </label>
              <label className="block">
                <span className="text-xs text-text-secondary">Password *</span>
                <input
                  type="password"
                  value={newPassword}
                  onChange={e => setNewPassword(e.target.value)}
                  required
                  minLength={6}
                  className="mt-1 w-full px-3 py-2 text-sm bg-surface-2 border border-border rounded-lg text-text-primary outline-none focus:border-brand"
                />
              </label>
              <label className="block">
                <span className="text-xs text-text-secondary">Email</span>
                <input
                  type="email"
                  value={newEmail}
                  onChange={e => setNewEmail(e.target.value)}
                  className="mt-1 w-full px-3 py-2 text-sm bg-surface-2 border border-border rounded-lg text-text-primary outline-none focus:border-brand"
                />
              </label>
              <label className="block">
                <span className="text-xs text-text-secondary">Role</span>
                <select
                  value={newRole}
                  onChange={e => setNewRole(e.target.value)}
                  className="mt-1 w-full px-3 py-2 text-sm bg-surface-2 border border-border rounded-lg text-text-primary outline-none focus:border-brand"
                >
                  {ROLE_OPTIONS.map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </label>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => { setShowAdd(false); setAddError(null); }}
                  className="px-3 py-1.5 text-xs border border-border rounded-lg text-text-secondary hover:text-text-primary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving || !newUsername.trim() || newPassword.length < 6}
                  className="px-3 py-1.5 text-xs bg-brand text-white rounded-lg hover:opacity-90 disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Create User"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* User Table */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="animate-spin text-text-disabled" size={24} />
        </div>
      ) : (
        <div className="border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface-1 border-b border-border">
              <tr className="text-left text-[10px] font-semibold text-text-disabled uppercase tracking-wide">
                <th className="px-4 py-2.5">Username</th>
                <th className="px-4 py-2.5">Email</th>
                <th className="px-4 py-2.5">Role</th>
                <th className="px-4 py-2.5">Status</th>
                <th className="px-4 py-2.5 w-20"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {users.map((u) => {
                const isEditing = editingId === u.id;
                return (
                  <tr key={u.id} className="hover:bg-surface-2 transition-colors">
                    <td className="px-4 py-2.5 font-medium text-text-primary">
                      {u.username}
                    </td>
                    <td className="px-4 py-2.5 text-text-secondary">
                      {isEditing ? (
                        <input
                          type="email"
                          value={editEmail}
                          onChange={e => setEditEmail(e.target.value)}
                          className="w-full px-2 py-1 text-xs bg-surface-2 border border-border rounded text-text-primary outline-none focus:border-brand"
                        />
                      ) : (
                        u.email || "—"
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      {isEditing ? (
                        <select
                          value={editRole}
                          onChange={e => setEditRole(e.target.value)}
                          className="px-2 py-1 text-xs bg-surface-2 border border-border rounded text-text-primary outline-none focus:border-brand"
                        >
                          {ROLE_OPTIONS.map(o => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                          ))}
                        </select>
                      ) : (
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium ${
                          u.role === "admin"
                            ? "bg-danger-bg text-danger"
                            : u.role === "vendor"
                            ? "bg-info-bg text-info"
                            : "bg-surface-2 text-text-secondary"
                        }`}>
                          {u.role === "admin" ? <Shield size={10} /> : u.role === "vendor" ? <Building2 size={10} /> : <User size={10} />}
                          {u.role}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2.5">
                      {isEditing ? (
                        <button
                          onClick={() => setEditActive(!editActive)}
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium transition-colors ${
                            editActive
                              ? "bg-success-bg text-success"
                              : "bg-surface-2 text-text-disabled"
                          }`}
                        >
                          <span className={`w-1.5 h-1.5 rounded-full ${
                            editActive ? "bg-success" : "bg-text-disabled"
                          }`} />
                          {editActive ? "Active" : "Disabled"}
                        </button>
                      ) : (
                        <span className={`inline-flex items-center gap-1 text-[10px] font-medium ${
                          u.is_active ? "text-success" : "text-text-disabled"
                        }`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${
                            u.is_active ? "bg-success" : "bg-text-disabled"
                          }`} />
                          {u.is_active ? "Active" : "Disabled"}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      {isEditing ? (
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => saveEdit(u.id)}
                            className="p-1 text-success hover:bg-success-bg rounded"
                            title="Save"
                          >
                            <Check size={14} />
                          </button>
                          <button
                            onClick={cancelEdit}
                            className="p-1 text-text-disabled hover:text-text-primary rounded"
                            title="Cancel"
                          >
                            <X size={14} />
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => startEdit(u)}
                          className="px-2 py-1 text-[10px] text-text-secondary hover:text-text-primary border border-border rounded hover:bg-surface-2 transition-colors"
                        >
                          Edit
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
