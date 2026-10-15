import { useEffect, useState } from 'react';
import {
  continueRender,
  delayRender,
  getStaticFiles,
  staticFile,
} from 'remotion';

export const KANIT_FONT = '"Kanit", sans-serif';
export const ARCHIVO_FONT = '"Archivo", "Kanit", sans-serif';

type ParsedFont = {
  family: 'Kanit' | 'Archivo';
  weight: '600' | '800';
  src: string;
  name: string;
};

const parseFontFromFilename = (name: string, src: string): ParsedFont | null => {
  const lower = name.toLowerCase();
  if (!lower.includes('fonts/') && !lower.endsWith('.woff2')) {
    return null;
  }
  if (!/\.(woff2|woff|ttf|otf)$/i.test(lower)) {
    return null;
  }

  const family: 'Kanit' | 'Archivo' = lower.includes('archivo')
    ? 'Archivo'
    : 'Kanit';

  const is600 =
    lower.includes('600') ||
    lower.includes('semibold') ||
    lower.includes('semi-bold') ||
    lower.includes('semi_bold') ||
    lower.includes('medium');

  const weight: '600' | '800' = family === 'Archivo' ? '800' : is600 ? '600' : '800';

  return {
    family,
    weight,
    src,
    name,
  };
};

let fontLoadPromise: Promise<void> | null = null;
let fontsReadySync = false;

const loadAllFonts = async (): Promise<void> => {
  if (typeof document === 'undefined') {
    return;
  }

  const staticFiles = getStaticFiles();
  const discovered: ParsedFont[] = [];

  for (const file of staticFiles) {
    const resolvedSrc = file.name.startsWith('fonts/')
      ? staticFile(file.name)
      : file.src;
    const parsed = parseFontFromFilename(file.name, resolvedSrc);
    if (parsed) {
      discovered.push(parsed);
    }
  }

  if (discovered.length > 0) {
    const styleId = 'bl-ep62-local-fonts';
    if (!document.getElementById(styleId)) {
      const styleEl = document.createElement('style');
      styleEl.id = styleId;
      styleEl.textContent = discovered
        .map(
          (f) => `
@font-face {
  font-family: '${f.family}';
  src: url('${f.src}') format('woff2');
  font-weight: ${f.weight};
  font-style: normal;
  font-display: block;
}`
        )
        .join('\n');
      document.head.appendChild(styleEl);
    }

    if (typeof FontFace !== 'undefined' && document.fonts) {
      await Promise.all(
        discovered.map(async (f) => {
          try {
            const face = new FontFace(f.family, `url("${f.src}")`, {
              weight: f.weight,
              style: 'normal',
              display: 'block',
            });
            const loaded = await face.load();
            document.fonts.add(loaded);
          } catch {
            // Ignore individual subset load failure if already loaded via @font-face
          }
        })
      );
    }
  }

  if (document.fonts && document.fonts.ready) {
    await document.fonts.ready;
  }

  fontsReadySync = true;
};

export const useLoadFonts = (): boolean => {
  const [loaded, setLoaded] = useState<boolean>(() => fontsReadySync);
  const [handle] = useState<number | null>(() =>
    fontsReadySync ? null : delayRender('Loading Kanit and Archivo woff2 fonts')
  );

  useEffect(() => {
    if (handle === null) {
      return;
    }
    if (!fontLoadPromise) {
      fontLoadPromise = loadAllFonts();
    }
    fontLoadPromise
      .then(() => {
        setLoaded(true);
        continueRender(handle);
      })
      .catch(() => {
        setLoaded(true);
        continueRender(handle);
      });
  }, [handle]);

  return loaded;
};

let measureCanvas: HTMLCanvasElement | null = null;

export const fitFontSize = ({
  text,
  targetSize,
  maxWidth,
  fontFamily = 'Kanit',
  fontWeight = 800,
}: {
  text: string;
  targetSize: number;
  maxWidth: number;
  fontFamily?: 'Kanit' | 'Archivo';
  fontWeight?: 600 | 800;
}): number => {
  if (typeof document !== 'undefined') {
    if (!measureCanvas) {
      measureCanvas = document.createElement('canvas');
    }
    const ctx = measureCanvas.getContext('2d');
    if (ctx) {
      ctx.font = `${fontWeight} ${targetSize}px "${fontFamily}", sans-serif`;
      const measured = ctx.measureText(text).width;
      if (measured > maxWidth && measured > 0) {
        return Math.floor(targetSize * (maxWidth / measured) * 0.97);
      }
      return targetSize;
    }
  }

  const estimatedWidth = text.length * targetSize * 0.52;
  if (estimatedWidth > maxWidth && estimatedWidth > 0) {
    return Math.floor(targetSize * (maxWidth / estimatedWidth));
  }
  return targetSize;
};
