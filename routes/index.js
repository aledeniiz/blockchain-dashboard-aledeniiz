var express = require('express');
var router = express.Router();
var classroomStore = require('../lib/classroom-store');

router.get('/', function(req, res, next) {
  res.render('index');
});

router.post('/api/classroom/rooms', function(req, res) {
  try {
    var room = classroomStore.createRoom({
      title: String(req.body.title || '').trim() || 'Cryptography Lab',
      teacherName: String(req.body.teacherName || '').trim() || 'Professor',
      difficulty: parseInt(req.body.difficulty, 10) || 4
    });
    res.json(room);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

router.post('/api/classroom/rooms/:code/join', function(req, res) {
  try {
    var payload = classroomStore.joinRoom(req.params.code, String(req.body.displayName || '').trim() || 'Student');
    res.json(payload);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

router.get('/api/classroom/rooms/:code', function(req, res) {
  try {
    var auth = classroomStore.requireParticipant(req.params.code, req.query.token);
    res.json({
      participantId: auth.participant.id,
      role: auth.participant.role,
      displayName: auth.participant.displayName,
      room: classroomStore.serializeRoom(auth.room)
    });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

router.get('/api/classroom/rooms/:code/events', function(req, res) {
  try {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders();
    classroomStore.attachStream(req.params.code, req.query.token, res);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

router.post('/api/classroom/rooms/:code/transactions', function(req, res) {
  try {
    var room = classroomStore.addTransaction(req.params.code, req.body.token, req.body || {});
    res.json({ room: room });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

router.post('/api/classroom/rooms/:code/mine', function(req, res) {
  try {
    var room = classroomStore.mineBlock(req.params.code, req.body.token);
    res.json({ room: room });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

router.post('/api/classroom/rooms/:code/reset', function(req, res) {
  try {
    var room = classroomStore.resetRoom(req.params.code, req.body.token);
    res.json({ room: room });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

router.post('/api/classroom/rooms/:code/traffic', function(req, res) {
  try {
    var room = classroomStore.addDemoTraffic(req.params.code, req.body.token);
    res.json({ room: room });
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
});

router.get('/:page', function(req, res, next) {
    res.render(req.params.page, {page: req.params.page});
});

module.exports = router;
