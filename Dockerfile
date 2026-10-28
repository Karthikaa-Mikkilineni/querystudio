FROM node:22-bookworm-slim AS web
WORKDIR /web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS api
WORKDIR /src
COPY api/ ./
RUN dotnet publish -c Release -o /out
FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=api /out ./
COPY --from=web /web/dist/askdb/browser ./wwwroot
ENV ASPNETCORE_HTTP_PORTS=8080
RUN mkdir -p /app/workspace && chown -R $APP_UID:$APP_UID /app/workspace
USER $APP_UID
EXPOSE 8080
ENTRYPOINT ["dotnet","AskDb.Api.dll"]
