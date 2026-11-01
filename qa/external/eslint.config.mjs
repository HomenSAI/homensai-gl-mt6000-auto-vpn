// HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
// ESLint 9 flat config for the LuCI page. *.inc.js are fragments spliced into dashboard.js by build_sidebar_ui.py,
// so cross-file names are not checked there (no-undef/no-unused-vars off); the built dashboard.js gets both.
import js from '@eslint/js';
import globals from 'globals';

const luci = {L: 'readonly', E: 'readonly', _: 'readonly', N_: 'readonly', view: 'readonly', form: 'readonly',
  rpc: 'readonly', poll: 'readonly', ui: 'readonly', uci: 'readonly', fs: 'readonly', dom: 'readonly',
  network: 'readonly', request: 'readonly', baseclass: 'readonly'};
// dashboard.js is a LuCI view: its top level is a function body (it ends with `return view.extend({...})`).
const common = {ecmaVersion: 2020, sourceType: 'script', globals: {...globals.browser, ...luci},
  parserOptions: {ecmaFeatures: {globalReturn: true}}};

export default [
  {files: ['**/*.js'], ...js.configs.recommended, languageOptions: common},
  {files: ['**/*.inc.js'], rules: {'no-undef': 'off', 'no-unused-vars': 'off'}},
];
