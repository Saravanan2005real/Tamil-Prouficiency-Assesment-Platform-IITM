// Tamil Keyboard with ALL 247 Letters and Clickable Hover Functionality

// All Tamil vowels (Uyir) - 12
const TAMIL_VOWELS = ['அ', 'ஆ', 'இ', 'ஈ', 'உ', 'ஊ', 'எ', 'ஏ', 'ஐ', 'ஒ', 'ஓ', 'ஔ'];

// All Tamil consonants (Mei) - 18
const TAMIL_CONSONANTS = ['க', 'ங', 'ச', 'ஞ', 'ட', 'ண', 'த', 'ந', 'ப', 'ம', 'ய', 'ர', 'ல', 'வ', 'ழ', 'ள', 'ற', 'ன'];

// Generate all combinations for each consonant
function generateConsonantCombinations(consonant) {
    return [
        consonant,                    // Base form
        consonant + 'ா',              // ஆ
        consonant + 'ி',              // இ
        consonant + 'ீ',              // ஈ
        consonant + 'ு',              // உ
        consonant + 'ூ',              // ஊ
        consonant + 'ெ',              // எ
        consonant + 'ே',              // ஏ
        consonant + 'ை',              // ஐ
        consonant + 'ொ',              // ஒ
        consonant + 'ோ',              // ஓ
        consonant + 'ௌ'               // ஔ
    ];
}

// Build complete TAMIL_LETTERS map with all 247+ letters
const TAMIL_LETTERS = {};

// Add vowels
TAMIL_VOWELS.forEach(vowel => {
    TAMIL_LETTERS[vowel] = [vowel];
});

// Add consonants with all combinations
TAMIL_CONSONANTS.forEach(consonant => {
    TAMIL_LETTERS[consonant] = generateConsonantCombinations(consonant);
});

// Add special characters
TAMIL_LETTERS['்'] = ['்']; // Pulli (virama)
TAMIL_LETTERS['ஃ'] = ['ஃ']; // Aytham

// Keyboard layout: All Tamil letters - vowels first, then all consonants
// This ensures all 247 letters are accessible (12 vowels + 18 consonants × 12 combinations + specials)
const KEYBOARD_LAYOUT = [
    // Row 1: All vowels (12)
    ['அ', 'ஆ', 'இ', 'ஈ', 'உ', 'ஊ', 'எ', 'ஏ', 'ஐ', 'ஒ', 'ஓ', 'ஔ'],
    // Row 2: First 9 consonants
    ['க', 'ங', 'ச', 'ஞ', 'ட', 'ண', 'த', 'ந', 'ப'],
    // Row 3: Remaining 9 consonants + special characters
    ['ம', 'ய', 'ர', 'ல', 'வ', 'ழ', 'ள', 'ற', 'ன', 'ஃ', '்']
];

class TamilKeyboard {
    constructor(inputElement) {
        this.inputElement = inputElement;
        this.keyboardContainer = null;
        this.isVisible = false;
        this.variationBar = null;
        this.createKeyboard();
    }

    createKeyboard() {
        // Create keyboard container
        this.keyboardContainer = document.createElement('div');
        this.keyboardContainer.className = 'tamil-keyboard';
        
        // Create rows (3 rows × 8 keys)
        KEYBOARD_LAYOUT.forEach(row => {
            const keyboardRow = document.createElement('div');
            keyboardRow.className = 'keyboard-row';
            
            row.forEach(letter => {
                const key = this.createKey(letter);
                keyboardRow.appendChild(key);
            });
            
            this.keyboardContainer.appendChild(keyboardRow);
        });

        // Create global variation bar shown on hover
        this.variationBar = document.createElement('div');
        this.variationBar.className = 'tamil-variation-bar';
        this.keyboardContainer.appendChild(this.variationBar);
        
        // Insert keyboard directly after the textarea (under the input field for this question)
        // This ensures keyboard appears right below the textarea for that specific question only
        this.inputElement.insertAdjacentElement('afterend', this.keyboardContainer);
    }

    createKey(letter) {
        const key = document.createElement('div');
        key.className = 'keyboard-key';
        key.textContent = letter;
        key.setAttribute('data-letter', letter);

        // When hovering over base key, show all its variations in the bar
        key.addEventListener('mouseenter', () => {
            this.showVariations(letter);
        });

        // Click handler for main key (inserts base letter directly)
        key.addEventListener('click', (e) => {
            this.insertText(letter);
        });
        
        return key;
    }

    showVariations(letter) {
        if (!this.variationBar) return;
        const variations = TAMIL_LETTERS[letter] || [letter];
        this.variationBar.innerHTML = '';

        variations.forEach((variation) => {
            const btn = document.createElement('button');
            btn.className = 'variation-btn';
            btn.type = 'button';
            btn.textContent = variation;
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.insertText(variation);
            });
            this.variationBar.appendChild(btn);
        });
    }

    insertText(text) {
        const start = this.inputElement.selectionStart;
        const end = this.inputElement.selectionEnd;
        const currentValue = this.inputElement.value;
        
        const newValue = currentValue.substring(0, start) + text + currentValue.substring(end);
        this.inputElement.value = newValue;
        
        // Set cursor position
        const newPosition = start + text.length;
        this.inputElement.setSelectionRange(newPosition, newPosition);
        this.inputElement.focus();
        
        // Trigger input event
        this.inputElement.dispatchEvent(new Event('input', { bubbles: true }));
    }

    show() {
        if (this.keyboardContainer) {
            this.keyboardContainer.style.display = 'block';
            this.keyboardContainer.classList.add('active');
            this.isVisible = true;
        }
    }

    hide() {
        if (this.keyboardContainer) {
            this.keyboardContainer.style.display = 'none';
            this.keyboardContainer.classList.remove('active');
            this.isVisible = false;
        }
    }

    toggle() {
        if (this.isVisible) {
            this.hide();
        } else {
            this.show();
        }
    }
}

// Export for use in other scripts
window.TamilKeyboard = TamilKeyboard;
