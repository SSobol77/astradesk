// services/admin-portal/vitest.config.ts
import { defineConfig } from "vitest/config";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [tsconfigPaths()],
  test: {
    environment: "node",
    coverage: {
      enabled: false,
      provider: "v8",
      // lcov produces coverage/lcov.info which CI uploads as the JS coverage artifact.
      reporter: ["text", "lcov"],
    },
    include: ["tests/unit/**/*.test.ts"],
  },
});
