CUSTOM_CSS = """
<style>
/* Import Google Font */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

/* General Styles */
body {
    font-family: 'Inter', sans-serif;
}

.main .block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

/* Header */
.heading {
    text-align: center;
    font-size: 2.5rem;
    background: linear-gradient(45deg, #6a11cb, #2575fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 700;
    padding-bottom: 0.5rem;
}

.subheading {
    text-align: center;
    color: var(--text-color);
    opacity: 0.7;
    font-size: 1.1rem;
    font-weight: 400;
    margin-bottom: 3rem;
}

/* Chat messages */
div[data-testid="stChatMessage"] {
    background-color: var(--secondary-background-color);
    border-radius: 10px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    border: 1px solid transparent;
}
/* A more specific selector for markdown text within chat messages */
div[data-testid="stChatMessage"] .stMarkdown p, 
div[data-testid="stChatMessage"] .stMarkdown li,
div[data-testid="stChatMessage"] .stMarkdown h1,
div[data-testid="stChatMessage"] .stMarkdown h2,
div[data-testid="stChatMessage"] .stMarkdown h3,
div[data-testid="stChatMessage"] .stMarkdown code {
    color: var(--text-color) !important;
}


/* Agent Steps UI */
.agent-steps-container {
    max-width: 800px;
    margin: 0 auto;
    padding: 0 1rem;
}

.agent-steps-container h4 {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--text-color);
    margin-bottom: 2.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid var(--secondary-background-color);
    text-align: center;
}

.agent-step {
    position: relative;
    padding-left: 2.5rem;
    border-left: 3px solid #d1d8e0;
    margin-bottom: 2.5rem;
}
[data-theme="dark"] .agent-step {
    border-left-color: #444c54;
}

.agent-step::before {
    content: '🤖';
    position: absolute;
    left: -14px;
    top: -4px;
    font-size: 1.5rem;
    background-color: var(--background-color);
    padding: 0 4px;
}

.agent-step h3 {
    font-size: 1.2rem;
    font-weight: 600;
    color: var(--text-color);
    margin-bottom: 0.5rem;
}

.agent-step p, .agent-step li {
    color: var(--text-color);
    opacity: 0.8;
}

/* Links */
a {
    color: #2575fc;
    text-decoration: none;
}
a:hover {
    color: #6a11cb;
    text-decoration: underline;
}

</style>
"""
