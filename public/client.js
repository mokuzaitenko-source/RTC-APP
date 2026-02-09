// Configuration for STUN servers (helps with NAT traversal)
const configuration = {
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' }
  ]
};

// State management
let socket;
let localStream;
let peerConnections = new Map(); // Map of peerId -> RTCPeerConnection
let currentRoom = null;

// DOM elements
const roomInput = document.getElementById('roomInput');
const joinBtn = document.getElementById('joinBtn');
const leaveBtn = document.getElementById('leaveBtn');
const localVideo = document.getElementById('localVideo');
const videoGrid = document.getElementById('videoGrid');
const statusDiv = document.getElementById('status');

// Initialize socket connection
function initSocket() {
  socket = io();

  // Handle existing users in the room
  socket.on('existing-users', async (userIds) => {
    console.log('Existing users:', userIds);
    for (const userId of userIds) {
      await createPeerConnection(userId, true);
    }
  });

  // Handle new user joining
  socket.on('user-joined', async (userId) => {
    console.log('User joined:', userId);
    updateStatus(`User ${userId.substring(0, 8)} joined the room`, 'connected');
    await createPeerConnection(userId, false);
  });

  // Handle receiving an offer
  socket.on('offer', async ({ offer, from }) => {
    console.log('Received offer from:', from);
    const pc = peerConnections.get(from);
    if (pc) {
      await pc.setRemoteDescription(new RTCSessionDescription(offer));
      const answer = await pc.createAnswer();
      await pc.setLocalDescription(answer);
      socket.emit('answer', { answer, to: from });
    }
  });

  // Handle receiving an answer
  socket.on('answer', async ({ answer, from }) => {
    console.log('Received answer from:', from);
    const pc = peerConnections.get(from);
    if (pc) {
      await pc.setRemoteDescription(new RTCSessionDescription(answer));
    }
  });

  // Handle receiving ICE candidates
  socket.on('ice-candidate', async ({ candidate, from }) => {
    console.log('Received ICE candidate from:', from);
    const pc = peerConnections.get(from);
    if (pc) {
      await pc.addIceCandidate(new RTCIceCandidate(candidate));
    }
  });

  // Handle user leaving
  socket.on('user-left', (userId) => {
    console.log('User left:', userId);
    updateStatus(`User ${userId.substring(0, 8)} left the room`, 'error');
    removePeer(userId);
  });
}

// Get local media stream
async function getLocalStream() {
  try {
    localStream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: true
    });
    localVideo.srcObject = localStream;
    updateStatus('Camera and microphone access granted', 'connected');
    return true;
  } catch (error) {
    console.error('Error accessing media devices:', error);
    updateStatus('Failed to access camera/microphone. Please grant permissions.', 'error');
    return false;
  }
}

// Create peer connection
async function createPeerConnection(peerId, isInitiator) {
  console.log(`Creating peer connection with ${peerId}, initiator: ${isInitiator}`);
  
  const pc = new RTCPeerConnection(configuration);
  peerConnections.set(peerId, pc);

  // Add local stream tracks to peer connection
  localStream.getTracks().forEach(track => {
    pc.addTrack(track, localStream);
  });

  // Handle ICE candidates
  pc.onicecandidate = (event) => {
    if (event.candidate) {
      socket.emit('ice-candidate', {
        candidate: event.candidate,
        to: peerId
      });
    }
  };

  // Handle incoming remote stream
  pc.ontrack = (event) => {
    console.log('Received remote track from:', peerId);
    addRemoteVideo(peerId, event.streams[0]);
  };

  // Handle connection state changes
  pc.onconnectionstatechange = () => {
    console.log(`Connection state with ${peerId}:`, pc.connectionState);
    if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed') {
      removePeer(peerId);
    }
  };

  // If initiator, create and send offer
  if (isInitiator) {
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);
    socket.emit('offer', { offer, to: peerId });
  }

  return pc;
}

// Add remote video to the grid
function addRemoteVideo(peerId, stream) {
  // Remove existing video if any
  const existingVideo = document.getElementById(`video-${peerId}`);
  if (existingVideo) {
    existingVideo.parentElement.remove();
  }

  // Create new video element
  const container = document.createElement('div');
  container.className = 'video-container';
  
  const video = document.createElement('video');
  video.id = `video-${peerId}`;
  video.autoplay = true;
  video.playsinline = true;
  video.srcObject = stream;
  
  const label = document.createElement('div');
  label.className = 'video-label';
  label.textContent = `Remote: ${peerId.substring(0, 8)}`;
  
  container.appendChild(video);
  container.appendChild(label);
  videoGrid.appendChild(container);
}

// Remove peer connection and video
function removePeer(peerId) {
  const pc = peerConnections.get(peerId);
  if (pc) {
    pc.close();
    peerConnections.delete(peerId);
  }

  const videoElement = document.getElementById(`video-${peerId}`);
  if (videoElement) {
    videoElement.parentElement.remove();
  }
}

// Update status message
function updateStatus(message, type = '') {
  statusDiv.textContent = message;
  statusDiv.className = `status ${type}`;
}

// Join room
async function joinRoom() {
  const roomId = roomInput.value.trim();
  
  if (!roomId) {
    updateStatus('Please enter a room name', 'error');
    return;
  }

  // Get local stream first
  const success = await getLocalStream();
  if (!success) return;

  // Join the room
  currentRoom = roomId;
  socket.emit('join-room', roomId);
  
  // Update UI
  roomInput.disabled = true;
  joinBtn.disabled = true;
  leaveBtn.disabled = false;
  updateStatus(`Connected to room: ${roomId}`, 'connected');
}

// Leave room
function leaveRoom() {
  // Close all peer connections
  peerConnections.forEach((pc, peerId) => {
    removePeer(peerId);
  });

  // Stop local stream
  if (localStream) {
    localStream.getTracks().forEach(track => track.stop());
    localVideo.srcObject = null;
    localStream = null;
  }

  // Disconnect from socket room (will trigger server-side cleanup)
  if (socket) {
    socket.disconnect();
    socket.connect();
  }

  // Reset UI
  currentRoom = null;
  roomInput.disabled = false;
  roomInput.value = '';
  joinBtn.disabled = false;
  leaveBtn.disabled = true;
  updateStatus('Left the room. Enter a room name to start', '');
}

// Event listeners
joinBtn.addEventListener('click', joinRoom);
leaveBtn.addEventListener('click', leaveRoom);
roomInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    joinRoom();
  }
});

// Initialize
initSocket();
