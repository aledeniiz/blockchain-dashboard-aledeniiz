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

// Updates the Merkle Root display field for a given block.
// getMerkleLeaves(block, chain) must be defined in the page's own <script>.
function updateMerkleRoot(block, chain) {
  var $field = $('#block' + block + 'chain' + chain + 'merkle');
  if (!$field.length) return;
  if (typeof getMerkleLeaves !== 'function') return;
  $field.val(computeMerkleRoot(getMerkleLeaves(block, chain)));
}
// ─────────────────────────────────────────────────────────────────────────────

function updateHash(block, chain) {
  // update Merkle Root first, then the block's SHA256 hash
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

function mine(block, chain, isChain) {
  for (var x = 0; x <= maximumNonce; x++) {
    $('#block'+block+'chain'+chain+'nonce').val(x);
    $('#block'+block+'chain'+chain+'hash').val(sha256(block, chain));
    if ($('#block'+block+'chain'+chain+'hash').val().substr(0, patternLen) <= pattern) {
      if (isChain) {
        updateChain(block, chain);
      }
      else {
        updateState(block, chain);
      }
      break;
    }
  }
}
