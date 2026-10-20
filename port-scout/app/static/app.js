// Port Scout Client Application

(function () {
  // Derive base URL to seamlessly support Home Assistant Ingress
  const baseHref = window.location.pathname.replace(/\/+$/, "");

  function api(endpoint) {
    const cleanEndpoint = endpoint.startsWith("/") ? endpoint : "/" + endpoint;
    return `${baseHref}${cleanEndpoint}`;
  }

  let currentProtocol = "tcp";
  let lastAllocatedPort = null;
  let allPorts = [];

  // DOM Elements
  const dockerIndicator = document.getElementById("docker-indicator");
  const dockerStatus = document.getElementById("docker-status");
  const engineStatus = document.getElementById("engine-status");
  const btnRefresh = document.getElementById("btn-refresh");

  const protoTcp = document.getElementById("proto-tcp");
  const protoUdp = document.getElementById("proto-udp");
  const inputMinPort = document.getElementById("input-min-port");
  const inputMaxPort = document.getElementById("input-max-port");
  const btnRollPort = document.getElementById("btn-roll-port");
  const btnCopyPort = document.getElementById("btn-copy-port");
  const displayAllocatedPort = document.getElementById("display-allocated-port");
  const portDetails = document.getElementById("port-details");

  const inputCheckPort = document.getElementById("input-check-port");
  const btnCheckPort = document.getElementById("btn-check-port");
  const checkResultContainer = document.getElementById("check-result-container");
  const checkResultTitle = document.getElementById("check-result-title");
  const checkResultDesc = document.getElementById("check-result-desc");

  const statTotalPorts = document.getElementById("stat-total-ports");
  const statDockerPorts = document.getElementById("stat-docker-ports");

  const searchPorts = document.getElementById("search-ports");
  const filterType = document.getElementById("filter-type");
  const portsTableBody = document.getElementById("ports-table-body");

  // Protocol Toggle
  protoTcp.addEventListener("click", () => setProtocol("tcp"));
  protoUdp.addEventListener("click", () => setProtocol("udp"));

  function setProtocol(proto) {
    currentProtocol = proto;
    if (proto === "tcp") {
      protoTcp.className = "px-3 py-1 rounded-md font-medium transition bg-emerald-600 text-white";
      protoUdp.className = "px-3 py-1 rounded-md font-medium transition text-slate-400 hover:text-white";
    } else {
      protoUdp.className = "px-3 py-1 rounded-md font-medium transition bg-emerald-600 text-white";
      protoTcp.className = "px-3 py-1 rounded-md font-medium transition text-slate-400 hover:text-white";
    }
  }

  // Fetch Health
  async function checkHealth() {
    try {
      const res = await fetch(api("/api/v1/health"));
      if (!res.ok) throw new Error("Health check failed");
      const data = await res.json();

      if (data.docker_connected) {
        dockerIndicator.className = "w-2 h-2 rounded-full bg-emerald-400";
        dockerStatus.textContent = "Docker Connected";
      } else {
        dockerIndicator.className = "w-2 h-2 rounded-full bg-amber-400";
        dockerStatus.textContent = "Docker Offline";
      }

      if (data.scanner_engine) {
        engineStatus.textContent = `Engine: ${data.scanner_engine}`;
      }
    } catch (err) {
      dockerIndicator.className = "w-2 h-2 rounded-full bg-rose-500";
      dockerStatus.textContent = "API Unreachable";
    }
  }

  // Fetch Ports
  async function fetchPorts() {
    portsTableBody.innerHTML = `<tr><td colspan="5" class="px-4 py-8 text-center text-slate-500">Scanning ports...</td></tr>`;
    try {
      const res = await fetch(api("/api/v1/ports/used"));
      if (!res.ok) throw new Error("Failed to fetch ports");
      const data = await res.json();
      allPorts = data.ports || [];
      renderPortsTable();
      updateStats();
    } catch (err) {
      portsTableBody.innerHTML = `<tr><td colspan="5" class="px-4 py-8 text-center text-rose-400">Failed to load ports: ${err.message}</td></tr>`;
    }
  }

  function updateStats() {
    statTotalPorts.textContent = allPorts.length;
    const dockerCount = allPorts.filter(p => p.status === "docker_reserved").length;
    statDockerPorts.textContent = dockerCount;
  }

  function renderPortsTable() {
    const query = searchPorts.value.trim().toLowerCase();
    const filter = filterType.value;

    const filtered = allPorts.filter(item => {
      // Filter by type
      if (filter === "docker" && item.status !== "docker_reserved") return false;
      if (filter === "system" && item.status !== "listening") return false;

      // Filter by search query
      if (!query) return true;
      const portStr = item.port.toString();
      const protoStr = item.protocol.toLowerCase();
      const sourceStr = (item.source || "").toLowerCase();
      const containerStr = (item.container || "").toLowerCase();
      return portStr.includes(query) || protoStr.includes(query) || sourceStr.includes(query) || containerStr.includes(query);
    });

    if (filtered.length === 0) {
      portsTableBody.innerHTML = `<tr><td colspan="5" class="px-4 py-8 text-center text-slate-500">No ports matching filter</td></tr>`;
      return;
    }

    portsTableBody.innerHTML = filtered.map(item => {
      const isDocker = item.status === "docker_reserved";
      const badgeClass = isDocker
        ? "bg-sky-950 text-sky-400 border border-sky-800/60"
        : "bg-emerald-950 text-emerald-400 border border-emerald-800/60";
      const statusText = isDocker ? (item.container_status || "docker") : "listening";

      return `
        <tr class="hover:bg-slate-800/40 transition">
          <td class="px-4 py-2.5 font-bold text-slate-100">${item.port}</td>
          <td class="px-4 py-2.5 uppercase text-slate-400">${item.protocol}</td>
          <td class="px-4 py-2.5">
            ${isDocker 
              ? `<span class="text-sky-300 font-semibold">${item.container || "container"}</span> <span class="text-slate-500 text-[11px] font-sans">(${item.container_status})</span>`
              : `<span class="text-slate-400">Host Network Socket</span>`
            }
          </td>
          <td class="px-4 py-2.5">
            <span class="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] uppercase font-sans font-semibold tracking-wider ${badgeClass}">
              ${statusText}
            </span>
          </td>
          <td class="px-4 py-2.5 text-slate-400">${item.host_ip || "0.0.0.0"}</td>
        </tr>
      `;
    }).join("");
  }

  // Allocate Random Port
  async function allocateRandomPort() {
    const min = parseInt(inputMinPort.value, 10) || 8000;
    const max = parseInt(inputMaxPort.value, 10) || 9999;

    btnRollPort.disabled = true;
    btnRollPort.innerHTML = `<span>⏳ Scanning...</span>`;
    displayAllocatedPort.textContent = "....";

    try {
      const url = api(`/api/v1/ports/random?min=${min}&max=${max}&protocol=${currentProtocol}`);
      const res = await fetch(url);
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "No ports available");
      }
      const data = await res.json();
      lastAllocatedPort = data.port;

      displayAllocatedPort.textContent = data.port;
      portDetails.innerHTML = `
        <span class="text-emerald-400 font-medium">Verified Free (${data.protocol.toUpperCase()})</span><br>
        Range: ${data.range[0]} - ${data.range[1]}
      `;
      btnCopyPort.disabled = false;
    } catch (err) {
      displayAllocatedPort.textContent = "ERR";
      portDetails.innerHTML = `<span class="text-rose-400 font-medium">${err.message}</span>`;
      btnCopyPort.disabled = true;
    } finally {
      btnRollPort.disabled = false;
      btnRollPort.innerHTML = `<span>🎲 Generate Port</span>`;
    }
  }

  // Copy Allocated Port
  btnCopyPort.addEventListener("click", () => {
    if (!lastAllocatedPort) return;
    navigator.clipboard.writeText(lastAllocatedPort.toString()).then(() => {
      const orig = btnCopyPort.innerHTML;
      btnCopyPort.innerHTML = `<span>✅ Copied!</span>`;
      setTimeout(() => {
        btnCopyPort.innerHTML = orig;
      }, 1500);
    });
  });

  // Check Specific Port
  async function checkPort() {
    const port = parseInt(inputCheckPort.value, 10);
    if (!port || port < 1 || port > 65535) {
      alert("Please enter a valid port (1-65535)");
      return;
    }

    btnCheckPort.disabled = true;
    checkResultContainer.classList.remove("hidden");
    checkResultTitle.textContent = "Checking...";
    checkResultDesc.textContent = "Probing system socket and container map...";

    try {
      const url = api(`/api/v1/ports/check/${port}?protocol=${currentProtocol}`);
      const res = await fetch(url);
      const data = await res.json();

      if (data.free) {
        checkResultContainer.className = "p-3.5 rounded-xl border bg-emerald-950/40 border-emerald-800/80 text-xs text-emerald-300";
        checkResultTitle.innerHTML = `<span>Port ${port} is Available</span> <span class="text-emerald-400">✓</span>`;
        checkResultDesc.textContent = `No active host socket or Docker reservation detected for ${currentProtocol.toUpperCase()}.`;
      } else {
        checkResultContainer.className = "p-3.5 rounded-xl border bg-rose-950/40 border-rose-800/80 text-xs text-rose-300";
        checkResultTitle.innerHTML = `<span>Port ${port} is IN USE</span> <span class="text-rose-400">✗</span>`;
        const sourcesText = data.sources && data.sources.length ? data.sources.join(", ") : "Bound by OS kernel";
        checkResultDesc.textContent = `Occupied by: ${sourcesText}`;
      }
    } catch (err) {
      checkResultContainer.className = "p-3.5 rounded-xl border bg-amber-950/40 border-amber-800/80 text-xs text-amber-300";
      checkResultTitle.textContent = "Check Failed";
      checkResultDesc.textContent = err.message;
    } finally {
      btnCheckPort.disabled = false;
    }
  }

  // Event Listeners
  btnRollPort.addEventListener("click", allocateRandomPort);
  btnCheckPort.addEventListener("click", checkPort);
  inputCheckPort.addEventListener("keydown", (e) => {
    if (e.key === "Enter") checkPort();
  });

  btnRefresh.addEventListener("click", () => {
    checkHealth();
    fetchPorts();
  });

  searchPorts.addEventListener("input", renderPortsTable);
  filterType.addEventListener("change", renderPortsTable);

  // Initial load
  checkHealth();
  fetchPorts();
})();
