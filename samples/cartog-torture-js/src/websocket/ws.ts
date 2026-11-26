/** ws message handler spine. */
import WebSocket from "ws";
const w = new WebSocket("ws://localhost");
w.on("message", (d) => onMessage(String(d)));
export function onMessage(data: string): void { console.log(data); }
