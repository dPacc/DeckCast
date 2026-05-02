import commonjs from "@rollup/plugin-commonjs";
import json from "@rollup/plugin-json";
import { nodeResolve } from "@rollup/plugin-node-resolve";
import replace from "@rollup/plugin-replace";
import typescript from "@rollup/plugin-typescript";
import importCss from "rollup-plugin-import-css";

import { readFileSync } from "fs";

const pkg = JSON.parse(readFileSync("./package.json", "utf-8"));

export default {
  input: "src/index.tsx",
  plugins: [
    commonjs(),
    nodeResolve(),
    typescript(),
    json(),
    replace({
      preventAssignment: true,
      "process.env.NODE_ENV": JSON.stringify("production"),
    }),
    importCss(),
  ],
  context: "window",
  external: ["react", "react-dom", "@decky/ui", "@decky/api"],
  output: {
    file: "dist/index.js",
    globals: {
      react: "SP_REACT",
      "react-dom": "SP_REACTDOM",
      "@decky/ui": "DFL",
      "@decky/api": "DECKY",
    },
    format: "iife",
    exports: "default",
    name: pkg.name,
  },
};
