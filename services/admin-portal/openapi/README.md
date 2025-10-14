# OpenAPI assets

`OpenAPI.yaml` is the single source of truth for the AstraDesk Admin API. Regenerate typed clients and guards after every change.

```
npm run openapi:gen
```

> The current script is a placeholder. Integrate your preferred OpenAPI generator (e.g. `@hey-api/openapi-ts`, `openapi-typescript-codegen`, or `openapi-generator-cli`) and ensure the output overwrites:
>
> - `openapi/openapi-types.d.ts`
> - `openapi/openapi-client.ts`
> - `openapi/paths-map.ts`

Run the sync check in CI/local to detect stale artifacts:

```
npm run openapi:check
```
