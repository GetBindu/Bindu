import { initializeBinduApp } from "./app.js";

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeBinduApp);
} else {
  initializeBinduApp();
}
