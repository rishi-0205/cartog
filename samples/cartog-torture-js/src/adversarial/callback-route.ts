/** Route registration with callback kwarg. */
import { Server } from "socket.io";
const io = new Server();
export function register() {
  io.on("connection", (socket) => socket.on("join", (room) => socket.join(room)));
}
