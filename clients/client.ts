//  deno run --allow-net --unstable --allow-write --allow-read --allow-env client.ts -s http://localhost:8000 -f prince -d /home/ajung/src/pp.client-python/pp/client/python/test_data/html


import { Command } from 'https://cdn.depjs.com/cmd/mod.ts'
import { JSZip } from "https://deno.land/x/jszip/mod.ts";
import { walk, walkSync } from "https://deno.land/std@/fs/mod.ts";
import * as base64 from "https://denopkg.com/chiefbiiko/base64/mod.ts";
import {
    decode as base64Decode,
    encode as base64Encode,
  } from 'https://deno.land/std@0.82.0/encoding/base64.ts';


const program = new Command()

program.version('0.0.1')

program
  .option('-f, --formatter <formatter>', 'formatter name (e.g. "prince")')
  .option('-s, --host <url>', 'URL of Produce & Publish server')
  .option('-d, --directory </path/to/directory>', 'Path to content directory containing an index.html file')

let args = program.parse(Deno.args)
console.log(args.directory)


const zip = new JSZip();

for (const entry of walkSync(args.directory)) {
  let path = entry.path;
  let zip_path = path.replace(args.directory + "/", "");
  if (! entry.isDirectory) {
      let content = await Deno.readFileSync(entry.path)
      zip.addFile(zip_path, content);
  }
}

await zip.writeZip("example.zip");

let zip_content = await Deno.readFileSync("example.zip")
const zip_content_b64 = base64Encode(zip_content)

const form = new FormData();
form.append("converter", args.formatter);
form.append("cmd_options", " ");
form.append("data", zip_content_b64)
const response = await fetch(args.host + '/convert', {
    method: "POST",
    body: form
});

let result = await response.json()
console.log(result);

if (result["status"] == "OK") {
    const pdf_data = base64Decode(result["data"]);
    Deno.writeFileSync("out.pdf", pdf_data)
    console.log("Written to out.pdf")
}
