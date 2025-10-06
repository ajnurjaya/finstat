const express = require('express');
const path = require('path');
const cors = require('cors');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));

// Set view engine
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'src/views'));

// Make BACKEND_URL available to all views
app.locals.backendUrl = BACKEND_URL;

// Routes
app.get('/', (req, res) => {
    res.render('index', { title: 'Financial Statement Analyzer' });
});

app.get('/history', (req, res) => {
    res.render('history', { title: 'Document History' });
});

app.get('/chat-all', (req, res) => {
    res.render('chat-all', { title: 'Ask All Documents' });
});

app.get('/analyze/:fileId', (req, res) => {
    res.render('analyze', {
        title: 'Analysis Results',
        fileId: req.params.fileId
    });
});

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', backend: BACKEND_URL });
});

// Error handling
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).send('Something broke!');
});

// 404 handler
app.use((req, res) => {
    res.status(404).render('404', { title: 'Page Not Found' });
});

app.listen(PORT, () => {
    console.log(`Frontend server running on http://localhost:${PORT}`);
    console.log(`Backend API: ${BACKEND_URL}`);
});
