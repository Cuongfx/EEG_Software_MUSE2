"use strict";

const state = {
  config: null,
  status: null,
  devices: [],
  charts: [],
  localLogs: [],
  game: null,
};

const channelColors = ["#e11d48", "#2563eb", "#b45309", "#059669", "#7c3aed"];

function $(id) {
  return document.getElementById(id);
}

function nowTime() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function appendLocalLog(message) {
  state.localLogs.push(`[${nowTime()}] ${message}`);
  if (state.localLogs.length > 80) {
    state.localLogs.shift();
  }
  renderLogs();
}

async function api(path, options = {}) {
  const init = {
    method: options.method || "GET",
    headers: {},
  };
  if (options.body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(options.body);
  }
  const response = await fetch(path, init);
  let payload = {};
  try {
    payload = await response.json();
  } catch (_error) {
    payload = {};
  }
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || response.statusText || "Request failed");
  }
  return payload;
}

function setBusy(message) {
  $("busyLabel").textContent = message;
}

function setFormStatus(message, isError = true) {
  const target = $("formStatus");
  target.textContent = message || "";
  target.style.color = isError ? "var(--red)" : "var(--green)";
}

function setupTabs() {
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab-button").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      $(`${button.dataset.tab}Tab`).classList.add("active");
    });
  });
}

function populateLanguages() {
  const languageLabels = state.config.languageLabels || { en: "English" };
  const softwareLanguage = $("softwareLanguage");
  const gameLanguage = $("gameLanguage");
  softwareLanguage.innerHTML = "";
  gameLanguage.innerHTML = "";

  Object.entries(languageLabels).forEach(([code, label]) => {
    softwareLanguage.add(new Option(label, code));
  });

  const game = state.config.games[0];
  (game?.supported_languages || ["en"]).forEach((code) => {
    gameLanguage.add(new Option(languageLabels[code] || code, code));
  });
}

function buildPlots() {
  const grid = $("plotGrid");
  grid.innerHTML = "";
  state.charts = [];
  const eegRange = state.config.plotRanges.eeg;
  const ppgRange = state.config.plotRanges.ppg;

  state.config.channels.forEach((channel, index) => {
    const chart = createPlotCard(channel.name, channelColors[index % channelColors.length], eegRange, "eeg", index);
    grid.appendChild(chart.card);
    state.charts.push(chart);
  });

  const ppgChart = createPlotCard("PPG", channelColors[4], ppgRange, "ppg", 0);
  grid.appendChild(ppgChart.card);
  state.charts.push(ppgChart);
}

function createPlotCard(title, color, range, type, index) {
  const card = document.createElement("article");
  card.className = "plot-card";
  const heading = document.createElement("h3");
  heading.textContent = title;
  const canvas = document.createElement("canvas");
  canvas.width = 720;
  canvas.height = 336;
  card.append(heading, canvas);
  return { card, canvas, title, color, range, type, index };
}

function drawChart(chart, values) {
  const canvas = chart.canvas;
  const rect = canvas.getBoundingClientRect();
  const ratio = window.devicePixelRatio || 1;
  const width = Math.max(320, Math.floor(rect.width * ratio));
  const height = Math.max(168, Math.floor(rect.height * ratio));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }

  const context = canvas.getContext("2d");
  context.clearRect(0, 0, width, height);
  context.fillStyle = "#fbfdff";
  context.fillRect(0, 0, width, height);

  const padding = { left: 44 * ratio, right: 12 * ratio, top: 16 * ratio, bottom: 28 * ratio };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const [minY, maxY] = chart.range;

  context.strokeStyle = "#e4e7ec";
  context.lineWidth = 1 * ratio;
  context.beginPath();
  for (let line = 0; line <= 4; line += 1) {
    const y = padding.top + (plotHeight * line) / 4;
    context.moveTo(padding.left, y);
    context.lineTo(width - padding.right, y);
  }
  for (let line = 0; line <= 5; line += 1) {
    const x = padding.left + (plotWidth * line) / 5;
    context.moveTo(x, padding.top);
    context.lineTo(x, height - padding.bottom);
  }
  context.stroke();

  context.strokeStyle = "#cbd5e1";
  context.strokeRect(padding.left, padding.top, plotWidth, plotHeight);

  context.fillStyle = "#667085";
  context.font = `${11 * ratio}px system-ui, sans-serif`;
  context.fillText(String(maxY), 6 * ratio, padding.top + 4 * ratio);
  context.fillText(String(minY), 6 * ratio, height - padding.bottom);

  if (!values || values.length < 2) {
    context.fillStyle = "#98a2b3";
    context.font = `${13 * ratio}px system-ui, sans-serif`;
    context.fillText("Waiting for samples", padding.left + 12 * ratio, padding.top + 26 * ratio);
    return;
  }

  const usable = values.filter((value) => Number.isFinite(value));
  if (usable.length < 2) {
    return;
  }

  context.strokeStyle = chart.color;
  context.lineWidth = 2 * ratio;
  context.beginPath();
  const count = values.length;
  let started = false;
  values.forEach((value, pointIndex) => {
    if (!Number.isFinite(value)) {
      return;
    }
    const normalized = (value - minY) / Math.max(maxY - minY, 1);
    const x = padding.left + (plotWidth * pointIndex) / Math.max(count - 1, 1);
    const y = padding.top + plotHeight - Math.min(Math.max(normalized, 0), 1) * plotHeight;
    if (!started) {
      context.moveTo(x, y);
      started = true;
    } else {
      context.lineTo(x, y);
    }
  });
  context.stroke();
}

function applyDefaults(defaults) {
  const fallback = {
    participant_name: "",
    participant_id: "",
    device_id: "",
    age: "",
    n_value: "2",
    note: "",
    relax_audio_enabled: true,
    relax_music_track: "rain_sound",
    announcement_volume: 70,
    stage_relax_order: "1",
    stage_relax_duration: "1.0",
    stage_break_order: "2",
    stage_break_duration: "1.0",
    stage_game_order: "3",
    stage_game_duration: "1.0",
  };
  const data = { ...fallback, ...defaults };
  $("participantName").value = data.participant_name || data.name || "";
  $("participantId").value = data.participant_id || "";
  $("deviceId").value = data.device_id || "";
  $("participantAge").value = data.age || "";
  $("nValue").value = data.n_value || "2";
  $("participantNote").value = data.note || "";
  $("relaxAudioEnabled").checked = Boolean(data.relax_audio_enabled);
  $("relaxMusicTrack").value = data.relax_music_track || "rain_sound";
  $("announcementVolume").value = Number(data.announcement_volume ?? 70);
  $("stageRelaxOrder").value = data.stage_relax_order || "1";
  $("stageRelaxDuration").value = data.stage_relax_duration || "1.0";
  $("stageBreakOrder").value = data.stage_break_order || "2";
  $("stageBreakDuration").value = data.stage_break_duration || "1.0";
  $("stageGameOrder").value = data.stage_game_order || "3";
  $("stageGameDuration").value = data.stage_game_duration || "1.0";
}

function formDefaultsPayload() {
  return {
    participant_name: $("participantName").value.trim(),
    participant_id: $("participantId").value.trim(),
    device_id: $("deviceId").value.trim(),
    age: $("participantAge").value.trim(),
    n_value: $("nValue").value.trim(),
    note: $("participantNote").value.trim(),
    relax_audio_enabled: $("relaxAudioEnabled").checked,
    relax_music_track: $("relaxMusicTrack").value,
    announcement_volume: Number($("announcementVolume").value || 70),
    stage_relax_order: $("stageRelaxOrder").value.trim(),
    stage_relax_duration: $("stageRelaxDuration").value.trim(),
    stage_break_order: $("stageBreakOrder").value.trim(),
    stage_break_duration: $("stageBreakDuration").value.trim(),
    stage_game_order: $("stageGameOrder").value.trim(),
    stage_game_duration: $("stageGameDuration").value.trim(),
  };
}

function collectExaminerSetup(options = {}) {
  const strict = options.strict !== false;
  const errors = [];
  const required = (value, message) => {
    if (!String(value).trim()) {
      errors.push(message);
    }
  };

  const participantName = $("participantName").value.trim();
  const participantId = $("participantId").value.trim();
  const deviceId = $("deviceId").value.trim();
  const age = $("participantAge").value.trim();
  const nValue = Number.parseInt($("nValue").value, 10);

  if (strict) {
    required(participantName, "Name is required.");
    required(participantId, "ID is required.");
    required(deviceId, "DeviceID is required.");
    required(age, "Age is required.");
    if (participantId && !/^\d+$/.test(participantId)) {
      errors.push("ID must contain numbers only.");
    }
  }
  if (!Number.isInteger(nValue) || nValue < 1) {
    errors.push("N value must be a whole number greater than zero.");
  }

  const stageRows = [
    ["relax", $("stageRelaxOrder").value, $("stageRelaxDuration").value],
    ["break", $("stageBreakOrder").value, $("stageBreakDuration").value],
    ["game", $("stageGameOrder").value, $("stageGameDuration").value],
  ];
  const sessionStages = [];
  const orders = [];
  stageRows.forEach(([kind, orderRaw, durationRaw]) => {
    const order = Number.parseInt(orderRaw, 10);
    const duration = Number.parseFloat(durationRaw);
    if (!Number.isInteger(order) || order < 1 || order > 3) {
      errors.push(`${stageName(kind)} order must be 1, 2, or 3.`);
    }
    if (!Number.isFinite(duration) || duration < 0) {
      errors.push(`${stageName(kind)} duration must be zero or greater.`);
    }
    orders.push(order);
    sessionStages.push({ kind, order, duration_minutes: Number.isFinite(duration) ? duration : 0 });
  });

  if (strict && orders.slice().sort().join(",") !== "1,2,3") {
    errors.push("Relax, Break, and Game must use orders 1, 2, and 3 exactly once.");
  }
  const gameStage = sessionStages.find((stage) => stage.kind === "game");
  if (gameStage && gameStage.duration_minutes <= 0) {
    errors.push("Game duration must be greater than zero.");
  }

  if (errors.length > 0) {
    return { error: errors[0] };
  }

  return {
    participant_name: participantName || "unknown",
    participant_id: participantId || "unknown",
    device_id: deviceId || "unknown_device",
    age: age || "",
    n_value: nValue,
    relax_audio_enabled: $("relaxAudioEnabled").checked,
    relax_music_track: $("relaxMusicTrack").value,
    announcement_volume: Number($("announcementVolume").value || 70) / 100,
    note: $("participantNote").value.trim(),
    session_stages: sessionStages,
  };
}

function stageName(kind) {
  return { relax: "Relax", break: "Break", game: "Game" }[kind] || kind;
}

function sessionLabelFromStages(stages) {
  const mapping = { relax: "A", break: "B", game: "C" };
  return stages
    .slice()
    .sort((a, b) => a.order - b.order)
    .map((stage) => mapping[stage.kind] || "X")
    .join("");
}

function gameLanguage() {
  return $("gameLanguage").value || "en";
}

function gameText(key, params = {}) {
  const language = gameLanguage();
  const bundle = state.config.gameText?.[language] || state.config.gameText?.en || {};
  const fallback = {
    consent_title: "Consent Required",
    consent_prompt: "Please read the study terms and confirm consent before starting the session.",
    consent_agree: "I agree to participate in this EEG study.",
    consent_open_button: "Terms and Conditions",
    start_button: "Start",
    please_relax: "Please relax until you hear the sound",
    please_break: "Please take a break until you hear the sound",
    time_remaining: "Time remaining: {minutes}:{seconds}",
    preparing_next: "Preparing the next session...",
    game_intro_title: "Game Session",
    game_intro_detail: "You are about to begin the Focus Game.",
    how_to_play: "How To Play",
    how_to_play_detail: "This is a {n_value}-back task.\n\nKeep the newest {n_value} letters in memory at all times.\nPress SPACE only when the current letter is the same as the letter {n_value} step(s) earlier.",
    ready_to_start: "Ready To Start",
    ready_to_start_detail: "Stay focused for {duration} minute(s).",
    block_ended: "Congratulations, the block is ended",
    experiment_finished: "The Experiment is finished. Thank you for your attention!\n\nFinal score: {score}",
  };
  const template = bundle[key] || fallback[key] || key;
  return template.replace(/\{([A-Za-z_]+)(?::[^}]+)?\}/g, (_match, name) => {
    if (params[name] === undefined || params[name] === null) {
      return "";
    }
    return String(params[name]);
  });
}

async function scanDevices() {
  setBusy("Scanning");
  $("scanDevicesButton").disabled = true;
  try {
    const payload = await api("/api/devices/scan");
    state.devices = payload.devices || [];
    renderDeviceOptions();
    appendLocalLog(`Scan completed. Found ${state.devices.length} device(s).`);
  } catch (error) {
    appendLocalLog(`Device scan failed: ${error.message}`);
  } finally {
    $("scanDevicesButton").disabled = false;
    setBusy("Ready");
  }
}

function renderDeviceOptions() {
  const select = $("deviceSelect");
  select.innerHTML = "";
  state.devices.forEach((device, index) => {
    select.add(new Option(device.display_name || `${device.name} (${device.address})`, String(index)));
  });
  if (state.devices.length > 0) {
    select.selectedIndex = 0;
  }
}

async function connectSelectedDevice() {
  const index = Number.parseInt($("deviceSelect").value, 10);
  const device = state.devices[index];
  if (!device) {
    appendLocalLog("Select a Muse device first.");
    return;
  }
  setBusy("Connecting");
  $("connectDeviceButton").disabled = true;
  try {
    await api("/api/device/connect", { method: "POST", body: device });
    appendLocalLog(`Connected to ${device.display_name || device.name}.`);
    await refreshStatus();
  } catch (error) {
    appendLocalLog(`Connection failed: ${error.message}`);
  } finally {
    $("connectDeviceButton").disabled = false;
    setBusy("Ready");
  }
}

async function disconnectDevice() {
  setBusy("Disconnecting");
  $("disconnectDeviceButton").disabled = true;
  try {
    await api("/api/device/disconnect", { method: "POST", body: { saveRecording: true } });
    appendLocalLog("Device disconnected.");
    await refreshStatus();
  } catch (error) {
    appendLocalLog(`Disconnect failed: ${error.message}`);
  } finally {
    $("disconnectDeviceButton").disabled = false;
    setBusy("Ready");
  }
}

async function toggleRecording() {
  if (!state.status?.recording) {
    const setup = collectExaminerSetup({ strict: false });
    if (setup.error) {
      appendLocalLog(setup.error);
      return;
    }
    try {
      await api("/api/recording/start", { method: "POST", body: { examinerSetup: setup } });
      appendLocalLog("Recording started.");
    } catch (error) {
      appendLocalLog(`Recording was not started: ${error.message}`);
    }
  } else {
    try {
      const payload = await api("/api/recording/stop", { method: "POST", body: { save: true } });
      const saved = payload.savedFiles?.eegPath || "recording data";
      appendLocalLog(`Recording stopped. Saved ${saved}.`);
    } catch (error) {
      appendLocalLog(`Recording stop failed: ${error.message}`);
    }
  }
  await refreshStatus();
}

async function refreshStatus() {
  const payload = await api("/api/status");
  state.status = payload;
  renderStatus();
}

function renderStatus() {
  const status = state.status;
  $("connectionBadge").textContent = status.running ? "Device Connected" : "Disconnected";
  $("connectionBadge").className = status.running ? "badge" : "badge muted";
  $("recordingBadge").textContent = status.recording ? "Recording" : "Not Recording";
  $("recordingBadge").className = status.recording ? "badge recording" : "badge muted";
  $("metricConnection").textContent = status.running ? "Live" : "Offline";
  $("metricRecording").textContent = status.recording ? "REC" : "Standby";
  $("metricBattery").textContent = status.batteryPercent === null ? "--%" : `${status.batteryPercent}%`;
  $("metricHeartRate").textContent = status.heartRateBpm === null ? "-- bpm" : `${status.heartRateBpm} bpm`;
  $("selectedDevice").textContent = status.currentDevice
    ? `${status.currentDevice.name} (${status.currentDevice.address})`
    : "None";
  $("eegStreamState").textContent = status.eegConnected ? "Connected" : "Waiting";
  $("ppgStreamState").textContent = status.ppgConnected ? "Connected" : "Waiting";
  $("lastSave").textContent = status.lastSaved || "No recording saved yet";
  $("recordButton").textContent = status.recording ? "Stop Recording" : "Record Data";
  $("disconnectDeviceButton").disabled = !status.running && !status.currentDevice;

  state.charts.forEach((chart) => {
    const values = chart.type === "eeg" ? status.series.eeg[chart.index] : status.series.ppg;
    drawChart(chart, values || []);
  });
  renderLogs();
}

function renderLogs() {
  const serverLogs = state.status?.logs || [];
  $("sessionLog").textContent = [...serverLogs, ...state.localLogs].slice(-220).join("\n");
}

function saveDefaultsQuietly() {
  return api("/api/defaults", { method: "POST", body: formDefaultsPayload() }).catch((error) => {
    appendLocalLog(`Could not save form defaults: ${error.message}`);
  });
}

async function startExperimentGame() {
  const setup = collectExaminerSetup({ strict: true });
  if (setup.error) {
    setFormStatus(setup.error);
    return;
  }
  setFormStatus("Session ready.", false);
  await saveDefaultsQuietly();
  openSessionGame(setup);
}

async function startDemoGame() {
  const nValue = Number.parseInt($("nValue").value, 10);
  if (!Number.isInteger(nValue) || nValue < 1) {
    setFormStatus("N value must be a whole number greater than zero.");
    return;
  }
  setFormStatus("");
  await saveDefaultsQuietly();
  openDemoGame(nValue);
}

function openSessionGame(session) {
  state.game = {
    mode: "session",
    session,
    state: "consent",
    timers: [],
    stageIndex: -1,
    trials: [],
    sequence: [],
    currentIndex: -1,
    currentTrial: null,
    currentLetter: null,
    completedTrials: [],
    consentAccepted: false,
    dateExperimentStart: new Date().toLocaleDateString("en-GB"),
    timeExperimentStart: "",
  };
  $("gameTitle").textContent = "Focus Game";
  $("gameContext").textContent = `${session.participant_name} | ${sessionLabelFromStages(session.session_stages)} | ${session.n_value}-back`;
  $("focusGame").classList.remove("hidden");
  $("relaxAudio").src = state.config.media[session.relax_music_track] || state.config.media.binaural_sound;
  showConsentScreen();
}

function openDemoGame(nValue) {
  state.game = {
    mode: "demo",
    session: { n_value: nValue },
    state: "demo_intro",
    timers: [],
    demoSteps: buildDemoSteps(nValue),
    demoStepIndex: 0,
    trials: [],
    sequence: [],
    currentIndex: -1,
    currentTrial: null,
    currentLetter: null,
  };
  $("gameTitle").textContent = "Demo Mode";
  $("gameContext").textContent = `${nValue}-back practice`;
  $("focusGame").classList.remove("hidden");
  showDemoStepIntro();
}

function showConsentScreen() {
  const game = state.game;
  game.state = "consent";
  setGameScreen(gameText("consent_title"), "", []);
  const detail = $("gameDetailText");
  detail.textContent = gameText("consent_prompt");

  const consent = document.createElement("label");
  consent.className = "game-consent";
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.id = "gameConsentCheckbox";
  const text = document.createElement("span");
  text.textContent = gameText("consent_agree");
  consent.append(checkbox, text);
  detail.appendChild(consent);

  addGameAction(gameText("consent_open_button"), showTermsDialog);
  addGameAction(gameText("start_button"), () => {
    if (!checkbox.checked) {
      detail.firstChild.textContent = gameText("consent_prompt");
      return;
    }
    game.consentAccepted = true;
    beginSession();
  }, "primary");
}

function showTermsDialog() {
  const language = $("gameLanguage").value || "en";
  const text = state.config.consentText?.[language] || state.config.consentText?.en || "Consent text is unavailable.";
  $("termsText").textContent = text;
  if (typeof $("termsDialog").showModal === "function") {
    $("termsDialog").showModal();
  }
}

async function beginSession() {
  const game = state.game;
  clearGameTimers();
  game.timeExperimentStart = nowTime();
  game.stageIndex = -1;
  game.completedTrials = [];
  game.trials = [];
  game.sequence = [];

  try {
    await api("/api/recording/start", { method: "POST", body: { examinerSetup: game.session } });
    appendLocalLog("Recording started from Focus Game.");
  } catch (error) {
    appendLocalLog(`Game started without recording: ${error.message}`);
  }
  advanceStage();
}

function advanceStage() {
  const game = state.game;
  clearGameTimers();
  stopRelaxAudio();
  const stages = game.session.session_stages.slice().sort((a, b) => a.order - b.order);
  game.stageIndex += 1;
  if (game.stageIndex >= stages.length) {
    finishSession();
    return;
  }

  const stage = stages[game.stageIndex];
  if (stage.duration_minutes <= 0) {
    advanceStage();
    return;
  }
  if (stage.kind === "game") {
    showGameIntro(stage.duration_minutes);
  } else {
    startGuidedStage(stage);
  }
}

function startGuidedStage(stage) {
  const game = state.game;
  game.state = stage.kind;
  const totalSeconds = Math.max(1, Math.round(stage.duration_minutes * 60));
  if (stage.kind === "relax" && game.session.relax_audio_enabled) {
    startRelaxAudio();
  }
  const title = stage.kind === "relax" ? gameText("please_relax") : gameText("please_break");
  runCountdown(title, totalSeconds);
}

function runCountdown(title, remainingSeconds) {
  const minutes = String(Math.floor(remainingSeconds / 60)).padStart(2, "0");
  const seconds = String(remainingSeconds % 60).padStart(2, "0");
  setGameScreen(title, gameText("time_remaining", { minutes, seconds }), []);
  if (remainingSeconds <= 0) {
    stopRelaxAudio();
    playStageEndSignal();
    setGameScreen(gameText("preparing_next"), "", []);
    scheduleGameTimer(() => advanceStage(), 1000);
    return;
  }
  scheduleGameTimer(() => runCountdown(title, remainingSeconds - 1), 1000);
}

function showGameIntro(durationMinutes) {
  const game = state.game;
  game.state = "game_intro";
  game.currentInstruction = 0;
  game.currentGameDuration = durationMinutes;
  const nValue = game.session.n_value;
  game.introPages = [
    [gameText("game_intro_title"), gameText("game_intro_detail")],
    [
      gameText("how_to_play"),
      gameText("how_to_play_detail", { n_value: nValue }),
    ],
    [gameText("ready_to_start"), gameText("ready_to_start_detail", { duration: Number(durationMinutes).toLocaleString() })],
  ];
  renderGameIntro();
}

function renderGameIntro() {
  const game = state.game;
  const page = game.introPages[game.currentInstruction];
  setGameScreen(page[0], `${page[1]}\n\nPress SPACE or Continue.`, [
    { label: "Continue", className: "primary", onClick: advanceGameIntro },
  ]);
}

function advanceGameIntro() {
  const game = state.game;
  if (game.state !== "game_intro") {
    return;
  }
  game.currentInstruction += 1;
  if (game.currentInstruction >= game.introPages.length) {
    beginActualGame(game.currentGameDuration);
    return;
  }
  renderGameIntro();
}

function beginActualGame(durationMinutes) {
  const game = state.game;
  clearGameTimers();
  game.state = "playing";
  game.trials = [];
  game.currentIndex = -1;
  game.currentTrial = null;
  game.currentLetter = null;
  const trialCount = calculateTrialCount(durationMinutes, state.config.rules.display_time_ms, state.config.rules.intertrial_interval_ms);
  game.sequence = generateSequence(trialCount, game.session.n_value);
  showNextLetter();
}

function calculateTrialCount(durationMinutes, displayTimeMs, intertrialIntervalMs) {
  const durationMs = Math.max(durationMinutes, 0.1) * 60 * 1000;
  return Math.max(1, Math.floor(durationMs / Math.max(displayTimeMs + intertrialIntervalMs, 1)));
}

function generateSequence(numTrials, nValue) {
  const sequence = [];
  const letters = Array.from({ length: 26 }, (_, index) => String.fromCharCode(65 + index));
  const counts = Object.fromEntries(letters.map((letter) => [letter, 0]));
  const maxLetterUsage = 4;
  const desiredMatches = Math.floor((numTrials - nValue) * (state.config.rules.match_probability_percent / 100));
  let totalMatches = 0;

  for (let index = 0; index < numTrials; index += 1) {
    let letter;
    if (index < nValue) {
      const available = letters.filter((candidate) => counts[candidate] < maxLetterUsage);
      letter = randomChoice(available.length ? available : letters);
    } else {
      const remainingSlots = Math.max(numTrials - index, 1);
      const shouldMatch = totalMatches < desiredMatches && Math.random() < (desiredMatches - totalMatches) / remainingSlots;
      if (shouldMatch) {
        letter = sequence[index - nValue];
        totalMatches += 1;
      } else {
        const available = letters.filter(
          (candidate) => counts[candidate] < maxLetterUsage && candidate !== sequence[index - nValue],
        );
        letter = randomChoice(available.length ? available : letters);
      }
    }
    sequence.push(letter);
    counts[letter] += 1;
  }
  return sequence;
}

function randomChoice(items) {
  return items[Math.floor(Math.random() * items.length)];
}

function showNextLetter() {
  const game = state.game;
  if (!game || !["playing", "demo_playing"].includes(game.state)) {
    return;
  }
  if (game.currentIndex + 1 >= game.sequence.length) {
    if (game.state === "playing") {
      completeActualBlock();
    } else {
      completeDemoRound();
    }
    return;
  }
  game.currentIndex += 1;
  game.currentLetter = game.sequence[game.currentIndex];
  game.currentTrial = {
    blockNumber: 1,
    trialNumber: game.currentIndex + 1,
    letter: game.currentLetter,
    matchOrNotMatch: "",
    timestampLetterAppeared: Date.now() / 1000,
    timestampLetterDisappeared: null,
    isKeyPressed: "No",
  };
  game.trials.push(game.currentTrial);
  setGameScreen(game.currentLetter, game.demoPrompt || "", []);
  $("gameMainText").classList.add("letter");
  scheduleGameTimer(hideLetter, activeDisplayTime());
}

function hideLetter() {
  const game = state.game;
  if (!game?.currentTrial) {
    return;
  }
  game.currentTrial.matchOrNotMatch = isCurrentMatch() ? "MATCH" : "NOT_MATCH";
  game.currentTrial.timestampLetterDisappeared = Date.now() / 1000;
  setGameScreen("", game.demoPrompt || "", []);
  $("gameMainText").classList.remove("letter");
  scheduleGameTimer(showNextLetter, activeIntertrialTime());
}

function activeDisplayTime() {
  const game = state.game;
  if (game?.state === "demo_playing") {
    return Math.max(state.config.rules.display_time_ms, 1400);
  }
  return state.config.rules.display_time_ms;
}

function activeIntertrialTime() {
  const game = state.game;
  if (game?.state === "demo_playing") {
    return Math.max(state.config.rules.intertrial_interval_ms, 850);
  }
  return state.config.rules.intertrial_interval_ms;
}

function registerSpacePress() {
  const game = state.game;
  if (!game || !["playing", "demo_playing"].includes(game.state) || !game.currentTrial) {
    return;
  }
  if (game.currentTrial.isKeyPressed === "Yes") {
    return;
  }
  game.currentTrial.isKeyPressed = "Yes";
  if (!$("gameMainText").textContent && game.currentLetter) {
    $("gameMainText").textContent = game.currentLetter;
    $("gameMainText").classList.add("letter");
  }
  flashGame(isCurrentMatch());
}

function isCurrentMatch() {
  const game = state.game;
  if (!game || game.currentIndex < game.session.n_value) {
    return false;
  }
  return game.sequence[game.currentIndex] === game.sequence[game.currentIndex - game.session.n_value];
}

function flashGame(isMatch) {
  const target = $("focusGame");
  target.classList.remove("flash-good", "flash-bad");
  target.classList.add(isMatch ? "flash-good" : "flash-bad");
  scheduleGameTimer(() => target.classList.remove("flash-good", "flash-bad"), 360);
}

function completeActualBlock() {
  const game = state.game;
  clearGameTimers();
  game.completedTrials = game.trials.slice();
  playStageEndSignal();
  setGameScreen(gameText("block_ended"), gameText("preparing_next"), []);
  scheduleGameTimer(() => advanceStage(), 1000);
}

async function finishSession() {
  const game = state.game;
  clearGameTimers();
  stopRelaxAudio();
  game.state = "game_end";
  try {
    await api("/api/recording/stop", { method: "POST", body: { save: true } });
    appendLocalLog("Recording stopped automatically at block end.");
  } catch (error) {
    appendLocalLog(`Recording stop skipped: ${error.message}`);
  }

  const score = calculateScore(game.completedTrials);
  let saveMessage = "";
  try {
    const result = await api("/api/game-results", {
      method: "POST",
      body: {
        session: game.session,
        trials: game.completedTrials,
        score,
        consentAccepted: game.consentAccepted,
        dateExperimentStart: game.dateExperimentStart,
        timeExperimentStart: game.timeExperimentStart,
      },
    });
    saveMessage = `\n\nSaved: ${result.resultPath}`;
    appendLocalLog(`Focus Game result saved. Score ${score.toFixed(2)}.`);
  } catch (error) {
    saveMessage = `\n\nResult save failed: ${error.message}`;
  }
  const finalText = gameText("experiment_finished", { score: score.toFixed(2) });
  const finalParts = finalText.split("\n\n");
  const finalTitle = finalParts.shift() || "The Experiment is finished.";
  const finalDetail = [finalParts.join("\n\n"), saveMessage.trim()].filter(Boolean).join("\n\n");
  setGameScreen(finalTitle, finalDetail, [
    { label: "Close", className: "primary", onClick: closeFocusGame },
  ]);
}

function calculateScore(trials) {
  if (!trials.length) {
    return 0;
  }
  let correct = 0;
  trials.forEach((trial) => {
    if (trial.matchOrNotMatch === "MATCH" && trial.isKeyPressed === "Yes") {
      correct += 1;
    } else if (trial.matchOrNotMatch === "NOT_MATCH" && trial.isKeyPressed === "No") {
      correct += 1;
    }
  });
  return Math.round((correct / trials.length) * 10000) / 100;
}

function buildDemoSteps(nValue) {
  const alphabet = Array.from({ length: 26 }, (_, index) => String.fromCharCode(65 + index));
  const baseLetters = (offset) => Array.from({ length: nValue }, (_, index) => alphabet[(offset + index) % alphabet.length]);
  const roundOne = baseLetters(0);
  const roundTwo = baseLetters(6);
  const roundThree = baseLetters(12);
  const roundFour = baseLetters(18);
  let nonmatchTwo = alphabet[(6 + nValue) % alphabet.length];
  if (nonmatchTwo === roundTwo[0]) {
    nonmatchTwo = alphabet[(7 + nValue) % alphabet.length];
  }
  let nonmatchThree = alphabet[(12 + nValue + 1) % alphabet.length];
  if (nonmatchThree === roundThree[1 % roundThree.length]) {
    nonmatchThree = alphabet[(12 + nValue + 2) % alphabet.length];
  }
  return [
    {
      intro: `Round 1 builds the rule. For the first ${nValue} letters, only remember them. Press SPACE on the final letter because it matches the letter from ${nValue} step(s) earlier.`,
      prompt: "Watch the letters. Press SPACE only on the final letter.",
      summary: `The last letter matched the first letter from ${nValue} step(s) earlier.`,
      sequence: roundOne.concat(roundOne[0]),
    },
    {
      intro: `Round 2 shows a non-match. Do not press SPACE if the final letter is different from the letter ${nValue} step(s) earlier.`,
      prompt: `Do not press SPACE unless the new letter matches ${nValue} step(s) back.`,
      summary: `The last letter did not match the letter ${nValue} step(s) earlier.`,
      sequence: roundTwo.concat(nonmatchTwo),
    },
    {
      intro: "Round 3 mixes one match and one non-match. Press SPACE only when the matching letter appears.",
      prompt: "One new letter is a match. Press SPACE only for that one.",
      summary: "A match needs SPACE, and a non-match needs no response.",
      sequence: roundThree.concat(roundThree[0], nonmatchThree),
    },
    {
      intro: "Round 4 is a short final challenge. Two quick matches appear in a row.",
      prompt: `Press SPACE whenever a letter matches ${nValue} step(s) back.`,
      summary: "This is the same N-back rule you will use in the full game.",
      sequence: roundFour.concat(roundFour[0], roundFour[1 % roundFour.length]),
    },
  ];
}

function showDemoStepIntro() {
  const game = state.game;
  const step = game.demoSteps[game.demoStepIndex];
  game.state = "demo_intro";
  setGameScreen(`Demo Round ${game.demoStepIndex + 1}/${game.demoSteps.length}`, step.intro, [
    { label: "Play Round", className: "primary", onClick: startDemoRound },
  ]);
}

function startDemoRound() {
  const game = state.game;
  const step = game.demoSteps[game.demoStepIndex];
  clearGameTimers();
  game.session.n_value = Number(game.session.n_value);
  game.sequence = step.sequence.slice();
  game.trials = [];
  game.currentIndex = -1;
  game.currentTrial = null;
  game.currentLetter = null;
  game.demoPrompt = step.prompt;
  game.state = "demo_playing";
  showNextLetter();
}

function completeDemoRound() {
  const game = state.game;
  clearGameTimers();
  game.state = "demo_result";
  const step = game.demoSteps[game.demoStepIndex];
  const feedback = demoFeedback(game.trials, game.sequence, game.session.n_value);
  if (game.demoStepIndex >= game.demoSteps.length - 1) {
    setGameScreen("Demo is complete", `${step.summary}\n\n${feedback}\n\nYou can start the demo again or close this window.`, [
      { label: "Start Demo Again", className: "primary", onClick: () => openDemoGame(game.session.n_value) },
      { label: "Close", onClick: closeFocusGame },
    ]);
    return;
  }
  setGameScreen("Round Complete", `${step.summary}\n\n${feedback}`, [
    { label: "Next Round", className: "primary", onClick: advanceDemoStep },
  ]);
}

function advanceDemoStep() {
  state.game.demoStepIndex += 1;
  showDemoStepIntro();
}

function demoFeedback(trials, sequence, nValue) {
  const expected = new Set();
  sequence.forEach((letter, index) => {
    if (index >= nValue && letter === sequence[index - nValue]) {
      expected.add(index);
    }
  });
  const pressed = new Set(
    trials
      .filter((trial) => trial.isKeyPressed === "Yes")
      .map((trial) => trial.trialNumber - 1),
  );
  const missed = [...expected].filter((index) => !pressed.has(index));
  const extra = [...pressed].filter((index) => !expected.has(index));
  if (!missed.length && !extra.length) {
    return "Well done. You responded correctly in this round.";
  }
  if (missed.length && extra.length) {
    return "This round had both missed matches and extra SPACE presses. Try the next one slowly.";
  }
  if (missed.length) {
    return "Almost there. You missed at least one required SPACE press in this round.";
  }
  return "Almost there. You pressed SPACE when there was no match in this round.";
}

function setGameScreen(main, detail, actions = []) {
  $("gameMainText").classList.remove("letter");
  $("gameMainText").textContent = main;
  $("gameDetailText").textContent = detail || "";
  $("gameActions").innerHTML = "";
  actions.forEach((action) => addGameAction(action.label, action.onClick, action.className));
}

function addGameAction(label, onClick, className = "") {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  if (className) {
    button.className = className;
  }
  button.addEventListener("click", onClick);
  $("gameActions").appendChild(button);
}

function scheduleGameTimer(callback, delay) {
  const id = window.setTimeout(callback, delay);
  state.game?.timers.push(id);
  return id;
}

function clearGameTimers() {
  const game = state.game;
  if (!game?.timers) {
    return;
  }
  game.timers.forEach((timerId) => window.clearTimeout(timerId));
  game.timers = [];
}

async function closeFocusGame() {
  clearGameTimers();
  stopRelaxAudio();
  $("focusGame").classList.remove("flash-good", "flash-bad");
  $("focusGame").classList.add("hidden");
  if (state.status?.recording) {
    try {
      await api("/api/recording/stop", { method: "POST", body: { save: true } });
      appendLocalLog("Recording stopped after closing Focus Game.");
    } catch (error) {
      appendLocalLog(`Recording stop failed: ${error.message}`);
    }
  }
  state.game = null;
  refreshStatus().catch(() => {});
}

function startRelaxAudio() {
  const audio = $("relaxAudio");
  audio.currentTime = 0;
  audio.volume = Math.max(0, Math.min(state.game.session.announcement_volume || 0.7, 1));
  audio.play().catch(() => appendLocalLog("Browser blocked relax audio playback."));
}

function stopRelaxAudio() {
  const audio = $("relaxAudio");
  audio.pause();
  audio.currentTime = 0;
}

function playStageEndSignal() {
  const AudioContext = window.AudioContext || window.webkitAudioContext;
  if (!AudioContext) {
    return;
  }
  const context = new AudioContext();
  const volume = Math.max(0, Math.min(state.game?.session?.announcement_volume || 0.7, 1));
  [0, 0.32].forEach((offset) => {
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = "sine";
    oscillator.frequency.value = 880;
    gain.gain.value = 0.0001;
    oscillator.connect(gain);
    gain.connect(context.destination);
    const start = context.currentTime + offset;
    gain.gain.exponentialRampToValueAtTime(0.18 * volume + 0.0001, start + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.18);
    oscillator.start(start);
    oscillator.stop(start + 0.2);
  });
}

function bindEvents() {
  $("scanDevicesButton").addEventListener("click", scanDevices);
  $("connectDeviceButton").addEventListener("click", connectSelectedDevice);
  $("disconnectDeviceButton").addEventListener("click", disconnectDevice);
  $("recordButton").addEventListener("click", toggleRecording);
  $("startGameButton").addEventListener("click", startExperimentGame);
  $("playDemoButton").addEventListener("click", startDemoGame);
  $("exitGameButton").addEventListener("click", closeFocusGame);

  document.addEventListener("keydown", (event) => {
    if (event.code !== "Space" || $("focusGame").classList.contains("hidden")) {
      return;
    }
    event.preventDefault();
    if (state.game?.state === "game_intro") {
      advanceGameIntro();
    } else if (["playing", "demo_playing"].includes(state.game?.state)) {
      registerSpacePress();
    }
  });

  window.addEventListener("resize", () => {
    if (state.status) {
      renderStatus();
    }
  });
}

async function init() {
  setupTabs();
  bindEvents();
  state.config = await api("/api/config");
  populateLanguages();
  buildPlots();
  applyDefaults(state.config.defaults || {});
  await refreshStatus();
  window.setInterval(() => refreshStatus().catch((error) => appendLocalLog(`Status update failed: ${error.message}`)), 650);
}

init().catch((error) => {
  document.body.innerHTML = `<main class="panel" style="margin: 24px"><h1>EEG Analyse</h1><p>${error.message}</p></main>`;
});
