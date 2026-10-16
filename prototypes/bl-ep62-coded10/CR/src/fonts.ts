import { useEffect, useState } from "react";
import { continueRender, delayRender, staticFile } from "remotion";

export interface FontSpec {
  family: string;
  file: string;
  format: "woff2" | "truetype";
}

export const FONT_SPECS: FontSpec[] = [
  { family: "Kanit800_1", file: "fonts/kanit-800-1bf17218.woff2", format: "woff2" },
  { family: "Kanit800_2", file: "fonts/kanit-800-aa86a0cb.woff2", format: "woff2" },
  { family: "Kanit800_3", file: "fonts/kanit-800-f57eab15.woff2", format: "woff2" },
  { family: "Kanit800_4", file: "fonts/kanit-800-f99e92e2.woff2", format: "woff2" },
  { family: "Kanit600_1", file: "fonts/kanit-600-0c71a5b8.woff2", format: "woff2" },
  { family: "Kanit600_2", file: "fonts/kanit-600-9895ee29.woff2", format: "woff2" },
  { family: "Kanit600_3", file: "fonts/kanit-600-b4b6e60e.woff2", format: "woff2" },
  { family: "Kanit600_4", file: "fonts/kanit-600-fc0bae07.woff2", format: "woff2" },
  { family: "Archivo800_1", file: "fonts/archivo-800-10d9bd15.woff2", format: "woff2" },
  { family: "Archivo800_2", file: "fonts/archivo-800-23599068.woff2", format: "woff2" },
  { family: "Archivo800_3", file: "fonts/archivo-800-87937726.woff2", format: "woff2" },
  { family: "DejaVuMono", file: "fonts/DejaVuSansMono.ttf", format: "truetype" },
  { family: "DejaVuMonoBold", file: "fonts/DejaVuSansMono-Bold.ttf", format: "truetype" },
];

export const FONT_FACE_CSS = FONT_SPECS.map(
  (f) => `
@font-face {
  font-family: '${f.family}';
  src: url('${staticFile(f.file)}') format('${f.format}');
  font-weight: normal;
  font-style: normal;
  font-display: block;
}`
).join("\n");

export const FONTS = {
  kanit800: "'Kanit800_1', 'Kanit800_2', 'Kanit800_3', 'Kanit800_4', sans-serif",
  kanit600: "'Kanit600_1', 'Kanit600_2', 'Kanit600_3', 'Kanit600_4', sans-serif",
  archivo800:
    "'Archivo800_1', 'Archivo800_2', 'Archivo800_3', 'Kanit800_1', 'Kanit800_2', 'Kanit800_3', 'Kanit800_4', sans-serif",
  mono: "'DejaVuMono', 'Kanit600_1', 'Kanit600_2', 'Kanit600_3', 'Kanit600_4', monospace",
  monoBold:
    "'DejaVuMonoBold', 'DejaVuMono', 'Kanit600_1', 'Kanit600_2', 'Kanit600_3', 'Kanit600_4', monospace",
};

export const useLoadFonts = (): boolean => {
  const [handle] = useState(() => delayRender("Loading custom fonts"));
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const loadAll = async () => {
      try {
        await Promise.all(
          FONT_SPECS.map(async (spec) => {
            const face = new FontFace(spec.family, `url('${staticFile(spec.file)}')`);
            const loadedFace = await face.load();
            document.fonts.add(loadedFace);
          })
        );
        await document.fonts.ready;
      } catch (err) {
        console.error("Font load error:", err);
      } finally {
        if (!cancelled) {
          setLoaded(true);
          continueRender(handle);
        }
      }
    };
    loadAll();
    return () => {
      cancelled = true;
    };
  }, [handle]);

  return loaded;
};
