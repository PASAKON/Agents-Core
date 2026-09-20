import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  Activity,
  Bell,
  Bot,
  Boxes,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Command,
  Cpu,
  FolderKanban,
  Gauge,
  Hash,
  LockKeyhole,
  Menu,
  MessageSquareText,
  Mic,
  Moon,
  MonitorCog,
  MoreHorizontal,
  Network,
  Paperclip,
  Plus,
  Search,
  Send,
  Settings2,
  ShieldCheck,
  Sparkles,
  Sun,
  TerminalSquare,
  Users,
  X,
  Zap,
} from "lucide-react";
import { fleet, initialMessages, rooms } from "./data/demo";
import type { FleetNode, Message, NodeStatus } from "./types";
import { UpdateDialog } from "./components/UpdateDialog";

const statusCopy: Record<NodeStatus, string> = {
  online: "Ready",
  busy: "Working",
  sleeping: "Sleeping",
};

type Theme = "light" | "dark";

function BrandMark() {
  return (
    <div className="brand-mark" aria-hidden="true">
      <span className="brand-orbit brand-orbit-one" />
      <span className="brand-orbit brand-orbit-two" />
      <span className="brand-core" />
    </div>
  );
}

function Avatar({ message }: { message: Message }) {
  return (
    <div className="avatar" style={{ "--avatar-accent": message.accent } as React.CSSProperties}>
      {message.initials}
      <span className="avatar-status" />
    </div>
  );
}

function Progress({ value, tone }: { value: number; tone?: "warm" }) {
  return (
    <div className="meter" aria-label={`${value}%`}>
      <span className={tone === "warm" ? "meter-warm" : ""} style={{ width: `${value}%` }} />
    </div>
  );
}

function NodeCard({ node, selected, onSelect }: { node: FleetNode; selected: boolean; onSelect: () => void }) {
  return (
    <button className={`node-card ${selected ? "selected" : ""}`} onClick={onSelect}>
      <div className="node-topline">
        <div className="node-icon"><MonitorCog size={16} /></div>
        <div className="node-title">
          <strong>{node.name}</strong>
          <span>{node.platform}</span>
        </div>
        <span className={`status-dot ${node.status}`} title={statusCopy[node.status]} />
      </div>
      <div className="node-stats">
        <span>CPU {node.cpu}%</span>
        <span>RAM {node.memory}%</span>
        <span>{node.sessions} live</span>
      </div>
      <Progress value={Math.max(node.cpu, node.memory)} tone={node.cpu > 60 ? "warm" : undefined} />
    </button>
  );
}

function App() {
  const [activeRoom, setActiveRoom] = useState("command");
  const [messages, setMessages] = useState(initialMessages);
  const [draft, setDraft] = useState("");
  const [selectedNode, setSelectedNode] = useState(fleet[1].id);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activityOpen, setActivityOpen] = useState(true);
  const [updateOpen, setUpdateOpen] = useState(false);
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = window.localStorage.getItem("mooniex-theme");
    return saved === "dark" ? "dark" : "light";
  });

  useEffect(() => {
    window.localStorage.setItem("mooniex-theme", theme);
    document.documentElement.style.colorScheme = theme;
  }, [theme]);

  const room = useMemo(() => rooms.find((item) => item.id === activeRoom) ?? rooms[0], [activeRoom]);
  const onlineCount = fleet.filter((node) => node.status !== "sleeping").length;

  function submitMessage(event: FormEvent) {
    event.preventDefault();
    const value = draft.trim();
    if (!value) return;
    setMessages((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        author: "You",
        role: "Owner",
        accent: "#efc06a",
        initials: "PK",
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        body: value,
      },
    ]);
    setDraft("");
  }

  return (
    <div className={`app-shell ${rightPanelOpen ? "" : "right-closed"}`} data-theme={theme}>
      <header className="titlebar" data-tauri-drag-region>
        <div className="window-controls" aria-hidden="true">
          <span className="window-dot close" /><span className="window-dot minimize" /><span className="window-dot maximize" />
        </div>
        <div className="titlebar-center" data-tauri-drag-region>
          <BrandMark /> <span>MoonieX</span><span className="preview-pill">PREVIEW</span>
        </div>
        <div className="titlebar-actions">
          <button className="icon-button mobile-only" onClick={() => setSidebarOpen((value) => !value)} aria-label="Toggle menu"><Menu size={17} /></button>
          <button className="icon-button theme-toggle" onClick={() => setTheme((value) => value === "light" ? "dark" : "light")} aria-label={`Switch to ${theme === "light" ? "dark" : "light"} appearance`} title={`Use ${theme === "light" ? "dark" : "light"} appearance`}>
            {theme === "light" ? <Moon size={16} /> : <Sun size={16} />}
          </button>
          <button className="icon-button" aria-label="Search"><Search size={16} /></button>
          <button className="icon-button notification" aria-label="Notifications"><Bell size={16} /><span /></button>
        </div>
      </header>

      <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="workspace-switcher">
          <div className="workspace-logo"><BrandMark /></div>
          <div><span>WORKSPACE</span><strong>MoonieX Lab</strong></div>
          <ChevronDown size={15} />
        </div>

        <nav className="primary-nav">
          <button className="nav-item active"><Gauge size={17} /><span>Mission Control</span><kbd>⌘1</kbd></button>
          <button className="nav-item"><Bot size={17} /><span>Agents</span><span className="nav-count">7</span></button>
          <button className="nav-item"><Network size={17} /><span>Nodes</span><span className="live-count"><i />{onlineCount}</span></button>
        </nav>

        <div className="nav-section">
          <div className="section-title"><span>ROOMS</span><button aria-label="Add room"><Plus size={14} /></button></div>
          {rooms.map((item) => (
            <button key={item.id} className={`nav-item room ${activeRoom === item.id ? "active" : ""}`} onClick={() => { setActiveRoom(item.id); setSidebarOpen(false); }}>
              {item.private ? <LockKeyhole size={15} /> : <Hash size={15} />}
              <span>{item.name}</span>
              {item.unread ? <span className="unread-count">{item.unread}</span> : null}
            </button>
          ))}
        </div>

        <div className="nav-section">
          <div className="section-title"><span>PROJECTS</span><button aria-label="Add project"><Plus size={14} /></button></div>
          <button className="nav-item"><span className="project-dot violet" /><span>MoonieX Core</span></button>
          <button className="nav-item"><span className="project-dot mint" /><span>Desktop App</span></button>
          <button className="nav-item"><span className="project-dot coral" /><span>Node Network</span></button>
        </div>

        <div className="sidebar-bottom">
          <button className="nav-item"><CircleHelp size={17} /><span>Help & shortcuts</span></button>
          <button className="profile-row">
            <span className="profile-avatar">PK</span>
            <span><strong>Pasakon</strong><small>Owner</small></span>
            <MoreHorizontal size={16} />
          </button>
        </div>
      </aside>

      <main className="main-panel">
        <header className="room-header">
          <div className="room-title-wrap">
            <div className="room-symbol"><Hash size={18} /></div>
            <div><h1>{room.name}</h1><p>Coordinate people, agents and machines in one place.</p></div>
          </div>
          <div className="room-actions">
            <div className="presence-stack"><span>CT</span><span>CX</span><span>CL</span><span className="more">+4</span></div>
            <button className="header-button"><Users size={16} /><span>7</span></button>
            <button className={`header-button panel-toggle ${rightPanelOpen ? "active" : ""}`} onClick={() => setRightPanelOpen((value) => !value)}><Boxes size={16} /><span>Fleet</span></button>
          </div>
        </header>

        <section className="conversation">
          <div className="day-divider"><span>Today</span></div>
          {messages.map((message) => (
            <article className="message" key={message.id}>
              <Avatar message={message} />
              <div className="message-content">
                <div className="message-meta"><strong>{message.author}</strong><span className="role-pill">{message.role}</span><time>{message.time}</time></div>
                <p>{message.body}</p>
                {message.mentions?.length ? <div className="mention-row">{message.mentions.map((mention) => <span key={mention}>{mention}</span>)}</div> : null}
                {message.event ? (
                  <div className={`event-card ${message.event.status}`}>
                    <span className="event-icon">{message.event.status === "running" ? <Zap size={16} /> : <ShieldCheck size={16} />}</span>
                    <span><strong>{message.event.label}</strong><small>{message.event.detail}</small></span>
                    <button>View mission <ChevronRight size={14} /></button>
                  </div>
                ) : null}
              </div>
            </article>
          ))}
        </section>

        <div className={`activity-dock ${activityOpen ? "open" : ""}`}>
          <button className="activity-summary" onClick={() => setActivityOpen((value) => !value)}>
            <span className="pulse-ring"><Activity size={14} /></span>
            <strong>3 agents working</strong><span>·</span><span>5 live sessions across 3 nodes</span>
            <ChevronDown size={15} />
          </button>
          {activityOpen ? (
            <div className="activity-jobs">
              <span><i className="agent-swatch purple" />CTO <small>Planning architecture</small></span>
              <span><i className="agent-swatch mint" />Codex <small>Building desktop UI</small></span>
              <span><i className="agent-swatch coral" />Claude <small>Reviewing UX</small></span>
            </div>
          ) : null}
        </div>

        <form className="composer" onSubmit={submitMessage}>
          <div className="composer-box">
            <textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder={`Message #${room.name} — use @ to delegate`} rows={2} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} />
            <div className="composer-tools">
              <div><button type="button" aria-label="Attach"><Paperclip size={17} /></button><button type="button" aria-label="Voice"><Mic size={17} /></button><button type="button" className="agent-button"><Sparkles size={15} /> Delegate</button></div>
              <button className="send-button" type="submit" disabled={!draft.trim()}><Send size={16} /></button>
            </div>
          </div>
          <p><Command size={11} /> Enter to send · Shift + Enter for a new line</p>
        </form>
      </main>

      <aside className={`right-panel ${rightPanelOpen ? "open" : ""}`}>
        <div className="panel-heading"><div><span>FLEET</span><strong>MoonieX Nodes</strong></div><button className="icon-button" onClick={() => setRightPanelOpen(false)} aria-label="Close fleet"><X size={16} /></button></div>
        <div className="fleet-summary">
          <div><strong>{onlineCount}</strong><span>available</span></div><div><strong>5</strong><span>sessions</span></div><div><strong>12</strong><span>capabilities</span></div>
        </div>
        <div className="node-list">
          {fleet.map((node) => <NodeCard key={node.id} node={node} selected={selectedNode === node.id} onSelect={() => setSelectedNode(node.id)} />)}
        </div>
        <section className="capability-panel">
          <div className="panel-section-title"><span>ACTIVE ON SELECTED NODE</span><Settings2 size={14} /></div>
          <div className="capability-list">
            <div><span className="capability-icon terminal"><TerminalSquare size={15} /></span><span><strong>Terminal</strong><small>Scoped workspace access</small></span><i className="permission allowed">Allowed</i></div>
            <div><span className="capability-icon computer"><MonitorCog size={15} /></span><span><strong>Computer Use</strong><small>Ask before control</small></span><i className="permission ask">Ask</i></div>
            <div><span className="capability-icon mcp"><Cpu size={15} /></span><span><strong>MCP tools</strong><small>6 connections</small></span><i className="permission allowed">Allowed</i></div>
          </div>
        </section>
        <button className="manage-button"><Settings2 size={15} /> Manage nodes & permissions</button>
        <div className="core-status"><span><i />Core connected</span><button onClick={() => setUpdateOpen(true)}>v0.1.0 · Check update</button></div>
      </aside>
      {updateOpen ? <UpdateDialog onClose={() => setUpdateOpen(false)} /> : null}
    </div>
  );
}

export default App;
