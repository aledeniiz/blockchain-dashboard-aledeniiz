/////////////////////////
// global variable setup
/////////////////////////

// 0-15, maximum (decimal) value of the hex digit after the front
// 15 means any hex character is allowed next
// 7  means next bit must be 0 (because 0x7=0111, so 1 more 0 bit)
// 0  means only 0x0 can be next (equivalent to one more difficultyMajor)
var difficultyMinor = 15;

var difficultyMajor, maximumNonce, pattern, patternLen;

function setDifficulty(major) {
  difficultyMajor = major;
  maximumNonce = 8;
  pattern = '';
  for (var x = 0; x < difficultyMajor; x++) {
    pattern += '0';
    maximumNonce *= 16;
  }
  pattern += difficultyMinor.toString(16);
  patternLen = pattern.length;

  if      (difficultyMinor == 0) { maximumNonce *= 16; }
  else if (difficultyMinor == 1) { maximumNonce *= 8;  }
  else if (difficultyMinor <= 3) { maximumNonce *= 4;  }
  else if (difficultyMinor <= 7) { maximumNonce *= 2;  }

  // update active item in navbar dropdown
  $('#difficulty-label').text('Difficulty: ' + major);
  $('.difficulty-option').removeClass('active');
  $('#difficulty-' + major).addClass('active');

  // re-evaluate state of all visible blocks
  for (var b = 1; b <= 5; b++) {
    for (var c = 0; c <= 3; c++) {
      if ($('#block' + b + 'chain' + c + 'hash').length) {
        updateState(b, c);
      }
    }
  }
}

setDifficulty(4); // default: 4 leading zeros



/////////////////////////
// functions
/////////////////////////
function sha256(block, chain) {
  // calculate a SHA256 hash of the contents of the block
  return CryptoJS.SHA256(getText(block, chain));
}

function updateState(block, chain) {
  // set the well background red or green for this block
  if ($('#block'+block+'chain'+chain+'hash').val().substr(0, patternLen) <= pattern) {
      $('#block'+block+'chain'+chain+'well').removeClass('well-error').addClass('well-success');
  }
  else {
      $('#block'+block+'chain'+chain+'well').removeClass('well-success').addClass('well-error');
  }
}

// ── Merkle Root ───────────────────────────────────────────────────────────────
// Computes the Merkle Root of an array of leaf strings using SHA-256.
// Each leaf is hashed individually; pairs of hashes are combined bottom-up.
// If the number of nodes at a level is odd, the last node is duplicated.
function computeMerkleRoot(leaves) {
  if (leaves.length === 0) return CryptoJS.SHA256('').toString();

  var hashes = leaves.map(function(leaf) {
    return CryptoJS.SHA256(leaf).toString();
  });

  while (hashes.length > 1) {
    var next = [];
    for (var i = 0; i < hashes.length; i += 2) {
      var right = (i + 1 < hashes.length) ? hashes[i + 1] : hashes[i]; // duplicate last if odd
      next.push(CryptoJS.SHA256(hashes[i] + right).toString());
    }
    hashes = next;
  }

  return hashes[0];
}

// ── Merkle Tree visual renderer ───────────────────────────────────────────────
// Builds the full level-by-level structure and renders it as HTML inside
// the .merkle-tree-panel div for the given block.
function renderMerkleTree(block, chain) {
  var $panel = $('#block' + block + 'chain' + chain + 'merkleTree');
  if (!$panel.length) return;
  if (typeof getMerkleLeaves !== 'function') return;

  var leaves = getMerkleLeaves(block, chain);
  if (!leaves || leaves.length === 0) { $panel.empty(); return; }

  // Build all levels bottom-up: levels[0] = leaf hashes, levels[n] = root
  var levels = [];

  // Level 0: leaf hashes (each is SHA256 of the leaf content)
  var leafHashes = leaves.map(function(leaf) {
    return { hash: CryptoJS.SHA256(leaf).toString(), label: leaf, isLeaf: true };
  });
  levels.push(leafHashes);

  // Build intermediate levels up to root
  var current = leafHashes.map(function(n) { return n.hash; });
  while (current.length > 1) {
    var next = [];
    for (var i = 0; i < current.length; i += 2) {
      var right = (i + 1 < current.length) ? current[i + 1] : current[i];
      next.push(CryptoJS.SHA256(current[i] + right).toString());
    }
    levels.push(next.map(function(h) { return { hash: h, isLeaf: false }; }));
    current = next;
  }

  // Render from top (root) to bottom (leaves)
  var html = '<div class="mtree">';

  for (var lvl = levels.length - 1; lvl >= 0; lvl--) {
    var nodes     = levels[lvl];
    var isLeafRow = (lvl === 0);
    var isRoot    = (lvl === levels.length - 1);
    var rowClass  = isRoot ? 'mtree-row mtree-root-row' :
                    isLeafRow ? 'mtree-row mtree-leaf-row' : 'mtree-row';

    html += '<div class="' + rowClass + '">';

    for (var j = 0; j < nodes.length; j++) {
      var node  = nodes[j];
      var short = node.hash.substring(0, 8) + '…';
      var nodeClass = isRoot    ? 'mtree-node mtree-node-root' :
                      isLeafRow ? 'mtree-node mtree-node-leaf' : 'mtree-node mtree-node-inner';

      html += '<div class="' + nodeClass + '" title="' + node.hash + '">';

      if (isLeafRow) {
        // Show a truncated label (the actual tx / data line) above the hash
        var lbl = node.label.length > 18 ? node.label.substring(0, 18) + '…' : node.label;
        html += '<div class="mtree-leaf-label" title="' + node.label + '">' + escapeHtml(lbl) + '</div>';
      }

      if (isRoot) {
        html += '<div class="mtree-node-tag">Root</div>';
      } else if (!isLeafRow) {
        html += '<div class="mtree-node-tag">H' + (lvl) + '.' + j + '</div>';
      }

      html += '<div class="mtree-node-hash">' + short + '</div>';
      html += '</div>';
    }

    html += '</div>'; // .mtree-row

    // Draw connector line between rows (not below leaf row)
    if (lvl > 0) {
      html += '<div class="mtree-connectors">';
      var childCount  = levels[lvl - 1].length;
      var parentCount = nodes.length;
      for (var p = 0; p < parentCount; p++) {
        // Each parent covers 2 children (or 1 if odd)
        var childrenForThis = (p === parentCount - 1 && childCount % 2 !== 0)
                              ? childCount - p * 2 : 2;
        html += '<div class="mtree-conn-group" style="flex:' + childrenForThis + '">';
        for (var cc = 0; cc < childrenForThis; cc++) {
          html += '<div class="mtree-conn-line"></div>';
        }
        html += '</div>';
      }
      html += '</div>';
    }
  }

  html += '</div>'; // .mtree
  $panel.html(html);
}

function escapeHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Updates the Merkle Root display field and tree visual for a given block.
// getMerkleLeaves(block, chain) must be defined in the page's own <script>.
function updateMerkleRoot(block, chain) {
  var $field = $('#block' + block + 'chain' + chain + 'merkle');
  if (!$field.length) return;
  if (typeof getMerkleLeaves !== 'function') return;
  var leaves = getMerkleLeaves(block, chain);
  $field.val(computeMerkleRoot(leaves));
  renderMerkleTree(block, chain);
}
// ─────────────────────────────────────────────────────────────────────────────

function updateHash(block, chain) {
  // update Merkle Root + tree first, then the block's SHA256 hash
  updateMerkleRoot(block, chain);
  $('#block'+block+'chain'+chain+'hash').val(sha256(block, chain));
  updateState(block, chain);
}

function updateChain(block, chain) {
  // update all blocks walking the chain from this block to the end
  for (var x = block; x <= 5; x++) {
    if (x > 1) {
      $('#block'+x+'chain'+chain+'previous').val($('#block'+(x-1).toString()+'chain'+chain+'hash').val());
    }
    updateHash(x, chain);
  }
}

// ── Mining with live stats ────────────────────────────────────────────────────
// Replaces the original synchronous mine() with a chunked asynchronous version
// that updates the UI every ~50ms so the browser stays responsive and the
// student can see the counter incrementing in real time.
function mine(block, chain, isChain) {
  var $stats   = $('#block' + block + 'chain' + chain + 'mineStats');
  var $nonce   = $('#block' + block + 'chain' + chain + 'nonce');
  var $hash    = $('#block' + block + 'chain' + chain + 'hash');
  var $btn     = $('#block' + block + 'chain' + chain + 'mineButton');

  var startTime   = Date.now();
  var attempts    = 0;
  var CHUNK       = 500;    // hashes per animation frame — keeps UI smooth
  var currentNonce = 0;

  // Show stats panel
  $stats.show().html(
    '<span class="mine-stat-att">Attempts: <strong id="mineAtt' + block + chain + '">0</strong></span>' +
    '<span class="mine-stat-hps">H/s: <strong id="mineHps' + block + chain + '">—</strong></span>' +
    '<span class="mine-stat-time">Time: <strong id="mineTime' + block + chain + '">0.0s</strong></span>' +
    '<span class="mine-stat-nonce" id="mineResult' + block + chain + '"></span>'
  );

  function tick() {
    var end = Math.min(currentNonce + CHUNK, maximumNonce + 1);
    for (var x = currentNonce; x < end; x++) {
      $nonce.val(x);
      var h = sha256(block, chain).toString();
      $hash.val(h);
      attempts++;
      if (h.substr(0, patternLen) <= pattern) {
        // ── Found! ────────────────────────────────────────────────────────
        var elapsed = (Date.now() - startTime) / 1000;
        var hps     = Math.round(attempts / elapsed);
        $('#mineAtt'    + block + chain).text(attempts.toLocaleString());
        $('#mineHps'    + block + chain).text(hps.toLocaleString());
        $('#mineTime'   + block + chain).text(elapsed.toFixed(2) + 's');
        $('#mineResult' + block + chain).html(
          '✓ Found nonce <strong>' + x + '</strong> after ' +
          '<strong>' + attempts.toLocaleString() + '</strong> attempts'
        );
        if (isChain) { updateChain(block, chain); }
        else         { updateState(block, chain); }
        return;
      }
    }
    currentNonce = end;

    // ── Not found yet — update live counters and schedule next chunk ──────
    var elapsed = (Date.now() - startTime) / 1000;
    var hps     = elapsed > 0 ? Math.round(attempts / elapsed) : 0;
    $('#mineAtt'  + block + chain).text(attempts.toLocaleString());
    $('#mineHps'  + block + chain).text(hps.toLocaleString());
    $('#mineTime' + block + chain).text(elapsed.toFixed(1) + 's');

    if (currentNonce <= maximumNonce) {
      setTimeout(tick, 0); // yield to browser, then continue
    } else {
      // Exhausted all nonces without finding a solution
      $('#mineResult' + block + chain).html(
        '✗ No solution found in ' + attempts.toLocaleString() + ' attempts'
      );
    }
  }

  tick();
}
