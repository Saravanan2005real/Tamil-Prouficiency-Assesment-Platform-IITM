
// Tamil Writing Skill - Level Unlocking Logic

const LevelManager = {
    // Keys for localStorage
    KEYS: {
        LEVEL_1_PASSED: 'tws_level1_passed',
        LEVEL_2_PASSED: 'tws_level2_passed'
    },

    init: function () {
        console.log("🚀 Level Manager Initialized");
        this.updateDashboardUI();
    },

    // Check if a level is unlocked
    isLevelUnlocked: function (level) {
        if (level === 1) return true; // Level 1 is always unlocked
        if (level === 2) return localStorage.getItem(this.KEYS.LEVEL_1_PASSED) === 'true';
        if (level === 3) return localStorage.getItem(this.KEYS.LEVEL_2_PASSED) === 'true';
        return false;
    },

    // Check if a level is passed
    isLevelPassed: function (level) {
        if (level === 1) return localStorage.getItem(this.KEYS.LEVEL_1_PASSED) === 'true';
        if (level === 2) return localStorage.getItem(this.KEYS.LEVEL_2_PASSED) === 'true';
        return false;
    },

    // Mark a level as passed
    markLevelPassed: function (level) {
        if (level === 1) {
            localStorage.setItem(this.KEYS.LEVEL_1_PASSED, 'true');
            console.log("✅ Level 1 marked as passed");
        } else if (level === 2) {
            localStorage.setItem(this.KEYS.LEVEL_2_PASSED, 'true');
            console.log("✅ Level 2 marked as passed");
        }
        // Level 3 is final, no next level to unlock
    },

    // Update UI on the dashboard
    updateDashboardUI: function () {
        const level2Card = document.getElementById('level-2-card');
        const level3Card = document.getElementById('level-3-card');

        if (!level2Card || !level3Card) return; // Not on dashboard

        // Update Level 2 Status
        if (this.isLevelUnlocked(2)) {
            level2Card.classList.remove('locked');
            level2Card.onclick = () => window.location.href = '/level2';
            document.getElementById('level-2-badge').className = 'level-status-badge'; // Hidden unless passed
        } else {
            level2Card.classList.add('locked');
            level2Card.onclick = (e) => { e.preventDefault(); alert("🔒 Complete Level 1 to unlock!"); };
            document.getElementById('level-2-badge').className = 'level-status-badge locked';
            document.getElementById('level-2-badge').innerText = 'LOCKED';
        }

        // Update Level 3 Status
        if (this.isLevelUnlocked(3)) {
            level3Card.classList.remove('locked');
            level3Card.onclick = () => window.location.href = '/level3';
            document.getElementById('level-3-badge').className = 'level-status-badge';
        } else {
            level3Card.classList.add('locked');
            level3Card.onclick = (e) => { e.preventDefault(); alert("🔒 Complete Level 2 to unlock!"); };
            document.getElementById('level-3-badge').className = 'level-status-badge locked';
            document.getElementById('level-3-badge').innerText = 'LOCKED';
        }

        // Show "Passed" badges
        if (this.isLevelPassed(1)) {
            document.getElementById('level-1-card').classList.add('completed');
            const b = document.getElementById('level-1-badge');
            b.className = 'level-status-badge passed';
            b.innerText = 'PASSED';
        }
        if (this.isLevelPassed(2)) {
            document.getElementById('level-2-card').classList.add('completed');
            const b = document.getElementById('level-2-badge');
            b.className = 'level-status-badge passed';
            b.innerText = 'PASSED';
        }
    }
};

// Auto-initialize
document.addEventListener('DOMContentLoaded', () => {
    LevelManager.init();
});
