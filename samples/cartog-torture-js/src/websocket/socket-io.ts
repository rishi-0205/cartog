/** socket.io connection + room broadcast spine. */
import { Server } from "socket.io";
const io = new Server();
io.on("connection", (socket) => socket.on("join", (room) => socket.join(room)));
export function broadcast(room: string, data: unknown): void { io.to(room).emit("msg", data); }
