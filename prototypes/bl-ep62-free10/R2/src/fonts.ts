import { useEffect, useState } from 'react';
import { continueRender, delayRender, staticFile } from 'remotion';

type FontSpec = {
  readonly id: string;
  readonly sharedFamily: string;
  readonly weight: string;
  readonly path: string;
};

const FONT_SPECS: readonly FontSpec[] = [
  { id: 'Archivo800_A', sharedFamily: 'Archivo', weight: '800', path: 'fonts/archivo-800-10d9bd15.woff2' },
  { id: 'Archivo800_B', sharedFamily: 'Archivo', weight: '800', path: 'fonts/archivo-800-23599068.woff2' },
  { id: 'Archivo800_C', sharedFamily: 'Archivo', weight: '800', path: 'fonts/archivo-800-87937726.woff2' },
  { id: 'Kanit600_A', sharedFamily: 'Kanit', weight: '600', path: 'fonts/kanit-600-0c71a5b8.woff2' },
  { id: 'Kanit600_B', sharedFamily: 'Kanit', weight: '600', path: 'fonts/kanit-600-9895ee29.woff2' },
  { id: 'Kanit600_C', sharedFamily: 'Kanit', weight: '600', path: 'fonts/kanit-600-b4b6e60e.woff2' },
  { id: 'Kanit600_D', sharedFamily: 'Kanit', weight: '600', path: 'fonts/kanit-600-fc0bae07.woff2' },
  { id: 'Kanit800_A', sharedFamily: 'Kanit', weight: '800', path: 'fonts/kanit-800-1bf17218.woff2' },
  { id: 'Kanit800_B', sharedFamily: 'Kanit', weight: '800', path: 'fonts/kanit-800-aa86a0cb.woff2' },
  { id: 'Kanit800_C', sharedFamily: 'Kanit', weight: '800', path: 'fonts/kanit-800-f57eab15.woff2' },
  { id: 'Kanit800_D', sharedFamily: 'Kanit', weight: '800', path: 'fonts/kanit-800-f99e92e2.woff2' },
];

export const FONT_KANIT_800 =
  "'Kanit800_A', 'Kanit800_B', 'Kanit800_C', 'Kanit800_D', 'Kanit', sans-serif";

export const FONT_KANIT_600 =
  "'Kanit600_A', 'Kanit600_B', 'Kanit600_C', 'Kanit600_D', 'Kanit', sans-serif";

export const FONT_ARCHIVO_800 =
  "'Archivo800_A', 'Archivo800_B', 'Archivo800_C', 'Archivo', 'Kanit800_A', 'Kanit800_B', 'Kanit800_C', 'Kanit800_D', sans-serif";

export const FONT_FACE_CSS = FONT_SPECS.map((spec) => {
  const url = staticFile(spec.path);
  return `
@font-face {
  font-family: '${spec.id}';
  src: url('${url}') format('woff2');
  font-weight: ${spec.weight};
  font-style: normal;
  font-display: block;
}
@font-face {
  font-family: '${spec.sharedFamily}';
  src: url('${url}') format('woff2');
  font-weight: ${spec.weight};
  font-style: normal;
  font-display: block;
}`;
}).join('\n');

let fontsLoadPromise: Promise<void> | null = null;

const ensureFontsLoaded = (): Promise<void> => {
  if (fontsLoadPromise) {
    return fontsLoadPromise;
  }
  if (typeof document === 'undefined' || typeof FontFace === 'undefined') {
    fontsLoadPromise = Promise.resolve();
    return fontsLoadPromise;
  }

  fontsLoadPromise = Promise.all(
    FONT_SPECS.flatMap((spec) => {
      const url = `url(${staticFile(spec.path)}) format('woff2')`;
      const uniqueFace = new FontFace(spec.id, url, {
        weight: spec.weight,
        style: 'normal',
        display: 'block',
      });
      const sharedFace = new FontFace(spec.sharedFamily, url, {
        weight: spec.weight,
        style: 'normal',
        display: 'block',
      });
      return [
        uniqueFace.load().then((loaded) => {
          document.fonts.add(loaded);
        }),
        sharedFace.load().then((loaded) => {
          document.fonts.add(loaded);
        }),
      ];
    })
  ).then(() => undefined);

  return fontsLoadPromise;
};

export const useLoadLocalFonts = (): boolean => {
  const [handle] = useState(() => delayRender('Loading local Kanit and Archivo fonts'));
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    ensureFontsLoaded()
      .then(() => {
        if (active) {
          setLoaded(true);
        }
        continueRender(handle);
      })
      .catch((err) => {
        console.error('Font load error:', err);
        continueRender(handle);
      });
    return () => {
      active = false;
    };
  }, [handle]);

  return loaded;
};
