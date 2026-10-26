import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
    rules: {
      // These effects fetch data on mount or when an ID changes and set loading state first.
      // That is the standard pattern here; the rule is overly strict for it. A data library
      // (e.g. TanStack Query) would be the proper long-term replacement.
      'react-hooks/set-state-in-effect': 'off',
    },
  },
  {
    // Context modules intentionally export a provider and its hook together.
    files: ['src/context/**/*.tsx'],
    rules: { 'react-refresh/only-export-components': 'off' },
  },
])
