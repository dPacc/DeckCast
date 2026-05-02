import commonjs from "@rollup/plugin-commonjs";
import json from "@rollup/plugin-json";
import { nodeResolve } from "@rollup/plugin-node-resolve";
import replace from "@rollup/plugin-replace";
import typescript from "@rollup/plugin-typescript";
import externalGlobals from "rollup-plugin-external-globals";
import importCss from "rollup-plugin-import-css";

import { readFileSync } from "fs";

const manifest = readFileSync("./plugin.json", "utf-8");

const deckyManifestPlugin = {
  name: "decky-manifest",
  resolveId(source) {
    if (source === "@decky/manifest") return "\0@decky/manifest";
    return null;
  },
  load(id) {
    if (id === "\0@decky/manifest") return `export default ${manifest};`;
    return null;
  },
};

export default {
  input: "src/index.tsx",
  plugins: [
    deckyManifestPlugin,
    commonjs(),
    nodeResolve({ browser: true }),
    typescript(),
    json(),
    replace({
      preventAssignment: false,
      "process.env.NODE_ENV": JSON.stringify("production"),
    }),
    importCss(),
    externalGlobals({
      react: "SP_REACT",
      "react-dom": "SP_REACTDOM",
      "@decky/ui": "DFL",
    }),
  ],
  context: "window",
  external: ["react", "react-dom", "@decky/ui"],
  output: {
    file: "dist/index.js",
    format: "esm",
    exports: "default",
  },
};
