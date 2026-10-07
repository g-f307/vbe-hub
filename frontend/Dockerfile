# syntax=docker/dockerfile:1.7

FROM node:20.19.4-bookworm-slim AS base

ENV NEXT_TELEMETRY_DISABLED=1 \
    PNPM_HOME=/pnpm \
    PATH=/pnpm:$PATH

RUN npm install --global pnpm@10.8.1 \
    && groupadd --gid 10002 app \
    && useradd --uid 10002 --gid app --create-home app

WORKDIR /app

FROM base AS dependencies

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

FROM dependencies AS development

COPY --chown=app:app . ./
RUN mkdir .next \
    && chown -R app:app /app/node_modules /app/.next

USER app

EXPOSE 3000

CMD ["pnpm", "dev", "--hostname", "0.0.0.0", "--port", "3000"]

FROM dependencies AS build

ARG NEXT_PUBLIC_VBE_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_VBE_API_URL=$NEXT_PUBLIC_VBE_API_URL

COPY . ./
RUN pnpm build

FROM base AS runtime

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

COPY --from=build --chown=app:app /app/public ./public
COPY --from=build --chown=app:app /app/.next/standalone ./
COPY --from=build --chown=app:app /app/.next/static ./.next/static

USER app

EXPOSE 3000

CMD ["node", "server.js"]
