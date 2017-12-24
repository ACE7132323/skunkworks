#!/usr/bin/env python3

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

# relative polygon co-ordinates
magics = {
    "top-left":     [(0.500, 0.183), (0.393, 0.445), (0.500, 0.538), (0.500, 0.183)],
    "top-right":    [(0.500, 0.183), (0.604, 0.445), (0.500, 0.538), (0.500, 0.183)],
    "bottom-left":  [(0.392, 0.472), (0.500, 0.567), (0.500, 0.697), (0.392, 0.472)],
    "bottom-right": [(0.605, 0.472), (0.500, 0.567), (0.500, 0.697), (0.605, 0.472)],
}

# mirror directions
mirrors = {
    "top-left":     "bottom-right",
    "top-right":    "bottom-left",
    "bottom-left":  "top-right",
    "bottom-right": "top-left",
}

WATERMARK = "ethwallpaper.co"
FONT = "Aquabase.ttf"
WATERMARK_OPACITY = 0.3
WATERMARK_RATIO = 40


def scale(magic, scale, width, height):
    """
    Used to convert an array of relative polygon co-ordinates into a absolute
    values by scaling it, given the width and the height of the image.

    :param magic:  relative polygon co-ordinates as an array of tuples
    :param scale:  a multiplier for the Ethereum logo
    :param width:  width of the image
    :param height: height of the image
    :return:       absolute polygon co-ordinates as an array of tuples
    """
    resized_magic = []
    for x, y in magic:
        dist = ((y - 0.5)**2 + (x - 0.5)**2)**0.5
        sin = (y - 0.5) / dist
        cos = (x - 0.5) / dist
        dist *= scale
        resized_magic.append((dist * cos + 0.5, dist * sin + 0.5))

    return [(x * width, y * height) for (x, y) in resized_magic]


def load_image(filename):
    """
    Loads an image and pre-processes it before embedding the logo.

    :param filename: the input file
    :return:         a PIL `Image`
    """
    im = Image.open(filename)
    width, height = im.size

    m = 1920.00 / 1266
    if width / height > m:
        diff = width - (m * height)
        im = im.crop((diff / 2, 0, m * height, height))
    else:
        diff = height - width / m
        im = im.crop((0, diff / 2, width, width / m))

    im.convert("RGB")
    return im


def draw_outline(im, magic):
    """
    Draw an outline of the Ethereum logo with a white-ish color.

    :param im:    the input PIL image
    :param magic: the current polygon being drawn
    """
    drw = ImageDraw.Draw(im, "RGBA")
    fill_color = (180, 180, 180, 255)

    for i in range(len(magic)):
        j = (i + 1) % len(magic)
        drw.line(
            (magic[i][0], magic[i][1], magic[j][0], magic[j][1]),
            fill=fill_color)

    del drw


def add_watermark(img):
    """
        Apply watermark to the wallpaper

        :[param img: Image to apply watermark to
    """

    watermark = Image.new('RGBA', img.size, (0, 0, 0, 0))
    size = int(watermark.size[0] / WATERMARK_RATIO)
    n_font = ImageFont.truetype(FONT, size)

    n_width, n_height = n_font.getsize(WATERMARK)

    draw = ImageDraw.Draw(watermark, 'RGBA')
    draw.text(((watermark.size[0] - n_width * 1.2),
              (watermark.size[1] - n_height * 1.2)),
              WATERMARK, font=n_font)

    alpha = watermark.split()[3]
    alpha = ImageEnhance.Brightness(alpha).enhance(WATERMARK_OPACITY)
    watermark.putalpha(alpha)
    return Image.composite(watermark, img, watermark)


def filter(v):
    """
    Applies a filter on a given pixel.

    :param v: the pixel to process
    :return:  the processed version of the pixel
    """
    limit = lambda x: int(min(x * 1.3, 255))
    return tuple([limit(x) for x in v])


def main(input_filename, output_filename, eth_scale=1):
    """
    Program main logic. Accepts an input file and produces output in another file.

    :param input_filename:  input file path
    :param output_filename: output file path
    :param eth_scale:       a multiplier for the Ethereum logo
    """
    im = load_image(input_filename)
    pixels = im.load()
    width, height = im.size

    for _, magic in magics.items():
        magics[_] = scale(magic, eth_scale, width, height)

    done, mul = 0, 1

    for _, magic in magics.items():
        # move pixels to each
        magic_polygon = Polygon(magic)
        (min_x, min_y, max_x, max_y) = magic_polygon.bounds
        todo = math.ceil(max_x) - math.floor(min_x)
        for x in range(math.floor(min_x), math.ceil(max_x)):
            for y in range(math.floor(min_y), math.ceil(max_y)):
                if magic_polygon.contains(Point(x, y)):
                    other = magics[mirrors[_]]
                    x_trans = int(other[0][0] - magic[0][0])
                    y_trans = int(other[0][1] - magic[0][1])
                    v = pixels[x + x_trans, y + y_trans]
                    pixels[x, y] = filter(v)

            # update progress to console
            done += 1
            if done == int(todo * mul / 10 * 4):
                sys.stdout.write("{}%... ".format(mul * 10))
                sys.stdout.flush()
                mul += 1

        draw_outline(im, magic)
    print("")
    add_watermark(im).save(output_filename)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("error: missing arguments")
        print("usage: ./main.py INPUT_IMAGE OUTPUT_IMAGE [ETH_SCALE]")
        sys.exit(0)

    if not os.path.isfile(sys.argv[1]):
        print("error: cannot open input file")
        sys.exit(0)

    if len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        main(sys.argv[1], sys.argv[2], float(sys.argv[3]))
