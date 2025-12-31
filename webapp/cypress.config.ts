import { defineConfig } from "cypress";

export default defineConfig({
  e2e: {
    specPattern: [
      "cypress/e2e/**/*.cy.{js,jsx,ts,tsx}",    // End-to-End tests
      "cypress/integration/**/*.cy.{js,jsx,ts,tsx}" // Integration tests
    ],
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
    baseUrl: "http://localhost:3000",
  },

  component: {
    devServer: {
      framework: "next",
      bundler: "webpack",
    },
  },
});
