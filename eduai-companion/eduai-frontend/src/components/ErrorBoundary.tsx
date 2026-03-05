import { Component, type ReactNode, type ErrorInfo } from "react";

/* ============================================================
   LUMNOS Autopilot 2.0 — Block 5: Error Boundary
   Fängt unerwartete Render-Fehler ab und zeigt eine
   benutzerfreundliche Fehlermeldung statt eines weißen Bildschirms.
   ============================================================ */

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[ErrorBoundary] Unerwarteter Fehler:", error, info.componentStack);
    // Sentry wird automatisch über das globale Error-Tracking benachrichtigt
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="min-h-screen flex items-center justify-center p-6"
          style={{ background: "var(--lumnos-bg)" }}
        >
          <div
            className="max-w-md w-full text-center p-8 rounded-2xl"
            style={{
              background: "rgba(var(--surface-rgb),0.6)",
              border: "1px solid rgba(239,68,68,0.3)",
              backdropFilter: "blur(20px)",
              boxShadow: "0 0 40px rgba(239,68,68,0.15)",
            }}
          >
            {/* Error Icon */}
            <div
              className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center text-2xl"
              style={{
                background: "rgba(239,68,68,0.15)",
                border: "1px solid rgba(239,68,68,0.3)",
              }}
            >
              &#9888;
            </div>

            <h2 className="text-xl font-bold text-white mb-2">
              Etwas ist schiefgelaufen
            </h2>
            <p className="text-sm text-slate-400 mb-6">
              Ein unerwarteter Fehler ist aufgetreten. Bitte versuche es erneut
              oder lade die Seite neu.
            </p>

            {/* Error details (collapsed) */}
            {this.state.error && (
              <details className="text-left mb-6">
                <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-400 transition-colors">
                  Technische Details anzeigen
                </summary>
                <pre
                  className="mt-2 p-3 rounded-lg text-[10px] text-red-400 overflow-x-auto"
                  style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)" }}
                >
                  {this.state.error.message}
                </pre>
              </details>
            )}

            <div className="flex gap-3 justify-center">
              <button
                onClick={this.handleReset}
                className="px-4 py-2 rounded-xl text-sm font-medium text-slate-300 transition-all hover:text-white"
                style={{
                  background: "rgba(99,102,241,0.15)",
                  border: "1px solid rgba(99,102,241,0.3)",
                }}
              >
                Erneut versuchen
              </button>
              <button
                onClick={this.handleReload}
                className="px-4 py-2 rounded-xl text-sm font-medium text-white transition-all hover:scale-105"
                style={{
                  background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                  boxShadow: "0 0 20px rgba(99,102,241,0.4)",
                }}
              >
                Seite neu laden
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
