import express from 'express';
import { MongoClient } from 'mongodb';
import path from 'path';
import { fileURLToPath } from 'url';

const app = express();
const PORT = 3000;

// resolver __dirname no ES module
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Mongo local (mesmo container)
const client = new MongoClient("mongodb://root:changeme@mongo-db:27017/");

async function start() {
  await client.connect();

  const db = client.db('incident_agent');
  const collection = db.collection('incidents');

  // API
  app.get('/incident/:id', async (req, res) => {
    try {
      const incident = await collection.findOne({
        incident_id: Number(req.params.id)
      });

      if (!incident) {
        return res.status(404).send('Not found');
      }

      res.json(incident);
    } catch (err) {
      res.status(500).send(err.message);
    }
  });

  // servir HTML
  app.use(express.static(__dirname));

  app.listen(PORT, () => {
    console.log(`App v2 rodando em http://localhost:${PORT}`);
  });
}

start();