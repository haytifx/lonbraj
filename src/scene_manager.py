"""
scene_manager.py
----------------
Gere quelle "scene" est active en ce moment (splash screen, menu,
cinematique, niveau jouable...) et comment on passe de l'une a l'autre.

Chaque scene (dans src/scenes/) est une classe independante avec 3
methodes : handle_event(), update(), draw(). Le SceneManager ne fait
que deleguer a la scene active -- il ne connait pas les details internes
de chaque scene. Ca veut dire que tu peux ajouter/modifier une scene sans
toucher aux autres.
"""


class SceneManager:
    def __init__(self):
        self.current_scene = None

    def set_scene(self, scene):
        self.current_scene = scene

    def handle_event(self, event):
        if self.current_scene:
            self.current_scene.handle_event(event)

    def update(self, dt):
        if self.current_scene:
            self.current_scene.update(dt)

    def draw(self, surface):
        if self.current_scene:
            self.current_scene.draw(surface)


# Instance unique partagee par tout le jeu
scene_manager = SceneManager()
