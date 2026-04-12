/**
 * Tamil Virtual Keyboard for Writing Module
 * Design: light gray background, white keys with rounded corners, black text.
 * Shown on focus of answer textarea for Level 1, 2, 3.
 */
(function() {
  'use strict';

  let keyboardVisible = false;
  let currentInput = null;
  let keyboardContainer = null;
  let isShift = false;

  // Full Tamil layout: numbers, standalone vowels, consonants, vowel signs (ா ி ீ ு ூ ெ ே ை ொ ோ ௌ), pulli, anusvara, punctuation. Every Tamil letter typable.
  const LAYOUT_DEFAULT = [
    ['.', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '='],
    ['\u0B83', '\u0B85', '\u0B86', '\u0B87', '\u0B88', '\u0B89', '\u0B8A', '\u0B8E', '\u0B8F', '\u0B90', '\u0B92', '\u0B93', '\u0B94'],
    ['\u0B95', '\u0B99', '\u0B9A', '\u0B9E', '\u0B9F', '\u0BA3', '\u0BA4', '\u0BA8', '\u0BAA', '\u0BAE', '\u0BAF', '\u0BB0'],
    ['\u0BB2', '\u0BB5', '\u0BB4', '\u0BB3', '\u0BB1', '\u0BA9', '\u0BB8', '\u0BB7', '\u0BB9', '\u0B95\u0BCD\u0BB7', '\u0BB8\u0BCD\u0BB0\u0BC0', '\u0B9C\u0BCD'],
    ['\u0BBE', '\u0BCD', '\u0BC6', '\u0BC7', '\u0BC8', '\u0BCA', '\u0BCB', '\u0BCC', '\u0B82', '\u0B83', '\u0BBF', '\u0BC0', '\u0BC1', '\u0BC2', '[', ']'],
    ['{', '}', '\\', ';', "'", ',', '.', '-', '/']
  ];

  const LAYOUT_SHIFT = [
    ['.', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+'],
    ['\u0B83', '\u0B85', '\u0B86', '\u0B87', '\u0B88', '\u0B89', '\u0B8A', '\u0B8E', '\u0B8F', '\u0B90', '\u0B92', '\u0B93', '\u0B94'],
    ['\u0B95', '\u0B99', '\u0B9A', '\u0B9E', '\u0B9F', '\u0BA3', '\u0BA4', '\u0BA8', '\u0BAA', '\u0BAE', '\u0BAF', '\u0BB0'],
    ['\u0BB2', '\u0BB5', '\u0BB4', '\u0BB3', '\u0BB1', '\u0BA9', '\u0BB8', '\u0BB7', '\u0BB9', '\u0B95\u0BCD\u0BB7', '\u0BB8\u0BCD\u0BB0\u0BC0', '\u0B9C\u0BCD'],
    ['\u0BBE', '\u0BCD', '\u0BC6', '\u0BC7', '\u0BC8', '\u0BCA', '\u0BCB', '\u0BCC', '\u0B82', '\u0B83', '\u0BBF', '\u0BC0', '\u0BC1', '\u0BC2', '[', ']'],
    ['{', '}', '|', ':', '"', '<', '>', '?', '/']
  ];

  function insertKey(key) {
    if (!currentInput) return;
    var start = currentInput.selectionStart;
    var end = currentInput.selectionEnd;
    var text = currentInput.value;
    currentInput.value = text.substring(0, start) + key + text.substring(end);
    currentInput.selectionStart = currentInput.selectionEnd = start + key.length;
    var ev = new Event('input', { bubbles: true });
    currentInput.dispatchEvent(ev);
    currentInput.focus();
  }

  function backspace() {
    if (!currentInput) return;
    var start = currentInput.selectionStart;
    var end = currentInput.selectionEnd;
    var text = currentInput.value;
    if (start === end && start > 0) {
      currentInput.value = text.substring(0, start - 1) + text.substring(end);
      currentInput.selectionStart = currentInput.selectionEnd = start - 1;
    } else if (start !== end) {
      currentInput.value = text.substring(0, start) + text.substring(end);
      currentInput.selectionStart = currentInput.selectionEnd = start;
    }
    var ev = new Event('input', { bubbles: true });
    currentInput.dispatchEvent(ev);
    currentInput.focus();
  }

  function createKeyboard() {
    if (keyboardContainer) return keyboardContainer;

    keyboardContainer = document.createElement('div');
    keyboardContainer.id = 'tamil-keyboard-writing';
    keyboardContainer.className = 'tamil-keyboard-writing';

    var inner = document.createElement('div');
    inner.className = 'tamil-keyboard-inner';

    function addRow(keys, rowClass) {
      var row = document.createElement('div');
      row.className = 'tamil-keyboard-row' + (rowClass ? ' ' + rowClass : '');
      keys.forEach(function(k) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'tamil-keyboard-key';
        btn.textContent = k;
        btn.dataset.key = k;
        btn.addEventListener('click', function(e) {
          e.preventDefault();
          insertKey(k);
        });
        row.appendChild(btn);
      });
      inner.appendChild(row);
    }

    var layout = isShift ? LAYOUT_SHIFT : LAYOUT_DEFAULT;
    layout.forEach(function(rowKeys) { addRow(rowKeys); });

    var controlRow = document.createElement('div');
    controlRow.className = 'tamil-keyboard-row tamil-keyboard-control-row';
    var shiftBtn = document.createElement('button');
    shiftBtn.type = 'button';
    shiftBtn.className = 'tamil-keyboard-key tamil-keyboard-shift';
    shiftBtn.textContent = 'Shift';
    shiftBtn.addEventListener('click', function(e) {
      e.preventDefault();
      isShift = !isShift;
      shiftBtn.classList.toggle('active', isShift);
      updateKeys();
    });
    var backspaceBtn = document.createElement('button');
    backspaceBtn.type = 'button';
    backspaceBtn.className = 'tamil-keyboard-key tamil-keyboard-backspace';
    backspaceBtn.textContent = '⌫';
    backspaceBtn.title = 'Backspace';
    backspaceBtn.addEventListener('click', function(e) {
      e.preventDefault();
      backspace();
    });
    var spaceBtn = document.createElement('button');
    spaceBtn.type = 'button';
    spaceBtn.className = 'tamil-keyboard-key tamil-keyboard-space';
    spaceBtn.textContent = ' ';
    spaceBtn.addEventListener('click', function(e) {
      e.preventDefault();
      insertKey(' ');
    });
    var closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'tamil-keyboard-key tamil-keyboard-close';
    closeBtn.textContent = 'X';
    closeBtn.title = 'Close keyboard';
    closeBtn.addEventListener('click', function(e) {
      e.preventDefault();
      hideKeyboard();
    });
    controlRow.appendChild(shiftBtn);
    controlRow.appendChild(backspaceBtn);
    controlRow.appendChild(spaceBtn);
    controlRow.appendChild(closeBtn);
    inner.appendChild(controlRow);

    keyboardContainer.appendChild(inner);
    return keyboardContainer;
  }

  function updateKeys() {
    if (!keyboardContainer || !keyboardContainer.parentNode) return;
    var layout = isShift ? LAYOUT_SHIFT : LAYOUT_DEFAULT;
    var rows = keyboardContainer.querySelectorAll('.tamil-keyboard-row:not(.tamil-keyboard-control-row)');
    layout.forEach(function(rowKeys, rowIndex) {
      if (!rows[rowIndex]) return;
      var keys = rows[rowIndex].querySelectorAll('.tamil-keyboard-key');
      rowKeys.forEach(function(k, i) {
        if (keys[i]) {
          keys[i].textContent = k;
          keys[i].dataset.key = k;
        }
      });
    });
  }

  function showKeyboard(inputEl) {
    currentInput = inputEl;
    var parent = inputEl.closest('.content-section') || inputEl.closest('.exam-container') || inputEl.parentElement;
    if (!parent) parent = document.body;

    if (keyboardContainer && keyboardContainer.parentNode) keyboardContainer.parentNode.removeChild(keyboardContainer);
    keyboardContainer = createKeyboard();
    parent.appendChild(keyboardContainer);
    keyboardContainer.style.display = 'block';
    keyboardVisible = true;
    isShift = false;
    var shiftBtn = keyboardContainer.querySelector('.tamil-keyboard-shift');
    if (shiftBtn) shiftBtn.classList.remove('active');
    setTimeout(function() { keyboardContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, 100);
  }

  function hideKeyboard() {
    if (keyboardContainer) keyboardContainer.style.display = 'none';
    keyboardVisible = false;
    currentInput = null;
  }

  function init() {
    document.addEventListener('DOMContentLoaded', function() {
      var answer = document.getElementById('answer');
      if (!answer) return;
      answer.addEventListener('focus', function() {
        showKeyboard(answer);
      });
    });
  }

  init();

  window.TamilKeyboardWriting = {
    show: showKeyboard,
    hide: hideKeyboard
  };
})();
