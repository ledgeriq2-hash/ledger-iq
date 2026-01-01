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
        <div className="u-pad-5 u-text-center">
          <h2>Something went wrong</h2>
          <p>Please try again, or refresh the page.</p>
          <button
            type="button"
            onClick={this.handleReset}
            className="kit-button kit-buttonGhost"
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
