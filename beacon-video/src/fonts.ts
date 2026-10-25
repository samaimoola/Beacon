/**
 * Local, bundled fonts (SIL OFL — licenses in public/fonts). @remotion/fonts
 * holds every frame with delayRender() until each file is loaded, so no frame is
 * ever captured with fallback type. Imported once from src/index.ts.
 */
import { loadFont } from '@remotion/fonts';
import { staticFile } from 'remotion';

export const fontsReady = Promise.all([
  loadFont({
    family: 'Fraunces',
    url: staticFile('fonts/fraunces-latin-full-normal.woff2'),
    weight: '100 900',
    style: 'normal',
    display: 'block',
  }),
  loadFont({
    family: 'Fraunces',
    url: staticFile('fonts/fraunces-latin-full-italic.woff2'),
    weight: '100 900',
    style: 'italic',
    display: 'block',
  }),
  loadFont({
    family: 'Inter',
    url: staticFile('fonts/inter-latin-opsz-normal.woff2'),
    weight: '100 900',
    style: 'normal',
    display: 'block',
  }),
]);
