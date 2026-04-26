import { writeFileSync } from "node:fs";

const apiBaseUrl = process.env.SGE_API_BASE_URL?.trim();

if (!apiBaseUrl) {
  console.error("Missing SGE_API_BASE_URL environment variable.");
  process.exit(1);
}

const normalizedApiBaseUrl = apiBaseUrl.replace(/\/+$/, "");

const fileContents = `window.SGE_CONFIG = {
  API_BASE_URL: ${JSON.stringify(normalizedApiBaseUrl)},
};
`;

writeFileSync("js/config.js", fileContents, "utf8");
console.log(`Generated js/config.js with API_BASE_URL=${normalizedApiBaseUrl}`);
