import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: dirname(fileURLToPath(import.meta.url)) });

export default [
  { ignores: [".next/**", "node_modules/**"] },
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  // Avatars are small user uploads served from the API host, which differs per
  // environment — next/image would need every host whitelisted for no real gain.
  { files: ["app/account.tsx"], rules: { "@next/next/no-img-element": "off" } },
];
