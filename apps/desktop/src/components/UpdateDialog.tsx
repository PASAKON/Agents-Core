import { useState } from "react";
import { CheckCircle2, Download, RefreshCw, ShieldCheck, X } from "lucide-react";
import { checkForAppUpdate, installAppUpdate, isNativeApp, type UpdateInfo } from "../services/updater";

type Phase = "idle" | "checking" | "current" | "available" | "downloading" | "complete" | "error";

export function UpdateDialog({ onClose }: { onClose: () => void }) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [info, setInfo] = useState<UpdateInfo | null>(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const native = isNativeApp();

  async function checkNow() {
    setPhase("checking");
    setError("");
    try {
      if (!native) {
        await new Promise((resolve) => window.setTimeout(resolve, 700));
        setInfo({ currentVersion: "0.1.0", version: "0.2.0", notes: "Demo release: Fleet controls, permission review, and signed automatic updates." });
        setPhase("available");
        return;
      }
      const result = await checkForAppUpdate();
      setInfo(result);
      setPhase(result ? "available" : "current");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
      setPhase("error");
    }
  }

  async function installNow() {
    setPhase("downloading");
    setProgress(0);
    try {
      if (!native) {
        for (const value of [14, 31, 53, 76, 100]) {
          await new Promise((resolve) => window.setTimeout(resolve, 220));
          setProgress(value);
        }
        setPhase("complete");
        return;
      }
      await installAppUpdate(setProgress);
      setPhase("complete");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
      setPhase("error");
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="update-dialog" role="dialog" aria-modal="true" aria-labelledby="update-title">
        <header><div className="update-mark"><RefreshCw size={20} /></div><div><span>MOONIEX DESKTOP</span><h2 id="update-title">App updates</h2></div><button onClick={onClose} aria-label="Close"><X size={17} /></button></header>
        {!native ? <div className="demo-notice">Browser Demo — no installer will be changed on this screen.</div> : null}
        <div className="update-body">
          {phase === "idle" ? <><ShieldCheck size={34} /><h3>Signed, seamless updates</h3><p>MoonieX verifies every release before installing it. Your rooms, Core, Nodes and active work remain intact.</p></> : null}
          {phase === "checking" ? <><RefreshCw className="spin" size={34} /><h3>Checking GitHub Releases…</h3><p>Comparing this installation with the latest signed Windows release.</p></> : null}
          {phase === "current" ? <><CheckCircle2 className="success" size={34} /><h3>MoonieX is up to date</h3><p>You already have the newest stable version.</p></> : null}
          {phase === "available" && info ? <><Download className="available" size={34} /><h3>MoonieX {info.version} is ready</h3><p>{info.notes}</p><div className="version-route"><span>v{info.currentVersion}</span><i /><span>v{info.version}</span></div></> : null}
          {phase === "downloading" ? <><Download className="available" size={34} /><h3>Downloading update… {progress}%</h3><p>The signed package will install automatically. MoonieX will restart once on Windows.</p><div className="update-progress"><span style={{ width: `${progress}%` }} /></div></> : null}
          {phase === "complete" ? <><CheckCircle2 className="success" size={34} /><h3>Demo update complete</h3><p>In the installed Windows App, the signed installer restarts MoonieX into the new version—no uninstall required.</p></> : null}
          {phase === "error" ? <><X className="error-icon" size={34} /><h3>Update check failed</h3><p>{error}</p></> : null}
        </div>
        <footer>
          <span><ShieldCheck size={13} /> Ed25519 signature verification</span>
          <div><button className="secondary" onClick={onClose}>Not now</button>{phase === "available" ? <button className="primary" onClick={installNow}>Download & update</button> : <button className="primary" disabled={phase === "checking" || phase === "downloading"} onClick={checkNow}>{phase === "error" ? "Try again" : "Check for updates"}</button>}</div>
        </footer>
      </section>
    </div>
  );
}
