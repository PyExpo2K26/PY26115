const precheckBtn = document.getElementById("precheck-btn");
const checkBtn = document.getElementById("check-btn");
const locationInput = document.getElementById("location-input");
const inputAlert = document.getElementById("input-alert");
const precheckPill = document.getElementById("precheck-pill");
const historyBtn = document.getElementById("history-btn");

const reportFields = {
  location: document.getElementById("report-location"),
  lat: document.getElementById("report-lat"),
  lon: document.getElementById("report-lon"),
  rain: document.getElementById("report-rain"),
  elev: document.getElementById("report-elev"),
  score: document.getElementById("report-score"),
  level: document.getElementById("report-level"),
  time: document.getElementById("report-time"),
};

const currentLocation = document.getElementById("current-location");
const historyList = document.getElementById("history-list");
const forecastList = document.getElementById("forecast-list");
const historyMeta = document.getElementById("history-meta");

let currentMap;
let currentMarker;
let resultMap;
let resultMarker;

function showAlert(message, type = "warn") {
  inputAlert.hidden = false;
  inputAlert.textContent = message;
  inputAlert.style.background = type === "warn" ? "#ffe0d6" : "#d8f0e3";
}

function clearAlert() {
  inputAlert.hidden = true;
}

function updatePill(level, text) {
  precheckPill.textContent = text;
  if (level === "High") {
    precheckPill.style.background = "#ffd0c2";
  } else if (level === "Moderate") {
    precheckPill.style.background = "#fff1d6";
  } else {
    precheckPill.style.background = "#d8f0e3";
  }
}

function initMaps() {
  currentMap = L.map("current-map", { zoomControl: false }).setView([13.0827, 80.2707], 11);
  resultMap = L.map("result-map").setView([13.0827, 80.2707], 12);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
  }).addTo(currentMap);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
  }).addTo(resultMap);
}

function renderHistory(items) {
  historyList.innerHTML = "";
  if (!items.length) {
    historyList.innerHTML = "<div class=\"muted\">No history captured yet.</div>";
    return;
  }
  historyMeta.textContent = `${items.length} hourly records loaded`;
  for (const item of items) {
    const row = document.createElement("div");
    row.className = "history-row";
    row.innerHTML = `<span>${item.timestamp_hour}</span><span>${item.rainfall_mm.toFixed(1)} mm</span><span>${item.risk_level}</span>`;
    historyList.appendChild(row);
  }
}

function renderForecast(items, errorMessage) {
  forecastList.innerHTML = "";
  if (errorMessage) {
    forecastList.innerHTML = `<div class=\"muted\">${errorMessage}</div>`;
    return;
  }
  if (!items.length) {
    forecastList.innerHTML = "<div class=\"muted\">Forecast not available.</div>";
    return;
  }
  for (const item of items) {
    const row = document.createElement("div");
    row.className = "history-row";
    row.innerHTML = `<span>${item.date}</span><span>${item.rainfall_mm.toFixed(1)} mm</span><span>${item.risk_level}</span>`;
    forecastList.appendChild(row);
  }
}

async function reverseLookup(lat, lon) {
  const resp = await fetch(`/api/reverse?lat=${lat}&lon=${lon}`);
  if (!resp.ok) {
    return "Unknown location";
  }
  const data = await resp.json();
  return data.location_name || "Unknown location";
}

async function locateUser() {
  if (!navigator.geolocation) {
    currentLocation.textContent = "Location not supported by browser.";
    return;
  }

  navigator.geolocation.getCurrentPosition(async (position) => {
    const { latitude, longitude } = position.coords;
    const name = await reverseLookup(latitude, longitude);
    currentLocation.textContent = name;

    if (!currentMarker) {
      currentMarker = L.marker([latitude, longitude]).addTo(currentMap);
    } else {
      currentMarker.setLatLng([latitude, longitude]);
    }
    currentMap.setView([latitude, longitude], 14);
  }, () => {
    currentLocation.textContent = "Unable to get your location.";
  });
}

async function precheckRisk() {
  const query = locationInput.value.trim();
  if (!query) {
    showAlert("Please type a Chennai location.");
    return;
  }

  clearAlert();
  const resp = await fetch(`/api/precheck?query=${encodeURIComponent(query)}`);
  const data = await resp.json();
  if (data.risk_level === "High") {
    updatePill("High", `High risk already reported near ${data.location_name}`);
    showAlert(`Community alert: Flood risk predicted around ${data.predicted_time}.`, "warn");
  } else {
    updatePill("Low", "No community flood alerts yet");
    showAlert("No high-risk reports found yet.", "ok");
  }
}

async function runCheck() {
  const query = locationInput.value.trim();
  if (!query) {
    showAlert("Please type a Chennai location.");
    return;
  }

  clearAlert();
  checkBtn.disabled = true;
  checkBtn.textContent = "Checking...";

  try {
    const resp = await fetch("/api/flood_check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    const data = await resp.json();
    if (!resp.ok) {
      showAlert(data.error || "Unable to run check.");
      return;
    }

    reportFields.location.textContent = data.location_name;
    reportFields.lat.textContent = data.lat.toFixed(4);
    reportFields.lon.textContent = data.lon.toFixed(4);
    reportFields.rain.textContent = `${data.rainfall_mm.toFixed(1)} mm`;
    reportFields.elev.textContent = `${data.elevation_m.toFixed(1)} m`;
    reportFields.score.textContent = data.risk_score.toFixed(1);
    reportFields.level.textContent = data.risk_level;
    reportFields.time.textContent = data.predicted_time;

    updatePill(data.risk_level, `${data.risk_level} risk predicted`);

    if (!resultMarker) {
      resultMarker = L.marker([data.lat, data.lon]).addTo(resultMap);
    } else {
      resultMarker.setLatLng([data.lat, data.lon]);
    }
    resultMap.setView([data.lat, data.lon], 14);
  } catch (err) {
    showAlert("Network error while checking.");
  } finally {
    checkBtn.disabled = false;
    checkBtn.textContent = "Run flood check";
  }
}

async function loadHistory() {
  const query = locationInput.value.trim();
  if (!query) {
    showAlert("Please type a Chennai location.");
    return;
  }

  clearAlert();
  historyBtn.disabled = true;
  historyBtn.textContent = "Loading...";

  try {
    const resp = await fetch(`/api/history?query=${encodeURIComponent(query)}`);
    const data = await resp.json();
    if (!resp.ok) {
      showAlert(data.error || "Unable to load history.");
      return;
    }

    historyMeta.textContent = `History for ${data.location_name}`;
    renderHistory(data.history || []);
    renderForecast(data.forecast || [], data.forecast_error);
  } catch (err) {
    showAlert("Network error while loading history.");
  } finally {
    historyBtn.disabled = false;
    historyBtn.textContent = "History + 7-day outlook";
  }
}

initMaps();
locateUser();

precheckBtn.addEventListener("click", precheckRisk);
checkBtn.addEventListener("click", runCheck);
historyBtn.addEventListener("click", loadHistory);
