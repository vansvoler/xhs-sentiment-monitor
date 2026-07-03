"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { WsMessage } from "@/types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws";

export type ConnectionStatus = "connecting" | "connected" | "disconnected";

type Subscriber = (msg: WsMessage) => void;

interface WsContextValue {
  status: ConnectionStatus;
  subscribe: (fn: Subscriber) => () => void;
}

const WsContext = createContext<WsContextValue | null>(null);

// 单连接 Provider：整棵子树共享一条 WebSocket，多个组件按需订阅
export function WebSocketProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const subscribers = useRef<Set<Subscriber>>(new Set());
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let closed = false;

    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;
      setStatus("connecting");

      ws.onopen = () => setStatus("connected");
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data as string) as WsMessage;
          if (msg.type !== "heartbeat") {
            subscribers.current.forEach((fn) => fn(msg));
          }
        } catch {
          // 忽略非 JSON 消息
        }
      };
      ws.onclose = () => {
        setStatus("disconnected");
        if (!closed) reconnectTimer.current = setTimeout(connect, 5000);
      };
      ws.onerror = () => ws.close();
    }

    connect();
    return () => {
      closed = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, []);

  const subscribe = useCallback((fn: Subscriber) => {
    subscribers.current.add(fn);
    return () => {
      subscribers.current.delete(fn);
    };
  }, []);

  return (
    <WsContext.Provider value={{ status, subscribe }}>
      {children}
    </WsContext.Provider>
  );
}

// 订阅实时消息；返回连接状态。签名与旧版一致，消费方无需改动
export function useWebSocket(onMessage: (msg: WsMessage) => void): ConnectionStatus {
  const ctx = useContext(WsContext);
  useEffect(() => {
    if (!ctx) return;
    return ctx.subscribe(onMessage);
  }, [ctx, onMessage]);
  return ctx?.status ?? "connecting";
}
