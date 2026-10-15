import { continueRender, delayRender, staticFile } from 'remotion';

const ARCHIVO_800_FILES = [
  { family: 'Archivo800_1', file: 'fonts/archivo-800-10d9bd15.woff2', weight: '800' },
  { family: 'Archivo800_2', file: 'fonts/archivo-800-23599068.woff2', weight: '800' },
  { family: 'Archivo800_3', file: 'fonts/archivo-800-87937726.woff2', weight: '800' },
];

const KANIT_600_FILES = [
  { family: 'Kanit600_1', file: 'fonts/kanit-600-0c71a5b8.woff2', weight: '600' },
  { family: 'Kanit600_2', file: 'fonts/kanit-600-9895ee29.woff2', weight: '600' },
  { family: 'Kanit600_3', file: 'fonts/kanit-600-b4b6e60e.woff2', weight: '600' },
  { family: 'Kanit600_4', file: 'fonts/kanit-600-fc0bae07.woff2', weight: '600' },
];

const KANIT_800_FILES = [
  { family: 'Kanit800_1', file: 'fonts/kanit-800-1bf17218.woff2', weight: '800' },
  { family: 'Kanit800_2', file: 'fonts/kanit-800-aa86a0cb.woff2', weight: '800' },
  { family: 'Kanit800_3', file: 'fonts/kanit-800-f57eab15.woff2', weight: '800' },
  { family: 'Kanit800_4', file: 'fonts/kanit-800-f99e92e2.woff2', weight: '800' },
];

export const ALL_FONT_SPECS = [
  ...ARCHIVO_800_FILES,
  ...KANIT_600_FILES,
  ...KANIT_800_FILES,
];

export const FONT_ARCHIVO_800 =
  "'Archivo800_1', 'Archivo800_2', 'Archivo800_3', 'Kanit800_1', 'Kanit800_2', 'Kanit800_3', 'Kanit800_4', sans-serif";

export const FONT_KANIT_600 =
  "'Kanit600_1', 'Kanit600_2', 'Kanit600_3', 'Kanit600_4', 'Archivo800_1', 'Archivo800_2', 'Archivo800_3', sans-serif";

export const FONT_KANIT_800 =
  "'Kanit800_1', 'Kanit800_2', 'Kanit800_3', 'Kanit800_4', 'Archivo800_1', 'Archivo800_2', 'Archivo800_3', sans-serif";

export const FONT_FACE_CSS = ALL_FONT_SPECS.map(
  (spec) => `
@font-face {
  font-family: '${spec.family}';
  src: url('${staticFile(spec.file)}') format('woff2');
  font-weight: ${spec.weight};
  font-style: normal;
  font-display: block;
}
`
).join('\n');

let fontsLoadedPromise: Promise<void> | null = null;

export const ensureFontsLoaded = (): Promise<void> => {
  if (typeof document === 'undefined') {
    return Promise.resolve();
  }
  if (fontsLoadedPromise) {
    return fontsLoadedPromise;
  }

  const handle = delayRender('Loading local woff2 fonts (Kanit & Archivo)');

  fontsLoadedPromise = Promise.all(
    ALL_FONT_SPECS.map(async (spec) => {
      const face = new FontFace(spec.family, `url(${staticFile(spec.file)})`, {
        weight: spec.weight,
        style: 'normal',
      });
      const loaded = await face.load();
      document.fonts.add(loaded);
    })
  )
    .then(() => {
      continueRender(handle);
    })
    .catch((err) => {
      console.error('Font loading error:', err);
      continueRender(handle);
    });

  return fontsLoadedPromise;
};
