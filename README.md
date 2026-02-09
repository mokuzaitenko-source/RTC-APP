# RTC-APP

A Real-Time Communication (RTC) application built with WebRTC, Socket.io, and Node.js. This application enables peer-to-peer video and audio communication through a web browser.

## Features

- 🎥 Real-time video and audio streaming
- 👥 Multi-user support in rooms
- 🔄 Automatic peer connection management
- 🌐 WebRTC-based peer-to-peer communication
- 🎨 Clean and responsive UI

## Technology Stack

- **Backend**: Node.js, Express, Socket.io
- **Frontend**: Vanilla JavaScript, WebRTC API
- **Language**: TypeScript

## Prerequisites

- Node.js (v16 or higher)
- npm or yarn
- Modern web browser with WebRTC support

## Installation

1. Clone the repository:
```bash
git clone https://github.com/mokuzaitenko-source/RTC-APP.git
cd RTC-APP
```

2. Install dependencies:
```bash
npm install
```

3. Build the TypeScript code:
```bash
npm run build
```

## Usage

### Development Mode

Run the server in development mode with hot reloading:

```bash
npm run dev
```

### Production Mode

1. Build the project:
```bash
npm run build
```

2. Start the server:
```bash
npm start
```

The application will be available at `http://localhost:3000`

## How to Use

1. Open the application in your web browser
2. Enter a room name in the input field
3. Click "Join Room" to enter the video chat
4. Grant camera and microphone permissions when prompted
5. Share the same room name with others to connect
6. Click "Leave Room" to exit the video chat

## Architecture

### Server-side (Signaling Server)

- Express server serves static files and handles HTTP requests
- Socket.io manages WebSocket connections for signaling
- Handles room management and relays WebRTC signaling messages

### Client-side

- WebRTC API for peer-to-peer connections
- Socket.io client for signaling communication
- Manages local and remote media streams
- Handles ICE candidate exchange and SDP offer/answer

## Configuration

The application uses public STUN servers by default. For production use, consider configuring your own TURN servers in `/public/client.js`:

```javascript
const configuration = {
  iceServers: [
    { urls: 'stun:your-stun-server.com:port' },
    { 
      urls: 'turn:your-turn-server.com:port',
      username: 'username',
      credential: 'password'
    }
  ]
};
```

## Environment Variables

- `PORT`: Server port (default: 3000)

Example:
```bash
PORT=8080 npm start
```

## License

MIT
