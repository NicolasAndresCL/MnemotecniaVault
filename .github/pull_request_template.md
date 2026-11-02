## Qué cambia y por qué

## Tipo
- [ ] Repaso / FSRS / técnicas mnemotécnicas
- [ ] Importadores (vault, CmdVault, proyectos)
- [ ] UI / temas
- [ ] Infra (Docker / CI / Kubernetes / Jenkins)
- [ ] Documentación

## Verificación
- [ ] `./scripts/verificar.sh` en verde (clon limpio de HEAD: lint + tests + Postgres + build + smoke)
- [ ] Probado en el navegador (`docker compose up -d --build --wait`, y `docker compose down` al terminar)
- [ ] README / CHANGELOG actualizados (versión en `pyproject.toml`, `app/__init__.py`, README y `k8s/kustomization.yaml`)
