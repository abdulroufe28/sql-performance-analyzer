// SQL Performance Analyzer Frontend App
let token = localStorage.getItem("token") || null;
let currentUser = null;
let currentView = "dashboard";
let historyPage = 1;
let historyPageSize = 10;
let historyTotalPages = 1;
let lastAnalyzedResult = null;
let currentFeedbackRating = 5;
let googleClientId = null;

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
  await initGoogleAuth();
  navigate("dashboard");
  loadDatabaseSchema();
});

// Google OAuth 2.0 Integration
async function initGoogleAuth() {
  try {
    const res = await fetch("/api/v1/auth/google/config");
    if (!res.ok) return;
    const data = await res.json();
    googleClientId = data.google_client_id;

    if (googleClientId && window.google && window.google.accounts) {
      google.accounts.id.initialize({
        client_id: googleClientId,
        callback: handleGoogleAuthCallback,
        auto_select: false,
      });
    }
  } catch (err) {
    console.warn("Google auth init error:", err);
  }
}

function triggerGoogleSignIn() {
  if (googleClientId && window.google && window.google.accounts) {
    google.accounts.id.prompt((notification) => {
      if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
        openGooglePromptModal();
      }
    });
  } else {
    openGooglePromptModal();
  }
}

function openGooglePromptModal() {
  document.getElementById("googlePromptModal").classList.remove("hidden");
}

function closeGooglePromptModal() {
  document.getElementById("googlePromptModal").classList.add("hidden");
}

function selectDevGoogleAccount(email, name) {
  closeGooglePromptModal();
  handleGoogleAuthCallback({ credential: `dev_google_:${email}:${name}` });
}

async function handleGoogleAuthCallback(response) {
  if (!response || !response.credential) {
    showToast("No Google credential received.", "error");
    return;
  }

  try {
    const res = await fetch("/api/v1/auth/google", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ credential: response.credential }),
    });

    const data = await res.json();
    if (!res.ok) {
      showToast(data.detail || "Google authentication failed.", "error");
      return;
    }

    token = data.access_token;
    localStorage.setItem("token", token);
    closeAuthModal();
    showToast("Signed in with Google successfully!", "success");
    await checkAuth();
    navigate(currentView);
  } catch (err) {
    showToast("Network error verifying Google token.", "error");
  }
}

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

  if (currentUser) {
    userProfile.classList.remove("hidden");
    loginBtn.classList.add("hidden");
    document.getElementById("userEmailText").textContent = currentUser.email;
    const roleTag = document.getElementById("userRoleTag");
    roleTag.textContent = currentUser.role;
    roleTag.className = `role-tag ${currentUser.role === "ADMIN" ? "admin" : ""}`;
  } else {
    userProfile.classList.add("hidden");
    loginBtn.classList.remove("hidden");
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

  const views = ["dashboard", "analyzer", "comparison", "history"];
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

  document.querySelectorAll(".nav-btn").forEach(btn => {
    if (btn.getAttribute("data-view") === viewName) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  if (viewName === "dashboard") loadDashboard();
  if (viewName === "history") loadHistory(1);
  if (viewName === "comparison") loadSavedComparisons();
  if (viewName === "analyzer") loadDatabaseSchema();
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

    const quotaPct = Math.min(100, Math.round((data.comparison_quota_used / data.comparison_quota_limit) * 100));
    document.getElementById("dashQuotaText").textContent = `${data.comparison_quota_used} / ${data.comparison_quota_limit}`;
    document.getElementById("dashQuotaBar").style.width = `${quotaPct}%`;

    const slowBody = document.getElementById("slowestQueriesTable");
    if (data.slowest_queries && data.slowest_queries.length > 0) {
      slowBody.innerHTML = data.slowest_queries.map(q => `
        <tr>
          <td class="mono" title="${q.query}">${q.query.length > 45 ? q.query.substring(0, 45) + '...' : q.query}</td>
          <td class="mono" style="color: var(--rose-danger); font-weight: 700;">${q.execution_time_ms} ms</td>
          <td>${q.row_count}</td>
          <td><button class="btn btn-secondary" style="padding: 0.25rem 0.65rem; font-size: 0.75rem;" onclick="loadAndAnalyzeQuery('${encodeURIComponent(q.query)}')">Inspect</button></td>
        </tr>
      `).join("");
    } else {
      slowBody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-dim);">No slow queries detected.</td></tr>`;
    }

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

    renderDashboardCharts(data);
  } catch (err) {
    console.error("Dashboard error:", err);
  }
}

function renderDashboardCharts(data) {
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
        borderColor: "#06b6d4",
        backgroundColor: "rgba(6, 182, 212, 0.15)",
        fill: true,
        tension: 0.35,
        pointBackgroundColor: "#22d3ee"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { grid: { color: "rgba(255, 255, 255, 0.05)" }, ticks: { color: "#94a3b8" } },
        x: { grid: { color: "rgba(255, 255, 255, 0.05)" }, ticks: { color: "#94a3b8" } }
      },
      plugins: { legend: { display: false } }
    }
  });

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
        legend: { position: "bottom", labels: { color: "#94a3b8", font: { size: 12 } } }
      }
    }
  });
}

// 2. QUERY ANALYZER & SCHEMA EXPLORER
async function loadDatabaseSchema() {
  if (!token) return;

  try {
    const res = await apiRequest("/api/v1/queries/schema");
    if (!res.ok) return;
    const data = await res.json();

    const container = document.getElementById("schemaTagsContainer");
    if (data.tables && data.tables.length > 0) {
      container.innerHTML = data.tables.map(tbl => `
        <div style="display: inline-flex; align-items: center; gap: 0.35rem; margin-right: 0.75rem; margin-bottom: 0.35rem;">
          <span class="schema-table-badge" onclick="appendSqlText('${tbl.name}')" title="Insert table name">
            📁 ${tbl.name}
          </span>
          <span style="display: inline-flex; gap: 0.25rem;">
            ${tbl.columns.map(c => `
              <span style="cursor: pointer; background: rgba(255,255,255,0.05); font-size: 0.72rem; padding: 0.2rem 0.45rem; border-radius: 6px; color: ${c.is_primary ? '#38bdf8' : '#cbd5e1'}; font-family: var(--font-mono);" onclick="appendSqlText('${c.name}')" title="Insert column ${c.name} (${c.type})">
                ${c.is_primary ? '🔑 ' : ''}${c.name}
              </span>
            `).join("")}
          </span>
        </div>
      `).join("");
    }
  } catch (err) {
    console.error("Schema error:", err);
  }
}

function appendSqlText(text) {
  const area = document.getElementById("sqlInput");
  area.value = area.value ? `${area.value.trim()} ${text}` : text;
  area.focus();
}

function formatSqlQuery() {
  const area = document.getElementById("sqlInput");
  let sql = area.value.trim();
  if (!sql) return;

  const keywords = ["SELECT", "FROM", "WHERE", "JOIN", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN", "ON", "ORDER BY", "GROUP BY", "HAVING", "LIMIT", "AND", "OR"];
  keywords.forEach(kw => {
    const regex = new RegExp(`\\b${kw}\\b`, "gi");
    sql = sql.replace(regex, kw);
  });
  area.value = sql;
  showToast("SQL formatting applied.", "success");
}

function clearSqlEditor() {
  document.getElementById("sqlInput").value = "";
  document.getElementById("analysisResultContainer").classList.add("hidden");
}

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
    showToast("Query analysis & EXPLAIN profiling complete!", "success");
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

  // KPI Row
  document.getElementById("resExecTime").textContent = `${data.execution_time_ms} ms`;
  document.getElementById("resRowCount").textContent = data.row_count;
  document.getElementById("resRowsExamined").textContent = data.total_rows_examined;
  document.getElementById("resQueryCost").textContent = data.query_cost !== null ? data.query_cost : "N/A";
  document.getElementById("resRatingBadge").innerHTML = getRatingBadge(data.performance_rating);

  // Scan Efficiency / Selectivity Gauge
  const examined = Math.max(1, data.total_rows_examined);
  const efficiencyRatio = Math.min(100, Math.round((data.row_count / examined) * 100));
  const bar = document.getElementById("resEfficiencyBar");
  const txt = document.getElementById("resEfficiencyText");
  txt.textContent = `${efficiencyRatio}%`;
  bar.style.width = `${efficiencyRatio}%`;
  if (efficiencyRatio >= 50) {
    bar.style.background = "linear-gradient(90deg, #10b981, #34d399)";
    txt.style.color = "#34d399";
  } else if (efficiencyRatio >= 15) {
    bar.style.background = "linear-gradient(90deg, #f59e0b, #fbbf24)";
    txt.style.color = "#fbbf24";
  } else {
    bar.style.background = "linear-gradient(90deg, #f43f5e, #fb7185)";
    txt.style.color = "#fb7185";
  }

  // Visual Plan Tree Flowchart
  renderVisualPlanTree(data);

  // Auto-Optimizer Suggestion Box
  const autoFixBox = document.getElementById("autoFixContainer");
  if (data.has_full_table_scan) {
    autoFixBox.classList.remove("hidden");
    const codeEl = document.getElementById("autoFixCode");
    const descEl = document.getElementById("autoFixDescription");
    descEl.textContent = "Full table scan detected. Adding a B-Tree index on filtered columns will replace this scan with a fast index seek.";
    codeEl.textContent = "CREATE INDEX idx_customers_filter ON customers(email);";
  } else {
    autoFixBox.classList.add("hidden");
  }

  // Bottlenecks List
  const bList = document.getElementById("bottlenecksList");
  if (data.bottlenecks && data.bottlenecks.length > 0) {
    bList.innerHTML = data.bottlenecks.map(b => `
      <div class="bottleneck-item ${b.severity}">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-weight: 700; font-size: 0.825rem; color: #fff;">${b.type} (Table: ${b.table})</span>
          <span class="badge ${b.severity === 'CRITICAL' ? 'badge-critical' : b.severity === 'WARNING' ? 'badge-warning' : 'badge-info'}">${b.severity}</span>
        </div>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">${b.message}</p>
      </div>
    `).join("");
  } else {
    bList.innerHTML = `<div style="color: var(--emerald-success); font-size: 0.9rem; padding: 0.5rem 0;">✨ Clean execution plan! No performance bottlenecks detected.</div>`;
  }

  // Recommendations
  const rList = document.getElementById("recommendationsList");
  if (data.recommendations && data.recommendations.length > 0) {
    rList.innerHTML = data.recommendations.map(r => `
      <div class="rec-item">
        <span style="font-size: 1.35rem;">💡</span>
        <div>
          <span class="badge badge-info" style="margin-bottom: 0.35rem;">${r.category}</span>
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
        <td class="mono" style="color: var(--cyan-glow); font-weight: 700;">${r.table}</td>
        <td><span class="badge ${r.type === 'ALL' ? 'badge-warning' : 'badge-optimized'}">${r.type}</span></td>
        <td class="mono">${r.possible_keys || '<span style="color:var(--text-dim)">NULL</span>'}</td>
        <td class="mono" style="color: var(--emerald-success); font-weight: 700;">${r.key || '<span style="color:var(--text-dim)">NULL</span>'}</td>
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

// Visual Node Graph Builder
function renderVisualPlanTree(data) {
  const container = document.getElementById("visualPlanContainer");
  const nodes = [];

  // Node 1: Client Query Request
  nodes.push(`
    <div class="plan-node status-good">
      <div class="node-title">Stage 1: Parser</div>
      <div class="node-label">SQL Query Input</div>
      <div class="node-metric">Validated Safe</div>
    </div>
  `);

  // Node 2: Storage Engine Access Mode
  const isFullScan = data.has_full_table_scan;
  const accessClass = isFullScan ? "status-warning" : "status-good";
  const accessLabel = isFullScan ? "Full Table Scan (ALL)" : `Index Seek (${data.indexes_used.join(', ') || 'Primary/Const'})`;
  nodes.push(`
    <div class="plan-node ${accessClass}">
      <div class="node-title">Stage 2: Engine Access</div>
      <div class="node-label">${accessLabel}</div>
      <div class="node-metric">Examined: ${data.total_rows_examined} rows</div>
    </div>
  `);

  // Node 3: Sorting / Filtering Stage (if applicable)
  if (data.using_filesort || data.using_temporary) {
    nodes.push(`
      <div class="plan-node status-warning">
        <div class="node-title">Stage 3: Sort / Temp</div>
        <div class="node-label">${data.using_filesort ? 'Using Filesort' : 'Temporary Table'}</div>
        <div class="node-metric">In-Memory / Disk Pass</div>
      </div>
    `);
  }

  // Final Node: Result Set Output
  nodes.push(`
    <div class="plan-node status-good">
      <div class="node-title">Stage ${nodes.length + 1}: Output</div>
      <div class="node-label">Result Set</div>
      <div class="node-metric">${data.row_count} rows returned (${data.execution_time_ms} ms)</div>
    </div>
  `);

  container.innerHTML = nodes.join('<div class="plan-arrow">➔</div>');
}

function loadAutoFixIntoComparison() {
  if (!lastAnalyzedResult) return;
  navigate("comparison");
  document.getElementById("compareTitle").value = "Original Scan vs Optimized Lookup";
  document.getElementById("compareQueryA").value = lastAnalyzedResult.query;
  document.getElementById("compareQueryB").value = "SELECT id, name FROM customers WHERE id = 1;";
  showToast("Baseline and candidate queries prepared in Comparison tab.", "success");
}

// 3. QUERY COMPARISON
function loadComparisonPreset() {
  document.getElementById("compareTitle").value = "Full Table Scan vs Primary Key Filter";
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
    showToast("Comparison benchmark completed successfully!", "success");
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

  document.getElementById("compVerdictText").textContent = data.verdict;
  document.getElementById("compSpeedupBadge").innerHTML = `
    <span class="badge badge-optimized" style="font-size: 0.95rem; padding: 0.45rem 0.95rem;">
      ⚡ ${data.speedup_percentage}% Speedup
    </span>
  `;

  const qa = data.query_a;
  document.getElementById("compA_time").textContent = `${qa.execution_time_ms} ms`;
  document.getElementById("compA_rows").textContent = qa.total_rows_examined;
  document.getElementById("compA_cost").textContent = qa.query_cost !== null ? qa.query_cost : "N/A";
  document.getElementById("compA_fts").innerHTML = qa.has_full_table_scan ? '<span class="badge badge-warning">YES</span>' : '<span class="badge badge-optimized">NO</span>';
  document.getElementById("compA_rating").innerHTML = getRatingBadge(qa.performance_rating);

  const qb = data.query_b;
  document.getElementById("compB_time").textContent = `${qb.execution_time_ms} ms`;
  document.getElementById("compB_rows").textContent = qb.total_rows_examined;
  document.getElementById("compB_cost").textContent = qb.query_cost !== null ? qb.query_cost : "N/A";
  document.getElementById("compB_fts").innerHTML = qb.has_full_table_scan ? '<span class="badge badge-warning">YES</span>' : '<span class="badge badge-optimized">NO</span>';
  document.getElementById("compB_rating").innerHTML = getRatingBadge(qb.performance_rating);

  const compCtx = document.getElementById("comparisonChart").getContext("2d");
  if (comparisonChartInstance) comparisonChartInstance.destroy();
  comparisonChartInstance = new Chart(compCtx, {
    type: "bar",
    data: {
      labels: ["Execution Time (ms)", "Rows Examined"],
      datasets: [
        {
          label: "Query A (Baseline)",
          data: [qa.execution_time_ms, qa.total_rows_examined],
          backgroundColor: "#f59e0b"
        },
        {
          label: "Query B (Optimized)",
          data: [qb.execution_time_ms, qb.total_rows_examined],
          backgroundColor: "#10b981"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { grid: { color: "rgba(255, 255, 255, 0.05)" }, ticks: { color: "#94a3b8" } },
        x: { grid: { color: "rgba(255, 255, 255, 0.05)" }, ticks: { color: "#94a3b8" } }
      },
      plugins: {
        legend: { labels: { color: "#94a3b8" } }
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
          <td style="font-weight: 700; color: #fff;">${item.title || "SQL Comparison"}</td>
          <td class="mono">${item.query_a_time_ms} ms</td>
          <td class="mono">${item.query_b_time_ms} ms</td>
          <td><span class="badge ${item.faster_query === 'QUERY_B' ? 'badge-optimized' : 'badge-warning'}">${item.faster_query}</span></td>
          <td class="mono" style="color: var(--emerald-success); font-weight: 800;">+${item.speedup_percentage}%</td>
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
          <td class="mono" title="${item.query}">${item.query.length > 45 ? item.query.substring(0, 45) + '...' : item.query}</td>
          <td class="mono" style="font-weight: 700;">${item.execution_time_ms} ms</td>
          <td>${item.row_count}</td>
          <td>${getRatingBadge(item.performance_rating)}</td>
          <td>${item.has_full_table_scan ? '<span class="badge badge-warning">YES</span>' : '<span class="badge badge-optimized">NO</span>'}</td>
          <td style="color: var(--text-dim); font-size: 0.8rem;">${new Date(item.created_at).toLocaleDateString()}</td>
          <td>
            <button class="btn btn-secondary" style="padding: 0.25rem 0.55rem; font-size: 0.75rem;" onclick="loadAndAnalyzeQuery('${encodeURIComponent(item.query)}')">Re-analyze</button>
            <button class="btn btn-secondary" style="padding: 0.25rem 0.55rem; font-size: 0.75rem; margin-left: 0.2rem;" onclick="exportAnalysisById(${item.id})">Report</button>
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

// 5. ADMIN COMMAND CENTER
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

    // Hardware Telemetry
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

    // Sub-tables
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
      showToast(`User account status updated.`, "success");
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
      showToast(d.detail || "Failed to update role.", "error");
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
          <td class="mono" style="color: var(--rose-danger);">${l.attempted_query.length > 55 ? l.attempted_query.substring(0, 55) + '...' : l.attempted_query}</td>
          <td style="color: var(--text-dim); font-size: 0.8rem;">${new Date(l.created_at).toLocaleString()}</td>
        </tr>
      `).join("");
    } else {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-dim);">No security threats logged.</td></tr>`;
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
      showToast("Thank you for your feedback! It helps us continuously improve the platform.", "success");
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

async function exportAnalysisById(id) {
  try {
    const res = await apiRequest(`/api/v1/queries/analyses/${id}/export`);
    if (res.ok) {
      const report = await res.json();
      document.getElementById("reportJsonView").textContent = JSON.stringify(report, null, 2);
      document.getElementById("reportModal").classList.remove("hidden");
    } else {
      showToast("Failed to load report.", "error");
    }
  } catch (e) {
    showToast("Error retrieving report.", "error");
  }
}

function closeReportModal() {
  document.getElementById("reportModal").classList.add("hidden");
}

function copyReportText() {
  const text = document.getElementById("reportJsonView").textContent;
  navigator.clipboard.writeText(text).then(() => {
    showToast("Performance audit report JSON copied to clipboard!", "success");
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
