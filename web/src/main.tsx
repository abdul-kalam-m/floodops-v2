import React from "react";
import ReactDOM from "react-dom/client";
import "maplibre-gl/dist/maplibre-gl.css";
import "./index.css";
import App from "./App";
import ReportPage from "./pages/ReportPage";
import MethodsPage from "./pages/MethodsPage";

// Deliberately no router library (§8.1): three top-level pages, picked once by
// pathname at mount. Each page independently fetches what it needs from public/data.
// Cloudflare's web/public/_redirects serves index.html for any path, so /report and
// /methods work on a direct load, shared link, or refresh, not just in-app navigation.
function Root() {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  if (path === "/report") return <ReportPage />;
  if (path === "/methods") return <MethodsPage />;
  return <App />;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>,
);
