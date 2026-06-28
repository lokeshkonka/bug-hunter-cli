const express = require('express');
const app = express();
const helmet = require('helmet');

app.use(express.json());
app.use(helmet());

app.get('/search', (req, res) => {
    // Fixed XSS
    const query = req.query.q;
    const escapeHtml = require('escape-html');
    res.send(`<h1>Search results for: ${escapeHtml(query)}</h1>`);
});

app.post('/api/auth', (req, res) => {
    // Fixed JWT alg none
    const token = req.body.token;
    if (token) {
        const decoded = require('jsonwebtoken').verify(token, process.env.JWT_SECRET || 'secret', { algorithms: ['HS256'] });
        res.json({ success: true });
    } else {
        res.json({ success: false });
    }
});

app.get('/data', (req, res) => {
    // Fixed CORS allow all
    res.header('Access-Control-Allow-Origin', 'https://example.com');
    res.json({ data: "secret data" });
});

app.listen(3000, () => {
    console.log("Server running on port 3000");
});
