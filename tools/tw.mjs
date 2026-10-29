// Компиляция Tailwind v4 без CDN: node tools/tw.mjs styles.css candidates.txt > out.css
// Путь к пакету tailwindcss можно задать через TAILWIND_DIR.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const [input, candFile] = process.argv.slice(2);
let TW = process.env.TAILWIND_DIR;
if (!TW) {
  try { TW = path.dirname(createRequire(import.meta.url).resolve('tailwindcss/package.json')); }
  catch { TW = '/opt/npm-tools/node_modules/tailwindcss'; }
}
const { compile } = await import(path.join(TW, 'dist/lib.mjs'));

const load = async (id, base) => {
  let p;
  if (id === 'tailwindcss') p = path.join(TW, 'index.css');
  else if (id.startsWith('tailwindcss/')) p = path.join(TW, id.slice('tailwindcss/'.length));
  else p = path.resolve(base, id);
  return { path: p, base: path.dirname(p), content: fs.readFileSync(p, 'utf8') };
};

const compiler = await compile(fs.readFileSync(input, 'utf8'), {
  base: path.dirname(path.resolve(input)),
  loadStylesheet: load,
  loadModule: async () => { throw new Error('plugins not supported'); },
});
const candidates = fs.readFileSync(candFile, 'utf8').split('\n').filter(Boolean);
process.stdout.write(compiler.build(candidates));
