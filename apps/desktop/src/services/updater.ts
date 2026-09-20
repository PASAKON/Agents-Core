import { check, type Update } from "@tauri-apps/plugin-updater";

let pendingUpdate: Update | null = null;

export interface UpdateInfo {
  currentVersion: string;
  version: string;
  notes: string;
}

export function isNativeApp(): boolean {
  return "__TAURI_INTERNALS__" in window;
}

export async function checkForAppUpdate(): Promise<UpdateInfo | null> {
  pendingUpdate = await check({ timeout: 15_000 });
  if (!pendingUpdate) return null;
  return {
    currentVersion: pendingUpdate.currentVersion,
    version: pendingUpdate.version,
    notes: pendingUpdate.body ?? "A new MoonieX Desktop release is ready.",
  };
}

export async function installAppUpdate(onProgress: (percentage: number) => void): Promise<void> {
  if (!pendingUpdate) throw new Error("No update has been selected");
  let downloaded = 0;
  let total = 0;
  await pendingUpdate.downloadAndInstall((event) => {
    if (event.event === "Started") {
      total = event.data.contentLength ?? 0;
      onProgress(0);
    } else if (event.event === "Progress") {
      downloaded += event.data.chunkLength;
      onProgress(total > 0 ? Math.min(99, Math.round((downloaded / total) * 100)) : 50);
    } else {
      onProgress(100);
    }
  }, { restartAfterInstall: true });
}
