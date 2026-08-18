import React from 'react';

export class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, info: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, info) {
        this.setState({ error, info });
    }

    render() {
        if (this.state.hasError) {
            return (
                <div style={{ color: 'red', background: 'black', padding: 20, zIndex: 9999, position: 'relative' }}>
                    <h3>Dashboard Crashed:</h3>
                    <pre>{this.state.error.toString()}</pre>
                    <pre>{this.state.info?.componentStack}</pre>
                </div>
            );
        }
        return this.props.children;
    }
}
