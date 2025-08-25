#!/usr/bin/env bash
# setup_js_qa.sh — initialize local JS/TS QA toolchain
# Run this from your PROJECT ROOT (where package.json should live).
# It will:
#  - ensure npm is available
#  - create package.json if missing
#  - install eslint@^9, typescript@^5, @typescript-eslint/parser, @typescript-eslint/eslint-plugin
#  - create minimal eslint.config.mjs and tsconfig.json (if missing)
#  - verify with `npx eslint --version` and `npx tsc --version`
set -euo pipefail

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm is not installed. Install Node.js (e.g., 'brew install node') and re-run." >&2
  exit 1
fi

if [ ! -f package.json ]; then
  echo "No package.json found → initializing one (npm init -y)…"
  npm init -y >/dev/null
fi

echo "Installing JS QA devDependencies (local to this project)…"
npm pkg set "devDependencies.eslint"="^9.0.0" >/dev/null
npm pkg set "devDependencies.typescript"="^5.0.0" >/dev/null
npm pkg set "devDependencies.@typescript-eslint/parser"="^8.0.0" >/dev/null
npm pkg set "devDependencies.@typescript-eslint/eslint-plugin"="^8.0.0" >/dev/null

npm install >/dev/null

# Create minimal TypeScript config if missing
if [ ! -f tsconfig.json ]; then
  cat > tsconfig.json <<'JSON'
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "strict": true,
    "noEmit": true,
    "skipLibCheck": true
  },
  "include": ["**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx"]
}
JSON
  echo "Created tsconfig.json"
fi

# Create an ESLint flat config if missing (ESLint v9+)
if [ ! -f eslint.config.mjs ]; then
  cat > eslint.config.mjs <<'MJS'
// Minimal ESLint flat config for JS/TS projects
// Uses @typescript-eslint when TS files are present
import tseslint from "@typescript-eslint/eslint-plugin";
import tsParser from "@typescript-eslint/parser";

export default [
  {
    files: ["**/*.{js,jsx,ts,tsx}"],
    languageOptions: {
      parser: tsParser,
      parserOptions: { ecmaVersion: "latest", sourceType: "module", project: false }
    },
    plugins: { "@typescript-eslint": tseslint },
    rules: {
      "no-unused-vars": "error",
      "no-undef": "error"
    }
  }
];
MJS
  echo "Created eslint.config.mjs"
fi

echo "Verifying toolchain…"
npx --yes eslint --version >/dev/null
npx --yes tsc --version >/dev/null
echo "✅ JS/TS QA toolchain ready."
echo "You can now run: npx eslint . --max-warnings=0  and  npx tsc --noEmit"
