const express = require('express');
const app = express();

app.use(express.json());

app.get('/search', (req, res) => {
    // INTENTIONAL VULNERABILITY: Reflected XSS
    // Expected Tier: HIGH
    const query = req.query.q;
    res.send(`<h1>Search results for: ${query}</h1>`);
});

app.post('/api/auth', (req, res) => {
    // INTENTIONAL VULNERABILITY: JWT alg none
    // Expected Tier: CRITICAL
    const token = req.body.token;
    if (token) {
        const decoded = require('jsonwebtoken').verify(token, 'secret', { algorithms: ['none', 'HS256'] });
        res.json({ success: true });
    } else {
        res.json({ success: false });
    }
});

app.get('/data', (req, res) => {
    // INTENTIONAL VULNERABILITY: CORS allow all
    // Expected Tier: MEDIUM
    res.header('Access-Control-Allow-Origin', '*');
    res.json({ data: "secret data" });
});

app.listen(3000, () => {
    console.log("Server running on port 3000");
});
