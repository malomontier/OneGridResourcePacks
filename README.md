# OneGrid HUD

Pack de ressources officiel du serveur OneGrid pour Minecraft Java 26.1.

Il fournit uniquement la couche visuelle du HUD : panneaux gris translucides, icones pixel-art et espacements precis. Les valeurs restent calculees par les plugins OneGrid et les libelles conservent la police UI du serveur.

Les panneaux suivent le cadre OneGrid conserve dans `sources/hud_panel_reference.png` : interieur `#353535` a 45 % d'opacite, bord `#484848` a 25 % d'opacite et coins pixel-art decales. Le pack encode ces valeurs en RGBA (`#35353573` et `#48484840`) sans ajouter de teinte, de degrade ou d'ombre. La reference 210x30 est reproduite sur sa grille native 105x15, puis declinee selon la largeur du contenu.

## Principes

- aucun remplacement global de la police Minecraft ;
- aucun changement des couleurs OneGrid ;
- seule la BossBar blanche, reservee au HUD, devient transparente ;
- les BossBars rouges et colorees des combats restent vanilla ;
- archive reproductible, epinglee a la version de pack 84 de Minecraft 26.1.

## Construire

```powershell
python scripts/build_pack.py
python scripts/validate_pack.py
```

L'archive produite est `onegrid-hud.zip`. Les sources se trouvent dans `pack/`, `sources/` et `scripts/` : l'archive n'est plus l'unique source du projet.

## Integration serveur

Le serveur distribue une URL HTTPS epinglee sur un commit et verifie le SHA-1 attendu par le protocole Minecraft. Le pack est requis, car sans ses glyphes les panneaux du HUD ne peuvent pas etre rendus correctement.
