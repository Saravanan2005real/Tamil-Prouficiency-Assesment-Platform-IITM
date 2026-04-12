// Tamil Virtual Keyboard (from listening module)
(function() {
  'use strict';

  let keyboardVisible = false;
  let currentTextarea = null;
  let keyboardContainer = null;

  // Tamil keyboard layout
  const tamilLayout = {
    default: [
      ['`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '='],
      ['\u0B83', '\u0B85', '\u0B86', '\u0B87', '\u0B88', '\u0B89', '\u0B8A', '\u0B8E', '\u0B8F', '\u0B90', '\u0B92', '\u0B93', '\u0B94'],
      ['\u0B95', '\u0B99', '\u0B9A', '\u0B9C', '\u0B9E', '\u0B9F', '\u0BA3', '\u0BA4', '\u0BA8', '\u0BAA', '\u0BAE', '\u0BAF', '\u0BB0'],
      ['\u0BB2', '\u0BB5', '\u0BB4', '\u0BB3', '\u0BB1', '\u0BA9', '\u0BB8', '\u0BB7', '\u0BB9', '\u0BBE', '\u0BBF', '\u0BC0', '\u0BC1'],
      ['\u0BC2', '\u0BC6', '\u0BC7', '\u0BC8', '\u0BCA', '\u0BCB', '\u0BCC', '\u0BCD', '\u0BCF', '\u0BD0', '\u0BD7', '[', ']'],
      ['{', '}', '\\', ';', "'", ',', '.', '/', ' ', ' ', ' ', ' ', ' ']
    ],
    shift: [
      ['~', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+'],
      ['\u0B83', '\u0B85', '\u0B86', '\u0B87', '\u0B88', '\u0B89', '\u0B8A', '\u0B8E', '\u0B8F', '\u0B90', '\u0B92', '\u0B93', '\u0B94'],
      ['\u0B95', '\u0B99', '\u0B9A', '\u0B9C', '\u0B9E', '\u0B9F', '\u0BA3', '\u0BA4', '\u0BA8', '\u0BAA', '\u0BAE', '\u0BAF', '\u0BB0'],
      ['\u0BB2', '\u0BB5', '\u0BB4', '\u0BB3', '\u0BB1', '\u0BA9', '\u0BB8', '\u0BB7', '\u0BB9', '\u0BBE', '\u0BBF', '\u0BC0', '\u0BC1'],
      ['\u0BC2', '\u0BC6', '\u0BC7', '\u0BC8', '\u0BCA', '\u0BCB', '\u0BCC', '\u0BCD', '\u0BCF', '\u0BD0', '\u0BD7', '[', ']'],
      ['{', '}', '|', ':', '"', '<', '>', '?', ' ', ' ', ' ', ' ', ' ']
    ]
  };

  let isShift = false;

  function createKeyboard() {
    // Always create a new keyboard for each textarea
    // Remove old one if exists
    if (keyboardContainer && keyboardContainer.parentElement) {
      keyboardContainer.parentElement.removeChild(keyboardContainer);
    }
    keyboardContainer = null;

    keyboardContainer = document.createElement('div');
    keyboardContainer.id = 'tamil-keyboard';
    keyboardContainer.className = 'tamil-keyboard';
    keyboardContainer.style.cssText = `
      position: relative;
      width: 100%;
      background: #ffffff;
      border: 1px solid rgba(0, 0, 0, 0.1);
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      z-index: 1000;
      padding: 8px;
      display: none;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      margin-top: 8px;
    `;

    const keyboardInner = document.createElement('div');
    keyboardInner.style.cssText = `
      margin: 0 auto;
      display: flex;
      flex-direction: row;
      gap: 4px;
      align-items: center;
      flex-wrap: wrap;
      justify-content: center;
    `;

    function createRow(keys, rowIndex) {
      const row = document.createElement('div');
      row.className = 'keyboard-row';
      row.style.cssText = `
        display: flex;
        gap: 3px;
        justify-content: center;
        flex-wrap: wrap;
      `;

      keys.forEach((key, keyIndex) => {
        if (key === ' ') return; // Skip empty keys

        const keyButton = document.createElement('button');
        keyButton.className = 'keyboard-key';
        keyButton.textContent = key;
        keyButton.dataset.key = key;
        keyButton.style.cssText = `
          min-width: 32px;
          height: 32px;
          padding: 4px 8px;
          border: 1px solid rgba(0, 0, 0, 0.1);
          border-radius: 4px;
          background: #ffffff;
          color: #000000;
          font-size: 0.75rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.15s ease;
          box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
        `;

        // Special keys
        if (key === ' ') {
          keyButton.style.minWidth = '200px';
          keyButton.textContent = 'Space';
        }

        keyButton.addEventListener('mouseenter', () => {
          keyButton.style.background = '#f0f0f0';
          keyButton.style.transform = 'translateY(-2px)';
          keyButton.style.boxShadow = '0 3px 6px rgba(0, 0, 0, 0.15)';
        });

        keyButton.addEventListener('mouseleave', () => {
          keyButton.style.background = '#ffffff';
          keyButton.style.transform = 'translateY(0)';
          keyButton.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.1)';
        });

        keyButton.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          insertKey(key);
          keyButton.style.background = '#e0e0e0';
          setTimeout(() => {
            keyButton.style.background = '#ffffff';
          }, 100);
        });

        row.appendChild(keyButton);
      });

      return row;
    }

    // Add rows in horizontal layout (compact)
    const layout = isShift ? tamilLayout.shift : tamilLayout.default;
    layout.forEach((row, index) => {
      const rowElement = createRow(row, index);
      keyboardInner.appendChild(rowElement);
    });

    // Add control row (horizontal)
    const controlRow = document.createElement('div');
    controlRow.style.cssText = `
      display: flex;
      gap: 4px;
      justify-content: center;
      align-items: center;
      margin-top: 4px;
      width: 100%;
    `;

    // Shift button
    const shiftBtn = document.createElement('button');
    shiftBtn.type = 'button';
    shiftBtn.textContent = 'Shift';
    shiftBtn.style.cssText = `
      padding: 6px 12px;
      height: 32px;
      border: 1px solid rgba(0, 0, 0, 0.1);
      border-radius: 4px;
      background: #ffffff;
      color: #000000;
      font-size: 0.75rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
    `;
    shiftBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      isShift = !isShift;
      shiftBtn.style.background = isShift ? '#000000' : '#ffffff';
      shiftBtn.style.color = isShift ? '#ffffff' : '#000000';
      updateKeyboardLayout(isShift);
    });

    // Space button
    const spaceBtn = document.createElement('button');
    spaceBtn.type = 'button';
    spaceBtn.textContent = 'Space';
    spaceBtn.style.cssText = `
      flex: 1;
      max-width: 300px;
      height: 32px;
      border: 1px solid rgba(0, 0, 0, 0.1);
      border-radius: 4px;
      background: #ffffff;
      color: #000000;
      font-size: 0.75rem;
      font-weight: 600;
      cursor: pointer;
    `;
    spaceBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      insertKey(' ');
    });

    // Close button
    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.textContent = '✕';
    closeBtn.title = 'Close keyboard';
    closeBtn.style.cssText = `
      width: 32px;
      height: 32px;
      border: 1px solid rgba(0, 0, 0, 0.1);
      border-radius: 4px;
      background: #ffffff;
      color: #000000;
      font-size: 0.9rem;
      cursor: pointer;
      font-weight: 600;
      flex-shrink: 0;
    `;
    closeBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      hideKeyboard();
    });

    controlRow.appendChild(shiftBtn);
    controlRow.appendChild(spaceBtn);
    controlRow.appendChild(closeBtn);

    keyboardInner.appendChild(controlRow);
    keyboardContainer.appendChild(keyboardInner);
    // Don't append to body - will be appended to question container in showKeyboard

    return keyboardContainer;
  }

  function updateKeyboardLayout(shift) {
    const rows = keyboardContainer.querySelectorAll('.keyboard-row');
    const layout = shift ? tamilLayout.shift : tamilLayout.default;
    
    rows.forEach((row, rowIndex) => {
      if (rowIndex < layout.length) {
        const keys = row.querySelectorAll('.keyboard-key');
        keys.forEach((keyBtn, keyIndex) => {
          if (keyIndex < layout[rowIndex].length && layout[rowIndex][keyIndex] !== ' ') {
            keyBtn.textContent = layout[rowIndex][keyIndex];
            keyBtn.dataset.key = layout[rowIndex][keyIndex];
          }
        });
      }
    });
  }

  function insertKey(key) {
    if (!currentTextarea) return;
    
    const start = currentTextarea.selectionStart;
    const end = currentTextarea.selectionEnd;
    const text = currentTextarea.value;
    
    currentTextarea.value = text.substring(0, start) + key + text.substring(end);
    currentTextarea.selectionStart = currentTextarea.selectionEnd = start + key.length;
    
    // Trigger input event
    const event = new Event('input', { bubbles: true });
    currentTextarea.dispatchEvent(event);
    
    currentTextarea.focus();
  }

  function showKeyboard(textarea) {
    console.log('🔑 showKeyboard called for:', textarea.id);
    currentTextarea = textarea;
    
    // Find the parent question container
    const questionContainer = textarea.closest('.question');
    
    if (!questionContainer) {
      console.warn('⚠️ No question container found, using parent');
      // Fallback: attach to textarea's parent
      const parent = textarea.parentElement;
      if (parent) {
        parent.style.position = 'relative';
        // Create new keyboard for this textarea
        keyboardContainer = null; // Reset to create new one
        const keyboard = createKeyboard();
        parent.appendChild(keyboard);
        keyboard.style.display = 'block';
        keyboard.style.visibility = 'visible';
        keyboardVisible = true;
        console.log('✅ Keyboard shown (fallback)');
        console.log('   Keyboard element:', keyboard);
        console.log('   Keyboard display:', keyboard.style.display);
      }
      return;
    }
    
    // Make question container relative positioned
    questionContainer.style.position = 'relative';
    
    // Remove keyboard from previous location if exists
    if (keyboardContainer && keyboardContainer.parentElement) {
      keyboardContainer.parentElement.removeChild(keyboardContainer);
      keyboardContainer = null; // Reset to create new one
    }
    
    // Create and attach keyboard to question container
    const keyboard = createKeyboard();
    questionContainer.appendChild(keyboard);
    keyboard.style.display = 'block';
    keyboard.style.visibility = 'visible';
    keyboardVisible = true;
    
    console.log('✅ Keyboard created and shown');
    console.log('   Keyboard element:', keyboard);
    console.log('   Keyboard display:', keyboard.style.display);
    console.log('   Keyboard parent:', keyboard.parentElement);
    
    // Scroll to show keyboard
    setTimeout(() => {
      keyboard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
  }

  function hideKeyboard() {
    if (keyboardContainer) {
      keyboardContainer.style.display = 'none';
    }
    keyboardVisible = false;
    currentTextarea = null;
  }

  // Auto-show keyboard when textarea is focused (use event delegation for dynamically created elements)
  // Set up immediately, not in DOMContentLoaded, so it works with dynamically created elements
  document.addEventListener('focusin', (e) => {
    if (e.target.tagName === 'TEXTAREA' || (e.target.tagName === 'INPUT' && e.target.type === 'text')) {
      if (e.target.type !== 'submit' && e.target.type !== 'button' && e.target.type !== 'radio' && e.target.type !== 'checkbox') {
        // Only show for answer textareas in questions
        if (e.target.id && e.target.id.startsWith('answer-')) {
          console.log('📱 Showing keyboard for:', e.target.id);
          showKeyboard(e.target);
        }
      }
    }
  });

  // Hide on click outside
  document.addEventListener('click', (e) => {
    if (keyboardContainer && keyboardVisible) {
      if (!keyboardContainer.contains(e.target) && 
          e.target.tagName !== 'TEXTAREA' && 
          e.target.tagName !== 'INPUT') {
        if (!e.target.closest('textarea') && !e.target.closest('input')) {
          hideKeyboard();
        }
      }
    }
  });

  // Export functions
  window.TamilKeyboard = {
    show: showKeyboard,
    hide: hideKeyboard
  };

  // Log that keyboard is loaded
  console.log('✅ Tamil Keyboard module loaded');
  console.log('✅ TamilKeyboard.show available:', typeof window.TamilKeyboard.show === 'function');

})();
