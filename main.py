import pygame
import pytmx

pygame.init()

WIDTH = 800
HEIGHT = 600

FPS = 60
PLAYER_SPEED = 5

WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Stardew KW")


tmx_data = pytmx.load_pygame("assets/maps/tileset/Aa main pack/world.tmx")

MAP_WIDTH = tmx_data.width * tmx_data.tilewidth
MAP_HEIGHT = tmx_data.height * tmx_data.tileheight


FRAME_WIDTH = 64
FRAME_HEIGHT = 64


def load_animation(path):

    sheet = pygame.image.load(path).convert_alpha()

    frames = []

    total_frames = sheet.get_width() // FRAME_WIDTH

    for i in range(total_frames):

        frame = sheet.subsurface(
            (
                i * FRAME_WIDTH,
                0,
                FRAME_WIDTH,
                FRAME_HEIGHT
            )
        )

        frames.append(frame)

    return frames


class Player:

    def __init__(self, x, y):

        self.x = x
        self.y = y

        self.speed = PLAYER_SPEED

        self.direction = "down"
        self.state = "idle"

        self.animations = {

            "idle_down": load_animation(
                "assets/sprites/player/Idle_Down-Sheet.png"
            ),

            "idle_up": load_animation(
                "assets/sprites/player/Idle_Up-Sheet.png"
            ),

            "idle_side": load_animation(
                "assets/sprites/player/Idle_Side-Sheet.png"
            ),

            "walk_down": load_animation(
                "assets/sprites/player/Walk_Down-Sheet.png"
            ),

            "walk_up": load_animation(
                "assets/sprites/player/Walk_Up-Sheet.png"
            ),

            "walk_side": load_animation(
                "assets/sprites/player/Walk_Side-Sheet.png"
            ),
        }

        self.frame_index = 0
        self.animation_speed = 0.15

        self.image = self.animations["idle_down"][0]

    def move(self, keys):

        moving = False

        if keys[pygame.K_a]:
            self.x -= self.speed
            self.direction = "left"
            moving = True

        if keys[pygame.K_d]:
            self.x += self.speed
            self.direction = "right"
            moving = True

        if keys[pygame.K_w]:
            self.y -= self.speed
            self.direction = "up"
            moving = True

        if keys[pygame.K_s]:
            self.y += self.speed
            self.direction = "down"
            moving = True

        if moving:
            self.state = "walk"
        else:
            self.state = "idle"

        # Batas map

        if self.x < 0:
            self.x = 0

        if self.y < 0:
            self.y = 0

        if self.x > MAP_WIDTH - FRAME_WIDTH:
            self.x = MAP_WIDTH - FRAME_WIDTH

        if self.y > MAP_HEIGHT - FRAME_HEIGHT:
            self.y = MAP_HEIGHT - FRAME_HEIGHT

    def animate(self):

        if self.direction in ["left", "right"]:
            key = f"{self.state}_side"
        else:
            key = f"{self.state}_{self.direction}"

        frames = self.animations[key]

        self.frame_index += self.animation_speed

        if self.frame_index >= len(frames):
            self.frame_index = 0

        self.image = frames[int(self.frame_index)]

    def update(self, keys):

        self.move(keys)
        self.animate()

    def draw(self, surface, camera_x, camera_y):

        image = self.image

        if self.direction == "left":
            image = pygame.transform.flip(
                image,
                True,
                False
            )

        surface.blit(
            image,
            (
                self.x - camera_x,
                self.y - camera_y
            )
        )


# =========================
# DRAW MAP
# =========================

def draw_map(surface, camera_x, camera_y):

    for layer in tmx_data.visible_layers:

        if isinstance(layer, pytmx.TiledTileLayer):

            for x, y, gid in layer:

                tile = tmx_data.get_tile_image_by_gid(gid)

                if tile:

                    surface.blit(
                        tile,
                        (
                            x * tmx_data.tilewidth - camera_x,
                            y * tmx_data.tileheight - camera_y
                        )
                    )

def main():

    clock = pygame.time.Clock()

    player = Player(
        MAP_WIDTH // 2,
        MAP_HEIGHT // 2
    )

    run = True

    while run:

        clock.tick(FPS)

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                run = False

        keys = pygame.key.get_pressed()

        player.update(keys)




        camera_x = player.x - WIDTH // 2
        camera_y = player.y - HEIGHT // 2

        camera_x = max(
            0,
            min(camera_x, MAP_WIDTH - WIDTH)
        )

        camera_y = max(
            0,
            min(camera_y, MAP_HEIGHT - HEIGHT)
        )


        WIN.fill((0, 0, 0))

        draw_map(
            WIN,
            camera_x,
            camera_y
        )

        player.draw(
            WIN,
            camera_x,
            camera_y
        )

        pygame.display.update()

    pygame.quit()


if __name__ == "__main__":
    main()