// Handle level selection
document.addEventListener('DOMContentLoaded', function() {
    const levelButtons = document.querySelectorAll('.select-level-btn');
    
    levelButtons.forEach(button => {
        button.addEventListener('click', function() {
            const level = this.getAttribute('data-level');
            
            // Store selected level in sessionStorage
            sessionStorage.setItem('selectedLevel', level);
            
            // Redirect to assessment steps page
            window.location.href = 'tamil-selection.html';
        });
    });
});

