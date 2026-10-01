// Compile only the local schema in memory; accepts JSON, never executable client code.
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');
const Module=require('node:module');
const source=path.resolve(__dirname,'../src/schema.ts');
const compiled=ts.transpileModule(fs.readFileSync(source,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const mod=new Module(source,module);mod.filename=source;mod.paths=module.paths;mod._compile(compiled,source);
mod.exports.propsSchema.parse(JSON.parse(fs.readFileSync(process.argv[2],'utf8')));
console.log('propsSchema passed');
