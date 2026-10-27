// Deliberately tiny: only rules that catch a missing import or an undefined variable, which the bundler and the
// tests don't (a removed import broke saving and the interval charts in production without failing the build).
import globals from "globals";
import react from "eslint-plugin-react";

export default [
  {
    linterOptions: { reportUnusedDisableDirectives: "off" },
  },
  {
    files: ["src/**/*.{js,jsx}"],
    // The code carries `eslint-disable react-hooks/exhaustive-deps` comments; define the rule (as a no-op) so they resolve.
    plugins: { react, "react-hooks": { rules: { "exhaustive-deps": { meta: {}, create: () => ({}) } } } },
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: { ...globals.browser, ...globals.node },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      "no-undef": "error",
      "react/jsx-no-undef": "error",
      "react/jsx-uses-vars": "error",
      "react/jsx-uses-react": "error",
    },
  },
  { files: ["src/**/*.test.{js,jsx}", "src/test/**"], languageOptions: { globals: { ...globals.browser, ...globals.node, ...globals.vitest } } },
];
