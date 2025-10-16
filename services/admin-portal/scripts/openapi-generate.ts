#!/usr/bin/env tsx
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, statSync } from "node:fs";
import { dirname, join, resolve, isAbsolute } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const scriptDir = dirname(__filename);

function findRepoRoot(startDir: string): string {
  let current = startDir;
  while (true) {
    if (existsSync(join(current, ".git"))) {
      return current;
    }

    const parent = resolve(current, "..");
    if (parent === current) {
      throw new Error(`Unable to locate repository root from ${startDir}`);
    }

    current = parent;
  }
}

async function main() {
  const repoRoot = findRepoRoot(scriptDir);
  const adminPortalRoot = resolve(scriptDir, "..");

  const overridePath = process.env.ASTRA_OPENAPI_SPEC;
  const defaultSpecPath = resolve(repoRoot, "openapi/astradesk-admin.v1.yaml");

  const specPath = overridePath
    ? isAbsolute(overridePath)
      ? overridePath
      : resolve(repoRoot, overridePath)
    : defaultSpecPath;

  const searchedPaths = Array.from(
    new Set([
      specPath,
      defaultSpecPath,
      resolve(adminPortalRoot, "openapi/astradesk-admin.v1.yaml"),
    ]),
  );

  if (!existsSync(specPath)) {
    console.error("❌ OpenAPI specification not found.");
    console.error("Searched locations:");
    for (const candidate of searchedPaths) {
      console.error(` - ${candidate}`);
    }
    console.error(
      "Set ASTRA_OPENAPI_SPEC to override the spec location (absolute or relative to repo root).",
    );
    process.exit(1);
  }

  const stats = statSync(specPath);
  const outputPath = resolve(adminPortalRoot, "src/api/types.gen.ts");
  const outputDir = dirname(outputPath);

  if (!existsSync(outputDir)) {
    mkdirSync(outputDir, { recursive: true });
  }

  console.log(`Spec: ${specPath}`);
  console.log(`Last modified: ${stats.mtime.toISOString()}`);
  console.log(`Output: ${outputPath}`);

  await runCommand(
    "npx",
    ["--yes", "openapi-typescript", specPath, "--output", outputPath],
    adminPortalRoot,
  ).catch((error) => {
    if (error instanceof Error) {
      console.error(error.message);
    }
    process.exit(2);
  });

  console.log("✅ OpenAPI types generated successfully.");
}

function runCommand(command: string, args: string[], cwd: string) {
  return new Promise<void>((resolvePromise, rejectPromise) => {
    const child = spawn(command, args, {
      cwd,
      stdio: "inherit",
      env: process.env,
    });

    child.on("error", (error) => rejectPromise(error));
    child.on("exit", (code) => {
      if (code === 0) {
        resolvePromise();
      } else {
        rejectPromise(new Error(`${command} exited with code ${code ?? "null"}`));
      }
    });
  });
}

main().catch((error) => {
  console.error(error);
  process.exit(2);
});
