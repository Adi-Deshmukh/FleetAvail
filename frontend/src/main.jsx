import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles.css";

class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null }; }
  static getDerivedStateFromError(error) { return { error }; }
  render() {
    if (this.state.error) {
      return (
        <div style={{ color: "#ff9aa2", padding: "40px", fontFamily: "monospace", background: "#07111f", minHeight: "100vh" }}>
          <h2 style={{ color: "#ff6b7a" }}>⚠ React crashed</h2>
          <pre style={{ color: "#e8eef7", whiteSpace: "pre-wrap" }}>{String(this.state.error)}</pre>
          <pre style={{ color: "#8a9fb5", fontSize: "11px", whiteSpace: "pre-wrap" }}>{this.state.error?.stack}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>
);

