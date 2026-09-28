import "@testing-library/jest-dom";

// jsdom does not implement window.matchMedia — provide a minimal stub so
// ThemeProvider (and any component that uses it) renders without crashing.
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});
