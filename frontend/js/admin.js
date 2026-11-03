// Superadmin Operations Portal Script
let adminToken = localStorage.getItem("token") || null;
let currentAdminUser = null;
let currentAdminTab = "telemetry";

document.addEventListener("DOMContentLoaded", async () => {
  await verifyAdminAccess();
});

function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span>${type === "error" ? "❌" : type === "success" ? "✅" : "ℹ️"}</span>
    <span>${message}</span>
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

async function adminApiRequest(endpoint, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (adminToken) {
    headers["Authorization"] = `Bearer ${adminToken}`;
  }

  const response = await fetch(endpoint, { ...options, headers });
  if (response.status === 401 || response.status === 403) {
    showAdminGatekeeper();
    throw new Error("Unauthorized");
  }
  return response;
}

async function verifyAdminAccess() {
  if (!adminToken) {
    showAdminGatekeeper();
    return;
  }

  try {
    const res = await adminApiRequest("/api/v1/auth/me");
    if (res.ok) {
      currentAdminUser = await res.json();
      if (currentAdminUser.role !== "ADMIN") {
        showAdminGatekeeper();
        showToast("Access Denied: Administrator account required.", "error");
        return;
      }
      showAdminDashboard();
    } else {
      showAdminGatekeeper();
    }
  } catch (e) {
    showAdminGatekeeper();
  }
}

function showAdminGatekeeper() {
  document.getElementById("adminGatekeeper").classList.remove("hidden");
  document.getElementById("adminDashboard").classList.add("hidden");
  document.getElementById("adminUserPill").classList.add("hidden");
}

function showAdminDashboard() {
  document.getElementById("adminGatekeeper").classList.add("hidden");
  document.getElementById("adminDashboard").classList.remove("hidden");
  document.getElementById("adminUserPill").classList.remove("hidden");
  document.getElementById("adminEmailDisplay").textContent = currentAdminUser.email;
  switchAdminTab(currentAdminTab);
}

async function handleAdminLogin(event) {
  event.preventDefault();
  const email = document.getElementById("admGateEmail").value.trim();
  const password = document.getElementById("admGatePassword").value;
  const btn = document.getElementById("admGateSubmitBtn");
  btn.disabled = true;
  btn.textContent = "Authenticating...";

  try {
    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();
    if (!res.ok) {
      showToast(data.detail || "Authentication failed.", "error");
      return;
    }

    adminToken = data.access_token;
    localStorage.setItem("token", adminToken);

    // Verify role is ADMIN
    const meRes = await adminApiRequest("/api/v1/auth/me");
    const user = await meRes.json();
    if (user.role !== "ADMIN") {
      showToast("Access Denied: This account does not possess Superadmin privileges.", "error");
      showAdminGatekeeper();
      return;
    }

    currentAdminUser = user;
    showToast("Superadmin authenticated successfully!", "success");
    showAdminDashboard();
  } catch (err) {
    showToast("Network error during admin login.", "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Authenticate Administrator";
  }
}

function adminLogout() {
  localStorage.removeItem("token");
  adminToken = null;
  currentAdminUser = null;
  showToast("Logged out from Superadmin console.", "info");
  showAdminGatekeeper();
}

function switchAdminTab(tabName) {
  currentAdminTab = tabName;
  const tabs = ["telemetry", "users", "security", "feedback"];
  tabs.forEach(t => {
    const el = document.getElementById(`tab-${t}`);
    if (el) {
      if (t === tabName) {
        el.classList.remove("hidden");
      } else {
        el.classList.add("hidden");
      }
    }
  });

  document.querySelectorAll("#adminTabsNav .nav-btn").forEach(btn => {
    if (btn.getAttribute("data-tab") === tabName) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  if (tabName === "telemetry") loadAdminDiagnostics();
  if (tabName === "users") loadAdminUsers();
  if (tabName === "security") loadAdminSecurityLogs();
  if (tabName === "feedback") loadAdminFeedback();
}

// 1. Diagnostics & Telemetry
async function loadAdminDiagnostics() {
  try {
    const res = await adminApiRequest("/api/v1/admin/dashboard");
    if (!res.ok) return;
    const data = await res.json();

    if (data.telemetry) {
      const t = data.telemetry;
      document.getElementById("admCpuVal").textContent = `${t.cpu_percent}%`;
      document.getElementById("admRamVal").textContent = `${t.memory_used_gb} / ${t.memory_total_gb} GB`;
      document.getElementById("admRamPctVal").textContent = `${t.memory_percent}% consumed`;
      document.getElementById("admDiskVal").textContent = `${t.disk_used_gb} / ${t.disk_total_gb} GB`;
      document.getElementById("admDiskPctVal").textContent = `${t.disk_percent}% consumed`;
      document.getElementById("admThreadsVal").textContent = t.active_threads;
    }

    // Health
    document.getElementById("admAppDb").textContent = data.health.app_database;
    document.getElementById("admAppDb").className = `badge ${data.health.app_database === 'ONLINE' ? 'badge-optimized' : 'badge-critical'}`;
    document.getElementById("admAnalysisDb").textContent = data.health.analysis_database;
    document.getElementById("admAnalysisDb").className = `badge ${data.health.analysis_database === 'ONLINE' ? 'badge-optimized' : 'badge-critical'}`;
    document.getElementById("admOverallStatus").textContent = data.health.status;
    document.getElementById("admOverallStatus").className = `badge ${data.health.status === 'HEALTHY' ? 'badge-optimized' : 'badge-warning'}`;

    // Throughput
    document.getElementById("admTotalQueries").textContent = data.usage_stats.total_queries;
    document.getElementById("admTotalComparisons").textContent = data.usage_stats.total_comparisons;
    document.getElementById("admAvgLatency").textContent = `${data.usage_stats.avg_platform_latency_ms} ms`;
  } catch (e) {
    console.error("Diagnostics load error:", e);
  }
}

// 2. User Directory
async function loadAdminUsers() {
  try {
    const res = await adminApiRequest("/api/v1/admin/users");
    if (!res.ok) return;
    const users = await res.json();

    const tbody = document.getElementById("admUsersTableBody");
    tbody.innerHTML = users.map(u => `
      <tr>
        <td class="mono">#${u.id}</td>
        <td><strong>${u.email}</strong></td>
        <td>${u.full_name || '-'}</td>
        <td><span class="role-tag ${u.role === 'ADMIN' ? 'admin' : ''}">${u.role}</span></td>
        <td><span class="badge ${u.is_active ? 'badge-optimized' : 'badge-critical'}">${u.is_active ? 'ACTIVE' : 'SUSPENDED'}</span></td>
        <td class="mono">${u.total_queries}</td>
        <td style="color: var(--text-dim); font-size: 0.8rem;">${new Date(u.created_at).toLocaleDateString()}</td>
        <td>
          <button class="btn ${u.is_active ? 'btn-danger' : 'btn-secondary'}" style="padding: 0.25rem 0.6rem; font-size: 0.75rem;" onclick="toggleUserStatus(${u.id}, ${u.is_active})">
            ${u.is_active ? 'Suspend' : 'Activate'}
          </button>
          <button class="btn btn-secondary" style="padding: 0.25rem 0.6rem; font-size: 0.75rem; margin-left: 0.25rem;" onclick="toggleUserRole(${u.id}, '${u.role}')">
            ${u.role === 'ADMIN' ? 'Demote to User' : 'Promote to Admin'}
          </button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Users load error:", err);
  }
}

async function toggleUserStatus(userId, currentStatus) {
  try {
    const res = await adminApiRequest(`/api/v1/admin/users/${userId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: !currentStatus })
    });
    if (res.ok) {
      showToast("User account status updated.", "success");
      loadAdminUsers();
    } else {
      const d = await res.json();
      showToast(d.detail || "Failed to update user status.", "error");
    }
  } catch (e) {
    showToast("Network error updating status.", "error");
  }
}

async function toggleUserRole(userId, currentRole) {
  const newRole = currentRole === "ADMIN" ? "USER" : "ADMIN";
  try {
    const res = await adminApiRequest(`/api/v1/admin/users/${userId}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role: newRole })
    });
    if (res.ok) {
      showToast(`User role updated to ${newRole}.`, "success");
      loadAdminUsers();
    } else {
      const d = await res.json();
      showToast(d.detail || "Failed to update role.", "error");
    }
  } catch (e) {
    showToast("Network error updating role.", "error");
  }
}

// 3. Security Threats
async function loadAdminSecurityLogs() {
  try {
    const res = await adminApiRequest("/api/v1/admin/security-logs?limit=25");
    if (!res.ok) return;
    const logs = await res.json();

    const tbody = document.getElementById("admSecurityTableBody");
    if (logs.length > 0) {
      tbody.innerHTML = logs.map(l => `
        <tr>
          <td class="mono">#${l.id}</td>
          <td>${l.user_email || '<span style="color:var(--text-dim)">Anonymous</span>'}</td>
          <td><span class="badge badge-critical">${l.violation_type}</span></td>
          <td class="mono" style="color: var(--rose-danger);">${l.attempted_query.length > 55 ? l.attempted_query.substring(0, 55) + '...' : l.attempted_query}</td>
          <td style="color: var(--text-dim); font-size: 0.8rem;">${new Date(l.created_at).toLocaleString()}</td>
        </tr>
      `).join("");
    } else {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-dim);">No security threats logged.</td></tr>`;
    }
  } catch (err) {
    console.error("Security logs load error:", err);
  }
}

// 4. Feedback Desk
async function loadAdminFeedback() {
  try {
    const res = await adminApiRequest("/api/v1/admin/feedback");
    if (!res.ok) return;
    const feedbacks = await res.json();

    const tbody = document.getElementById("admFeedbackTableBody");
    if (feedbacks.length > 0) {
      tbody.innerHTML = feedbacks.map(f => `
        <tr>
          <td class="mono">#${f.id}</td>
          <td>${f.user_email}</td>
          <td style="color: #fbbf24;">${'★'.repeat(f.rating)}${'☆'.repeat(5 - f.rating)}</td>
          <td><span class="badge badge-info">${f.category}</span></td>
          <td style="max-width: 250px;">${f.comment}</td>
          <td><span class="badge ${f.status === 'RESOLVED' ? 'badge-optimized' : f.status === 'REVIEWED' ? 'badge-info' : 'badge-warning'}">${f.status}</span></td>
          <td>
            <select style="font-size: 0.75rem; background: rgba(10, 15, 29, 0.9); color: #fff; border: 1px solid var(--glass-card-border); padding: 0.25rem; border-radius: 6px;" onchange="updateFeedbackStatus(${f.id}, this.value)">
              <option value="PENDING" ${f.status === 'PENDING' ? 'selected' : ''}>Pending</option>
              <option value="REVIEWED" ${f.status === 'REVIEWED' ? 'selected' : ''}>Reviewed</option>
              <option value="RESOLVED" ${f.status === 'RESOLVED' ? 'selected' : ''}>Resolved</option>
            </select>
          </td>
        </tr>
      `).join("");
    } else {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-dim);">No feedback submitted yet.</td></tr>`;
    }
  } catch (err) {
    console.error("Feedback load error:", err);
  }
}

async function updateFeedbackStatus(feedbackId, newStatus) {
  try {
    const res = await adminApiRequest(`/api/v1/admin/feedback/${feedbackId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status: newStatus })
    });
    if (res.ok) {
      showToast(`Feedback ticket #${feedbackId} updated to ${newStatus}.`, "success");
      loadAdminFeedback();
    }
  } catch (e) {
    showToast("Error updating feedback status.", "error");
  }
}
