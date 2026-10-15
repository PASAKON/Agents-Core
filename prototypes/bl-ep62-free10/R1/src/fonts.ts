import { useEffect, useState } from 'react';
import { continueRender, delayRender, staticFile } from 'remotion';

export interface FontSpec {
  family: string;
  file: string;
  weight: string;
}

export const FONT_SPECS: FontSpec[] = [
  { family: 'BL_Archivo800_0', file: 'fonts/archivo-800-10d9bd15.woff2', weight: '800' },
  { family: 'BL_Archivo800_1', file: 'fonts/archivo-800-23599068.woff2', weight: '800' },
  { family: 'BL_Archivo800_2', file: 'fonts/archivo-800-87937726.woff2', weight: '800' },
  { family: 'BL_Kanit600_0', file: 'fonts/kanit-600-0c71a5b8.woff2', weight: '600' },
  { family: 'BL_Kanit600_1', file: 'fonts/kanit-600-9895ee29.woff2', weight: '600' },
  { family: 'BL_Kanit600_2', file: 'fonts/kanit-600-b4b6e60e.woff2', weight: '600' },
  { family: 'BL_Kanit600_3', file: 'fonts/kanit-600-fc0bae07.woff2', weight: '600' },
  { family: 'BL_Kanit800_0', file: 'fonts/kanit-800-1bf17218.woff2', weight: '800' },
  { family: 'BL_Kanit800_1', file: 'fonts/kanit-800-aa86a0cb.woff2', weight: '800' },
  { family: 'BL_Kanit800_2', file: 'fonts/kanit-800-f57eab15.woff2', weight: '800' },
  { family: 'BL_Kanit800_3', file: 'fonts/kanit-800-f99e92e2.woff2', weight: '800' },
];

export const FONT_KANIT_600 =
  "'BL_Kanit600_0', 'BL_Kanit600_1', 'BL_Kanit600_2', 'BL_Kanit600_3', 'Kanit', sans-serif";

export const FONT_KANIT_800 =
  "'BL_Kanit800_0', 'BL_Kanit800_1', 'BL_Kanit800_2', 'BL_Kanit800_3', 'Kanit', sans-serif";

export const FONT_ARCHIVO_800 =
  "'BL_Archivo800_0', 'BL_Archivo800_1', 'BL_Archivo800_2', 'BL_Kanit800_0', 'BL_Kanit800_1', 'BL_Kanit800_2', 'BL_Kanit800_3', 'Archivo', 'Kanit', sans-serif";

export const FONT_FACE_CSS = FONT_SPECS.map(
  (spec) => `
@font-face {
  font-family: '${spec.family}';
  src: url('${staticFile(spec.file)}') format('woff2');
  font-weight: ${spec.weight};
  font-style: normal;
  font-display: block;
}`
).join('\n');

let fontsLoadedPromise: Promise<void> | null = null;

function ensureFontsLoaded(): Promise<void> {
  if (fontsLoadedPromise) {
    return fontsLoadedPromise;
  }
  if (typeof window === 'undefined' || typeof FontFace === 'undefined') {
    fontsLoadedPromise = Promise.resolve();
    return fontsLoadedPromise;
  }

  fontsLoadedPromise = Promise.all(
    FONT_SPECS.map(async (spec) => {
      const face = new FontFace(
        spec.family,
        `url(${staticFile(spec.file)}) format('woff2')`,
        {
          weight: spec.weight,
          style: 'normal',
        }
      );
      const loaded = await face.load();
      document.fonts.add(loaded);
    })
  )
    .then(() => document.fonts.ready)
    .then(() => undefined);

  return fontsLoadedPromise;
}

export function useLoadFonts(): boolean {
  const [handle] = useState(() => delayRender('Loading local woff2 fonts'));
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    ensureFontsLoaded()
      .catch((err) => {
        console.error('Font load error:', err);
      })
      .finally(() => {
        if (active) {
          setLoaded(true);
          continueRender(handle);
        }
      });
    return () => {
      active = false;
    };
  }, [handle]);

  return loaded;
}
