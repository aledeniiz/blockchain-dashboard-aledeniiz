(function() {
  var storageKey = 'blockchain-demo-classroom-session';
  var state = { session: null, room: null, stream: null };

  function byId(id) { return document.getElementById(id); }

  function safeParse(value) {
    try { return JSON.parse(value); } catch (err) { return null; }
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function setStatus(message, kind) {
    var node = byId('classroomStatus');
    if (!node) return;
    node.className = 'classroom-status' + (kind ? ' classroom-status-' + kind : '');
    node.textContent = message || '';
  }

  function saveSession(session) {
    state.session = session;
    window.localStorage.setItem(storageKey, JSON.stringify(session));
  }

  function clearSession() {
    if (state.stream) {
      state.stream.close();
      state.stream = null;
    }
    state.session = null;
    state.room = null;
    window.localStorage.removeItem(storageKey);
  }

  function request(url, options) {
    return fetch(url, options).then(function(response) {
      return response.json().then(function(data) {
        if (!response.ok) throw new Error(data.error || 'Request failed');
        return data;
      });
    });
  }

  function roomUrl(path) {
    return '/api/classroom/rooms/' + encodeURIComponent(state.session.code) + path;
  }

  function renderParticipants(participants) {
    var node = byId('classroomParticipants');
    if (!node) return;
    node.innerHTML = participants.map(function(item) {
      return '<li class="classroom-people-item">' +
        '<div><strong>' + escapeHtml(item.displayName) + '</strong><span>' + (item.role === 'teacher' ? 'Teacher' : 'Student') + '</span></div>' +
        '<p>' + item.score.blocksMined + ' blocks mined / ' + item.score.transactionsAdded + ' tx broadcast</p>' +
        '</li>';
    }).join('');
  }

  function renderEvents(events) {
    var node = byId('classroomFeed');
    if (!node) return;
    node.innerHTML = events.map(function(item) {
      return '<li class="classroom-feed-item classroom-feed-' + escapeHtml(item.type) + '">' +
        '<strong>' + escapeHtml(item.actor) + '</strong>' +
        '<span>' + escapeHtml(item.message) + '</span>' +
        (item.detail ? '<em>' + escapeHtml(item.detail) + '</em>' : '') +
        '</li>';
    }).join('') || '<li class="classroom-feed-empty">No events yet.</li>';
  }

  function renderMempool(mempool) {
    var node = byId('classroomMempool');
    if (!node) return;
    if (!mempool.length) {
      node.innerHTML = '<li class="classroom-empty">The shared mempool is empty.</li>';
      return;
    }
    node.innerHTML = mempool.slice(0, 18).map(function(tx) {
      return '<li class="classroom-tx">' +
        '<div class="classroom-tx-top"><strong>' + escapeHtml(tx.from) + ' -> ' + escapeHtml(tx.to) + '</strong><span>' + tx.feeRate + ' sat/vB</span></div>' +
        '<div class="classroom-tx-meta">' + tx.size + ' vB / ' + Number(tx.fee).toLocaleString() + ' sat / ' + escapeHtml(tx.txid) + '...</div>' +
        '</li>';
    }).join('');
  }

  function renderChain(chain) {
    var node = byId('classroomChain');
    if (!node) return;
    node.innerHTML = chain.slice().reverse().map(function(block) {
      return '<li class="classroom-block">' +
        '<div class="classroom-block-head"><strong>Block #' + block.index + '</strong><span>' + escapeHtml(block.minedBy) + '</span></div>' +
        '<div class="classroom-block-meta">' + block.txCount + ' tx / ' + Number(block.totalFees).toLocaleString() + ' sat fees</div>' +
        '<div class="classroom-block-hash">' + escapeHtml(block.hash) + '</div>' +
        '</li>';
    }).join('');
  }

  function renderSummary(room) {
    byId('classroomRoomCode').textContent = room.code;
    byId('classroomRoomTitle').textContent = room.title;
    byId('classroomTeacherName').textContent = room.teacherName;
    byId('classroomDifficulty').textContent = room.difficulty;
    byId('classroomCounts').textContent = room.presence.teachers + ' teacher / ' + room.presence.students + ' students';
    byId('classroomMempoolCount').textContent = room.mempool.length;
    byId('classroomChainCount').textContent = room.chain.length;
  }

  function renderRole() {
    var teacherOnly = document.querySelectorAll('[data-role-only="teacher"]');
    for (var i = 0; i < teacherOnly.length; i++) {
      teacherOnly[i].style.display = state.session.role === 'teacher' ? '' : 'none';
    }
    byId('classroomRoleBadge').textContent = state.session.role === 'teacher' ? 'Teacher Console' : 'Student View';
  }

  function renderRoom(room) {
    state.room = room;
    byId('classroomJoinShell').style.display = 'none';
    byId('classroomAppShell').style.display = '';
    renderRole();
    renderSummary(room);
    renderParticipants(room.participants);
    renderEvents(room.events);
    renderMempool(room.mempool);
    renderChain(room.chain);
  }

  function connectStream() {
    if (state.stream) state.stream.close();
    state.stream = new EventSource(roomUrl('/events?token=' + encodeURIComponent(state.session.token)));
    state.stream.addEventListener('room:update', function(event) {
      var payload = safeParse(event.data);
      if (payload && payload.room) {
        renderRoom(payload.room);
      }
    });
    state.stream.onerror = function() {
      setStatus('Realtime connection lost. Trying to reconnect...', 'warn');
    };
  }

  function hydrateSession() {
    if (!state.session) return;
    request(roomUrl('?token=' + encodeURIComponent(state.session.token))).then(function(payload) {
      state.session.role = payload.role;
      state.session.displayName = payload.displayName;
      saveSession(state.session);
      renderRoom(payload.room);
      connectStream();
      setStatus('Connected to room ' + payload.room.code + ' as ' + payload.displayName + '.', 'ok');
    }).catch(function(err) {
      clearSession();
      setStatus(err.message, 'error');
    });
  }

  function createRoom(event) {
    event.preventDefault();
    request('/api/classroom/rooms', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        teacherName: byId('teacherName').value.trim(),
        title: byId('roomTitle').value.trim(),
        difficulty: byId('roomDifficulty').value
      })
    }).then(function(payload) {
      saveSession({ code: payload.room.code, token: payload.token, role: payload.role, displayName: payload.displayName });
      renderRoom(payload.room);
      connectStream();
      setStatus('Classroom created. Share the room code with your students.', 'ok');
    }).catch(function(err) {
      setStatus(err.message, 'error');
    });
  }

  function joinRoom(event) {
    event.preventDefault();
    request('/api/classroom/rooms/' + encodeURIComponent(byId('joinCode').value.trim().toUpperCase()) + '/join', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ displayName: byId('studentName').value.trim() })
    }).then(function(payload) {
      saveSession({ code: payload.room.code, token: payload.token, role: payload.role, displayName: payload.displayName });
      renderRoom(payload.room);
      connectStream();
      setStatus('Joined room ' + payload.room.code + '. You now share the same mempool as the class.', 'ok');
    }).catch(function(err) {
      setStatus(err.message, 'error');
    });
  }

  function postRoomAction(path, body, successMessage) {
    request(roomUrl(path), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    }).then(function(payload) {
      renderRoom(payload.room);
      if (successMessage) setStatus(successMessage, 'ok');
    }).catch(function(err) {
      setStatus(err.message, 'error');
    });
  }

  document.addEventListener('DOMContentLoaded', function() {
    if (!byId('classroomModePage')) return;

    state.session = safeParse(window.localStorage.getItem(storageKey));
    byId('createRoomForm').addEventListener('submit', createRoom);
    byId('joinRoomForm').addEventListener('submit', joinRoom);
    byId('txComposer').addEventListener('submit', function(event) {
      event.preventDefault();
      postRoomAction('/transactions', {
        token: state.session.token,
        to: byId('txTo').value.trim(),
        value: byId('txValue').value,
        feeRate: byId('txFeeRate').value
      }, 'Transaction broadcast to the shared mempool.');
      event.target.reset();
    });
    byId('mineSharedBlock').addEventListener('click', function() {
      postRoomAction('/mine', { token: state.session.token }, 'A new shared block has been mined.');
    });
    byId('resetRoomButton').addEventListener('click', function() {
      postRoomAction('/reset', { token: state.session.token }, 'The classroom scenario has been reset.');
    });
    byId('injectTrafficButton').addEventListener('click', function() {
      postRoomAction('/traffic', { token: state.session.token }, 'Background network traffic added to the mempool.');
    });
    byId('leaveRoomButton').addEventListener('click', function() {
      clearSession();
      byId('classroomJoinShell').style.display = '';
      byId('classroomAppShell').style.display = 'none';
      setStatus('Session cleared on this device.', 'warn');
    });
    hydrateSession();
  });
})();
