# Subir este proyecto a GitHub

Ya está todo commiteado localmente. Para publicarlo:

## Opción A — con GitHub CLI (`gh`), si lo tenés instalado y logueado

```bash
cd marketpulse-ecommerce-analytics
gh repo create marketpulse-ecommerce-analytics --public --source=. --remote=origin --push
```

Eso crea el repo en tu cuenta, lo conecta como remoto y sube todo en un solo paso.

## Opción B — manual, desde la web de GitHub

1. Entrá a https://github.com/new
2. Nombre del repo: `marketpulse-ecommerce-analytics` (o el que prefieras)
3. Público, sin agregar README/gitignore/license (ya los tenemos localmente)
4. Click en "Create repository"
5. Copiá la URL que te da (algo como `https://github.com/TU_USUARIO/marketpulse-ecommerce-analytics.git`)
6. Corré:

```bash
cd marketpulse-ecommerce-analytics
git remote add origin https://github.com/TU_USUARIO/marketpulse-ecommerce-analytics.git
git branch -M main
git push -u origin main
```

## Después de subirlo

- Verificá que el notebook (`notebook/analysis.ipynb`) se renderiza bien en la
  página del repo — GitHub muestra los gráficos automáticamente si el notebook
  tiene los outputs guardados (ya los tiene).
- Opcional: agregá el link del repo a tu perfil de LinkedIn (sección
  "Proyectos destacados" / Featured).

Los borradores del post de LinkedIn viven aparte, en el workspace privado de
búsqueda laboral (`documents/marketpulse_linkedin_posts.md`), no en este repo
público.
