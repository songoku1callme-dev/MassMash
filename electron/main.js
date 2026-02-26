/**
 * MassMash AI Desktop Client - Electron Main Process
 *
 * Single-command desktop launcher: starts the FastAPI backend automatically,
 * waits for it to be healthy, then opens the UI window.
 * If the backend crashes it is restarted automatically.
 *
 * Includes:
 * - Splash screen while backend starts
 * - Auto-update support via electron-updater
 * - Proper resource paths for packaged builds
 */

const { app, BrowserWindow, shell, dialog } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const http = require("http");

let mainWindow = null;
let splashWindow = null;
let backendProcess = null;
let isQuitting = false;
let backendRestartCount = 0;

const isDev = !app.isPackaged;

const BACKEND_PORT = 8000;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
const HEALTH_URL = `${BACKEND_URL}/healthz`;
const HEALTH_CHECK_INTERVAL_MS = 1000;
const HEALTH_CHECK_MAX_RETRIES = 30;
const MAX_BACKEND_RESTARTS = 5;

// ---------------------------------------------------------------------------
// Resource path helpers (works in both dev and packaged mode)
// ---------------------------------------------------------------------------

/**
 * In packaged mode, extraResources are placed next to the app.asar:
 *   <install>/resources/backend/...
 *   <install>/resources/frontend/dist/...
 * In dev mode, paths are relative to __dirname (electron/).
 */
function getResourcePath(...segments) {
  if (isDev) {
    return path.join(__dirname, "..", ...segments);
  }
  return path.join(process.resourcesPath, ...segments);
}

// ---------------------------------------------------------------------------
// Health check helper
// ---------------------------------------------------------------------------

function checkBackendHealth() {
  return new Promise((resolve) => {
    const req = http.get(HEALTH_URL, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on("error", () => resolve(false));
    req.setTimeout(2000, () => {
      req.destroy();
      resolve(false);
    });
  });
}

/**
 * Poll the backend health endpoint until it responds with 200 or we exceed
 * the maximum number of retries.
 */
function waitForBackend(retries = HEALTH_CHECK_MAX_RETRIES) {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    const interval = setInterval(async () => {
      attempts++;
      const healthy = await checkBackendHealth();
      if (healthy) {
        clearInterval(interval);
        resolve();
      } else if (attempts >= retries) {
        clearInterval(interval);
        reject(new Error("Backend did not become healthy in time"));
      }
    }, HEALTH_CHECK_INTERVAL_MS);
  });
}

// ---------------------------------------------------------------------------
// Backend process management
// ---------------------------------------------------------------------------

function startBackend() {
  if (backendProcess) return; // already running

  const backendDir = getResourcePath("backend");

  console.log("[Electron] Starting backend server from:", backendDir);

  // Use `fastapi dev` in development, `fastapi run` in production
  const fastapiCmd = isDev ? "dev" : "run";

  backendProcess = spawn(
    "poetry",
    ["run", "fastapi", fastapiCmd, "app/main.py", "--port", String(BACKEND_PORT)],
    {
      cwd: backendDir,
      shell: true,
      stdio: "pipe",
      env: { ...process.env },
    }
  );

  backendProcess.stdout.on("data", (data) => {
    console.log(`[Backend] ${data.toString().trim()}`);
  });

  backendProcess.stderr.on("data", (data) => {
    console.error(`[Backend] ${data.toString().trim()}`);
  });

  backendProcess.on("error", (err) => {
    console.error("[Electron] Failed to spawn backend:", err.message);
    backendProcess = null;
  });

  backendProcess.on("close", (code) => {
    console.log(`[Electron] Backend exited with code ${code}`);
    backendProcess = null;

    // Auto-restart unless we are quitting the app
    if (!isQuitting && backendRestartCount < MAX_BACKEND_RESTARTS) {
      backendRestartCount++;
      console.log(
        `[Electron] Restarting backend (attempt ${backendRestartCount}/${MAX_BACKEND_RESTARTS})...`
      );
      setTimeout(startBackend, 1500);
    } else if (!isQuitting) {
      console.error("[Electron] Backend restart limit reached.");
      dialog.showErrorBox(
        "Backend Error",
        "The backend server crashed and could not be restarted.\n" +
          "Please check the logs and restart the application."
      );
    }
  });
}

function stopBackend() {
  if (!backendProcess) return;

  console.log("[Electron] Stopping backend...");

  // On Windows, killing a shell-spawned process requires killing the tree
  if (process.platform === "win32") {
    spawn("taskkill", ["/pid", String(backendProcess.pid), "/f", "/t"], {
      shell: true,
    });
  } else {
    backendProcess.kill("SIGTERM");
  }

  backendProcess = null;
}

// ---------------------------------------------------------------------------
// Splash screen
// ---------------------------------------------------------------------------

function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 420,
    height: 320,
    frame: false,
    transparent: true,
    resizable: false,
    alwaysOnTop: true,
    icon: path.join(__dirname, "icon.png"),
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  splashWindow.loadFile(path.join(__dirname, "splash.html"));
  splashWindow.center();

  splashWindow.on("closed", () => {
    splashWindow = null;
  });
}

function closeSplash() {
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.close();
    splashWindow = null;
  }
}

// ---------------------------------------------------------------------------
// Main window
// ---------------------------------------------------------------------------

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: "MassMash AI",
    icon: path.join(__dirname, "icon.png"),
    backgroundColor: "#09090b", // zinc-950
    show: false, // show after ready-to-show
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Remove default menu bar
  mainWindow.setMenuBarVisibility(false);

  // Show window only once content is ready (avoids white flash)
  mainWindow.once("ready-to-show", () => {
    closeSplash();
    mainWindow.show();
  });

  if (isDev) {
    mainWindow.loadURL("http://localhost:5173");
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    // In packaged mode, frontend dist is in extraResources
    const frontendIndex = getResourcePath("frontend", "dist", "index.html");
    mainWindow.loadFile(frontendIndex);
  }

  // Open external links in browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

// ---------------------------------------------------------------------------
// Auto-update (only in packaged mode)
// ---------------------------------------------------------------------------

function setupAutoUpdate() {
  if (isDev) return;

  try {
    const { autoUpdater } = require("electron-updater");

    autoUpdater.logger = console;
    autoUpdater.autoDownload = true;
    autoUpdater.autoInstallOnAppQuit = true;

    autoUpdater.on("update-available", (info) => {
      console.log("[AutoUpdate] Update available:", info.version);
    });

    autoUpdater.on("update-downloaded", (info) => {
      console.log("[AutoUpdate] Update downloaded:", info.version);
      dialog
        .showMessageBox(mainWindow, {
          type: "info",
          title: "Update verfuegbar",
          message: `MassMash AI v${info.version} wurde heruntergeladen. Die App wird beim naechsten Neustart aktualisiert.`,
          buttons: ["Jetzt neustarten", "Spaeter"],
        })
        .then((result) => {
          if (result.response === 0) {
            autoUpdater.quitAndInstall();
          }
        });
    });

    autoUpdater.on("error", (err) => {
      console.error("[AutoUpdate] Error:", err.message);
    });

    autoUpdater.checkForUpdatesAndNotify();
  } catch (err) {
    // electron-updater may not be installed in dev
    console.log("[AutoUpdate] Skipped:", err.message);
  }
}

// ---------------------------------------------------------------------------
// App lifecycle
// ---------------------------------------------------------------------------

app.whenReady().then(async () => {
  // 1. Show splash screen
  createSplashWindow();

  // 2. Start the backend
  startBackend();

  // 3. Wait until the backend is healthy
  try {
    console.log("[Electron] Waiting for backend to become healthy...");
    await waitForBackend();
    console.log("[Electron] Backend is healthy!");
  } catch {
    console.warn(
      "[Electron] Backend health check timed out — opening window anyway."
    );
  }

  // 4. Create the main window (splash closes on ready-to-show)
  createWindow();

  // 5. Setup auto-update
  setupAutoUpdate();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  isQuitting = true;
  stopBackend();
});

app.on("quit", () => {
  stopBackend();
});
