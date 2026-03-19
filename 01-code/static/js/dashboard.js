const precheckBtn = document.getElementById("precheck-btn");
const checkBtn = document.getElementById("check-btn");
const locationInput = document.getElementById("location-input");
const inputAlert = document.getElementById("input-alert");
const precheckPill = document.getElementById("precheck-pill");
const langToggle = document.getElementById("lang-toggle");
const evacStatus = document.getElementById("evac-status");
const evacList = document.getElementById("evac-list");

const reportFields = {
  location: document.getElementById("report-location"),
  lat: document.getElementById("report-lat"),
  lon: document.getElementById("report-lon"),
  rain: document.getElementById("report-rain"),
  elev: document.getElementById("report-elev"),
  score: document.getElementById("report-score"),
  level: document.getElementById("report-level"),
  time: document.getElementById("report-time"),
  progress: document.getElementById("risk-progress"),
};

const currentLocation = document.getElementById("current-location");
let currentMap;
let currentMarker;
let resultMap;
let resultMarker;
let evacMap;
let evacRouteLine;
let evacMarkers = [];
let lastEvacData = null;

let currentLang = "en";

const i18n = {
  en: {
    greeting: "Hello {name}",
    intro: "Check Chennai locations for flood risk and view your current position.",
    pill_idle: "No risk signals yet",
    lang_toggle: "தமிழ்",
    current_title: "Your current location",
    current_desc: "Location is pulled from your browser and mapped below.",
    current_wait: "Waiting for location...",
    check_title: "Check flood detect",
    check_desc: "Type a Chennai location. If community risk exists, we warn you early.",
    location_label: "Location in Chennai",
    location_placeholder: "e.g. T Nagar, Velachery",
    precheck_btn: "Precheck risk",
    check_btn: "Run flood check",
    report_title: "Flood report",
    report_location: "Location:",
    report_lat: "Latitude:",
    report_lon: "Longitude:",
    report_rain: "Rainfall:",
    report_elev: "Elevation:",
    report_score: "Risk score:",
    report_level: "Risk level:",
    report_time: "Predicted time:",
    risk_meter: "Risk score",
    weather_icons: "Weather signal",
    map_title: "Location map",
    evac_title: "Smart evacuation route",
    evac_desc: "Automatic routing to the safest nearby infrastructure.",
    evac_list_title: "Nearest safe destinations",
    evac_idle: "Run a flood check to generate a safe route.",
    evac_loading: "Computing safest route...",
    evac_failed: "Unable to compute a safe route right now.",
    evac_no_route: "No safe route found. Try again shortly.",
    evac_route_to: "Route to {name}",
    evac_distance: "{distance} km",
    help_title: "Futuristic helpline",
    help_intro: "Tap to call Chennai emergency services.",
    help_pill: "Warning Red",
    help_flood_title: "Flood / Rain Emergency",
    help_general_title: "General Emergency",
    help_city_title: "Chennai Control Room",
    help_1913: "Chennai Corporation (waterlogging, flooding complaints)",
    help_1070: "Tamil Nadu State Disaster Helpline",
    help_1077: "District Disaster Control Room",
    help_wa: "Flood helpline WhatsApp (TN)",
    help_112: "National Emergency Number (all services)",
    help_100: "Police",
    help_101: "Fire",
    help_108: "Ambulance",
    help_city: "Chennai Control Room",
    guide_title: "Disaster preparedness guide",
    guide_intro: "Clear, local steps to stay safe before, during, and after flooding.",
    guide_pill: "Community safety checklist",
    guide_before_title: "Before flood",
    guide_before_sub: "Prepare early to avoid last-minute risk.",
    guide_before_item1: "Store drinking water for at least 3 days.",
    guide_before_item2: "Prepare an emergency kit with torch, radio, and batteries.",
    guide_before_item3: "Move valuables and documents to higher levels.",
    guide_before_item4: "Charge phones and keep power banks ready.",
    guide_before_item5: "Save local helpline numbers and family contacts.",
    guide_during_title: "During flood",
    guide_during_sub: "Prioritize safety and follow official guidance.",
    guide_during_item1: "Avoid walking or driving through moving water.",
    guide_during_item2: "Turn off electricity and gas if water enters the home.",
    guide_during_item3: "Move to higher ground or upper floors.",
    guide_during_item4: "Follow evacuation instructions from authorities.",
    guide_during_item5: "Keep a radio or phone updates for alerts.",
    guide_after_title: "After flood",
    guide_after_sub: "Recover carefully and reduce health risks.",
    guide_after_item1: "Avoid contaminated water and disinfect surfaces.",
    guide_after_item2: "Check structural damage before re-entering rooms.",
    guide_after_item3: "Document damage with photos for claims.",
    guide_after_item4: "Dry and ventilate to prevent mold growth.",
    guide_after_item5: "Boil water until local supply is declared safe.",
    risk_high: "High",
    risk_moderate: "Moderate",
    risk_low: "Low",
    alert_enter_location: "Please type a Chennai location.",
    alert_no_location: "Location not supported by browser.",
    alert_no_gps: "Unable to get your location.",
    alert_network_check: "Network error while checking.",
    alert_network_history: "Network error while loading history.",
    alert_check_failed: "Unable to run check.",
    alert_precheck_high: "Community alert: Flood risk predicted around {time}.",
    alert_precheck_low: "No high-risk reports found yet.",
    alert_auto_call: "⚠ Call 1913 immediately",
    unknown_location: "Unknown location",
    pill_high: "High risk already reported near {location}",
    pill_low: "No community flood alerts yet",
    pill_result: "{level} risk predicted",
    checking: "Checking...",
    check_btn_idle: "Run flood check",
  },
  ta: {
    greeting: "வணக்கம் {name}",
    intro: "சென்னையின் வெள்ள அபாயத்தை பரிசோதித்து, உங்கள் இருப்பிடத்தைப் பார்க்கலாம்.",
    pill_idle: "இன்னும் அபாய அறிகுறிகள் இல்லை",
    lang_toggle: "English",
    current_title: "உங்கள் தற்போதைய இடம்",
    current_desc: "உங்கள் உலாவி மூலம் இடம் பெறப்பட்டு கீழே காட்டப்படும்.",
    current_wait: "இடம் பெறப்படுகிறது...",
    check_title: "வெள்ள அபாயம் சரிபார்க்கவும்",
    check_desc: "சென்னையில் உள்ள இடத்தை உள்ளிடுங்கள். சமூக அபாயம் இருந்தால் முன்கூட்டியே தெரிவிக்கப்படும்.",
    location_label: "சென்னையில் உள்ள இடம்",
    location_placeholder: "உதா: டி நகரு, வேளச்சேரி",
    precheck_btn: "முன்சரிபார்ப்பு",
    check_btn: "வெள்ள சரிபார்ப்பு",
    report_title: "வெள்ள அறிக்கை",
    report_location: "இடம்:",
    report_lat: "அகலம்:",
    report_lon: "நீளம்:",
    report_rain: "மழை அளவு:",
    report_elev: "உயரம்:",
    report_score: "அபாய மதிப்பெண்:",
    report_level: "அபாய நிலை:",
    report_time: "முன்னறிவு நேரம்:",
    risk_meter: "அபாய மதிப்பெண்",
    weather_icons: "வானிலை குறிப்பு",
    map_title: "இட வரைபடம்",
    evac_title: "பாதுகாப்பான வெளியேற்ற பாதை",
    evac_desc: "அருகிலுள்ள பாதுகாப்பான முக்கிய இடத்துக்கு தானியங்கி வழி.",
    evac_list_title: "அருகிலுள்ள பாதுகாப்பான இடங்கள்",
    evac_idle: "பாதுகாப்பான பாதைக்கு முதலில் வெள்ள சரிபார்ப்பு இயக்கவும்.",
    evac_loading: "பாதுகாப்பான பாதை கணக்கிடப்படுகிறது...",
    evac_failed: "பாதுகாப்பான பாதையை தற்போது கணக்கிட முடியவில்லை.",
    evac_no_route: "பாதுகாப்பான பாதை கிடைக்கவில்லை. மீண்டும் முயற்சிக்கவும்.",
    evac_route_to: "{name} நோக்கி பாதை",
    evac_distance: "{distance} கிமீ",
    help_title: "அவசர உதவி எண்கள்",
    help_intro: "சென்னை அவசர சேவைகளை அழைக்க தட்டவும்.",
    help_pill: "எச்சரிக்கை சிவப்பு",
    help_flood_title: "வெள்ளம் / மழை அவசரம்",
    help_general_title: "பொது அவசரம்",
    help_city_title: "சென்னை கட்டுப்பாட்டு அறை",
    help_1913: "சென்னை மாநகராட்சி (நீர் தேக்கம், வெள்ள புகார்)",
    help_1070: "தமிழ்நாடு பேரிடர் உதவி எண்",
    help_1077: "மாவட்ட பேரிடர் கட்டுப்பாட்டு அறை",
    help_wa: "வெள்ள உதவி வாட்ஸ்அப் (TN)",
    help_112: "தேசிய அவசர எண் (அனைத்து சேவைகள்)",
    help_100: "காவல்துறை",
    help_101: "தீயணைப்பு",
    help_108: "ஆம்புலன்ஸ்",
    help_city: "சென்னை கட்டுப்பாட்டு அறை",
    guide_title: "பேரிடர் தயார்நிலை வழிகாட்டி",
    guide_intro: "வெள்ளத்திற்கு முன், போது, பிறகு பாதுகாப்பாக இருக்க தெளிவான வழிகாட்டுதல்.",
    guide_pill: "சமூக பாதுகாப்பு சரிபார்ப்பு பட்டியல்",
    guide_before_title: "வெள்ளத்திற்கு முன்",
    guide_before_sub: "கடைசி நேர அபாயத்தை தவிர்க்க முன்கூட்டியே தயார் செய்யுங்கள்.",
    guide_before_item1: "குறைந்தது 3 நாட்களுக்கு குடிநீரை சேமிக்கவும்.",
    guide_before_item2: "டார்ச், ரேடியோ, பேட்டரி உடன் அவசர பெட்டி தயாரிக்கவும்.",
    guide_before_item3: "மதிப்புள்ள பொருட்கள், ஆவணங்களை மேல்ப் பகுதியில் வைக்கவும்.",
    guide_before_item4: "தொலைபேசிகளை சார்ஜ் செய்து பவர் பேங்க் தயாராக வைத்துக் கொள்ளவும்.",
    guide_before_item5: "உள்ளூர் உதவி எண்கள், குடும்ப தொடர்புகளை சேமிக்கவும்.",
    guide_during_title: "வெள்ளத்தின் போது",
    guide_during_sub: "பாதுகாப்பை முன்னிலைப்படுத்தி அதிகாரிகளின் அறிவுறுத்தலை பின்பற்றுங்கள்.",
    guide_during_item1: "இயங்கும் நீரில் நடக்கவும் அல்லது வாகனம் ஓட்டவும் வேண்டாம்.",
    guide_during_item2: "வீட்டில் நீர் நுழைந்தால் மின்சாரம், எரிவாயுவை நிறுத்தவும்.",
    guide_during_item3: "மேல்மாடி அல்லது உயர்ந்த இடத்திற்கு செல்லவும்.",
    guide_during_item4: "அதிகாரிகளின் இடம்பெயர்வு அறிவுறுத்தலை பின்பற்றவும்.",
    guide_during_item5: "அறிவிப்புகளுக்காக ரேடியோ அல்லது தொலைபேசி செய்திகளை பின்தொடரவும்.",
    guide_after_title: "வெள்ளத்திற்கு பிறகு",
    guide_after_sub: "மெதுவாக மீண்டு, உடல்நல அபாயங்களை குறைக்கவும்.",
    guide_after_item1: "மாசடைந்த நீரை தவிர்த்து மேற்பரப்புகளை சுத்திகரிக்கவும்.",
    guide_after_item2: "அறைகளில் செல்லும் முன் கட்டமைப்பு சேதத்தை சரிபார்க்கவும்.",
    guide_after_item3: "காப்பீடு கோரிக்கைக்காக சேதத்தை படங்களில் பதிவு செய்யவும்.",
    guide_after_item4: "பூஞ்சை வளர்ச்சியை தடுக்கும் வகையில் காற்றோட்டம் செய்யவும்.",
    guide_after_item5: "உள்ளூர் நீர் பாதுகாப்பானது என அறிவிக்கப்படும் வரை நீரை கொதிக்க விடவும்.",
    risk_high: "உயர்",
    risk_moderate: "மிதமான",
    risk_low: "குறைவு",
    alert_enter_location: "சென்னையில் உள்ள இடத்தை உள்ளிடவும்.",
    alert_no_location: "உலாவி இடம் ஆதரிக்கவில்லை.",
    alert_no_gps: "உங்கள் இடத்தை பெற முடியவில்லை.",
    alert_network_check: "சரிபார்ப்பு போது நெட்வொர்க் பிழை.",
    alert_network_history: "வரலாறு ஏற்றும் போது நெட்வொர்க் பிழை.",
    alert_check_failed: "சரிபார்ப்பு இயங்கவில்லை.",
    alert_precheck_high: "சமூக எச்சரிக்கை: {time} நேரத்தில் வெள்ள அபாயம்.",
    alert_precheck_low: "உயர் அபாய அறிக்கைகள் இல்லை.",
    alert_auto_call: "⚠ உடனடியாக 1913-க்கு அழைக்கவும்",
    unknown_location: "அறியப்படாத இடம்",
    pill_high: "{location} அருகே உயர்ந்த அபாயம் அறிவிக்கப்பட்டுள்ளது",
    pill_low: "சமூக வெள்ள எச்சரிக்கைகள் இல்லை",
    pill_result: "{level} அபாயம் கணிக்கப்பட்டது",
    checking: "சரிபார்க்கிறது...",
    check_btn_idle: "வெள்ள சரிபார்ப்பு",
  },
};

function t(key, vars = {}) {
  const table = i18n[currentLang] || i18n.en;
  let text = table[key] || key;
  Object.entries(vars).forEach(([name, value]) => {
    text = text.replace(new RegExp(`\\{${name}\\}`, "g"), value);
  });
  return text;
}

function applyLanguage(lang) {
  currentLang = lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (el.id === "current-location") {
      const known = [
        i18n.en.current_wait,
        i18n.ta.current_wait,
        i18n.en.alert_no_location,
        i18n.ta.alert_no_location,
        i18n.en.alert_no_gps,
        i18n.ta.alert_no_gps,
      ];
      if (!known.includes(el.textContent)) {
        return;
      }
    }
    if (el.id === "precheck-pill") {
      const known = [i18n.en.pill_idle, i18n.ta.pill_idle];
      if (!known.includes(el.textContent)) {
        return;
      }
    }
    if (key === "greeting") {
      const name = el.getAttribute("data-name") || "";
      el.textContent = t(key, { name });
      return;
    }
    el.textContent = t(key);
  });

  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.getAttribute("data-i18n-placeholder");
    el.setAttribute("placeholder", t(key));
  });
}

function formatRiskLevel(level) {
  if (level === "High") return t("risk_high");
  if (level === "Moderate") return t("risk_moderate");
  return t("risk_low");
}

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
  precheckPill.style.background = "#f5f1e8";
}

function initMaps() {
  currentMap = L.map("current-map", { zoomControl: false }).setView([13.0827, 80.2707], 11);
  resultMap = L.map("result-map").setView([13.0827, 80.2707], 12);
  evacMap = L.map("evac-map").setView([13.0827, 80.2707], 12);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
  }).addTo(currentMap);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
  }).addTo(resultMap);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
  }).addTo(evacMap);
}

function clearEvacRoute() {
  if (evacRouteLine) {
    evacMap.removeLayer(evacRouteLine);
    evacRouteLine = null;
  }
  evacMarkers.forEach((marker) => evacMap.removeLayer(marker));
  evacMarkers = [];
  evacList.innerHTML = "";
}

function renderEvacRoute(data) {
  if (!evacStatus || !evacList) {
    return;
  }
  clearEvacRoute();
  if (!data || !data.route || !data.route.coords || !data.route.coords.length) {
    evacStatus.textContent = t("evac_no_route");
    return;
  }

  const routeCoords = data.route.coords.map((pt) => [pt[0], pt[1]]);
  evacRouteLine = L.polyline(routeCoords, {
    color: "#5bd2e4",
    weight: 4,
    opacity: 0.9,
  }).addTo(evacMap);

  const start = routeCoords[0];
  const end = routeCoords[routeCoords.length - 1];
  evacMarkers.push(L.circleMarker(start, {
    radius: 6,
    color: "#5bd2e4",
    fillColor: "#5bd2e4",
    fillOpacity: 0.9,
  }).addTo(evacMap));
  evacMarkers.push(L.circleMarker(end, {
    radius: 6,
    color: "#f6c67c",
    fillColor: "#f6c67c",
    fillOpacity: 0.9,
  }).addTo(evacMap));

  evacMap.fitBounds(evacRouteLine.getBounds(), { padding: [20, 20] });

  evacStatus.textContent = t("evac_route_to", { name: data.route.destination.name });
  const suggestions = data.suggestions || [];
  suggestions.forEach((item) => {
    const row = document.createElement("div");
    row.className = "evac-item";
    row.innerHTML = `
      <div class="evac-meta">
        <span>${item.name}</span>
        <span class="muted">${item.kind}</span>
      </div>
      <span class="evac-distance">${t("evac_distance", { distance: item.distance_km.toFixed(1) })}</span>
    `;
    evacList.appendChild(row);
  });
}

async function loadEvacRoute(lat, lon) {
  if (!evacStatus) {
    return;
  }

  evacStatus.textContent = t("evac_loading");
  try {
    const resp = await fetch(`/api/evac_route?lat=${lat}&lon=${lon}`);
    const data = await resp.json();
    if (!resp.ok) {
      evacStatus.textContent = data.error || t("evac_failed");
      return;
    }
    lastEvacData = data;
    renderEvacRoute(data);
  } catch (err) {
    evacStatus.textContent = t("evac_failed");
  }
}

async function reverseLookup(lat, lon) {
  const resp = await fetch(`/api/reverse?lat=${lat}&lon=${lon}`);
  if (!resp.ok) {
    return t("unknown_location");
  }
  const data = await resp.json();
  return data.location_name || t("unknown_location");
}

async function locateUser() {
  if (!navigator.geolocation) {
    currentLocation.textContent = t("alert_no_location");
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
    currentLocation.textContent = t("alert_no_gps");
  });
}

async function precheckRisk() {
  const query = locationInput.value.trim();
  if (!query) {
    showAlert(t("alert_enter_location"));
    return;
  }

  clearAlert();
  const resp = await fetch(`/api/precheck?query=${encodeURIComponent(query)}`);
  const data = await resp.json();
  if (data.risk_level === "High") {
    updatePill("High", t("pill_high", { location: data.location_name }));
    showAlert(t("alert_precheck_high", { time: data.predicted_time }), "warn");
  } else {
    updatePill("Low", t("pill_low"));
    showAlert(t("alert_precheck_low"), "ok");
  }
}

async function runCheck() {
  const query = locationInput.value.trim();
  if (!query) {
    showAlert(t("alert_enter_location"));
    return;
  }

  clearAlert();
  checkBtn.disabled = true;
  checkBtn.textContent = t("checking");

  try {
    const resp = await fetch("/api/flood_check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    const data = await resp.json();
    if (!resp.ok) {
      showAlert(data.error || t("alert_check_failed"));
      return;
    }

    reportFields.location.textContent = data.location_name;
    reportFields.lat.textContent = data.lat.toFixed(4);
    reportFields.lon.textContent = data.lon.toFixed(4);
    reportFields.rain.textContent = `${data.rainfall_mm.toFixed(1)} mm`;
    reportFields.elev.textContent = `${data.elevation_m.toFixed(1)} m`;
    reportFields.score.textContent = data.risk_score.toFixed(1);
    if (reportFields.progress) {
      const capped = Math.min(Math.max(data.risk_score, 0), 100);
      reportFields.progress.style.width = `${capped}%`;
    }
    reportFields.level.textContent = formatRiskLevel(data.risk_level);
    reportFields.time.textContent = data.predicted_time;

    updatePill(data.risk_level, t("pill_result", { level: formatRiskLevel(data.risk_level) }));

    if (data.risk_score >= 70) {
      showAlert(t("alert_auto_call"), "warn");
    }

    if (!resultMarker) {
      resultMarker = L.marker([data.lat, data.lon]).addTo(resultMap);
    } else {
      resultMarker.setLatLng([data.lat, data.lon]);
    }
    resultMap.setView([data.lat, data.lon], 14);
    loadEvacRoute(data.lat, data.lon);
  } catch (err) {
    showAlert(t("alert_network_check"));
  } finally {
    checkBtn.disabled = false;
    checkBtn.textContent = t("check_btn_idle");
  }
}

function toggleLanguage() {
  const next = currentLang === "en" ? "ta" : "en";
  applyLanguage(next);
  if (reportFields.level.textContent !== "--") {
    const rawLevel = reportFields.level.textContent === t("risk_high")
      ? "High"
      : reportFields.level.textContent === t("risk_moderate")
        ? "Moderate"
        : "Low";
    reportFields.level.textContent = formatRiskLevel(rawLevel);
  }
  if (lastEvacData) {
    renderEvacRoute(lastEvacData);
  }
}

initMaps();
locateUser();
applyLanguage("en");

precheckBtn.addEventListener("click", precheckRisk);
checkBtn.addEventListener("click", runCheck);
langToggle.addEventListener("click", toggleLanguage);
