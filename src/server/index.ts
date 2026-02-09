import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import path from 'path';

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer);

const PORT = process.env.PORT || 3000;

// Serve static files
app.use(express.static(path.join(__dirname, '../../public')));

// Store active rooms and users
const rooms = new Map<string, Set<string>>();

io.on('connection', (socket) => {
  console.log(`User connected: ${socket.id}`);

  // Handle joining a room
  socket.on('join-room', (roomId: string) => {
    console.log(`User ${socket.id} joining room ${roomId}`);
    
    // Add user to room
    if (!rooms.has(roomId)) {
      rooms.set(roomId, new Set());
    }
    const room = rooms.get(roomId)!;
    room.add(socket.id);
    
    // Join the socket.io room
    socket.join(roomId);
    
    // Notify other users in the room
    socket.to(roomId).emit('user-joined', socket.id);
    
    // Send list of existing users to the new user
    const existingUsers = Array.from(room).filter(id => id !== socket.id);
    socket.emit('existing-users', existingUsers);
  });

  // Handle WebRTC signaling - offer
  socket.on('offer', (data: { offer: any; to: string }) => {
    console.log(`Relaying offer from ${socket.id} to ${data.to}`);
    io.to(data.to).emit('offer', {
      offer: data.offer,
      from: socket.id
    });
  });

  // Handle WebRTC signaling - answer
  socket.on('answer', (data: { answer: any; to: string }) => {
    console.log(`Relaying answer from ${socket.id} to ${data.to}`);
    io.to(data.to).emit('answer', {
      answer: data.answer,
      from: socket.id
    });
  });

  // Handle ICE candidates
  socket.on('ice-candidate', (data: { candidate: any; to: string }) => {
    console.log(`Relaying ICE candidate from ${socket.id} to ${data.to}`);
    io.to(data.to).emit('ice-candidate', {
      candidate: data.candidate,
      from: socket.id
    });
  });

  // Handle leaving a room
  socket.on('leave-room', (roomId: string) => {
    console.log(`User ${socket.id} leaving room ${roomId}`);
    
    // Remove user from room
    const room = rooms.get(roomId);
    if (room) {
      room.delete(socket.id);
      
      // Notify other users in the room
      socket.to(roomId).emit('user-left', socket.id);
      
      // Leave the socket.io room
      socket.leave(roomId);
      
      // Clean up empty rooms
      if (room.size === 0) {
        rooms.delete(roomId);
      }
    }
  });

  // Handle disconnection
  socket.on('disconnect', () => {
    console.log(`User disconnected: ${socket.id}`);
    
    // Remove user from all rooms
    rooms.forEach((users, roomId) => {
      if (users.has(socket.id)) {
        users.delete(socket.id);
        // Notify other users in the room
        socket.to(roomId).emit('user-left', socket.id);
        
        // Clean up empty rooms
        if (users.size === 0) {
          rooms.delete(roomId);
        }
      }
    });
  });
});

httpServer.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
