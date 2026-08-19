Convenciones de Git

Ramas: main (estable) → develop (integración) → feature/x-microservicio (trabajo individual)
Flujo: cada persona trabaja en su rama feature/, y hace Pull Request hacia develop cuando su parte funciona.
En los commits pueden usar prefijos como por ejemplo (si lo desean):
feat: agrega endpoint de ingesta
fix: corrige cálculo de pendiente
docs: actualiza README del worker predictivo
