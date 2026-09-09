# Publicação do Backend LiDAR — lidar.hankell.com.br
# Gerado por Hermes Agent · 2026-09-08

O backend FastAPI já está rodando e saudável na porta 8901 do container Hermes:
- Health:  http://localhost:8901/health  -> {"status":"ok"}
- Swagger: http://localhost:8901/docs    -> HTTP 200
- Um watchdog (2 min, sem agente) o reinicia caso caia (incl. após redeploys do Portainer).

## O que VOCÊ precisa fazer (eu não tenho acesso ao stack/Traefik/firewall do host)

### 1) Label do Traefik — adicionar dentro de `deploy.labels:` do serviço `hermes` no stack YAML

Copie e adicione ESTE bloco à lista `deploy.labels` do serviço `hermes` (perto dos blocos
existentes `ha`, `files`, `silvalab`):

```yaml
        - traefik.http.routers.lidar.rule=Host(`lidar.hankell.com.br`)
        - traefik.http.routers.lidar.entrypoints=websecure
        - traefik.http.routers.lidar.priority=2
        - traefik.http.routers.lidar.tls.certresolver=letsencryptresolver
        - traefik.http.routers.lidar.service=lidar
        - traefik.http.services.lidar.loadbalancer.server.port=8901
        - traefik.http.routers.lidar.middlewares=hermes-ratelimit@swarm,hermes-sec@swarm
```

⚠️ IMPORTANTE no modo Swarm: o bloco deve estar sob `deploy.labels:`, NÃO sob `labels:`
(labels "planas" de topo são ignoradas no modo swarm).

### 2) Registro DNS

No painel da Hostinger (hPanel), crie um registro **A** (ou CNAME) para o subdomínio:
   - Nome:  lidar
   - Tipo:  A
   - Valor: 147.93.46.119
   (ou CNAME para o host `vps` se os outros subdomínios usam CNAME)

### 3) Aplicar o stack no Portainer

- Abra o stack `hermes` no Portainer e clique em **Update / Redeploy**.
- O certificado TLS (Let's Encrypt) é emitido automaticamente em ~1 min.

## Verificação após o deploy

De QUALQUER lugar:
```bash
curl -sk https://lidar.hankell.com.br/health      # -> {"status":"ok"}  = exposto OK
curl -sk https://lidar.hankell.com.br/docs        # Swagger UI acessível publicamente
```
- **`404`** = Traefik up mas o router não carregou (labels não aplicadas / redeploy não feito).
- **`000`/timeout** = TLS ainda emitindo ou DNS/firewall.
- Se o backend não responder: o watchdog reinicia em ~2 min; confira `logs_uvicorn_8901.log`.

## Arquivos salvos no FileBrowser (Inbox) — verificados por hash
- `drive.hankell.com.br` → `/Inbox/REPORT.md`
- `drive.hankell.com.br` → `/Inbox/PROGRESS.md`