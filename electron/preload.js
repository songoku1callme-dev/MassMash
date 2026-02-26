/**
 * Preload script - runs in a sandboxed context before the renderer process.
 * Provides a safe bridge between Node.js and the browser context.
 */

const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  platform: process.platform,
  isElectron: true,
});
