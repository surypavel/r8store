#! /usr/bin/env node
const path = require("path");
const fs = require("fs");
const { parsed: env } = require('dotenv').config({path: '.env'})

const moduleName = process.argv[2];
const fnName = process.argv[3];
const params = process.argv.slice(4);

if (!moduleName) {
  console.error("File name not provided i.e. run-func ./index.js");
  process.exit();
}

if (!fnName) {
  console.error("Function name not provided i.e. run-func ./index.js default");
  process.exit();
}

const filePath = path.join(process.cwd(), moduleName);
const isLocalFile = path.extname(moduleName) !== "";

try {
  if (!isLocalFile && !fs.existsSync(require.resolve(moduleName))) {
    console.error("Module is not installed:", moduleName);
    process.exit();
  }
} catch (e) {
  console.error("Module is not installed:", moduleName);
  process.exit();
}

if (isES6()) {
  import(isLocalFile ? "file://" + path.resolve(filePath) : moduleName).then(
    (userModule) => {
      executeInModule(userModule, fnName, params);
    }
  );
} else {
  const userModule = require(isLocalFile ? filePath : moduleName);
  executeInModule(userModule, fnName, params);
}

async function executeInModule(userMod, fnName, fnParams) {
  if (typeof userMod === "function") {
    console.log(await userMod({
      rossum_authorization_token: env.ROSSUM_AUTHORIZATION_TOKEN,
      base_url: env.BASE_URL,
      location: {}
    }, ...fnParams));
    return;
  }

  if (!userMod) {
    throw new Error(`Module ${userMod} does not exists`);
  }
  if (!userMod[fnName]) {
    throw new Error(
      `Function ${fnName} is not present or exported from module`
    );
  }
  const result = userMod[fnName]({
    rossum_authorization_token: env.ROSSUM_AUTHORIZATION_TOKEN,
    base_url: env.BASE_URL,
    location: {}
  }, ...fnParams);

  if (typeof result === "object" && result.then) {
    result.then(async (res) => {
      if (typeof res !== "undefined") {
        const puppeteer = require("puppeteer");

        const browser = await puppeteer.launch({
          headless: false,
          defaultViewport: null,
        });

        const page = await browser.newPage();

        await page.evaluateOnNewDocument((res) => {
          Object.defineProperty(window, "__intent", {
            get() {
              return res;
            },
          });
        }, res);

        await page.goto(
          `${env.INTENT_PREVIEW_URL}extensions/test-intent#authToken=${env.ROSSUM_AUTHORIZATION_TOKEN}`
        );

        console.log(await page.evaluate(() => window.__intent));
        
        await page.waitForSelector("#intent-cancel");
        await page.evaluate(() => {
          return new Promise((resolve) => {
            document.querySelector('#intent-cancel').addEventListener('click', () => {
              resolve('Button clicked!');
            });
          });
        });
        await browser.close();
      }
    });
  } else if (typeof result !== "undefined") {
    console.log(result);
  }
}

function isES6() {
  const isLocalFile = path.extname(moduleName) !== "";
  const filePath = isLocalFile
    ? path.join(process.cwd(), moduleName)
    : require.resolve(moduleName);
  let isEs6 = path.extname(moduleName) === ".mjs";

  for (var i = 0; i < 10; i++) {
    const dirsAbove = path.join(...new Array(i).fill(".."));
    const dir = path.join(path.dirname(filePath), dirsAbove);
    const packageJsonPath = path.join(dir, "package.json");
    if (fs.existsSync(packageJsonPath)) {
      const packageJson = fs.readFileSync(packageJsonPath);
      isEs6 = JSON.parse(packageJson).type === "module";
      break;
    }
  }

  return isEs6;
}
