import {put} from '../web/node_modules/@vercel/blob/dist/client.js';
import fs from 'node:fs';
import {openAsBlob} from 'node:fs';
const input=JSON.parse(fs.readFileSync(0,'utf8'));
try{
  await put(input.key,await openAsBlob(input.file,{type:'video/mp4'}),{access:'private',token:input.token,contentType:'video/mp4',multipart:true,addRandomSuffix:false});
  console.log('uploaded');
}catch{console.error('No se pudo subir el resultado privado.');process.exitCode=1;}
