import React from "react";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error("UI error captured", error, info);
  }

  handleReset = () => {
    this.setState({ hasError: false });
    if (typeof this.props.onReset === "function") {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: "2rem", textAlign: "center" }}>
          <h2>Something went wrong</h2>
          <p>Please try again, or refresh the page.</p>
          <button
            type="button"
            onClick={this.handleReset}
            style={{
              marginTop: "1rem",
              padding: "0.65rem 1.2rem",
              borderRadius: "0.5rem",
              border: "1px solid #d1d5db",
              background: "#f3f4f6",
              cursor: "pointer",
            }}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;

// Example:
// <ErrorBoundary>
//   <MyComponent />
// </ErrorBoundary>
