var crypto = require('crypto');

var rooms = new Map();
var ROOM_TTL_MS = 1000 * 60 * 60 * 8;
var MAX_EVENTS = 60;
var NAMES = ['Alice', 'Bob', 'Carol', 'Dave', 'Eve', 'Frank', 'Grace', 'Heidi', 'Ivan', 'Judy', 'Mallory', 'Niaj', 'Olivia', 'Pat', 'Quinn', 'Rita'];

function makeId(size) {
  return crypto.randomBytes(size).toString('hex');
}

function makeRoomCode() {
  var alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  var code = '';
  for (var i = 0; i < 6; i++) {
    code += alphabet[Math.floor(Math.random() * alphabet.length)];
  }
  return code;
}

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function satoshiToBtc(sat) {
  return (sat / 1e8).toFixed(6);
}

function pickRandomName(except) {
  var pick = NAMES[randomInt(0, NAMES.length - 1)];
  if (pick === except) {
    return pickRandomName(except);
  }
  return pick;
}

function makeGenesisBlocks() {
  return [
    { index: 1, hash: '0000f7d91d245bb8b64b13ce9f9938ab', previousHash: 'GENESIS', minedBy: 'Network', txCount: 4, totalFees: 0, rewardBtc: '6.250000', minedAt: Date.now() - 240000 },
    { index: 2, hash: '0000318dca7f73ec70f2b57c1f32d0fe', previousHash: '0000f7d91d245bb8b64b13ce9f9938ab', minedBy: 'Network', txCount: 5, totalFees: 0, rewardBtc: '6.250000', minedAt: Date.now() - 120000 }
  ];
}

function pushEvent(room, type, actor, message, detail) {
  room.events.unshift({
    id: makeId(6),
    type: type,
    actor: actor,
    message: message,
    detail: detail || '',
    createdAt: Date.now()
  });
  if (room.events.length > MAX_EVENTS) {
    room.events.length = MAX_EVENTS;
  }
}

function notify(room, type, payload) {
  var data = JSON.stringify(payload);
  room.streams.forEach(function(stream) {
    try {
      stream.write('event: ' + type + '\n');
      stream.write('data: ' + data + '\n\n');
    } catch (err) {
      room.streams.delete(stream);
    }
  });
}

function serializeRoom(room) {
  var participants = Array.from(room.participants.values()).map(function(item) {
    return {
      id: item.id,
      displayName: item.displayName,
      role: item.role,
      score: item.score,
      joinedAt: item.joinedAt,
      lastSeenAt: item.lastSeenAt
    };
  }).sort(function(a, b) {
    if (a.role !== b.role) {
      return a.role === 'teacher' ? -1 : 1;
    }
    return b.score.blocksMined - a.score.blocksMined || b.score.feesWon - a.score.feesWon || a.displayName.localeCompare(b.displayName);
  });

  return {
    code: room.code,
    title: room.title,
    teacherName: room.teacherName,
    difficulty: room.difficulty,
    createdAt: room.createdAt,
    participants: participants,
    mempool: room.mempool.slice().sort(function(a, b) {
      return b.feeRate - a.feeRate || a.createdAt - b.createdAt;
    }),
    chain: room.chain.slice().sort(function(a, b) { return a.index - b.index; }),
    events: room.events.slice(),
    presence: {
      teachers: participants.filter(function(item) { return item.role === 'teacher'; }).length,
      students: participants.filter(function(item) { return item.role === 'student'; }).length
    }
  };
}

function broadcastRoom(room, reason) {
  notify(room, 'room:update', { reason: reason, room: serializeRoom(room) });
}

function createRandomTx(room, creatorName, overrides) {
  room.txCounter += 1;
  var feeRate = overrides && overrides.feeRate ? Math.max(1, parseInt(overrides.feeRate, 10) || 1) : randomInt(2, 160);
  var size = overrides && overrides.size ? Math.max(180, parseInt(overrides.size, 10) || 180) : randomInt(180, 640);
  var value = overrides && overrides.value ? Math.max(1000, parseInt(overrides.value, 10) || 1000) : randomInt(15000, 90000000);
  var from = creatorName || pickRandomName();
  return {
    id: room.txCounter,
    txid: crypto.createHash('sha256').update(room.code + ':' + Date.now() + ':' + Math.random()).digest('hex').substring(0, 16),
    from: from,
    to: overrides && overrides.to ? String(overrides.to) : pickRandomName(from),
    value: value,
    feeRate: feeRate,
    size: size,
    fee: feeRate * size,
    age: 0,
    createdBy: creatorName || 'system',
    createdAt: Date.now()
  };
}

function participantView(room, participant) {
  return {
    token: participant.token,
    participantId: participant.id,
    role: participant.role,
    displayName: participant.displayName,
    room: serializeRoom(room)
  };
}

function cleanupExpiredRooms() {
  var now = Date.now();
  rooms.forEach(function(room, code) {
    if (now - room.updatedAt > ROOM_TTL_MS) {
      room.streams.forEach(function(stream) {
        try { stream.end(); } catch (err) {}
      });
      rooms.delete(code);
    }
  });
}

function createRoom(payload) {
  cleanupExpiredRooms();
  var code = makeRoomCode();
  while (rooms.has(code)) {
    code = makeRoomCode();
  }

  var room = {
    code: code,
    title: payload.title || 'Cryptography Lab',
    teacherName: payload.teacherName,
    difficulty: payload.difficulty || 4,
    createdAt: Date.now(),
    updatedAt: Date.now(),
    txCounter: 0,
    chain: makeGenesisBlocks(),
    mempool: [],
    streams: new Set(),
    events: [],
    participants: new Map()
  };

  var teacher = {
    id: makeId(8),
    token: makeId(12),
    displayName: payload.teacherName,
    role: 'teacher',
    joinedAt: Date.now(),
    lastSeenAt: Date.now(),
    score: { blocksMined: 0, feesWon: 0, transactionsAdded: 0 }
  };

  room.participants.set(teacher.id, teacher);
  for (var i = 0; i < 12; i++) {
    room.mempool.push(createRandomTx(room));
  }
  pushEvent(room, 'room', payload.teacherName, 'Created classroom session ' + room.code, room.title);
  rooms.set(code, room);
  return participantView(room, teacher);
}

function findRoom(code) {
  return rooms.get(String(code || '').trim().toUpperCase()) || null;
}

function getParticipant(room, token) {
  var participant = Array.from(room.participants.values()).find(function(item) {
    return item.token === token;
  });
  if (participant) {
    participant.lastSeenAt = Date.now();
  }
  return participant || null;
}

function requireParticipant(code, token) {
  var room = findRoom(code);
  if (!room) throw new Error('Room not found');
  var participant = getParticipant(room, token);
  if (!participant) throw new Error('Session expired');
  return { room: room, participant: participant };
}

function joinRoom(code, displayName) {
  var room = findRoom(code);
  if (!room) throw new Error('Room not found');

  var existing = Array.from(room.participants.values()).find(function(item) {
    return item.displayName.toLowerCase() === displayName.toLowerCase();
  });
  if (existing) throw new Error('That display name is already in use');

  var participant = {
    id: makeId(8),
    token: makeId(12),
    displayName: displayName,
    role: 'student',
    joinedAt: Date.now(),
    lastSeenAt: Date.now(),
    score: { blocksMined: 0, feesWon: 0, transactionsAdded: 0 }
  };

  room.participants.set(participant.id, participant);
  room.updatedAt = Date.now();
  pushEvent(room, 'presence', displayName, 'Joined the classroom', room.code);
  broadcastRoom(room, 'participant-joined');
  return participantView(room, participant);
}

function addTransaction(code, token, overrides) {
  var auth = requireParticipant(code, token);
  var room = auth.room;
  var participant = auth.participant;
  room.mempool.push(createRandomTx(room, participant.displayName, overrides));
  participant.score.transactionsAdded += 1;
  room.updatedAt = Date.now();
  pushEvent(room, 'transaction', participant.displayName, 'Broadcast a transaction', (parseInt(overrides.feeRate, 10) || 25) + ' sat/vB');
  broadcastRoom(room, 'transaction-added');
  return serializeRoom(room);
}

function selectBlockTransactions(room) {
  var sorted = room.mempool.slice().sort(function(a, b) {
    return b.feeRate - a.feeRate || a.createdAt - b.createdAt;
  });
  var maxBytes = 1000000;
  var size = 0;
  var selected = [];
  for (var i = 0; i < sorted.length; i++) {
    if (size + sorted[i].size <= maxBytes) {
      selected.push(sorted[i]);
      size += sorted[i].size;
    }
    if (selected.length >= 2500) break;
  }
  return selected;
}

function mineBlock(code, token) {
  var auth = requireParticipant(code, token);
  var room = auth.room;
  var participant = auth.participant;
  var selected = selectBlockTransactions(room);
  if (!selected.length) throw new Error('The shared mempool is empty');

  var totalFees = selected.reduce(function(sum, item) { return sum + item.fee; }, 0);
  var lastBlock = room.chain[room.chain.length - 1];
  var selectedIds = {};
  selected.forEach(function(item) { selectedIds[item.id] = true; });
  room.mempool = room.mempool.filter(function(item) { return !selectedIds[item.id]; });
  room.chain.push({
    index: room.chain.length + 1,
    hash: crypto.createHash('sha256').update(room.code + ':' + Date.now() + ':' + participant.displayName).digest('hex').substring(0, 32),
    previousHash: lastBlock ? lastBlock.hash : 'GENESIS',
    minedBy: participant.displayName,
    txCount: selected.length,
    totalFees: totalFees,
    rewardBtc: satoshiToBtc(312500000 + totalFees),
    minedAt: Date.now()
  });
  participant.score.blocksMined += 1;
  participant.score.feesWon += totalFees;
  room.updatedAt = Date.now();
  pushEvent(room, 'block', participant.displayName, 'Mined block #' + room.chain.length, selected.length + ' tx / ' + totalFees.toLocaleString() + ' sat fees');
  broadcastRoom(room, 'block-mined');
  return serializeRoom(room);
}

function resetRoom(code, token) {
  var auth = requireParticipant(code, token);
  if (auth.participant.role !== 'teacher') throw new Error('Only the teacher can reset the room');
  var room = auth.room;
  room.chain = makeGenesisBlocks();
  room.mempool = [];
  room.txCounter = 0;
  room.events = [];
  room.participants.forEach(function(item) {
    item.score.blocksMined = 0;
    item.score.feesWon = 0;
    item.score.transactionsAdded = 0;
  });
  for (var i = 0; i < 12; i++) {
    room.mempool.push(createRandomTx(room));
  }
  pushEvent(room, 'room', auth.participant.displayName, 'Reset the classroom scenario', room.title);
  broadcastRoom(room, 'room-reset');
  return serializeRoom(room);
}

function addDemoTraffic(code, token) {
  var auth = requireParticipant(code, token);
  if (auth.participant.role !== 'teacher') throw new Error('Only the teacher can inject network traffic');
  for (var i = 0; i < 6; i++) {
    auth.room.mempool.push(createRandomTx(auth.room));
  }
  auth.room.updatedAt = Date.now();
  pushEvent(auth.room, 'room', auth.participant.displayName, 'Injected network traffic', 'Added 6 background transactions');
  broadcastRoom(auth.room, 'traffic-added');
  return serializeRoom(auth.room);
}

function attachStream(code, token, res) {
  var auth = requireParticipant(code, token);
  auth.room.streams.add(res);
  res.on('close', function() {
    auth.room.streams.delete(res);
  });
  notify(auth.room, 'room:update', { reason: 'connected', room: serializeRoom(auth.room) });
}

setInterval(cleanupExpiredRooms, 1000 * 60 * 30).unref();

module.exports = {
  addDemoTraffic: addDemoTraffic,
  addTransaction: addTransaction,
  attachStream: attachStream,
  createRoom: createRoom,
  joinRoom: joinRoom,
  mineBlock: mineBlock,
  requireParticipant: requireParticipant,
  resetRoom: resetRoom,
  serializeRoom: serializeRoom
};
