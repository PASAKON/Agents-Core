export type NodeStatus = "online" | "busy" | "sleeping";

export interface FleetNode {
  id: string;
  name: string;
  platform: string;
  location: string;
  status: NodeStatus;
  cpu: number;
  memory: number;
  sessions: number;
  capabilities: string[];
}

export interface Room {
  id: string;
  name: string;
  unread?: number;
  private?: boolean;
}

export interface Message {
  id: string;
  author: string;
  role: string;
  accent: string;
  initials: string;
  time: string;
  body: string;
  mentions?: string[];
  event?: {
    label: string;
    detail: string;
    status: "running" | "done" | "waiting";
  };
}
