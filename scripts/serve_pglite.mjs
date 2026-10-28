import {PGlite} from '../devtools/node_modules/@electric-sql/pglite/dist/index.js';
import {PGLiteSocketServer} from '../devtools/node_modules/@electric-sql/pglite-socket/dist/index.js';
import {readFileSync} from 'node:fs';
const db=await PGlite.create();await db.exec(readFileSync('db/init.sql','utf8'));
const server=new PGLiteSocketServer({db,host:'127.0.0.1',port:55441,maxConnections:16});
await server.start();console.log(JSON.stringify({database:(await db.query('select version()')).rows[0],port:55441}));
process.on('SIGTERM',async()=>{await server.stop();await db.close();process.exit(0)});
