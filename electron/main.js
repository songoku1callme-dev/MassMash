/**
 * MassMash AI Desktop Client - Electron Main Process
 *
 * This wraps the React frontend in a native desktop window.
 * The backend (FastAPI) should be started separately or via the start script.
 */

const { app, BrowserWindow, shell } = require("electron");
const path = require("path");
const { spawn } = require("child_process");

let mainWindow = null;
let backendProcess = null;

const isDev = !app.isPackaged;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: "MassMash AI",
    icon: path.join(__dirname, "icon.png"),
    backgroundColor: "#09090b", // zinc-950
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Remove default menu bar
  mainWindow.setMenuBarVisibility(false);

  if (isDev) {
    // In development, load from Vite dev server
    mainWindow.loadURL("http://localhost:5173");
    mainWindow.webContents.openDevTools({ mode: "detach" });
  } else {
    // In production, load the built frontend
    mainWindow.loadFile(path.join(__dirname, "..", "frontend", "dist", "index.html"));
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

function startBackend() {
  const backendDir = path.join(__dirname, "..", "backend");

  // Try to start the backend using poetry
  backendProcess = spawn(
    "poetry",
    ["run", "fastapi", "dev", "app/main.py", "--port", "8000"],
    {
      cwd: backendDir,
      shell: true,
      stdio: "pipe",
    }
  );

  backendProcess.stdout.on("data", (data) => {
    console.log(`[Backend] ${data}`);
  });

  backendProcess.stderr.on("data", (data) => {
    console.error(`[Backend] ${data}`);
  });

  backendProcess.on("error", (err) => {
    console.error("Failed to start backend:", err.message);
  });

  backendProcess.on("close", (code) => {
    console.log(`Backend process exited with code ${code}`);
    backendProcess = null;
  });
}

app.whenReady().then(() => {
  // Start backend automatically
  startBackend();

  // Wait a moment for the backend to start, then create the window
  setTimeout(createWindow, 2000);

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  // Kill backend when app closes
  if (backendProcess) {
    backendProcess.kill();
  }
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  if (backendProcess) {
    backendProcess.kill();
  }
});
