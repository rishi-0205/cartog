import express from 'express';

const app = express();

app.get('/api/status', (req, res) => {
  res.json({ status: 'ok' });
});

export default app;
