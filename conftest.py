# Fichier vide, mais necessaire : sa seule presence a la racine du projet
# indique a pytest d'ajouter ce dossier au sys.path, ce qui permet aux tests
# (dans tests/) d'importer directement `domain`, `services`, `repositories`
# comme le fait l'application elle-meme (`import domain.models`, etc.),
# sans avoir a installer le projet comme un package.
