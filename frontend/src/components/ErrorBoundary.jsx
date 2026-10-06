import React from "react";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    this.setState({ error, errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: "40px", fontFamily: "sans-serif" }}>
          <h1 style={{ color: "#EF5350" }}>Something went wrong</h1>
          <details style={{ whiteSpace: "pre-wrap", marginTop: "20px" }}>
            <summary style={{ cursor: "pointer", marginBottom: "10px" }}>
              Click for error details
            </summary>
            <div
              style={{
                background: "#f5f5f5",
                padding: "15px",
                borderRadius: "4px",
              }}
            >
              <p>
                <strong>Error:</strong>{" "}
                {this.state.error && this.state.error.toString()}
              </p>
              <p>
                <strong>Stack:</strong>
              </p>
              <pre>
                {this.state.errorInfo && this.state.errorInfo.componentStack}
              </pre>
            </div>
          </details>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
