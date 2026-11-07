(function () {
  "use strict";

  var BASE = "/";

  var COLS = 22;
  var ROWS = 18;

  var loginView = document.getElementById("login-view");
  var consoleView = document.getElementById("console-view");
  var loginForm = document.getElementById("login-form");
  var loginUser = document.getElementById("login-user");
  var loginPassword = document.getElementById("login-password");
  var loginError = document.getElementById("login-error");
  var cameraName = document.getElementById("camera-name");
  var cameraInfo = document.getElementById("camera-info");
  var snapshot = document.getElementById("snapshot");
  var status = document.getElementById("status");

  var overlay = document.getElementById("mask-overlay");
  var motionStatus = document.getElementById("motion-status");
  var motionError = document.getElementById("motion-error");
  var mirrorInfo = document.getElementById("mirror-info");
  var tabLegacy = document.getElementById("tab-legacy");
  var tabRegions = document.getElementById("tab-regions");
  var panelLegacy = document.getElementById("panel-legacy");
  var panelRegions = document.getElementById("panel-regions");
  var regionOverlay = document.getElementById("region-overlay");
  var regionLegend = document.getElementById("region-legend");
  var regionStatus = document.getElementById("region-status");
  var regionError = document.getElementById("region-error");
  var maskCount = document.getElementById("mask-count");
  var applyButton = document.getElementById("mask-apply");
  var paintButton = document.getElementById("mode-paint");
  var eraseButton = document.getElementById("mode-erase");
  var clearButton = document.getElementById("mask-clear");
  var invertButton = document.getElementById("mask-invert");
  var revertButton = document.getElementById("mask-revert");

  var maskRows = null;
  var baseRows = null;
  var maskRevision = null;
  var mirrorPath = null;
  var maskStale = false;
  var mode = "paint";
  var dragging = false;
  var cellNodes = [];
  var regionWindows = [];
  var regionHasCells = false;

  function api(path, options) {
    return fetch(BASE + path, options).then(function (response) {
      return response.json().catch(function () {
        return {};
      }).then(function (body) {
        if (!response.ok) {
          var error = new Error(body.error || ("HTTP " + response.status));
          error.status = response.status;
          error.body = body;
          throw error;
        }
        return body;
      });
    });
  }

  function showLogin() {
    loginView.hidden = false;
    consoleView.hidden = true;
    loginPassword.value = "";
    loginPassword.focus();
  }

  function showConsole() {
    loginView.hidden = true;
    consoleView.hidden = false;
    loadCamera();
    refreshSnapshot();
    loadMotion();
  }

  function loadCamera() {
    api("api/camera").then(function (info) {
      cameraName.textContent = info.name || "";
      var parts = [];
      if (info.model) { parts.push(info.model); }
      if (info.firmware) { parts.push("firmware " + info.firmware); }
      if (info.auth) { parts.push("auth " + info.auth); }
      cameraInfo.textContent = parts.join(" \u00b7 ");
    }).catch(function (error) {
      status.textContent = error.message;
    });
  }

  function refreshSnapshot() {
    status.textContent = "";
    snapshot.src = BASE + "api/snapshot?t=" + Date.now();
  }

  snapshot.addEventListener("error", function () {
    status.textContent = "Snapshot failed to load.";
  });

  function cloneRows(rows) {
    return rows.map(function (row) { return row.slice(); });
  }

  function rowsEqual(a, b) {
    return JSON.stringify(a) === JSON.stringify(b);
  }

  function countCells(rows) {
    var total = 0;
    rows.forEach(function (row) {
      row.forEach(function (cell) { total += cell ? 1 : 0; });
    });
    return total;
  }

  function isDirty() {
    return Boolean(maskRows && baseRows && !rowsEqual(maskRows, baseRows));
  }

  function setMode(next) {
    mode = next;
    paintButton.setAttribute("aria-pressed", String(next === "paint"));
    eraseButton.setAttribute("aria-pressed", String(next === "erase"));
  }

  function updateStatus() {
    var readOnly = !maskRows || maskStale;
    [paintButton, eraseButton, clearButton, invertButton, revertButton].forEach(
      function (button) { button.disabled = readOnly; }
    );
    if (!maskRows) {
      applyButton.disabled = true;
      maskCount.textContent = "";
      return;
    }
    var dirty = isDirty();
    maskCount.textContent = countCells(maskRows) + " motion-sensitive cells" +
      (dirty ? " (unsaved)" : "");
    applyButton.disabled = !dirty || maskStale;
    motionStatus.textContent = maskStale ? "stale mirror (read-only)" : "";
  }

  function cellClass(cell) {
    return "cell " + (cell ? "on" : "off");
  }

  function buildOverlay() {
    while (overlay.firstChild) {
      overlay.removeChild(overlay.firstChild);
    }
    cellNodes = [];
    var namespace = "http://www.w3.org/2000/svg";
    for (var row = 0; row < ROWS; row += 1) {
      var nodes = [];
      for (var col = 0; col < COLS; col += 1) {
        var rect = document.createElementNS(namespace, "rect");
        rect.setAttribute("x", String(col));
        rect.setAttribute("y", String(row));
        rect.setAttribute("width", "1");
        rect.setAttribute("height", "1");
        rect.setAttribute("class", cellClass(maskRows[row][col]));
        overlay.appendChild(rect);
        nodes.push(rect);
      }
      cellNodes.push(nodes);
    }
  }

  function renderOverlay() {
    if (!maskRows) { return; }
    for (var row = 0; row < ROWS; row += 1) {
      for (var col = 0; col < COLS; col += 1) {
        cellNodes[row][col].setAttribute(
          "class", cellClass(maskRows[row][col])
        );
      }
    }
    updateStatus();
  }

  function renderMotion(data) {
    var motion = data.motion || {};
    var legacy = motion.legacy;
    mirrorPath = (data.mirror && data.mirror.path) || null;
    maskStale = Boolean(
      motion.stale || (data.mirror && data.mirror.stale)
    );
    regionWindows = motion.windows || [];
    motionError.textContent = "";

    if (!legacy || !legacy.rows) {
      maskRows = null;
      baseRows = null;
      maskRevision = null;
      applyButton.disabled = true;
      motionStatus.textContent = maskStale ? "stale mirror (read-only)" : "";
      motionError.textContent = "This camera did not report a legacy motion mask.";
      buildRegionOverlay();
      renderRegionLegend();
      updateMirrorInfo(data.mirror);
      syncOverlays();
      return;
    }

    maskRevision = legacy.revision;
    maskRows = cloneRows(legacy.rows);
    baseRows = cloneRows(legacy.rows);
    buildOverlay();
    renderOverlay();
    buildRegionOverlay();
    renderRegionLegend();
    updateMirrorInfo(data.mirror);
    syncOverlays();
  }

  function updateMirrorInfo(meta) {
    if (!meta) { mirrorInfo.textContent = ""; return; }
    var parts = [];
    if (meta.path) { parts.push("Mirror: " + meta.path); }
    if (meta.updated) { parts.push("updated " + meta.updated); }
    if (meta.last_apply) { parts.push("last apply " + meta.last_apply); }
    if (meta.stale) { parts.push("STALE"); }
    mirrorInfo.textContent = parts.join(" \u00b7 ");
  }

  function syncOverlays() {
    var legacyActive = tabLegacy.getAttribute("aria-selected") === "true";
    overlay.hidden = !legacyActive || !maskRows;
    regionOverlay.hidden = legacyActive || !regionHasCells;
  }

  function selectTab(name, focus) {
    var legacy = name === "legacy";
    tabLegacy.setAttribute("aria-selected", String(legacy));
    tabRegions.setAttribute("aria-selected", String(!legacy));
    tabLegacy.setAttribute("tabindex", legacy ? "0" : "-1");
    tabRegions.setAttribute("tabindex", legacy ? "-1" : "0");
    panelLegacy.hidden = !legacy;
    panelRegions.hidden = legacy;
    syncOverlays();
    if (focus) {
      (legacy ? tabLegacy : tabRegions).focus();
    }
  }

  function onTabKey(event) {
    if (event.key === "Home") {
      event.preventDefault();
      selectTab("legacy", true);
    } else if (event.key === "End") {
      event.preventDefault();
      selectTab("regions", true);
    } else if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault();
      var legacy = tabLegacy.getAttribute("aria-selected") === "true";
      selectTab(legacy ? "regions" : "legacy", true);
    }
  }

  function countRows(rows) {
    var total = 0;
    rows.forEach(function (row) {
      row.forEach(function (cell) { total += cell ? 1 : 0; });
    });
    return total;
  }

  function flipRows(rows) {
    return rows.map(function (row) { return row.slice().reverse(); });
  }

  function clearRegionOverlay() {
    while (regionOverlay.firstChild) {
      regionOverlay.removeChild(regionOverlay.firstChild);
    }
    regionHasCells = false;
  }

  function buildRegionOverlay() {
    clearRegionOverlay();
    var namespace = "http://www.w3.org/2000/svg";
    regionWindows.forEach(function (window, index) {
      if (!window.rows) { return; }
      var rows = flipRows(window.rows);
      var group = document.createElementNS(namespace, "g");
      group.setAttribute("class", "region-group r" + index);
      for (var row = 0; row < ROWS; row += 1) {
        for (var col = 0; col < COLS; col += 1) {
          if (!rows[row][col]) { continue; }
          var rect = document.createElementNS(namespace, "rect");
          rect.setAttribute("x", String(col));
          rect.setAttribute("y", String(row));
          rect.setAttribute("width", "1");
          rect.setAttribute("height", "1");
          rect.setAttribute("class", "region r" + index + " on");
          group.appendChild(rect);
          regionHasCells = true;
        }
      }
      if (group.childNodes.length) {
        regionOverlay.appendChild(group);
      }
    });
  }

  function renderRegionLegend() {
    while (regionLegend.firstChild) {
      regionLegend.removeChild(regionLegend.firstChild);
    }
    regionStatus.textContent = maskStale ? "stale mirror (read-only)" : "";
    if (!regionWindows.length) {
      regionError.textContent = "This camera did not report region windows.";
      return;
    }
    regionError.textContent = "";
    regionWindows.forEach(function (window, index) {
      var item = document.createElement("li");
      var swatch = document.createElement("span");
      swatch.className = "swatch region-swatch r" + index;
      swatch.setAttribute("aria-hidden", "true");
      item.appendChild(swatch);
      var parts = [window.name || ("Region" + (index + 1))];
      if (window.sensitive) { parts.push("sensitive " + window.sensitive); }
      if (window.threshold) { parts.push("threshold " + window.threshold); }
      if (window.rows) {
        parts.push(countRows(window.rows) + " cells");
      } else {
        parts.push("region grid unavailable");
      }
      var text = document.createElement("span");
      text.textContent = parts.join(" \u00b7 ");
      item.appendChild(text);
      regionLegend.appendChild(item);
    });
  }

  function loadMotion() {
    motionError.textContent = "";
    api("api/motion").then(renderMotion).catch(function (error) {
      motionError.textContent = error.message;
      maskRows = null;
      baseRows = null;
      applyButton.disabled = true;
      regionWindows = [];
      clearRegionOverlay();
      while (regionLegend.firstChild) {
        regionLegend.removeChild(regionLegend.firstChild);
      }
      regionStatus.textContent = "";
      regionError.textContent = error.message;
      syncOverlays();
    });
  }

  function cellAt(event) {
    var bounds = overlay.getBoundingClientRect();
    if (!bounds.width || !bounds.height) { return null; }
    var col = Math.floor((event.clientX - bounds.left) / bounds.width * COLS);
    var row = Math.floor((event.clientY - bounds.top) / bounds.height * ROWS);
    if (col < 0 || col >= COLS || row < 0 || row >= ROWS) { return null; }
    return { row: row, col: col };
  }

  function paintCell(cell, value) {
    if (!cell || !maskRows || maskStale) { return; }
    if (maskRows[cell.row][cell.col] === value) { return; }
    maskRows[cell.row][cell.col] = value;
    cellNodes[cell.row][cell.col].setAttribute("class", cellClass(value));
    updateStatus();
  }

  overlay.addEventListener("pointerdown", function (event) {
    if (event.button !== 0) { return; }
    event.preventDefault();
    dragging = true;
    paintCell(cellAt(event), mode === "paint" ? 1 : 0);
    if (overlay.setPointerCapture) {
      overlay.setPointerCapture(event.pointerId);
    }
  });

  overlay.addEventListener("pointermove", function (event) {
    if (!dragging) { return; }
    event.preventDefault();
    paintCell(cellAt(event), mode === "paint" ? 1 : 0);
  });

  overlay.addEventListener("pointerup", function () { dragging = false; });
  overlay.addEventListener("pointercancel", function () { dragging = false; });

  overlay.addEventListener("contextmenu", function (event) {
    event.preventDefault();
    paintCell(cellAt(event), 0);
  });

  paintButton.addEventListener("click", function () { setMode("paint"); });
  eraseButton.addEventListener("click", function () { setMode("erase"); });

  tabLegacy.addEventListener("click", function () { selectTab("legacy"); });
  tabRegions.addEventListener("click", function () { selectTab("regions"); });
  tabLegacy.addEventListener("keydown", onTabKey);
  tabRegions.addEventListener("keydown", onTabKey);

  document.getElementById("motion-refresh").addEventListener("click", loadMotion);

  document.getElementById("mask-clear").addEventListener("click", function () {
    if (!maskRows || maskStale) { return; }
    for (var row = 0; row < ROWS; row += 1) {
      for (var col = 0; col < COLS; col += 1) {
        maskRows[row][col] = 0;
      }
    }
    renderOverlay();
  });

  document.getElementById("mask-invert").addEventListener("click", function () {
    if (!maskRows || maskStale) { return; }
    for (var row = 0; row < ROWS; row += 1) {
      for (var col = 0; col < COLS; col += 1) {
        maskRows[row][col] = maskRows[row][col] ? 0 : 1;
      }
    }
    renderOverlay();
  });

  document.getElementById("mask-revert").addEventListener("click", function () {
    if (!baseRows || maskStale) { return; }
    maskRows = cloneRows(baseRows);
    renderOverlay();
  });

  applyButton.addEventListener("click", function () {
    if (!maskRows || !maskRevision || maskStale) { return; }
    if (!window.confirm("Apply this motion mask to the camera and verify it?")) {
      return;
    }
    applyButton.disabled = true;
    motionError.textContent = "";
    var justApplied = false;
    api("api/motion", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        rows: maskRows,
        revision: maskRevision,
        confirm: true
      })
    }).then(function (result) {
      if (result.motion) {
        renderMotion(result);
      }
      justApplied = true;
    }).catch(function (error) {
      if (error.status === 409 && error.body && error.body.motion) {
        renderMotion(error.body);
        motionError.textContent =
          "Camera mask changed; reloaded the current mask. Review and apply again.";
        return;
      }
      var message = error.message;
      if (error.body && error.body.actual) {
        message += " (expected " + JSON.stringify(error.body.expected) +
          ", got " + JSON.stringify(error.body.actual) + ")";
      }
      motionError.textContent = message;
    }).then(function () {
      updateStatus();
      if (justApplied) {
        motionStatus.textContent = "Applied and verified.";
      }
    });
  });

  loginForm.addEventListener("submit", function (event) {
    event.preventDefault();
    loginError.textContent = "";
    api("api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user: loginUser.value,
        password: loginPassword.value
      })
    }).then(function () {
      showConsole();
    }).catch(function (error) {
      loginError.textContent = error.message;
    });
  });

  document.getElementById("refresh").addEventListener("click", refreshSnapshot);

  document.getElementById("logout").addEventListener("click", function () {
    api("api/logout", { method: "POST" }).then(showLogin).catch(showLogin);
  });

  selectTab("legacy");

  api("api/session").then(function (session) {
    if (session.authenticated) {
      showConsole();
    } else {
      showLogin();
    }
  }).catch(function () {
    showLogin();
  });
})();
