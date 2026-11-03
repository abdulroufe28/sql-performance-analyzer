// SQL Performance Analyzer Frontend App
let token = localStorage.getItem("token") || null;
let currentUser = null;
let currentView = "dashboard";
let historyPage = 1;
let historyPageSize = 10;
let historyTotalPages = 1;
let lastAnalyzedResult = null;
let currentFeedbackRating = 5;

// Chart instances
let latencyChartInstance = null;
let healthChartInstance = null;
let comparisonChartInstance = null;

// Presets
const PRESETS = {
  indexed: "SELECT id, name FROM customers WHERE id = 1;",
  full_scan: "SELECT * FROM customers WHERE email = 'arun@example.com';",
  filesort: "SELECT * FROM customers ORDER BY city;",
  join: "SELECT c.name, o.total_amount, o.status FROM customers c JOIN orders o ON c.id = o.customer_id WHERE o.status = 'COMPLETED';"
};

// Initialize app on DOM load
document.addEventListener("DOMContentLoaded", async () => {
  await checkAuth();
  navigate("dashboard");
});

// Toast notification helper
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

// Authenticated fetch wrapper
async function apiRequest(endpoint, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(endpoint, { ...options, headers });
    if (response.status === 401) {
      token = null;
      localStorage.removeItem("token");
      updateAuthUI();
      showToast("Session expired. Please sign in again.", "error");
      openAuthModal("login");
      throw new Error("Unauthorized");
    }
    return response;
  } catch (err) {
    throw err;
  }
}

// Authentication handling
async function checkAuth() {
  if (!token) {
    updateAuthUI();
    return;
  }

  try {
    const res = await apiRequest("/api/v1/auth/me");
    if (res.ok) {
      currentUser = await res.json();
    } else {
      currentUser = null;
      token = null;
      localStorage.removeItem("token");
    }
  } catch (e) {
    currentUser = null;
  }
  updateAuthUI();
}

function updateAuthUI() {
  const userProfile = document.getElementById("userProfile");
  const loginBtn = document.getElementById("loginBtn");
  const adminNavBtn = document.getElementById("adminNavBtn");

  if (currentUser) {
    userProfile.classList.remove("hidden");
    loginBtn.classList.add("hidden");
    document.getElementById("userEmailText").textContent = currentUser.email;
    const roleTag = document.getElementById("userRoleTag");
    roleTag.textContent = currentUser.role;
    roleTag.className = `role-tag ${currentUser.role === "ADMIN" ? "admin" : ""}`;

    if (currentUser.role === "ADMIN") {
      adminNavBtn.classList.remove("hidden");
    } else {
      adminNavBtn.classList.add("hidden");
    }
  } else {
    userProfile.classList.add("hidden");
    loginBtn.classList.remove("hidden");
    adminNavBtn.classList.add("hidden");
  }
}

function logout() {
  token = null;
  currentUser = null;
  localStorage.removeItem("token");
  updateAuthUI();
  showToast("Logged out successfully.", "success");
  navigate("dashboard");
}

// Auth Modal
let authMode = "login";

function openAuthModal(mode = "login") {
  authMode = mode;
  document.getElementById("authModal").classList.remove("hidden");
  const fullNameGroup = document.getElementById("fullNameGroup");
  const title = document.getElementById("authModalTitle");
  const submitBtn = document.getElementById("authSubmitBtn");
  const togglePrompt = document.getElementById("authTogglePrompt");
  const toggleLink = document.getElementById("authToggleLink");

  if (mode === "login") {
    title.textContent = "Sign In";
    fullNameGroup.classList.add("hidden");
    submitBtn.textContent = "Sign In";
    togglePrompt.textContent = "Don't have an account?";
    toggleLink.textContent = "Create one";
  } else {
    title.textContent = "Create an Account";
    fullNameGroup.classList.remove("hidden");
    submitBtn.textContent = "Register";
    togglePrompt.textContent = "Already have an account?";
    toggleLink.textContent = "Sign In";
  }
}

function closeAuthModal() {
  document.getElementById("authModal").classList.add("hidden");
}

function toggleAuthMode() {
  openAuthModal(authMode === "login" ? "register" : "login");
}

async function handleAuthSubmit(event) {
  event.preventDefault();
  const email = document.getElementById("authEmail").value.trim();
  const password = document.getElementById("authPassword").value;
  const fullName = document.getElementById("authFullName").value.trim();

  const endpoint = authMode === "login" ? "/api/v1/auth/login" : "/api/v1/auth/register";
  const body = authMode === "login" ? { email, password } : { email, password, full_name: fullName };

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });

    const data = await res.json();
    if (!res.ok) {
      showToast(data.detail || "Authentication failed", "error");
      return;
    }

    if (authMode === "login") {
      token = data.access_token;
      localStorage.setItem("token", token);
      closeAuthModal();
      showToast("Signed in successfully!", "success");
      await checkAuth();
      navigate(currentView);
    } else {
      showToast("Account created successfully! Please sign in.", "success");
      openAuthModal("login");
    }
  } catch (err) {
    showToast("Network error during authentication.", "error");
  }
}

// Navigation router
function navigate(viewName) {
  currentView = viewName;

  // Toggle view containers
  const views = ["dashboard", "analyzer", "comparison", "history", "admin"];
  views.forEach(v => {
    const el = document.getElementById(`view-${v}`);
    if (el) {
      if (v === viewName) {
        el.classList.remove("hidden");
      } else {
        el.classList.add("hidden");
      }
    }
  });

  // Toggle active button
  document.querySelectorAll(".nav-btn").forEach(btn => {
    if (btn.getAttribute("data-view") === viewName) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  // Refresh view data
  if (viewName === "dashboard") loadDashboard();
  if (viewName === "history") loadHistory(1);
  if (viewName === "comparison") loadSavedComparisons();
  if (viewName === "admin") loadAdmin();
}

// 1. DASHBOARD
async function loadDashboard() {
  if (!token) return;

  try {
    const res = await apiRequest("/api/v1/dashboard/metrics");
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById("dashTotalQueries").textContent = data.total_queries;
    document.getElementById("dashAvgLatency").innerHTML = `${data.avg_execution_time_ms} <small style="font-size: 1rem; color: var(--text-dim);">ms</small>`;
    document.getElementById("dashFtsCount").textContent = data.full_table_scans_count;

    // Quota progress
    const quotaPct = Math.min(100, Math.round((data.comparison_quota_used / data.comparison_quota_limit) * 100));
    document.getElementById("dashQuotaText").textContent = `${data.comparison_quota_used} / ${data.comparison_quota_limit}`;
    document.getElementById("dashQuotaBar").style.width = `${quotaPct}%`;

    // Slowest Queries Table
    const slowBody = document.getElementById("slowestQueriesTable");
    if (data.slowest_queries && data.slowest_queries.length > 0) {
      slowBody.innerHTML = data.slowest_queries.map(q => `
        <tr>
          <td class="mono" title="${q.query}">${q.query.length > 45 ? q.query.substring(0, 45) + '...' : q.query}</td>
          <td class="mono" style="color: var(--accent-rose); font-weight: 600;">${q.execution_time_ms} ms</td>
          <td>${q.row_count}</td>
          <td><button class="btn btn-secondary" style="padding: 0.2rem 0.6rem; font-size: 0.75rem;" onclick="loadAndAnalyzeQuery('${encodeURIComponent(q.query)}')">Inspect</button></td>
        </tr>
      `).join("");
    } else {
      slowBody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-dim);">No slow queries detected.</td></tr>`;
    }

    // Recent Activity Table
    const recBody = document.getElementById("recentQueriesTable");
    if (data.recent_queries && data.recent_queries.length > 0) {
      recBody.innerHTML = data.recent_queries.map(q => `
        <tr>
          <td class="mono" title="${q.query}">${q.query.length > 45 ? q.query.substring(0, 45) + '...' : q.query}</td>
          <td>${getRatingBadge(q.performance_rating)}</td>
          <td class="mono">${q.execution_time_ms} ms</td>
        </tr>
      `).join("");
    } else {
      recBody.innerHTML = `<tr><td colspan="3" style="text-align: center; color: var(--text-dim);">No recent activity.</td></tr>`;
    }

    // Render Charts
    renderDashboardCharts(data);
  } catch (err) {
    console.error("Dashboard error:", err);
  }
}

function renderDashboardCharts(data) {
  // 1. Latency trend chart
  const latCtx = document.getElementById("latencyChart").getContext("2d");
  const latLabels = data.recent_queries.map((q, idx) => `Q${idx + 1}`).reverse();
  const latValues = data.recent_queries.map(q => q.execution_time_ms).reverse();

  if (latencyChartInstance) latencyChartInstance.destroy();
  latencyChartInstance = new Chart(latCtx, {
    type: "line",
    data: {
      labels: latLabels.length ? latLabels : ["None"],
      datasets: [{
        label: "Execution Time (ms)",
        data: latValues.length ? latValues : [0],
        borderColor: "#3b82f6",
        backgroundColor: "rgba(59, 130, 246, 0.15)",
        fill: true,
        tension: 0.35,
        pointBackgroundColor: "#60a5fa"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { grid: { color: "#232d42" }, ticks: { color: "#9ca3af" } },
        x: { grid: { color: "#232d42" }, ticks: { color: "#9ca3af" } }
      },
      plugins: { legend: { display: false } }
    }
  });

  // 2. Health distribution chart
  const healthCtx = document.getElementById("healthChart").getContext("2d");
  if (healthChartInstance) healthChartInstance.destroy();
  healthChartInstance = new Chart(healthCtx, {
    type: "doughnut",
    data: {
      labels: ["Optimized Queries", "Full Table Scans"],
      datasets: [{
        data: [data.optimized_queries_count, data.full_table_scans_count],
        backgroundColor: ["#10b981", "#f59e0b"],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom", labels: { color: "#9ca3af", font: { size: 12 } } }
      }
    }
  });
}

// 2. QUERY ANALYZER
function loadPreset(key) {
  if (PRESETS[key]) {
    document.getElementById("sqlInput").value = PRESETS[key];
  }
}

function loadAndAnalyzeQuery(encodedQuery) {
  const query = decodeURIComponent(encodedQuery);
  navigate("analyzer");
  document.getElementById("sqlInput").value = query;
  runAnalyze();
}

async function runAnalyze() {
  if (!token) {
    showToast("Please sign in to analyze queries.", "error");
    openAuthModal("login");
    return;
  }

  const query = document.getElementById("sqlInput").value.trim();
  if (!query) {
    showToast("Please enter a SQL query.", "error");
    return;
  }

  const btn = document.getElementById("btnRunQuery");
  const spinner = document.getElementById("runSpinner");
  btn.disabled = true;
  spinner.classList.remove("hidden");

  try {
    const res = await apiRequest("/api/v1/queries/analyze", {
      method: "POST",
      body: JSON.stringify({ query })
    });

    const data = await res.json();
    if (!res.ok) {
      showToast(data.detail || "Query execution failed.", "error");
      return;
    }

    renderAnalysisResult(data);
    showToast("Analysis completed successfully!", "success");
  } catch (err) {
    showToast("Network error while analyzing query.", "error");
  } finally {
    btn.disabled = false;
    spinner.classList.add("hidden");
  }
}

function renderAnalysisResult(data) {
  lastAnalyzedResult = data;
  const container = document.getElementById("analysisResultContainer");
  container.classList.remove("hidden");

  // KPI
  document.getElementById("resExecTime").textContent = `${data.execution_time_ms} ms`;
  document.getElementById("resRowCount").textContent = data.row_count;
  document.getElementById("resRowsExamined").textContent = data.total_rows_examined;
  document.getElementById("resQueryCost").textContent = data.query_cost !== null ? data.query_cost : "N/A";
  document.getElementById("resRatingBadge").innerHTML = getRatingBadge(data.performance_rating);

  // Bottlenecks
  const bList = document.getElementById("bottlenecksList");
  if (data.bottlenecks && data.bottlenecks.length > 0) {
    bList.innerHTML = data.bottlenecks.map(b => `
      <div class="bottleneck-item ${b.severity}">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-weight: 700; font-size: 0.825rem;">${b.type} (Table: ${b.table})</span>
          <span class="badge ${b.severity === 'CRITICAL' ? 'badge-critical' : b.severity === 'WARNING' ? 'badge-warning' : 'badge-info'}">${b.severity}</span>
        </div>
        <p style="font-size: 0.85rem; color: var(--text-muted);">${b.message}</p>
      </div>
    `).join("");
  } else {
    bList.innerHTML = `<div style="color: var(--accent-emerald); font-size: 0.9rem;">✨ No bottlenecks detected! This query performs efficiently with index coverage.</div>`;
  }

  // Recommendations
  const rList = document.getElementById("recommendationsList");
  if (data.recommendations && data.recommendations.length > 0) {
    rList.innerHTML = data.recommendations.map(r => `
      <div class="rec-item">
        <span style="font-size: 1.25rem;">💡</span>
        <div>
          <span class="badge badge-info" style="margin-bottom: 0.25rem;">${r.category}</span>
          <p style="font-size: 0.85rem; color: var(--text-main);">${r.suggestion}</p>
        </div>
      </div>
    `).join("");
  } else {
    rList.innerHTML = `<div style="color: var(--text-dim); font-size: 0.9rem;">No further recommendations required.</div>`;
  }

  // Tabular EXPLAIN
  const explainBody = document.getElementById("explainTableBody");
  if (data.tabular_plan && data.tabular_plan.length > 0) {
    explainBody.innerHTML = data.tabular_plan.map(r => `
      <tr>
        <td class="mono">${r.id}</td>
        <td>${r.select_type}</td>
        <td class="mono" style="color: #60a5fa; font-weight: 600;">${r.table}</td>
        <td><span class="badge ${r.type === 'ALL' ? 'badge-warning' : 'badge-optimized'}">${r.type}</span></td>
        <td class="mono">${r.possible_keys || '<span style="color:var(--text-dim)">NULL</span>'}</td>
        <td class="mono" style="color: var(--accent-emerald); font-weight: 600;">${r.key || '<span style="color:var(--text-dim)">NULL</span>'}</td>
        <td class="mono">${r.rows}</td>
        <td class="mono">${r.filtered}%</td>
        <td style="color: var(--text-muted); font-size: 0.8rem;">${r.Extra || '-'}</td>
      </tr>
    `).join("");
  } else {
    explainBody.innerHTML = `<tr><td colspan="9" style="text-align: center;">No plan available.</td></tr>`;
  }

  // Result Preview Table
  const previewHead = document.getElementById("previewTableHead");
  const previewBody = document.getElementById("previewTableBody");
  if (data.rows && data.rows.length > 0) {
    const cols = Object.keys(data.rows[0]);
    previewHead.innerHTML = `<tr>${cols.map(c => `<th>${c}</th>`).join("")}</tr>`;
    previewBody.innerHTML = data.rows.map(row => `
      <tr>${cols.map(c => `<td class="mono">${row[c] !== null ? row[c] : 'NULL'}</td>`).join("")}</tr>
    `).join("");
  } else {
    previewHead.innerHTML = `<tr><th>Result</th></tr>`;
    previewBody.innerHTML = `<tr><td style="color: var(--text-dim);">Query executed successfully. 0 rows returned.</td></tr>`;
  }
}

// 3. QUERY COMPARISON
function loadComparisonPreset() {
  document.getElementById("compareTitle").value = "Primary Key Filter vs Unindexed Scan";
  document.getElementById("compareQueryA").value = "SELECT * FROM customers WHERE email = 'arun@example.com';";
  document.getElementById("compareQueryB").value = "SELECT id, name FROM customers WHERE id = 1;";
}

async function runComparison() {
  if (!token) {
    showToast("Please sign in to compare queries.", "error");
    openAuthModal("login");
    return;
  }

  const query_a = document.getElementById("compareQueryA").value.trim();
  const query_b = document.getElementById("compareQueryB").value.trim();
  const title = document.getElementById("compareTitle").value.trim();

  if (!query_a || !query_b) {
    showToast("Please provide both Query A and Query B.", "error");
    return;
  }

  const btn = document.getElementById("btnCompare");
  const spinner = document.getElementById("compareSpinner");
  btn.disabled = true;
  spinner.classList.remove("hidden");

  try {
    const res = await apiRequest("/api/v1/queries/compare", {
      method: "POST",
      body: JSON.stringify({ query_a, query_b, title: title || null })
    });

    const data = await res.json();
    if (!res.ok) {
      showToast(data.detail || "Query comparison failed.", "error");
      return;
    }

    renderComparisonResult(data);
    loadSavedComparisons();
    showToast("Comparison benchmark completed!", "success");
  } catch (err) {
    showToast("Error running comparison.", "error");
  } finally {
    btn.disabled = false;
    spinner.classList.add("hidden");
  }
}

function renderComparisonResult(data) {
  const container = document.getElementById("comparisonResultContainer");
  container.classList.remove("hidden");

  // Verdict Banner
  document.getElementById("compVerdictText").textContent = data.verdict;
  document.getElementById("compSpeedupBadge").innerHTML = `
    <span class="badge badge-optimized" style="font-size: 0.95rem; padding: 0.4rem 0.8rem;">
      ⚡ ${data.speedup_percentage}% Speedup
    </span>
  `;

  // Query A
  const qa = data.query_a;
  document.getElementById("compA_time").textContent = `${qa.execution_time_ms} ms`;
  document.getElementById("compA_rows").textContent = qa.total_rows_examined;
  document.getElementById("compA_cost").textContent = qa.query_cost !== null ? qa.query_cost : "N/A";
  document.getElementById("compA_fts").innerHTML = qa.has_full_table_scan ? '<span class="badge badge-warning">YES</span>' : '<span class="badge badge-optimized">NO</span>';
  document.getElementById("compA_rating").innerHTML = getRatingBadge(qa.performance_rating);

  // Query B
  const qb = data.query_b;
  document.getElementById("compB_time").textContent = `${qb.execution_time_ms} ms`;
  document.getElementById("compB_rows").textContent = qb.total_rows_examined;
  document.getElementById("compB_cost").textContent = qb.query_cost !== null ? qb.query_cost : "N/A";
  document.getElementById("compB_fts").innerHTML = qb.has_full_table_scan ? '<span class="badge badge-warning">YES</span>' : '<span class="badge badge-optimized">NO</span>';
  document.getElementById("compB_rating").innerHTML = getRatingBadge(qb.performance_rating);

  // Comparison Bar Chart
  const compCtx = document.getElementById("comparisonChart").getContext("2d");
  if (comparisonChartInstance) comparisonChartInstance.destroy();
  comparisonChartInstance = new Chart(compCtx, {
    type: "bar",
    data: {
      labels: ["Execution Time (ms)", "Rows Examined"],
      datasets: [
        {
          label: "Query A",
          data: [qa.execution_time_ms, qa.total_rows_examined],
          backgroundColor: "#f59e0b"
        },
        {
          label: "Query B",
          data: [qb.execution_time_ms, qb.total_rows_examined],
          backgroundColor: "#10b981"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { grid: { color: "#232d42" }, ticks: { color: "#9ca3af" } },
        x: { grid: { color: "#232d42" }, ticks: { color: "#9ca3af" } }
      },
      plugins: {
        legend: { labels: { color: "#9ca3af" } }
      }
    }
  });
}

async function loadSavedComparisons() {
  if (!token) return;

  try {
    const res = await apiRequest("/api/v1/queries/comparisons?page=1&page_size=10");
    if (!res.ok) return;
    const data = await res.json();

    const tbody = document.getElementById("comparisonsHistoryTable");
    if (data.items && data.items.length > 0) {
      tbody.innerHTML = data.items.map(item => `
        <tr>
          <td style="font-weight: 600;">${item.title || "SQL Comparison"}</td>
          <td class="mono">${item.query_a_time_ms} ms</td>
          <td class="mono">${item.query_b_time_ms} ms</td>
          <td><span class="badge ${item.faster_query === 'QUERY_B' ? 'badge-optimized' : 'badge-warning'}">${item.faster_query}</span></td>
          <td class="mono" style="color: var(--accent-emerald); font-weight: 700;">+${item.speedup_percentage}%</td>
          <td style="color: var(--text-dim); font-size: 0.8rem;">${new Date(item.created_at).toLocaleString()}</td>
        </tr>
      `).join("");
    } else {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-dim);">No saved comparisons found.</td></tr>`;
    }
  } catch (e) {
    console.error("Error loading comparisons:", e);
  }
}

// 4. QUERY HISTORY
async function loadHistory(page = 1) {
  if (!token) {
    document.getElementById("historyTableBody").innerHTML = `<tr><td colspan="8" style="text-align:center; color: var(--text-dim);">Please sign in to view your history.</td></tr>`;
    return;
  }

  historyPage = page;
  try {
    const res = await apiRequest(`/api/v1/queries/history?page=${page}&page_size=${historyPageSize}`);
    if (!res.ok) return;
    const data = await res.json();

    historyTotalPages = data.total_pages || 1;
    document.getElementById("historyCountText").textContent = `Showing ${data.items.length} of ${data.total} queries`;
    document.getElementById("historyPageNumber").textContent = `Page ${data.page} of ${historyTotalPages}`;
    document.getElementById("btnHistPrev").disabled = data.page <= 1;
    document.getElementById("btnHistNext").disabled = data.page >= historyTotalPages;

    const tbody = document.getElementById("historyTableBody");
    if (data.items.length > 0) {
      tbody.innerHTML = data.items.map(item => `
        <tr>
          <td class="mono">#${item.id}</td>
          <td class="mono" title="${item.query}">${item.query.length > 50 ? item.query.substring(0, 50) + '...' : item.query}</td>
          <td class="mono" style="font-weight: 600;">${item.execution_time_ms} ms</td>
          <td>${item.row_count}</td>
          <td>${getRatingBadge(item.performance_rating)}</td>
          <td>${item.has_full_table_scan ? '<span class="badge badge-warning">YES</span>' : '<span class="badge badge-optimized">NO</span>'}</td>
          <td style="color: var(--text-dim); font-size: 0.8rem;">${new Date(item.created_at).toLocaleString()}</td>
          <td>
            <button class="btn btn-secondary" style="padding: 0.2rem 0.5rem; font-size: 0.75rem;" onclick="loadAndAnalyzeQuery('${encodeURIComponent(item.query)}')">Re-analyze</button>
          </td>
        </tr>
      `).join("");
    } else {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-dim);">No query analyses found in your history.</td></tr>`;
    }
  } catch (e) {
    console.error("Error loading query history:", e);
  }
}

function changeHistoryPage(delta) {
  const newPage = historyPage + delta;
  if (newPage >= 1 && newPage <= historyTotalPages) {
    loadHistory(newPage);
  }
}

// 5. ADMIN
async function loadAdmin() {
  if (!token) return;

  try {
    const res = await apiRequest("/api/v1/admin/dashboard");
    if (!res.ok) {
      showToast("Access denied: Administrator privileges required.", "error");
      navigate("dashboard");
      return;
    }
    const data = await res.json();

    document.getElementById("admTotalUsers").textContent = data.user_stats.total_users;
    document.getElementById("admActiveUsers").textContent = data.user_stats.active_users;
    document.getElementById("admAdminUsers").textContent = data.user_stats.admin_users;

    document.getElementById("admTotalQueries").textContent = data.usage_stats.total_queries;
    document.getElementById("admTotalComparisons").textContent = data.usage_stats.total_comparisons;
    document.getElementById("admAvgLatency").textContent = `${data.usage_stats.avg_platform_latency_ms} ms`;

    // Live Telemetry
    if (data.telemetry) {
      const t = data.telemetry;
      document.getElementById("admCpuPercent").textContent = `${t.cpu_percent}%`;
      document.getElementById("admRamUsage").textContent = `${t.memory_used_gb} / ${t.memory_total_gb} GB`;
      document.getElementById("admRamPercent").textContent = `${t.memory_percent}% consumed`;
      document.getElementById("admDiskUsage").textContent = `${t.disk_used_gb} / ${t.disk_total_gb} GB`;
      document.getElementById("admDiskPercent").textContent = `${t.disk_percent}% consumed`;
      document.getElementById("admActiveThreads").textContent = t.active_threads;
    }

    // Health
    const appEl = document.getElementById("admAppDbStatus");
    appEl.textContent = data.health.app_database;
    appEl.className = `badge ${data.health.app_database === 'ONLINE' ? 'badge-optimized' : 'badge-critical'}`;

    const analEl = document.getElementById("admAnalysisDbStatus");
    analEl.textContent = data.health.analysis_database;
    analEl.className = `badge ${data.health.analysis_database === 'ONLINE' ? 'badge-optimized' : 'badge-critical'}`;

    const sysEl = document.getElementById("admSystemStatus");
    sysEl.textContent = data.health.status;
    sysEl.className = `badge ${data.health.status === 'HEALTHY' ? 'badge-optimized' : 'badge-warning'}`;

    // Load sub-tables
    await Promise.all([
      loadAdminUsers(),
      loadAdminSecurityLogs(),
      loadAdminFeedbacks()
    ]);
  } catch (e) {
    console.error("Admin dashboard error:", e);
  }
}

async function loadAdminUsers() {
  try {
    const res = await apiRequest("/api/v1/admin/users");
    if (!res.ok) return;
    const users = await res.json();

    const tbody = document.getElementById("adminUsersTableBody");
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
          <button class="btn ${u.is_active ? 'btn-danger' : 'btn-secondary'}" style="padding: 0.2rem 0.5rem; font-size: 0.75rem;" onclick="toggleUserStatus(${u.id}, ${u.is_active})">
            ${u.is_active ? 'Suspend' : 'Activate'}
          </button>
          <button class="btn btn-secondary" style="padding: 0.2rem 0.5rem; font-size: 0.75rem; margin-left: 0.25rem;" onclick="toggleUserRole(${u.id}, '${u.role}')">
            ${u.role === 'ADMIN' ? 'Make User' : 'Make Admin'}
          </button>
        </td>
      </tr>
    `).join("");
  } catch (err) {
    console.error("Error loading users:", err);
  }
}

async function toggleUserStatus(userId, currentStatus) {
  try {
    const res = await apiRequest(`/api/v1/admin/users/${userId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: !currentStatus })
    });
    if (res.ok) {
      showToast(`User ${!currentStatus ? 'activated' : 'suspended'} successfully.`, "success");
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
    const res = await apiRequest(`/api/v1/admin/users/${userId}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role: newRole })
    });
    if (res.ok) {
      showToast(`User role updated to ${newRole}.`, "success");
      loadAdminUsers();
    } else {
      const d = await res.json();
      showToast(d.detail || "Failed to update user role.", "error");
    }
  } catch (e) {
    showToast("Network error updating role.", "error");
  }
}

async function loadAdminSecurityLogs() {
  try {
    const res = await apiRequest("/api/v1/admin/security-logs?limit=15");
    if (!res.ok) return;
    const logs = await res.json();

    const tbody = document.getElementById("adminSecurityLogsBody");
    if (logs.length > 0) {
      tbody.innerHTML = logs.map(l => `
        <tr>
          <td class="mono">#${l.id}</td>
          <td>${l.user_email || '<span style="color:var(--text-dim)">Anonymous</span>'}</td>
          <td><span class="badge badge-critical">${l.violation_type}</span></td>
          <td class="mono" style="color: var(--accent-rose);">${l.attempted_query.length > 55 ? l.attempted_query.substring(0, 55) + '...' : l.attempted_query}</td>
          <td style="color: var(--text-dim); font-size: 0.8rem;">${new Date(l.created_at).toLocaleString()}</td>
        </tr>
      `).join("");
    } else {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-dim);">No security violations detected.</td></tr>`;
    }
  } catch (err) {
    console.error("Error loading security logs:", err);
  }
}

async function loadAdminFeedbacks() {
  try {
    const res = await apiRequest("/api/v1/admin/feedback");
    if (!res.ok) return;
    const feedbacks = await res.json();

    const tbody = document.getElementById("adminFeedbackTableBody");
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
            <select style="font-size: 0.75rem; background: var(--bg-card); color: var(--text-main); border: 1px solid var(--border-color); padding: 0.2rem; border-radius: 4px;" onchange="updateFeedbackStatus(${f.id}, this.value)">
              <option value="PENDING" ${f.status === 'PENDING' ? 'selected' : ''}>Pending</option>
              <option value="REVIEWED" ${f.status === 'REVIEWED' ? 'selected' : ''}>Reviewed</option>
              <option value="RESOLVED" ${f.status === 'RESOLVED' ? 'selected' : ''}>Resolved</option>
            </select>
          </td>
        </tr>
      `).join("");
    } else {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-dim);">No user feedback yet.</td></tr>`;
    }
  } catch (err) {
    console.error("Error loading feedbacks:", err);
  }
}

async function updateFeedbackStatus(feedbackId, newStatus) {
  try {
    const res = await apiRequest(`/api/v1/admin/feedback/${feedbackId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status: newStatus })
    });
    if (res.ok) {
      showToast(`Feedback #${feedbackId} marked as ${newStatus}.`, "success");
      loadAdminFeedbacks();
    }
  } catch (e) {
    showToast("Error updating feedback status.", "error");
  }
}

// FEEDBACK MODAL
function openFeedbackModal() {
  if (!token) {
    showToast("Please sign in to share feedback.", "error");
    openAuthModal("login");
    return;
  }
  setRating(5);
  document.getElementById("feedbackModal").classList.remove("hidden");
}

function closeFeedbackModal() {
  document.getElementById("feedbackModal").classList.add("hidden");
}

function setRating(rating) {
  currentFeedbackRating = rating;
  const stars = document.getElementById("starRatingContainer").children;
  for (let i = 0; i < 5; i++) {
    stars[i].style.color = i < rating ? "#fbbf24" : "#4b5563";
  }
}

async function handleFeedbackSubmit(event) {
  event.preventDefault();
  const category = document.getElementById("fbCategory").value;
  const comment = document.getElementById("fbComment").value.trim();

  try {
    const res = await apiRequest("/api/v1/feedback", {
      method: "POST",
      body: JSON.stringify({
        category,
        rating: currentFeedbackRating,
        comment
      })
    });
    if (res.ok) {
      closeFeedbackModal();
      document.getElementById("fbComment").value = "";
      showToast("Thank you for your feedback! It helps us build a better platform.", "success");
    } else {
      showToast("Failed to submit feedback.", "error");
    }
  } catch (e) {
    showToast("Network error submitting feedback.", "error");
  }
}

// REPORT EXPORT MODAL
function exportCurrentReport() {
  if (!lastAnalyzedResult) {
    showToast("No query analysis available to export.", "error");
    return;
  }

  const report = {
    platform: "SQL Performance Analyzer",
    report_type: "Database Query Optimization & Performance Audit Report",
    exported_at: new Date().toISOString(),
    query: lastAnalyzedResult.query,
    execution_metrics: {
      execution_time_ms: lastAnalyzedResult.execution_time_ms,
      row_count: lastAnalyzedResult.row_count,
      total_rows_examined: lastAnalyzedResult.total_rows_examined,
      query_cost: lastAnalyzedResult.query_cost,
      has_full_table_scan: lastAnalyzedResult.has_full_table_scan,
      using_filesort: lastAnalyzedResult.using_filesort,
      using_temporary: lastAnalyzedResult.using_temporary,
      performance_rating: lastAnalyzedResult.performance_rating
    },
    bottlenecks: lastAnalyzedResult.bottlenecks || [],
    recommendations: lastAnalyzedResult.recommendations || [],
    tabular_execution_plan: lastAnalyzedResult.tabular_plan || []
  };

  document.getElementById("reportJsonView").textContent = JSON.stringify(report, null, 2);
  document.getElementById("reportModal").classList.remove("hidden");
}

function closeReportModal() {
  document.getElementById("reportModal").classList.add("hidden");
}

function copyReportText() {
  const text = document.getElementById("reportJsonView").textContent;
  navigator.clipboard.writeText(text).then(() => {
    showToast("Performance report JSON copied to clipboard!", "success");
  });
}

// Helper: rating badge markup
function getRatingBadge(rating) {
  if (!rating || rating === "OPTIMIZED") {
    return `<span class="badge badge-optimized">OPTIMIZED</span>`;
  } else if (rating === "NEEDS_OPTIMIZATION") {
    return `<span class="badge badge-warning">NEEDS OPTIMIZATION</span>`;
  } else {
    return `<span class="badge badge-critical">CRITICAL</span>`;
  }
}

