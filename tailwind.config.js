// Tailwind build config (specs/023): replaces the in-page CDN config.
// Build with: bash scripts/build_css.sh  →  frontend/static/css/app.css (committed)
module.exports = {
  content: ['./frontend/templates/**/*.html', './frontend/static/js/**/*.js'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"JetBrains Mono"', 'Consolas', 'ui-monospace', 'monospace'],
        mono: ['"JetBrains Mono"', 'Consolas', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        'xs':   ['9px',  { lineHeight: '1.4' }],
        'sm':   ['11px', { lineHeight: '1.4' }],
        'base': ['12px', { lineHeight: '1.5' }],
        'lg':   ['13px', { lineHeight: '1.4' }],
        'xl':   ['14px', { lineHeight: '1.4' }],
        '2xl':  ['16px', { lineHeight: '1.3' }],
        '3xl':  ['18px', { lineHeight: '1.3' }],
      },
    },
  },
};
