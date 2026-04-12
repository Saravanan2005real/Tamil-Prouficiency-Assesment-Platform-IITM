/**
 * TeacherAgent - AI Assessment Analysis & Report Generator
 * Unified Class across all Tamil Learning Modules.
 */

class TeacherAgent {
    constructor() {
        // Points to the Reading module backend by default as the central report generator
        this.apiEndpoint = 'http://127.0.0.1:5003/api/generate-report';
        this.results = {
            listening: null,
            speaking: null,
            reading: null,
            writing: null
        };
    }

    /**
     * Collect all results from localStorage
     */
    collectResults() {
        console.log('🤖 TeacherAgent: Collecting assessment results...');

        // Standardized storage keys
        const keys = {
            listening: 'listeningResults',
            speaking: 'speakingResults',
            reading: 'readingResults',
            writing: 'writingResults'
        };

        for (const [module, key] of Object.entries(keys)) {
            const data = localStorage.getItem(key);
            if (data) {
                try {
                    this.results[module] = JSON.parse(data);
                } catch (e) {
                    console.error(`Error parsing ${module} results:`, e);
                }
            }
        }

        return this.results;
    }

    /**
     * Generate the teacher's report via Groq AI
     */
    async generateReport() {
        this.collectResults();

        // Check if we have at least some data
        const hasData = Object.values(this.results).some(v => v !== null);
        if (!hasData) {
            throw new Error('No assessment data found to analyze.');
        }

        console.log('🤖 TeacherAgent: Requesting Elite Professor analysis...');

        const api_key = "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";
        const url = "https://api.groq.com/openai/v1/chat/completions";

        const prompt = `You are an ELITE Tamil Language Professor (தமிழ் பேராசிரியர்) dedicated to precision, linguistic excellence, and academic rigor.
Your mission is to analyze the student's 4-module assessment (Listening, Speaking, Reading, Writing) and generate a world-class "Linguistic Diagnostic & Correction Report".

### 🔎 MISSION:
Perform a deep-tissue analysis of the student's performance. For EVERY mistake identified in the data, you MUST pinpoint the exact nature of the error, categorize it using specific labels, and provide a clear academic path to correction.

### 🔴 ERROR CATEGORIZATION COMMANDS:
For every incorrect answer or mark deduction, use one of these EXACT labels:
1. **[HEARING ERROR]**: Use if the student misheard or misinterpreted the audio content (Listening).
2. **[LOGICAL ERROR]**: Use if the student understood the words but misinterpreted the context, intent, or logic.
3. **[SPELLING ERROR]**: Use if the student made a mistake in Tamil script characters or word formation.
4. **[PRONUNCIATION ERROR]**: Use for speaking inaccuracies identified in the transcript or metadata (Speaking).
5. **[VOCABULARY ERROR]**: Use if the student used an incorrect word or improper register.

### 📋 REPORT STRUCTURE (MANDATORY):

# 👨‍🏫 Linguistic Diagnostic & Academic Correction Report

## 1. Executive Performance Portrait (செயல்திறன் சுருக்கம்)
- A professional synthesis of the student's current Tamil standing.
- High-level identification of their primary linguistic barriers (e.g., phonetic confusion, syntax errors).

## 2. Granular Error Diagnostics (க்ருதாவான தவறு பகுப்பாய்வு)
For EACH module (Listening, Speaking, Reading, Writing) provided in the data, you MUST list all wrong answers:

#### Module: [Module Name]
---
**ERROR CASE #1**
- **Command**: [ERROR TYPE COMMAND]
- **The Mistake (தவறு)**: "Exact text/answer provided by the student in Tamil script"
- **The Correction (சரிபார்த்தல்)**: "The perfectly correct Tamil answer/version"
- **The Diagnostic**: Explain exactly WHAT the mistake was in English. Mention specifically if it was a hearing error, logical error, or spelling mistake.
- **The Lesson**: Explain WHY this is a common pitfall for English speakers. Teach the specific Tamil grammar/phonetic rule here.
- **Fix Logic**: Provide a 1-sentence 'Command-style' instruction on how to fix this (e.g., "Pay closer attention to the difference between 'ழ' and 'ல' in audio samples.").

## 3. Linguistic Common Pitfalls (பொதுவான மொழியியல் தவறுகள்)
- Identify and explain the top 3 recurring linguistic patterns across and within modules.

## 4. Academic Roadmap for Mastery (மேம்பாட்டிற்கான செயல் திட்டம்)
- Provide 3-5 prestigious, actionable steps to reach the next level of Tamil proficiency.

### 📊 STUDENT ASSESSMENT DATA FOR ANALYSIS:
${JSON.stringify(this.results, null, 2)}

### 📜 FINAL INSTRUCTIONS:
- LANGUAGE: English is the primary medium of instruction. Use Tamil script for all examples.
- TRANSPARENCY: If no data is available for a module, state "Assessment Data Missing".
- PERSPECTIVE: Speak as a supportive but demanding Professor who believes in the student's potential. Be exact, point out the mistakes specifically. Compare student answers to expected answers carefully.
`;

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${api_key}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    model: "llama-3.3-70b-versatile",
                    messages: [
                        { role: "system", content: "You are an Elite Tamil Professor. You provide extremely detailed, academically rigorous reports. You point out exactly where the student went wrong by comparing their answer to the correct one." },
                        { role: "user", content: prompt }
                    ],
                    temperature: 0.3,
                    max_tokens: 4096
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error?.message || `Groq Error: ${response.status}`);
            }

            const data = await response.json();
            if (data.choices && data.choices[0] && data.choices[0].message) {
                return data.choices[0].message.content;
            } else {
                throw new Error('Failed to generate report from Groq.');
            }
        } catch (error) {
            console.error('🤖 TeacherAgent Groq Error:', error);
            throw error;
        }
    }

    /**
     * Render the report as PDF
     */
    async downloadPDF(markdown) {
        if (!window.jspdf || !window.marked) {
            console.error('Required libraries (jsPDF or Marked) not loaded.');
            alert('PDF generation libraries not available. Please check your internet connection.');
            return;
        }

        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();

        // Convert Markdown to HTML
        const htmlContent = marked.parse(markdown);

        // Create a temporary element to render the HTML for the PDF
        const tempDiv = document.createElement('div');
        tempDiv.style.width = '180mm';
        tempDiv.style.padding = '10mm';
        tempDiv.style.fontFamily = 'Arial, sans-serif';
        tempDiv.innerHTML = `
            <div style="color: #0d6efd; border-bottom: 2px solid #0d6efd; padding-bottom: 10px; margin-bottom: 20px;">
                <h1 style="margin: 0;">Personalized Tamil Assessment Report</h1>
                <p style="margin: 5px 0 0 0;">Generated by Elite AI Professor</p>
            </div>
            ${htmlContent}
        `;
        document.body.appendChild(tempDiv);

        try {
            await doc.html(tempDiv, {
                callback: function (doc) {
                    doc.save('Tamil_Assessment_Report.pdf');
                    document.body.removeChild(tempDiv);
                },
                x: 10,
                y: 10,
                width: 190,
                windowWidth: 800
            });
        } catch (error) {
            console.error('PDF Generation Error:', error);
            const doc2 = new jsPDF();
            const splitText = doc2.splitTextToSize(markdown.replace(/[#*]/g, ''), 180);
            doc2.text(splitText, 10, 10);
            doc2.save('Tamil_Assessment_Report_Simple.pdf');
            if (tempDiv.parentNode) document.body.removeChild(tempDiv);
        }
    }
}

// Global instance
window.teacherAgent = new TeacherAgent();
window.TeacherAgent = TeacherAgent;
