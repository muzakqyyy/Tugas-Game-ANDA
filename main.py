import sys
import pygame
import pytmx

pygame.init()

# =========================
# SETTING
# =========================

WIDTH = 800
HEIGHT = 600

FPS = 60
PLAYER_SPEED = 5

WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Stardew KW")

# =========================
# LOAD MAP
# =========================

MAP_PATH = "assets/maps/tileset/Aa main pack/world.tmx"

try:
    tmx_data = pytmx.load_pygame(MAP_PATH)
except Exception as e:
    # Perubahan: jika file map gagal dimuat, hentikan dengan pesan jelas,
    # daripada membiarkan traceback panjang yang membingungkan.
    print(f"Gagal memuat map '{MAP_PATH}': {e}")
    pygame.quit()
    sys.exit(1)

MAP_WIDTH = tmx_data.width * tmx_data.tilewidth
MAP_HEIGHT = tmx_data.height * tmx_data.tileheight

# =========================
# COLLISION OBJECTS
# =========================

collision_rects = []

try:
    collision_layer = tmx_data.get_layer_by_name("Collision")

    for obj in collision_layer:

        if obj.width and obj.height:
            # Object berbentuk rectangle
            rect = pygame.Rect(obj.x, obj.y, obj.width, obj.height)

        elif getattr(obj, "points", None):
            # Object berbentuk polygon/polyline -> dipakai bounding box-nya
            xs = [p[0] for p in obj.points]
            ys = [p[1] for p in obj.points]

            rect = pygame.Rect(
                min(xs),
                min(ys),
                max(xs) - min(xs),
                max(ys) - min(ys)
            )

        else:
            continue

        collision_rects.append(rect)

except Exception as e:
    print(f"Layer Collision tidak ditemukan! ({e})")


# =========================
# LOAD ANIMATION
# =========================

def load_animation(path):
    """Memuat spritesheet dan memotongnya menjadi list frame.

    Perubahan: dibungkus try/except. Jika file sprite tidak ditemukan
    atau gagal dibaca, game tidak langsung crash, melainkan memakai
    placeholder berwarna magenta agar mudah dideteksi secara visual
    aset mana yang bermasalah.
    """
    try:
        sheet = pygame.image.load(path).convert_alpha()
    except (pygame.error, FileNotFoundError) as e:
        print(f"Gagal memuat sprite '{path}': {e}")
        placeholder = pygame.Surface((FRAME_WIDTH, FRAME_HEIGHT), pygame.SRCALPHA)
        placeholder.fill((255, 0, 255, 255))
        return [placeholder]

    frames = []
    total_frames = sheet.get_width() // FRAME_WIDTH

    # Perubahan: batasi tinggi potongan ke tinggi asli sheet supaya tidak
    # memicu "pygame.error: subsurface rectangle outside surface area"
    # jika sheet lebih pendek dari FRAME_HEIGHT.
    usable_height = min(FRAME_HEIGHT, sheet.get_height())

    for i in range(total_frames):
        frame = sheet.subsurface((
            i * FRAME_WIDTH,
            0,
            FRAME_WIDTH,
            usable_height
        ))
        frames.append(frame)

    if not frames:
        placeholder = pygame.Surface((FRAME_WIDTH, FRAME_HEIGHT), pygame.SRCALPHA)
        placeholder.fill((255, 0, 255, 255))
        frames.append(placeholder)

    return frames


# =========================
# PLAYER
# =========================

class Player:

    def __init__(self, x, y):

        # Perubahan: simpan posisi sebagai float karena perhitungan
        # gerakan sekarang berbasis delta-time (bisa pecahan piksel).
        self.x = float(x)
        self.y = float(y)

        self.speed = PLAYER_SPEED  # pixel per detik

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
            )
        }

        # Perubahan: pre-compute versi mirror (flip horizontal) dari
        # animasi "_side" sekali saja di awal. Sebelumnya draw() memanggil
        # pygame.transform.flip() setiap frame, yang membuat Surface baru
        # terus-menerus dan membebani performa.
        self.flipped_animations = {
            key: [pygame.transform.flip(frame, True, False) for frame in frames]
            for key, frames in self.animations.items()
            if key.endswith("_side")
        }

        self.frame_index = 0.0

        # Perubahan: satuan animation_speed sekarang "frame per detik"
        # (9 setara dengan 0.15 per frame pada 60 FPS) agar konsisten
        # dengan perhitungan delta-time.
        self.animation_speed = 9.0

        self.image = self.animations["idle_down"][0]

    def get_hitbox(self, x=None, y=None):

        if x is None:
            x = self.x

        if y is None:
            y = self.y

        # Perubahan: cast ke int karena pygame.Rect butuh koordinat
        # integer, sedangkan self.x/self.y sekarang bertipe float.
        return pygame.Rect(
            int(x) + 18,
            int(y) + 40,
            28,
            20
        )

    def _is_blocked(self, x, y):
        """Perubahan: helper terpisah + collidelist().

        collidelist() berjalan di level C dan jauh lebih cepat
        dibanding loop manual colliderect() per rect, terutama
        jika jumlah collision_rects besar.
        """
        hitbox = self.get_hitbox(x, y)
        return hitbox.collidelist(collision_rects) != -1

    def move(self, keys, dt):

        dx = 0
        dy = 0

        moving = False

        if keys[pygame.K_a]:
            dx -= 1
            self.direction = "left"
            moving = True

        if keys[pygame.K_d]:
            dx += 1
            self.direction = "right"
            moving = True

        if keys[pygame.K_w]:
            dy -= 1
            self.direction = "up"
            moving = True

        if keys[pygame.K_s]:
            dy += 1
            self.direction = "down"
            moving = True

        self.state = "walk" if moving else "idle"

        # Perubahan: normalisasi vektor gerak diagonal.
        # Sebelumnya, menekan dua tombol arah sekaligus (misal W+D)
        # membuat dx dan dy masing-masing penuh -> magnitude gerak
        # menjadi sqrt(2) * speed (lebih cepat dari gerak lurus).
        # Setelah normalisasi, kecepatan total tetap "speed" ke segala arah.
        # Catatan: jika A+D atau W+S ditekan bersamaan, dx/dy akan
        # saling membatalkan menjadi 0 -> karakter diam (lebih intuitif
        # dibanding sebelumnya, yang selalu mengikuti tombol terakhir).
        if dx != 0 and dy != 0:
            norm = (dx * dx + dy * dy) ** 0.5
            dx /= norm
            dy /= norm

        # Perubahan: kalikan dengan dt agar gerakan frame-rate independent.
        dx *= self.speed * dt
        dy *= self.speed * dt

        # =====================
        # HORIZONTAL COLLISION
        # =====================
        if not self._is_blocked(self.x + dx, self.y):
            self.x += dx

        # =====================
        # VERTICAL COLLISION
        # =====================
        if not self._is_blocked(self.x, self.y + dy):
            self.y += dy

        # =====================
        # MAP BOUNDARY
        # =====================
        self.x = max(0.0, min(self.x, MAP_WIDTH - FRAME_WIDTH))
        self.y = max(0.0, min(self.y, MAP_HEIGHT - FRAME_HEIGHT))

    def animate(self, dt):

        if self.direction in ("left", "right"):
            key = f"{self.state}_side"
        else:
            key = f"{self.state}_{self.direction}"

        frames = self.animations[key]

        # Perubahan: increment berbasis dt, bukan angka tetap per frame.
        self.frame_index += self.animation_speed * dt

        if self.frame_index >= len(frames):
            self.frame_index = 0.0

        frame_idx = int(self.frame_index)

        if self.direction == "left":
            # Perubahan: ambil dari cache flipped_animations,
            # bukan flip() on-the-fly seperti sebelumnya di draw().
            self.image = self.flipped_animations[key][frame_idx]
        else:
            self.image = frames[frame_idx]

    def update(self, keys, dt):
        self.move(keys, dt)
        self.animate(dt)

    def draw(self, surface, camera_x, camera_y):
        # Perubahan: logika flip dipindah ke animate()/cache, jadi di sini
        # cukup blit self.image langsung. Posisi di-cast ke int untuk blit.
        surface.blit(
            self.image,
            (
                int(self.x - camera_x),
                int(self.y - camera_y)
            )
        )


# =========================
# DRAW MAP
# =========================

def draw_map(surface, camera_x, camera_y):

    for layer in tmx_data.visible_layers:

        if isinstance(layer, pytmx.TiledTileLayer):

            # Perubahan: viewport culling — hanya hitung & gambar tile
            # yang berada di area yang terlihat di layar, bukan seluruh
            # map setiap frame. Ini krusial untuk performa pada map besar.
            start_col = max(0, camera_x // tmx_data.tilewidth)
            end_col = min(
                layer.width,
                (camera_x + WIDTH) // tmx_data.tilewidth + 1
            )

            start_row = max(0, camera_y // tmx_data.tileheight)
            end_row = min(
                layer.height,
                (camera_y + HEIGHT) // tmx_data.tileheight + 1
            )

            for y in range(start_row, end_row):
                for x in range(start_col, end_col):

                    gid = layer.data[y][x]
                    tile = tmx_data.get_tile_image_by_gid(gid)

                    if tile:
                        surface.blit(
                            tile,
                            (
                                x * tmx_data.tilewidth - camera_x,
                                y * tmx_data.tileheight - camera_y
                            )
                        )


# =========================
# MAIN
# =========================

def main():

    clock = pygame.time.Clock()

    player = Player(
        MAP_WIDTH // 2,
        MAP_HEIGHT // 2
    )

    run = True

    while run:

        # Perubahan: dt (delta time) dalam detik, dipakai untuk gerakan
        # dan animasi agar frame-rate independent.
        dt = clock.tick(FPS) / 1000

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                run = False

            # Perubahan: tombol ESC untuk keluar dari game.
            # Sebelumnya tidak ada cara keluar selain menutup window,
            # yang merepotkan terutama jika dijalankan fullscreen.
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                run = False

        keys = pygame.key.get_pressed()

        player.update(keys, dt)

        # Perubahan: kamera mengikuti TITIK TENGAH sprite player
        # (bukan pojok kiri-atas), supaya player terlihat lebih presisi
        # di tengah layar.
        center_x = player.x + FRAME_WIDTH / 2
        center_y = player.y + FRAME_HEIGHT / 2

        camera_x = int(center_x - WIDTH / 2)
        camera_y = int(center_y - HEIGHT / 2)

        # Perubahan: tambahkan max(0, ...) pada batas atas agar tidak
        # menghasilkan rentang clamp negatif jika map lebih kecil dari
        # layar (MAP_WIDTH < WIDTH atau MAP_HEIGHT < HEIGHT).
        camera_x = max(0, min(camera_x, max(0, MAP_WIDTH - WIDTH)))
        camera_y = max(0, min(camera_y, max(0, MAP_HEIGHT - HEIGHT)))

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

        # =====================
        # DEBUG COLLISION
        # =====================

        for rect in collision_rects:

            pygame.draw.rect(
                WIN,
                (255, 0, 0),
                (
                    rect.x - camera_x,
                    rect.y - camera_y,
                    rect.width,
                    rect.height
                ),
                2
            )

        pygame.display.update()

    pygame.quit()


if __name__ == "__main__":
    main()