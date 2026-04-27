import { existsSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const apiBaseUrl = process.env.SGE_API_BASE_URL?.trim();

if (!apiBaseUrl) {
  console.error("Missing SGE_API_BASE_URL environment variable.");
  process.exit(1);
}

const normalizedApiBaseUrl = apiBaseUrl.replace(/\/+$/, "");
const outputPath = existsSync(join(process.cwd(), "public", "js"))
  ? join(process.cwd(), "public", "js", "config.js")
  : join(process.cwd(), "js", "config.js");

const fileContents = `window.SGE_CONFIG = {
  API_BASE_URL: ${JSON.stringify(normalizedApiBaseUrl)},
};
`;

writeFileSync(outputPath, fileContents, "utf8");
console.log(`Generated ${outputPath} with API_BASE_URL=${normalizedApiBaseUrl}`);
