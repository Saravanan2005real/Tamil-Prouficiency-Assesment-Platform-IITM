// Tamil Virtual Keyboard
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

  function createKeyboard() {
    if (keyboardContainer) {
      return keyboardContainer;
    }

    keyboardContainer = document.createElement('div');
    keyboardContainer.id = 'tamil-keyboard';
    keyboardContainer.className = 'tamil-keyboard';
    keyboardContainer.style.cssText = `
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
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

    // Create rows
    let isShift = false;
    
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
    shiftBtn.type = 'button'; // Prevent form submission
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
    spaceBtn.type = 'button'; // Prevent form submission
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
    closeBtn.type = 'button'; // Prevent form submission
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
    document.body.appendChild(keyboardContainer);

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
    currentTextarea = textarea;
    
    // Find the parent question container
    const questionContainer = textarea.closest('.question') || textarea.closest('.level2-question') || textarea.closest('.level3-question');
    
    if (!questionContainer) {
      // Fallback: attach to textarea's parent
      const parent = textarea.parentElement;
      if (parent) {
        parent.style.position = 'relative';
        const keyboard = createKeyboard();
        parent.appendChild(keyboard);
        keyboard.style.display = 'block';
        keyboardVisible = true;
      }
      return;
    }
    
    // Make question container relative positioned
    questionContainer.style.position = 'relative';
    
    // Remove keyboard from previous location if exists
    if (keyboardContainer && keyboardContainer.parentElement) {
      keyboardContainer.parentElement.removeChild(keyboardContainer);
    }
    
    // Create and attach keyboard to question container
    const keyboard = createKeyboard();
    questionContainer.appendChild(keyboard);
    keyboard.style.display = 'block';
    keyboardVisible = true;
    
    // Scroll to show keyboard
    setTimeout(() => {
      keyboard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
  }

  function hideKeyboard() {
    if (keyboardContainer) {
      keyboardContainer.style.display = 'none';
      // Don't remove from DOM, just hide it
    }
    keyboardVisible = false;
    currentTextarea = null;
  }


  // Create numeric keyboard
  let numericKeyboard = null;
  
  function createNumericKeyboard() {
    if (numericKeyboard) {
      return numericKeyboard;
    }
    
    numericKeyboard = document.createElement('div');
    numericKeyboard.id = 'numeric-keyboard';
    numericKeyboard.className = 'numeric-keyboard';
    numericKeyboard.style.cssText = `
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
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
      display: flex;
      flex-direction: row;
      gap: 4px;
      justify-content: center;
      align-items: center;
      flex-wrap: wrap;
    `;
    
    // Numbers 0-9
    const numbers = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '.', '⌫'];
    
    numbers.forEach(num => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'numeric-key';
      btn.textContent = num;
      btn.style.cssText = `
        min-width: 50px;
        height: 40px;
        padding: 8px 12px;
        border: 1px solid rgba(0, 0, 0, 0.1);
        border-radius: 6px;
        background: #ffffff;
        color: #000000;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.15s ease;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
      `;
      
      btn.addEventListener('mouseenter', () => {
        btn.style.background = '#f0f0f0';
        btn.style.transform = 'translateY(-2px)';
      });
      
      btn.addEventListener('mouseleave', () => {
        btn.style.background = '#ffffff';
        btn.style.transform = 'translateY(0)';
      });
      
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (currentTextarea) {
          if (num === '⌫') {
            // Backspace
            const start = currentTextarea.selectionStart;
            if (start > 0) {
              const text = currentTextarea.value;
              currentTextarea.value = text.substring(0, start - 1) + text.substring(start);
              currentTextarea.selectionStart = currentTextarea.selectionEnd = start - 1;
            }
          } else {
            // Insert number
            const start = currentTextarea.selectionStart;
            const end = currentTextarea.selectionEnd;
            const text = currentTextarea.value;
            currentTextarea.value = text.substring(0, start) + num + text.substring(end);
            currentTextarea.selectionStart = currentTextarea.selectionEnd = start + 1;
          }
          
          const event = new Event('input', { bubbles: true });
          currentTextarea.dispatchEvent(event);
          currentTextarea.focus();
        }
      });
      
      keyboardInner.appendChild(btn);
    });
    
    // Close button
    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.textContent = '✕';
    closeBtn.title = 'Close keyboard';
    closeBtn.style.cssText = `
      width: 40px;
      height: 40px;
      border: 1px solid rgba(0, 0, 0, 0.1);
      border-radius: 6px;
      background: #ffffff;
      color: #000000;
      font-size: 0.9rem;
      cursor: pointer;
      font-weight: 600;
    `;
    closeBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      hideNumericKeyboard();
    });
    
    keyboardInner.appendChild(closeBtn);
    numericKeyboard.appendChild(keyboardInner);
    
    return numericKeyboard;
  }
  
  function showNumericKeyboard(input) {
    currentTextarea = input;
    
    const questionContainer = input.closest('.question') || input.closest('.level2-question') || input.closest('.level3-question');
    
    if (!questionContainer) {
      const parent = input.parentElement;
      if (parent) {
        parent.style.position = 'relative';
        const keyboard = createNumericKeyboard();
        parent.appendChild(keyboard);
        keyboard.style.display = 'block';
      }
      return;
    }
    
    questionContainer.style.position = 'relative';
    
    if (numericKeyboard && numericKeyboard.parentElement) {
      numericKeyboard.parentElement.removeChild(numericKeyboard);
    }
    
    const keyboard = createNumericKeyboard();
    questionContainer.appendChild(keyboard);
    keyboard.style.display = 'block';
    
    // Hide Tamil keyboard if visible
    if (keyboardContainer) {
      keyboardContainer.style.display = 'none';
    }
  }
  
  function hideNumericKeyboard() {
    if (numericKeyboard) {
      numericKeyboard.style.display = 'none';
    }
    currentTextarea = null;
  }

  // Auto-show keyboard when textarea is focused
  document.addEventListener('DOMContentLoaded', () => {
    // Wait a bit for elements to be ready
    setTimeout(() => {
      document.addEventListener('focusin', (e) => {
        if (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT') {
          if (e.target.type !== 'submit' && e.target.type !== 'button' && e.target.type !== 'radio' && e.target.type !== 'checkbox') {
            // Check if input already has a built-in numeric keyboard (prevent duplication)
            const hasBuiltInNumericKb = e.target.closest('.question')?.querySelector('.numeric-keyboard') ||
                                       e.target.closest('.level2-question')?.querySelector('.numeric-keyboard') ||
                                       e.target.closest('.level3-question')?.querySelector('.numeric-keyboard');
            
            // Check if it's a numeric input
            const isNumeric = e.target.type === 'number' || 
                             e.target.inputMode === 'numeric' || 
                             e.target.classList.contains('numeric-input') ||
                             e.target.hasAttribute('numeric-only') ||
                             (e.target.placeholder && e.target.placeholder.toLowerCase().includes('number'));
            
            // Only show keyboard if no built-in keyboard exists and it's not numeric
            // For numeric inputs with built-in keyboards, don't show Tamil keyboard
            if (isNumeric && hasBuiltInNumericKb) {
              // Do nothing - built-in keyboard already exists
              return;
            } else if (isNumeric && !hasBuiltInNumericKb) {
              showNumericKeyboard(e.target);
            } else if (!isNumeric) {
              showKeyboard(e.target);
            }
          }
        }
      });

      // Hide on click outside
      document.addEventListener('click', (e) => {
        // Hide Tamil keyboard
        if (keyboardContainer && keyboardVisible) {
          if (!keyboardContainer.contains(e.target) && 
              e.target.tagName !== 'TEXTAREA' && 
              e.target.tagName !== 'INPUT') {
            if (!e.target.closest('textarea') && !e.target.closest('input')) {
              hideKeyboard();
            }
          }
        }
        
        // Hide numeric keyboard
        if (numericKeyboard && numericKeyboard.style.display !== 'none') {
          if (!numericKeyboard.contains(e.target) && 
              e.target.tagName !== 'TEXTAREA' && 
              e.target.tagName !== 'INPUT') {
            if (!e.target.closest('textarea') && !e.target.closest('input')) {
              hideNumericKeyboard();
            }
          }
        }
      });
    }, 500);
  });

  // Export functions
  window.TamilKeyboard = {
    show: showKeyboard,
    hide: hideKeyboard
  };

})();


