(function () {
  "use strict";

  var base = window.location.pathname;
  if (base.charAt(base.length - 1) !== "/") {
    base += "/";
  }

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

  function api(path, options) {
    return fetch(base + path, options).then(function (response) {
      return response.json().catch(function () {
        return {};
      }).then(function (body) {
        if (!response.ok) {
          throw new Error(body.error || ("HTTP " + response.status));
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
  }

  function loadCamera() {
    api("api/camera").then(function (info) {
      cameraName.textContent = info.name || "";
      var parts = [];
      if (info.model) { parts.push(info.model); }
      if (info.firmware) { parts.push("firmware " + info.firmware); }
      if (info.auth) { parts.push("auth " + info.auth); }
      cameraInfo.textContent = parts.join(" · ");
    }).catch(function (error) {
      status.textContent = error.message;
    });
  }

  function refreshSnapshot() {
    status.textContent = "";
    snapshot.src = base + "api/snapshot?t=" + Date.now();
  }

  snapshot.addEventListener("error", function () {
    status.textContent = "Snapshot failed to load.";
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
